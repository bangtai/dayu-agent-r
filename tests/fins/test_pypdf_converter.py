"""pypdf 降级转换器的契约测试。

覆盖 :class:`PypdfFallbackConverter` 对 :class:`DoclingConverter` 协议的
履行情况：输入校验、取消语义、失败种类映射、结果自洽性，以及工厂的
后端选择行为。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

import pytest

from dayu.fins.pipelines import pypdf_converter as converter_module
from dayu.fins.pipelines.docling_converter_factory import create_docling_converter
from dayu.fins.pipelines.docling_process_converter import (
    DoclingConversionCancelledError,
    DoclingConversionConfig,
    DoclingConversionError,
    DoclingConversionFailureKind,
    ProcessDoclingConverter,
)
from dayu.fins.pipelines.pypdf_converter import PypdfFallbackConverter

_CONFIG = DoclingConversionConfig(
    do_ocr=True,
    do_table_structure=True,
    table_mode="accurate",
    do_cell_matching=True,
)


class _FakeCancellation:
    """最小取消观察实现，用于驱动取消分支。"""

    def __init__(self, *, cancelled: bool) -> None:
        self._cancelled = cancelled

    def is_cancelled(self) -> bool:
        return self._cancelled


def _run(coro):
    return asyncio.run(coro)


def _convert(
    data: bytes = b"%PDF-1.7",
    stream_name: str = "sample.pdf",
    *,
    cancellation=None,
):
    return _run(
        PypdfFallbackConverter().convert_to_json_bytes(
            data,
            stream_name,
            config=_CONFIG,
            cancellation=cancellation,
        )
    )


def test_empty_input_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _convert(b"")


def test_blank_stream_name_raises_value_error() -> None:
    with pytest.raises(ValueError):
        _convert(stream_name="   ")


def test_invalid_config_raises_value_error() -> None:
    bad = DoclingConversionConfig(
        do_ocr=True,
        do_table_structure=True,
        table_mode="accurate",
        do_cell_matching=True,
    )
    object.__setattr__(bad, "do_ocr", "yes")
    with pytest.raises(ValueError):
        _run(
            PypdfFallbackConverter().convert_to_json_bytes(
                b"%PDF-1.7", "sample.pdf", config=bad, cancellation=None
            )
        )


def test_cancelled_token_raises_before_conversion(monkeypatch) -> None:
    called = False

    def _boom(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("转换不应被执行")

    monkeypatch.setattr(
        converter_module, "convert_pdf_bytes_to_docling_json_bytes", _boom
    )
    with pytest.raises(DoclingConversionCancelledError):
        _convert(cancellation=_FakeCancellation(cancelled=True))
    assert called is False


def test_success_returns_self_consistent_result(monkeypatch) -> None:
    payload = json.dumps({"schema_name": "DoclingDocument"}).encode("utf-8")
    monkeypatch.setattr(
        converter_module,
        "convert_pdf_bytes_to_docling_json_bytes",
        lambda raw, name: payload,
    )
    result = _convert()
    assert result.json_bytes == payload
    assert result.size == len(payload)
    assert result.sha256 == hashlib.sha256(payload).hexdigest()


def test_conversion_failure_maps_to_execution_kind(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("pdf-inspector 提取失败")

    monkeypatch.setattr(
        converter_module, "convert_pdf_bytes_to_docling_json_bytes", _boom
    )
    with pytest.raises(DoclingConversionError) as error:
        _convert()
    assert error.value.kind is DoclingConversionFailureKind.CONVERTER_EXECUTION
    assert error.value.exit_code is None
    assert isinstance(error.value.__cause__, RuntimeError)


def test_cancellation_after_conversion_raises(monkeypatch) -> None:
    payload = b"{}"
    monkeypatch.setattr(
        converter_module,
        "convert_pdf_bytes_to_docling_json_bytes",
        lambda raw, name: payload,
    )
    token = _FakeCancellation(cancelled=False)
    original = converter_module.convert_pdf_bytes_to_docling_json_bytes

    def _convert_then_cancel(raw, name):
        token._cancelled = True
        return original(raw, name)

    monkeypatch.setattr(
        converter_module, "convert_pdf_bytes_to_docling_json_bytes", _convert_then_cancel
    )
    with pytest.raises(DoclingConversionCancelledError):
        _convert(cancellation=token)


def test_factory_defaults_to_docling_backend(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DAYU_FINS_CONVERTER", raising=False)
    assert isinstance(
        create_docling_converter(tmp_path), ProcessDoclingConverter
    )


def test_factory_selects_pypdf_backend(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DAYU_FINS_CONVERTER", "pypdf")
    assert isinstance(create_docling_converter(tmp_path), PypdfFallbackConverter)


def test_factory_rejects_unknown_backend(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DAYU_FINS_CONVERTER", "not-a-backend")
    with pytest.raises(DoclingConversionError) as error:
        create_docling_converter(tmp_path)
    assert error.value.kind is DoclingConversionFailureKind.CONVERTER_CONSTRUCTION


def test_factory_backend_value_is_case_and_space_insensitive(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DAYU_FINS_CONVERTER", "  PyPDF  ")
    assert isinstance(create_docling_converter(tmp_path), PypdfFallbackConverter)


@pytest.mark.skipif(
    os.environ.get("DAYU_SKIP_REAL_PDF_TESTS") == "1",
    reason="显式跳过真实 PDF 转换测试",
)
def test_real_pdf_produces_valid_docling_document(tmp_path: Path) -> None:
    """用真实 PDF 验证产出能被 docling_core 反序列化。"""

    pdf = tmp_path / "probe.pdf"
    _write_minimal_pdf(pdf)
    result = _convert(pdf.read_bytes(), "probe.pdf")

    from docling_core.types.doc.document import DoclingDocument

    document = DoclingDocument.model_validate(json.loads(result.json_bytes))
    assert document.name == "probe.pdf"
    assert len(document.texts) >= 1


def _write_minimal_pdf(path: Path) -> None:
    """写入一个带单页文本的最小合法 PDF。"""

    stream = b"BT /F1 12 Tf 72 720 Td (contract probe) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))
