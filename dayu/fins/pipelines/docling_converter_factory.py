"""集中 Fins 默认转换器的管理员配置装配，不产生部署默认值。"""

from __future__ import annotations

import os
from pathlib import Path

from dayu.documents.xbrl_config import XbrlConfigurationError, load_xbrl_conversion_config
from dayu.fins.pipelines.docling_process_converter import (
    DoclingConversionError,
    DoclingConversionFailureKind,
    DoclingConverter,
    ProcessDoclingConverter,
)
from dayu.fins.pipelines.pypdf_converter import PypdfFallbackConverter

_XBRL_CONFIG_ENV = "DAYU_XBRL_CONFIG"
_BACKEND_ENV = "DAYU_FINS_CONVERTER"
_BACKEND_PYPDF = "pypdf"
_BACKEND_DOCLING = "docling"


def create_docling_converter(workspace_root: Path) -> DoclingConverter:
    """参数：禁止管理员输入进入的工作区；返回：显式配置转换器；异常：坏配置抛 construction 错误。

    转换后端由环境变量 ``DAYU_FINS_CONVERTER`` 选择：

    - ``docling``（默认）：上游的 ``ProcessDoclingConverter`` 子进程实现，
      契约与行为完全不变，需要完整的 Docling ML 依赖。
    - ``pypdf``：pdf-inspector / poppler / pypdf 纯解析链路，不加载
      PyTorch 与 transformers，适用于低内存主机。该后端不消费 XBRL
      配置，因此 ``DAYU_XBRL_CONFIG`` 在 pypdf 模式下不参与装配。

    :param workspace_root: 工作区根目录，用于解析默认 XBRL 配置。
    :returns: 选定后端对应的转换器实例。
    :raises DoclingConversionError: 后端取值非法或 XBRL 配置损坏时抛出。
    """
    backend = os.environ.get(_BACKEND_ENV, _BACKEND_DOCLING).strip().lower()
    if backend == _BACKEND_PYPDF:
        return PypdfFallbackConverter()
    if backend != _BACKEND_DOCLING:
        raise DoclingConversionError(
            DoclingConversionFailureKind.CONVERTER_CONSTRUCTION,
            "Docling converter construction failed",
            None,
        )
    raw = os.environ.get(_XBRL_CONFIG_ENV)
    try:
        if raw is not None and not raw:
            raise XbrlConfigurationError("显式 XBRL 配置路径不能为空")
        config = load_xbrl_conversion_config(Path(raw) if raw is not None else None, workspace_root)
    except XbrlConfigurationError as exc:
        raise DoclingConversionError(
            DoclingConversionFailureKind.CONVERTER_CONSTRUCTION,
            "Docling converter construction failed",
            None,
        ) from exc
    return ProcessDoclingConverter(xbrl_config=config)
