"""官方年度分类准入与未决资格回归；网络响应为原件，workflow 转换资产为合成。"""

from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from dayu.contracts.json_value import JsonValue
from dayu.fins.domain.document_models import FilingUpdateRequest
from dayu.fins.domain.enums import SourceKind
from dayu.fins.downloaders import hkexnews_downloader as hk
from dayu.fins.pipelines.cn_download_models import (
    CnCompanyProfile, CnFiscalPeriod, CnReportQuery, HkexnewsRawAnnouncement,
)
from dayu.fins.pipelines.cn_form_utils import PeriodDownloadWindow
from dayu.fins.pipelines.cn_pipeline import CnPipeline
from dayu.fins.pipelines.cn_report_selection import (
    hk_annual_end_date, local_hk_annual_ends, resolve_hk_report_period,
    select_hkexnews_report_candidates,
)
from dayu.fins.pipelines.hk_download_rebuild import rebuild_hk_periods
from dayu.fins.storage import SourceIntegrityReason, SourceIntegrityStatus
from tests.fins.test_cn_download_workflow import _FakeConverter, _FailingConverter, _build_pipeline
from tests.fins.test_cn_report_selection import _head_meta, _hk_raw
from tests.fins.test_f5_storage_calendar import _no_head
from tests.fins.test_f5_workflow_rebuild import _RawDiscovery, _manifest_row, _tree

_FIXTURE = Path(__file__).parent / "fixtures/hk_period_evidence_20261018"
_QUERY = CnReportQuery(
    market="HK", normalized_ticker="0388", start_date="2025-01-01", end_date="2026-10-18",
    discovery_periods=("FY", "H1", "Q1", "Q2", "Q3", "Q4"),
)
_ANNUAL_ENDS = {"11548890": date(2024, 12, 31), "12030670": date(2025, 12, 31)}
_QUARTER_YEARS = {"11655015": 2025, "12131985": 2026}
_CAPTURE_HASHES = (
    "aeccdcaf1303421fc83f727e1c280ebf72f1661c071d1f6253bed4fd0fc64f44",
    "ab71115547bdb241688a381b6b9e1520a36d9616cccb08722e7f9f589f3a9eec",
    "5e57e9bea03225f1dde71e39597a0a80dee9ba3d4c1f2c12283db85735a5a17a",
)


@pytest.fixture
def official_raw() -> tuple[HkexnewsRawAnnouncement, ...]:
    """读取完整官方响应并经真实 downloader 解析。

    参数：无；fixture 内不注入预计算财期或年结日。
    返回：同一公司、同一查询窗的 27 条原始公告。
    异常：provenance/hash/完整快照或原始行非法时断言失败或透传解析异常。
    """
    provenance: JsonValue = json.loads((_FIXTURE / "provenance.json").read_text())
    assert isinstance(provenance, dict)
    captures = provenance["captures"]
    assert isinstance(captures, list) and len(captures) == 3
    raw: list[HkexnewsRawAnnouncement] = []
    periods: tuple[CnFiscalPeriod, ...] = ("FY", "H1", "Q1")
    for capture, period, digest in zip(captures, periods, _CAPTURE_HASHES, strict=True):
        assert isinstance(capture, dict)
        filename = capture["file"]
        assert isinstance(filename, str)
        body = (_FIXTURE / filename).read_bytes()
        assert len(body) == capture["bytes"]
        assert hashlib.sha256(body).hexdigest() == capture["sha256"] == digest
        assert capture["status_code"] == 200 and capture["retrieved_at"]
        url = capture["url"]
        assert isinstance(url, str) and url.startswith("https://www1.hkexnews.hk/")
        payload: hk.JsonValue = json.loads(body)
        snapshot = hk._parse_title_search_snapshot(
            payload, requested_row_range=100, stock_code="00388",
            category_spec=hk._PERIOD_TO_CATEGORY_SPEC[period], language="zh",
        )
        for row in snapshot.rows:
            stock = row["STOCK_CODE"]
            assert isinstance(stock, str) and hk._announcement_matches_stock(stock, "00388")
            parsed = hk._parse_announcement(row, language="zh")
            assert parsed is not None
            raw.append(parsed)
    assert len(raw) == 27
    return tuple(raw)


