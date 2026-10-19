"""Fins 的隔离窄页提取调用与取消 owner；复用公共可中断进程，不承载原生对象。"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from dayu.contracts.json_value import JsonValue
from dayu.fins.download_contract import FinsDownloadProviderError, FinsDownloadSource, FinsDownloadTransportCategory
from dayu.documents.pdf_text_worker import PdfTextWorker
from dayu.fins.pipelines.cn_download_owned_task import await_owned_task
from dayu.runtime.interruptible_process import (
    InterruptibleProcessHandle, InterruptibleProcessCompleted, InterruptibleProcessFailed,
)

HK_BODY_PAGE_LIMIT = 3
_POLL_SECONDS = 0.02
_CLOSE_GRACE_SECONDS = 0.5
_INPUT_PREFIX = "dayu-hk-body-"
_INPUT_FILENAME = "input.pdf"
_NO_PROCESS_RESULT_ERROR = "process_exited_without_result"
ExtractionFailure = Literal["startup", "result", "crash", "input", "import", "native", "ipc", "close", "cleanup"]


_FAILURE_MESSAGES: dict[ExtractionFailure, str] = {
    "crash": "港股报告正文提取进程异常退出", "startup": "港股报告正文提取未能启动", "result": "港股报告正文提取未正常完成",
    "input": "港股报告原件交接读取失败", "import": "港股报告正文提取组件不可用", "native": "港股报告原件文本读取失败",
    "ipc": "港股报告正文提取结果校验失败", "close": "港股报告原件读取资源关闭失败",
    "cleanup": "港股报告正文提取进程回收失败",
}


class HkBodyExtractionError(FinsDownloadProviderError):
    """提取执行失败，和正文不支持的 unknown 分离。"""

    def __init__(self, reason: ExtractionFailure, detail: str) -> None:
        """保存 typed 原因。参数：reason/detail 为阶段及原错。返回：无。异常：无。"""
        self.reason = reason
        self.detail = detail
        super().__init__(source=FinsDownloadSource.HKEXNEWS, transport_category=FinsDownloadTransportCategory.PROTOCOL,
                         retryable=False, safe_message=_FAILURE_MESSAGES[reason])


@dataclass(frozen=True, slots=True)
class HkExtractedPages:
    """父侧已核验协议及原件摘要的窄提取结果。"""

    pages: tuple[str, ...]
    sha256: str
    worker_pid: int
    worker_thread: int


def _checkpoint(checkpoint: Callable[[], None] | None) -> None:
    """观察 Host 取消。参数：checkpoint 为上层控制点。返回：无。异常：取消原样透传。"""
    if checkpoint is not None:
        checkpoint()


def _decode(value: JsonValue, pdf_bytes: bytes) -> HkExtractedPages:
    """校验 IPC。参数：value/bytes 为消息及输入。返回：窄结果。异常：ExtractionError。"""
    if not isinstance(value, dict) or value.get("protocol") != "pdf-text-v1":
        raise HkBodyExtractionError("ipc", "invalid protocol")
    if "error" in value:
        stage = value.get("error")
        if stage not in ("input", "import", "native", "close"):
            raise HkBodyExtractionError("ipc", "invalid worker failure stage")
        raise HkBodyExtractionError(stage, f"{value.get('error_type')}: {value.get('message')}")
    pages, digest, pid, thread = value.get("pages"), value.get("sha256"), value.get("pid"), value.get("thread")
    if (not isinstance(pages, list) or not all(isinstance(p, str) for p in pages)
        or len(pages) > HK_BODY_PAGE_LIMIT or not isinstance(digest, str) or digest != hashlib.sha256(pdf_bytes).hexdigest()
        or type(pid) is not int or type(thread) is not int):
        raise HkBodyExtractionError("ipc", "invalid pages, digest or worker identity")
    return HkExtractedPages(tuple(p for p in pages if isinstance(p, str)), digest, pid, thread)


async def extract_hk_pages_async(pdf_bytes: bytes, checkpoint: Callable[[], None] | None) -> HkExtractedPages:
    """执行单请求 spawn 并在所有路径回收。

    参数：pdf_bytes 为实际原件；checkpoint 为 Host 取消观察。
    返回：已校验页文本。异常：取消原样传播；执行/协议/回收错误为 ExtractionError。
    """
    _checkpoint(checkpoint)
    directory, target = _prepare_worker_input(pdf_bytes)
    handle: InterruptibleProcessHandle | None = None
    decoded: HkExtractedPages | None = None
    primary_error: BaseException | None = None
    try:
        try:
            handle = InterruptibleProcessHandle(target)
        except Exception as exc:
            raise HkBodyExtractionError("startup", str(exc)) from exc
        _checkpoint(checkpoint)
        try:
            handle.start()
        except Exception as exc:
            raise HkBodyExtractionError("startup", str(exc)) from exc
        while True:
            _checkpoint(checkpoint)
            try:
                result = await handle.wait(_POLL_SECONDS)
            except Exception as exc:
                raise HkBodyExtractionError("result", str(exc)) from exc
            _checkpoint(checkpoint)
            if isinstance(result, InterruptibleProcessFailed):
                raise HkBodyExtractionError("crash" if result.error_type == _NO_PROCESS_RESULT_ERROR else "result", f"{result.error_type}: {result.message}; exit={result.exitcode}")
            if isinstance(result, InterruptibleProcessCompleted):
                decoded = _decode(result.value, pdf_bytes)
                _checkpoint(checkpoint)
                break
    except BaseException as exc:
        primary_error = exc
    finally:
        cleanup_error: BaseException | None = None
        try:
            if handle is not None:
                await _close_extraction_handle(handle)
        except BaseException as exc:
            cleanup_error = exc
        try:
            _cleanup_worker_input(directory)
        except BaseException as exc:
            if cleanup_error is not None:
                exc.__cause__ = cleanup_error
            cleanup_error = exc
        if primary_error is not None:
            raise primary_error from cleanup_error
        if cleanup_error is not None:
            raise cleanup_error
    _checkpoint(checkpoint)
    assert decoded is not None
    return decoded


def _run_extraction(pdf_bytes: bytes, checkpoint: Callable[[], None] | None) -> HkExtractedPages:
    """在所属线程独立 loop 中运行。参数：原件/控制点。返回：页结果。异常：原错透传。"""
    return asyncio.run(extract_hk_pages_async(pdf_bytes, checkpoint))


def extract_hk_pages(pdf_bytes: bytes, checkpoint: Callable[[], None] | None = None) -> HkExtractedPages:
    """同步 discovery 桥接，兼容调用线程已有 loop。

    参数：pdf_bytes 为原件；checkpoint 为 Host 取消观察。
    返回：页结果。异常：取消与 typed 执行失败透传，线程退出前已完成进程回收。
    """
    _checkpoint(checkpoint)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_extraction(pdf_bytes, checkpoint)
    # discovery 的同步公共接口不能嵌套 loop；独立线程拥有整个异步生命周期。
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="hk-body") as executor:
        return executor.submit(_run_extraction, pdf_bytes, checkpoint).result()


async def _close_extraction_handle(handle: InterruptibleProcessHandle) -> None:
    """等待回收完成；关闭期间Task取消也不遗留后台worker。

    参数：handle为本次进程。返回：无。异常：Task取消原样传播；回收失败为typed cleanup。
    """
    closing = asyncio.create_task(handle.close(kill_grace_seconds=_CLOSE_GRACE_SECONDS))
    try:
        await await_owned_task(closing)
    except asyncio.CancelledError as cancellation:
        if cancellation.__cause__ is not None:
            raise cancellation from HkBodyExtractionError("cleanup", str(cancellation.__cause__))
        raise
    except Exception as exc:
        raise HkBodyExtractionError("cleanup", str(exc)) from exc


def _prepare_worker_input(pdf_bytes: bytes) -> tuple[TemporaryDirectory[str], PdfTextWorker]:
    """创建同次IPC输入；spawn只运输小描述符，不运输大PDF pickle。

    参数：pdf_bytes为已通过网络/仓储取得的实际字节。返回：临时目录所有权及worker描述符。
    异常：输入暂存失败为typed startup；失败路径先清理自身临时资源。
    """
    try:
        directory = TemporaryDirectory(prefix=_INPUT_PREFIX)
    except OSError as exc:
        raise HkBodyExtractionError("startup", str(exc)) from exc
    try:
        path = Path(directory.name) / _INPUT_FILENAME
        path.write_bytes(pdf_bytes)
    except OSError as exc:
        _cleanup_worker_input(directory)
        raise HkBodyExtractionError("startup", str(exc)) from exc
    return directory, PdfTextWorker(str(path), HK_BODY_PAGE_LIMIT)


def _cleanup_worker_input(directory: TemporaryDirectory[str]) -> None:
    """释放同次IPC输入。参数：directory为本次所有权。返回：无。异常：typed cleanup保留原因。"""
    try:
        directory.cleanup()
    except OSError as exc:
        raise HkBodyExtractionError("cleanup", str(exc)) from exc
