"""HK正文来源的snapshot原件接线；selection年度供证函数保持纯事实输入。"""
from collections.abc import Callable
import hashlib
from dayu.fins.domain.enums import SourceKind
from dayu.fins.pipelines.cn_download_models import CnReportPdf, CnReportPublication, HkBodyEvidence
from dayu.fins.pipelines.report_original_source import read_report_pdf, ReportOriginalSourceError
from dayu.fins.pipelines.hk_body_facts import resolve_hk_body_facts, HkBodyFacts
from dayu.fins.storage import SourceDocumentRepositoryProtocol, SourceIntegrityStatus
from dayu.fins.storage.source_integrity import SourceIntegrityRevisionConflictError

def read_local_hk_body_pdfs(ticker: str, repository: SourceDocumentRepositoryProtocol, checkpoint: Callable[[], None] | None) -> tuple[CnReportPdf, ...]:
    """仅读取已发布完整正文来源的HK原件，不触碰标题来源PDF。

    参数：ticker/repository/checkpoint 为公司、仓储和取消。返回：exact snapshot原件。异常：完整性/仓储/取消透传。
    """
    entries = repository.read_source_meta_integrity_view(ticker, SourceKind.FILING, batch=None)
    result: list[CnReportPdf] = []
    for entry in entries:
        meta = entry.source_meta
        if (entry.integrity.status is not SourceIntegrityStatus.COMPLETE or meta.get("source_provider") != "hkexnews"
            or meta.get("report_date_source") != "source_document" or meta.get("ingest_method") != "download" or meta.get("is_deleted") is not False):
            continue
        revision, source_id = entry.integrity.revision, meta.get("source_id")
        if revision is None or not isinstance(source_id, str):
            raise SourceIntegrityRevisionConflictError()
        publication = CnReportPublication("hkexnews", source_id, entry.document_id, revision)
        original = read_report_pdf(ticker, entry.document_id, publication, meta, repository, checkpoint)
        if meta.get("pdf_sha256") != hashlib.sha256(original.pdf_bytes).hexdigest():
            raise ReportOriginalSourceError()
        result.append(original)
    return tuple(result)


def local_hk_body_evidence(ticker: str, pdfs: tuple[CnReportPdf, ...], checkpoint: Callable[[], None] | None) -> tuple[HkBodyEvidence, ...]:
    """将本地实际原件交回同一正文owner，纯事实函数不持仓储。

    参数：ticker/pdfs/checkpoint为公司、原件和取消。返回：带原件来源的事实。异常：执行/取消透传。
    """
    result: list[HkBodyEvidence] = []
    for pdf in pdfs:
        facts = resolve_hk_body_facts(pdf.pdf_bytes, ticker, checkpoint)
        if isinstance(facts, HkBodyFacts):
            result.append(HkBodyEvidence(ticker, pdf.publication.source_id, pdf.source_url, facts, pdf.publication))
    return tuple(result)