def test_official_annual_dates_confirm_both_q1_without_title_gate(
    official_raw: tuple[HkexnewsRawAnnouncement, ...],
) -> None:
    """验证两条年度原始分类供证，两个三个月来源只在取得证据后确认 Q1。

    参数：official_raw 为正式 fixture 解析的原始响应。
    返回：无。
    异常：年度准入、原始身份或 11/0 选择结果漂移时断言失败。
    """
    by_id = {raw.document_id: raw for raw in official_raw}
    annuals = {
        raw.document_id: end for raw in official_raw
        if (end := hk_annual_end_date(title=raw.title, category_text=raw.category_text)) is not None
    }
    assert annuals == _ANNUAL_ENDS
    for source_id, end in annuals.items():
        raw = by_id[source_id]
        facts = resolve_hk_report_period(title=raw.title, category_text=raw.category_text, annual_ends=(end,))
        assert facts is not None and facts[0] == end.year
        assert facts[1].identity_period == "Q4" and facts[1].covered_periods == ("FY", "Q4")
    quarters = tuple(by_id[source_id] for source_id in _QUARTER_YEARS)
    unknown = select_hkexnews_report_candidates(
        query=_QUERY, announcements=quarters, local_annual_ends=(), read_head_meta=_no_head,
    )
    assert unknown.candidates == ()
    assert {item.source_id for item in unknown.uncertain_reports} == set(_QUARTER_YEARS)
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=official_raw, local_annual_ends=(), read_head_meta=_head_meta,
    )
    assert len(selected.candidates) == 11 and not selected.uncertain_reports
    for candidate in selected.candidates:
        raw = by_id[candidate.source_id]
        assert (candidate.title, candidate.category_text, candidate.source_url, candidate.filing_date) == (
            raw.title, raw.category_text, raw.source_url, raw.filing_date,
        )
        if candidate.source_id in _QUARTER_YEARS:
            year = _QUARTER_YEARS[candidate.source_id]
            assert candidate.fiscal_year == year and candidate.report_date == f"{year}-03-31"
            assert candidate.period_projection.identity_period == "Q1"
            assert candidate.period_projection.covered_periods == ("Q1",)


@pytest.mark.parametrize(("title", "category", "annual_end", "uncertain"), (
    ("公告", "季度業績", None, False),
    ("截至2025年3月31日止三個月的季度業績", "季度業績", None, True),
    ("截至2025年12月31日止全年股息", "股息或分派（公告表格）", None, False),
    ("截至2025年12月31日止全年業績董事會日期", "董事會召開日期", None, False),
    ("截至2025年12月31日止全年業績", "", None, False),
    ("截至2025年12月31日止全年業績", "年報 / 末期業績", None, False),
    ("截至2025年12月31日止年度的第二次中期股息", "末期業績 / 股息或分派", date(2025, 12, 31), False),
    ("第二次中期股息", "末期業績 / 股息或分派", None, False),
    ("截至2025年12月31日及2024年12月31日止年度的股息", "末期業績 / 股息或分派", None, False),
    ("截至2025年2月30日止全年業績及股息", "末期業績 / 股息或分派", None, True),
    ("截至2025年12月31日止六個月的中期業績及股息", "末期業績 / 股息或分派", None, True),
    ("截至2025年12月31日止年度的股息", "末期業績 / 中期業績 / 股息或分派", None, False),
))
def test_annual_and_unresolved_qualifications_share_family_without_expanding_unknown(
    title: str, category: str, annual_end: date | None, uncertain: bool,
) -> None:
    """区分年度供证、未决资格与组合分类冲突，不把纯股息当组合反例。

    参数：title/category 为明确合成的边界输入；annual_end/uncertain 为 owner 预期。
    返回：无。
    异常：年度资格、忽略/未决集合或未知触发 HEAD 时断言失败。
    """
    assert hk_annual_end_date(title=title, category_text=category) == annual_end
    result = select_hkexnews_report_candidates(
        query=replace(_QUERY, discovery_periods=("Q1",)),
        announcements=(_hk_raw(document_id="synthetic", title=title, category_text=category),),
        local_annual_ends=(), read_head_meta=_no_head,
    )
    assert result.candidates == ()
    assert bool(result.uncertain_reports) is uncertain
    if annual_end is not None:
        facts = resolve_hk_report_period(title=title, category_text=category, annual_ends=(annual_end,))
        assert facts is not None and facts[1].identity_period == "Q4"
        assert facts[1].covered_periods == ("FY", "Q4")


