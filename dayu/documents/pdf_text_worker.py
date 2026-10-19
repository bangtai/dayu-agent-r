"""单请求 PDF 窄页提取 worker；原生句柄仅在 spawn 子进程的同一线程内存在。"""

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import importlib
import os
from pathlib import Path
import threading
from typing import Protocol, cast

from dayu.contracts.json_value import JsonValue


class _NativeCloseError(RuntimeError):
    """保留 native close 失败阶段，和文本提取错误区分。"""


class _Closable(Protocol):
    """可显式关闭的原生句柄。"""

    def close(self) -> None:
        """关闭句柄。参数：无。返回：无。异常：原生错误透传。"""
        ...


def _close_native(handle: _Closable) -> None:
    """标记关闭错误。参数：handle为原生句柄。返回：无。异常：NativeCloseError。"""
    try:
        handle.close()
    except Exception as exc:
        raise _NativeCloseError(str(exc)) from exc


class _TextPage(Protocol):
    """PDFium 文本句柄的窄类型边界。"""

    def get_text_range(self) -> str:
        """读取全文。参数：无。返回：页文本。异常：原生错误透传。"""
        ...

    def close(self) -> None:
        """释放句柄。参数：无。返回：无。异常：原生错误透传。"""
        ...


class _Page(Protocol):
    """PDFium 页面句柄的窄类型边界。"""

    def get_textpage(self) -> _TextPage:
        """打开文本页。参数：无。返回：句柄。异常：原生错误透传。"""
        ...

    def close(self) -> None:
        """释放页面。参数：无。返回：无。异常：原生错误透传。"""
        ...


class _Document(Protocol):
    """PDFium 文档句柄的窄类型边界。"""

    def __len__(self) -> int:
        """读取页数。参数：无。返回：页数。异常：原生错误透传。"""
        ...

    def __getitem__(self, index: int) -> _Page:
        """打开页面。参数：index 为零起序号。返回：句柄。异常：原生错误透传。"""
        ...

    def close(self) -> None:
        """释放文档。参数：无。返回：无。异常：原生错误透传。"""
        ...


class _Pdfium(Protocol):
    """无静态类型的第三方包只在真实窄边界声明所用接口。"""

    def PdfDocument(self, input: bytes) -> _Document:
        """打开原件。参数：input 为原件字节。返回：句柄。异常：原生错误透传。"""
        ...


@dataclass(frozen=True, slots=True)
class PdfTextWorker:
    """可序列化的单请求 target；不加载 Docling、不持有父进程原生对象。"""

    input_path: str
    max_pages: int

    def __call__(self) -> JsonValue:
        """提取并显式关闭全部句柄。

        参数：无；输入在 frozen 请求中。返回：含协议、摘要和物理页文本的 IPC 消息。
        异常：无；import/native/close 普通异常保留阶段和类型；进程崩溃由调用者识别。
        """
        # 延迟 import 是隔离边界要求：父进程不能因装配 target 加载 PDFium。
        stage = "input"
        try:
            pdf_bytes = Path(self.input_path).read_bytes()
            stage = "import"
            pdfium = cast(_Pdfium, importlib.import_module("pypdfium2"))
            stage = "native"
            pages: list[JsonValue] = []
            with ExitStack() as documents:
                document = pdfium.PdfDocument(pdf_bytes)
                documents.callback(_close_native, document)
                for index in range(min(len(document), self.max_pages)):
                    with ExitStack() as handles:
                        page = document[index]
                        handles.callback(_close_native, page)
                        textpage = page.get_textpage()
                        handles.callback(_close_native, textpage)
                        pages.append(textpage.get_text_range())
                        stage = "close"
                    stage = "native"
                stage = "close"
            return {"protocol": "pdf-text-v1", "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                    "pages": pages, "pid": os.getpid(), "thread": threading.get_ident()}
        except Exception as exc:
            if isinstance(exc, _NativeCloseError):
                stage = "close"
            return {"protocol": "pdf-text-v1", "error": stage, "error_type": type(exc).__name__, "message": str(exc)}
