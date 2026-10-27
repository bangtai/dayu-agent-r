"""基于 pdf-inspector / pypdf / poppler 的 Docling 替代转换器。

本模块提供一个满足 :class:`DoclingConverter` 协议的实现，用纯 Python/Rust
的 PDF 解析链路替代 Docling 的 PyTorch + transformers 推理流水线。

适用场景
--------
低内存主机（实测 1.6GB）上 Docling 单次转换常驻 900MB~1GB，会被内核 OOM
杀死。本转换器不加载任何 ML 依赖，单份港股招股书（9MB / 500 页）约 27 秒
完成，峰值内存仅数百 MB。

产出契约
--------
产出与 Docling 相同的 ``DoclingDocument`` JSON 字典（``schema_name`` /
``body`` / ``groups`` / ``texts`` / ``pictures``），下游 ``DoclingProcessor``
无需任何改动即可消费。
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Final

from dayu.contracts.cancellation import CancellationToken
from dayu.docling_fallback import convert_pdf_bytes_to_docling_json_bytes
from dayu.fins.pipelines.docling_process_converter import (
    DoclingConversionCancelledError,
    DoclingConversionConfig,
    DoclingConversionError,
    DoclingConversionFailureKind,
    DoclingConversionResult,
    _SAFE_FAILURE_MESSAGES,
    _validate_conversion_request,
)
from dayu.log import Log

_MODULE: Final[str] = "FINS.PYPDF_CONVERTER"

# 转换失败统一映射为执行失败种类；消息必须是契约内固定文本。
_EXECUTION_FAILURE_MESSAGE: Final[str] = _SAFE_FAILURE_MESSAGES[
    DoclingConversionFailureKind.CONVERTER_EXECUTION
]


class PypdfFallbackConverter:
    """用 pdf-inspector / poppler / pypdf 替代 Docling ML 流水线的转换器。

    与 :class:`~dayu.fins.pipelines.docling_process_converter.ProcessDoclingConverter`
    的差异：
    - 不启动子进程、不写临时目录，转换在调用进程内完成；
    - 不加载 PyTorch / transformers，低内存主机可稳定运行；
    - 产出的 ``DoclingDocument`` 同样通过 ``docling_core`` 序列化，
      下游消费方无感知。

    保持不变的部分：输入校验、取消观察、结果的非负长度与 SHA-256
    自洽性均由 :class:`DoclingConversionResult` 构造期复核。
    """

    def __init__(self) -> None:
        """参数：无；返回：无；异常：本构造不抛出异常。"""

    async def convert_to_json_bytes(
        self,
        input_bytes: bytes,
        stream_name: str,
        *,
        config: DoclingConversionConfig,
        cancellation: CancellationToken | None,
    ) -> DoclingConversionResult:
        """把 PDF 字节转换为完成校验的 Docling JSON。

        :param input_bytes: 不可变原始文档字节。
        :param stream_name: 输入名，用于保留扩展名与日志标识。
        :param config: 闭合转换配置；本实现不支持 OCR 与表格结构开关，
            一律按文本层 + 表格启发式提取处理，配置仅参与合法性校验。
        :param cancellation: 公共取消观察 token；``None`` 表示无取消源。
        :returns: 长度与 SHA-256 自洽的 JSON 结果。
        :raises ValueError: 输入、名称或配置非法时抛出。
        :raises DoclingConversionCancelledError: 请求取消时抛出。
        :raises DoclingConversionError: 转换执行失败时抛出。
        """

        _validate_conversion_request(input_bytes, stream_name, config)
        if cancellation is not None and cancellation.is_cancelled():
            raise DoclingConversionCancelledError()

        Log.info(
            f"pypdf 降级转换开始: {stream_name} ({len(input_bytes)} bytes)",
            module=_MODULE,
        )

        # 提取是 CPU 密集操作（单份 500 页约 27 秒），放到工作线程执行，
        # 避免阻塞事件循环导致同一进程内其他协程停摆。
        try:
            json_bytes = await asyncio.to_thread(
                convert_pdf_bytes_to_docling_json_bytes,
                input_bytes,
                stream_name,
            )
        except asyncio.CancelledError:
            # 外层 task 取消：to_thread 无法中断线程，但结果会被丢弃。
            raise
        except Exception as exc:  # noqa: BLE001 - 统一映射为契约内失败种类
            Log.warning(
                f"pypdf 降级转换失败: {stream_name} "
                f"({type(exc).__name__}: {exc})",
                module=_MODULE,
            )
            raise DoclingConversionError(
                DoclingConversionFailureKind.CONVERTER_EXECUTION,
                _EXECUTION_FAILURE_MESSAGE,
                None,
            ) from exc

        if cancellation is not None and cancellation.is_cancelled():
            raise DoclingConversionCancelledError()

        result = DoclingConversionResult(
            json_bytes=json_bytes,
            size=len(json_bytes),
            sha256=hashlib.sha256(json_bytes).hexdigest(),
        )
        Log.info(
            f"pypdf 降级转换完成: {stream_name} ({result.size} bytes)",
            module=_MODULE,
        )
        return result