@pytest.mark.parametrize("title", (
    "截至2025年12月31日止2024/2025年度的綜合財務報表",
    "截至2024年12月31日止2024/25年度的綜合財務報表",
    "FY2025 ANNUAL RESULTS FOR YEAR ENDED 31 DECEMBER 2024",
    "2025財年 截至2024年12月31日止年度末期業績",
    "截至2024年12月31日止年度的綜合財務報表（2023年比較資料）",
))
def test_ambiguous_annual_source_cannot_confirm_three_month_quarter(
    title: str, official_raw: tuple[HkexnewsRawAnnouncement, ...],
) -> None:
    """年度证据必须通过统一财年歧义校验，不能据冲突来源确认三个月季度。

    参数：title 为合成歧义年度标题；official_raw 提供真实三个月季度原始行。
    返回：无。
    异常：年度绕过校验、季度被确认或未知触发 HEAD 时断言失败。
    """
    category = "公告及通告 - [末期業績]"
    assert resolve_hk_report_period(title=title, category_text=category, annual_ends=()) is None
    assert hk_annual_end_date(title=title, category_text=category) is None
    quarter = next(raw for raw in official_raw if raw.document_id == "11655015")
    annual = _hk_raw(document_id="synthetic-ambiguous-annual", title=title, category_text=category)
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(annual, quarter), local_annual_ends=(), read_head_meta=_no_head,
    )
    assert selected.candidates == ()
    target = next(report for report in selected.uncertain_reports if report.source_id == quarter.document_id)
    assert target.report_date == "2025-03-31" and target.existing_document_id is None
    assert target.reason_category == "uncertain_hk_period"
    assert all(report.existing_document_id is None for report in selected.uncertain_reports)


class _OfficialRawDiscovery(_RawDiscovery):
    """运输官方 raw 和公司身份；PDF/Docling 仍使用明确合成测试资产。"""

    def resolve_company(self, query: CnReportQuery) -> CnCompanyProfile:
        """返回与官方响应同源的公司身份。

        参数：query 为真实 workflow 查询。
        返回：香港交易所的固定官方公司身份。
        异常：无。
        """
        return CnCompanyProfile(
            provider="hkexnews", company_id="HKEX:781", company_name="香港交易所",
            ticker=query.normalized_ticker,
        )


def _business_assets(pipeline: CnPipeline, document_id: str) -> dict[str, bytes]:
    """从完整 source snapshot 读取业务资产，元数据修正不应改变这些内容。

    参数：pipeline 为隔离仓储宿主；document_id 为已发布来源身份。
    返回：声明的业务文件名到实际字节的映射，不含 storage 元数据。
    异常：snapshot 或业务文件读取异常原样传播。
    """
    assets: dict[str, bytes] = {}
    with pipeline.source_repository.read_source_snapshot(
        "0388", document_id, SourceKind.FILING, materialize_files=True,
    ) as snapshot:
        for file in snapshot.files:
            with snapshot.get_source(file.name).open() as stream:
                assets[file.name] = stream.read()
    return assets


@pytest.mark.parametrize("fail_conversion", (False, True))
def test_real_fs_local_annual_q1_publication_retry_and_idempotency(
    tmp_path: Path, official_raw: tuple[HkexnewsRawAnnouncement, ...], fail_conversion: bool,
) -> None:
    """以真实 Fs 验证 unknown→年度供证→Q1 发布、失败重试及资产幂等。

    参数：tmp_path 为隔离仓储；official_raw 为官方原始公告；fail_conversion 控制一次失败轮。
    返回：无。
    异常：来源资格、身份/资产/索引或重复发布漂移时断言失败。
    """
    quarters = tuple(raw for raw in official_raw if raw.document_id in _QUARTER_YEARS)
    discovery = _OfficialRawDiscovery(tmp_path, quarters)
    pipeline = _build_pipeline(
        tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=_FakeConverter(),
    )
    unknown = pipeline.download(ticker="0388", form_type="Q1", start_date="2025", end_date="2026", start_is_explicit=True)
    assert unknown["filings"] == [] and discovery.download_calls == 0
    uncertain = unknown["uncertain_reports"]
    assert isinstance(uncertain, list) and len(uncertain) == 2
    discovery.raw = official_raw
    seeded = pipeline.download(ticker="0388", form_type="Q4", start_date="2025", end_date="2026", start_is_explicit=True)
    assert seeded["uncertain_reports"] == []
    annual_entries = pipeline.source_repository.read_source_meta_integrity_view("0388", SourceKind.FILING, batch=None)
    assert len(annual_entries) == 2
    assert set(local_hk_annual_ends(annual_entries).values()) == set(_ANNUAL_ENDS.values())
    for entry in annual_entries:
        for patch in ({"is_deleted": True}, {"ticker": "0005"}, {"company_id": "HKEX:foreign"},
                      {"source_provider": "cninfo"}, {"ingest_method": "upload"}):
            assert local_hk_annual_ends((replace(entry, source_meta={**entry.source_meta, **patch}),)) == {}
        assert local_hk_annual_ends((replace(entry, integrity=replace(
            entry.integrity, status=SourceIntegrityStatus.REPAIR_REQUIRED,
            reasons=(SourceIntegrityReason.ORIGINAL_FILE_MISSING,),
        )),)) == {}
    discovery.raw = quarters
    if fail_conversion:
        broken = _build_pipeline(
            tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery,
            converter=_FailingConverter(RuntimeError("本测试有意转换失败")),
        )
        failed = broken.download(ticker="0388", form_type="Q1", start_date="2025", end_date="2026", start_is_explicit=True)
        summary = failed["summary"]
        assert isinstance(summary, dict) and summary["failed"] == 2
        assert failed["uncertain_reports"] == []
        assert broken.source_repository.read_source_meta_integrity_view("0388", SourceKind.FILING, batch=None) == annual_entries
    result = pipeline.download(ticker="0388", form_type="Q1", start_date="2025", end_date="2026", start_is_explicit=True)
    assert result["uncertain_reports"] == []
    entries = pipeline.source_repository.read_source_meta_integrity_view("0388", SourceKind.FILING, batch=None)
    assert len(entries) == 4 and all(entry.integrity.status is SourceIntegrityStatus.COMPLETE for entry in entries)
    assert tuple(entry for entry in entries if entry.source_meta["source_id"] in _ANNUAL_ENDS) == annual_entries
    for entry in entries:
        meta = entry.source_meta
        source_id = meta["source_id"]
        if isinstance(source_id, str) and source_id in _QUARTER_YEARS:
            year = _QUARTER_YEARS[source_id]
            row = _manifest_row(tmp_path, entry.document_id, processed=False)
            for material in (meta, row):
                assert material["fiscal_year"] == year and material["report_date"] == f"{year}-03-31"
                assert material["form_type"] == material["fiscal_period"] == "Q1"
            assert meta["covered_fiscal_periods"] == ["Q1"]
    result_rows = result["filings"]
    assert isinstance(result_rows, list) and len(result_rows) == 2
    for row in result_rows:
        assert isinstance(row, dict) and row["form_type"] == "Q1"
        assert row["covered_fiscal_periods"] == ["Q1"]
    stable = _tree(tmp_path / "portfolio")
    repeated = pipeline.download(ticker="0388", form_type="Q1", start_date="2025", end_date="2026", start_is_explicit=True)
    assert repeated["uncertain_reports"] == []
    assert _tree(tmp_path / "portfolio") == stable


def test_rebuild_reprojects_current_v3_from_raw_annual_input(
    tmp_path: Path, official_raw: tuple[HkexnewsRawAnnouncement, ...],
) -> None:
    """证明相同 v3 标签不会跳过新年度准入，隔离仓储中的旧财期被重新解析。

    参数：tmp_path 为隔离根；official_raw 为官方原始标题/分类。
    返回：无。
    异常：同版本缓存跳过、财期不正确或内容/身份变化时断言失败。
    """
    discovery = _OfficialRawDiscovery(tmp_path, official_raw)
    pipeline = _build_pipeline(tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=_FakeConverter())
    pipeline.download(ticker="0388", form_type="Q1,Q4", start_date="2025", end_date="2026", start_is_explicit=True)
    entries = pipeline.source_repository.read_source_meta_integrity_view("0388", SourceKind.FILING, batch=None)
    batch = pipeline.batching_repository.begin_batch("0388")
    for entry in entries:
        meta = dict(entry.source_meta)
        meta["period_resolution_version"] = "hk-period-v3"
        source_id = meta["source_id"]
        assert isinstance(source_id, str)
        if source_id in _QUARTER_YEARS:
            # 显式构造已有同版本旧投影；原始分类/标题保持官方事实，不注入年度日期。
            meta.update(form_type="Q3", fiscal_period="Q3", report_kind="Q3", covered_fiscal_periods=["Q3"])
        internal = meta["internal_document_id"]
        form = meta["form_type"]
        assert isinstance(internal, str) and isinstance(form, str)
        pipeline.source_repository.update_source_document(FilingUpdateRequest(
            ticker="0388", document_id=entry.document_id, internal_document_id=internal, form_type=form, meta=meta,
        ), SourceKind.FILING, batch=batch)
    pipeline.batching_repository.commit_batch(batch)
    before = {entry.document_id: pipeline.source_repository.get_source_meta("0388", entry.document_id, SourceKind.FILING) for entry in entries}
    assets = {entry.document_id: _business_assets(pipeline, entry.document_id) for entry in entries}
    rows, uncertain, cancelled = rebuild_hk_periods(pipeline, "0388", (
        PeriodDownloadWindow(fiscal_period="Q1", start_date="2025-01-01", end_date="2026-12-31"),
        PeriodDownloadWindow(fiscal_period="Q3", start_date="2025-01-01", end_date="2026-12-31"),
    ), None)
    assert not uncertain and not cancelled and len(rows) == 2
    assert all(row["status"] == "downloaded" and row["form_type"] == "Q1" for row in rows)
    for row in rows:
        doc = row["document_id"]
        assert isinstance(doc, str)
        meta = pipeline.source_repository.get_source_meta("0388", doc, SourceKind.FILING)
        assert meta["period_resolution_version"] == "hk-period-v3"
        assert meta["fiscal_period"] == "Q1" and meta["covered_fiscal_periods"] == ["Q1"]
        for key in ("document_id", "internal_document_id", "source_fingerprint", "remote_fingerprint", "document_version"):
            assert meta[key] == before[doc][key]
        assert _business_assets(pipeline, doc) == assets[doc]
