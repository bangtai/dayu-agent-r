"""主体报告作用域回归：官方完整 raw；边界标题及 PDF/Docling 资产明确为合成。"""

from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from dayu.contracts.json_value import JsonValue
from dayu.fins.domain.document_models import BatchToken, DocumentHandle, FilingUpdateRequest, SourceDocumentUpsertRequest
from dayu.fins.domain.enums import SourceKind
from dayu.fins.downloaders import hkexnews_downloader as hk
from dayu.fins.pipelines.cn_download_models import CnCompanyProfile, CnFiscalPeriod, CnReportQuery, HkexnewsRawAnnouncement
from dayu.fins.pipelines.cn_form_utils import PeriodDownloadWindow
from dayu.fins.pipelines.cn_pipeline import CnPipeline
from dayu.fins.pipelines.cn_report_selection import (
    hk_annual_end_date, hk_report_end_date, hk_report_subject_title, local_hk_annual_ends,
    resolve_hk_report_period, select_hkexnews_report_candidates,
)
from dayu.fins.pipelines.hk_download_rebuild import rebuild_hk_periods
from dayu.fins.storage import SourceIntegrityStatus, SourceMetaIntegrityReadEntry
from tests.fins.test_cn_download_workflow import (
    _FakeConverter, _FailingConverter, _CancelAfterConvertConverter, _CancelState, _build_pipeline,
)
from tests.fins.test_cn_report_selection import _head_meta, _hk_raw
from tests.fins.test_f5_storage_calendar import _no_head
from tests.fins.test_f5_workflow_rebuild import _RawDiscovery, _manifest_row, _tree

_FIXTURE = Path(__file__).parent / "fixtures/hk_report_title_scope_20261019"
_TITLE = "2026中期報告及有關2025年度報告的補充資料"
_CATEGORY = "財務報表/環境、社會及管治資料 - [中期/半年度報告]"
_QUERY = CnReportQuery(
    market="HK", normalized_ticker="9633", start_date="2025-01-01", end_date="2026-10-19",
    discovery_periods=("FY", "H1", "Q1", "Q2", "Q3", "Q4"),
)
_HASHES = (
    "34644b08de8df726fc4e405f4f4b2d36b90c819d4acad47b5e46ef0632dbe743",
    "dc5d569ceb4d2468e7675fe83a72f6391eae4a494072305ef581268df57c3b12",
    "3d9896c01325bbffec3804ce7135f82a61e51f97bf65c1400af2fab2634c3c36",
)
# 下列普通标题均为合成 owner 输入，不作为真实发行人的线上受损证据。
_SINGLE_SUBJECT_CASES: tuple[tuple[str, str, int, CnFiscalPeriod, tuple[CnFiscalPeriod, ...], str | None, bool], ...] = (
    ("有關2026年中期業績公告", "中期業績", 2026, "Q2", ("H1", "Q2"), None, False),
    ("有關截至2025年12月31日止年度之全年業績公告", "末期業績", 2025, "Q4", ("FY", "Q4"), "2025-12-31", False),
    ("有關2025年度報告", "年報", 2025, "FY", ("FY",), None, False),
    ("2025年報及環境、社會及管治報告", "年報", 2025, "FY", ("FY",), None, False),
    ("2025年度報告及財務報表", "年報", 2025, "FY", ("FY",), None, False),
    ("2026中期報告及財務報表", "中期報告", 2026, "H1", ("H1",), None, False),
    ("2025年度報告及股東周年大會資料", "年報", 2025, "FY", ("FY",), None, False),
    ("有關2025年度報告及有關股東周年大會資料", "年報", 2025, "FY", ("FY",), None, False),
    ("有關截至2025年12月31日止年度報告及財務報表", "年報", 2025, "FY", ("FY",), "2025-12-31", False),
    ("截至2026年6月30日止中期報告與財務報表", "中期報告", 2026, "H1", ("H1",), "2026-06-30", False),
    ("2031 年 年报和环境、社会及管治报告", "年报", 2031, "FY", ("FY",), None, False),
    ("有关2031年中期报告与财务报表（修订版）", "中期报告", 2031, "H1", ("H1",), None, True),
    ("有關2026年中期業績公告（更正）", "中期業績", 2026, "Q2", ("H1", "Q2"), None, True),
    ("2026中期報告（補充）", "中期報告", 2026, "H1", ("H1",), None, True),
    ("2026中期報告及有關資料", "中期報告", 2026, "H1", ("H1",), None, False),
    ("2025年度报告及有关资料", "年报", 2025, "FY", ("FY",), None, False),
)
# 两端都是明确财期主体；交换顺序后仍不能由分类静默选择其一。
_PARALLEL_SUBJECT_PAIRS: tuple[tuple[str, str, str, str], ...] = (
    ("2026中期業績公告", "2026年報", "及", "中期業績"),
    ("2026中期業績公告", "2026年報", "與", "年報"),
    ("2026第一季度業績公告", "2026年報", "和", "第一季度業績"),
    ("2026全年業績公告", "2026中期報告", "及", "末期業績"),
    ("2026中期業績公告", "2026中期報告", "及", "中期業績"),
    ("2026第二季度報告", "2026中期報告", "與", "中期報告"),
    ("2025年報", "2025年第三季報告", "及", "年報"),
    ("2025年报", "2025年第一季报告", "与", "年报"),
    ("2025年報", "2025年第四季報告", "和", "年報"),
    ("2026中期报告", "2026第二季报告", "及", "中期报告"),
    ("截至2025年12月31日止年度報告", "2025第三季報告", "及", "年報"),
    ("截至2025年12月31日止全年業績公告", "2025中期報告", "及", "末期業績"),
)


class _OfficialRawDiscovery(_RawDiscovery):
    """运输官方 raw 和公司身份，PDF/Docling 明确使用合成资产。"""

    def resolve_company(self, query: CnReportQuery) -> CnCompanyProfile:
        """提供与官方公开股票映射一致的公司身份。

        参数：query 为真实 workflow 查询。
        返回：农夫山泉的官方 provider 身份。
        异常：无。
        """
        return CnCompanyProfile(provider="hkexnews", company_id="HKEX:1000054238", company_name="農夫山泉", ticker=query.normalized_ticker)


@pytest.fixture
def official_raw() -> tuple[HkexnewsRawAnnouncement, ...]:
    """逐字校验完整官方原响应，再交真实 provider 解析。

    参数：无，不提供预计算财期。
    返回：年报、中期、业绩三个分类的全部二十条 raw。
    异常：来源、哈希或 provider 结构错误时断言失败或透传解析异常。
    """
    return _load_official_raw()


def _load_official_raw() -> tuple[HkexnewsRawAnnouncement, ...]:
    """校验并解析可离线重放的原始公告。

    参数：无。
    返回：全部二十条 raw，不注入财年财期。
    异常：哈希不一致断言失败，provider 解析错误透传。
    """
    provenance: JsonValue = json.loads((_FIXTURE / "provenance.json").read_bytes())
    assert isinstance(provenance, dict)
    captures = provenance["captures"]
    assert isinstance(captures, list) and len(captures) == 3
    periods: tuple[CnFiscalPeriod, ...] = ("FY", "H1", "Q1")
    raw: list[HkexnewsRawAnnouncement] = []
    for capture, period, digest in zip(captures, periods, _HASHES, strict=True):
        assert isinstance(capture, dict) and isinstance(capture["body_file"], str)
        body = (_FIXTURE / capture["body_file"]).read_bytes()
        assert len(body) == capture["bytes"]
        assert hashlib.sha256(body).hexdigest() == capture["sha256"] == digest
        assert capture["status_code"] == 200 and capture["retrieved_at"]
        url = capture["url"]
        assert isinstance(url, str) and url.startswith("https://www1.hkexnews.hk/")
        payload: hk.JsonValue = json.loads(body)
        snapshot = hk._parse_title_search_snapshot(
            payload, requested_row_range=100, stock_code="09633",
            category_spec=hk._PERIOD_TO_CATEGORY_SPEC[period], language="zh",
        )
        for row in snapshot.rows:
            parsed = hk._parse_announcement(row, language="zh")
            assert parsed is not None
            raw.append(parsed)
    assert len(raw) == 20
    return tuple(raw)


def test_official_full_raw_confirms_subject_without_changing_seven(
    official_raw: tuple[HkexnewsRawAnnouncement, ...],
) -> None:
    """验证真实完整标题只新增 H1，原七份及 raw provenance 保持。

    参数：official_raw 为完整正式原响应。
    返回：无。
    异常：候选、覆盖、修订、日期或来源漂移时断言失败。
    """
    previous = select_hkexnews_report_candidates(
        query=_QUERY, announcements=tuple(raw for raw in official_raw if raw.document_id != "12345879"),
        local_annual_ends=(), read_head_meta=_head_meta,
    )
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=official_raw, local_annual_ends=(), read_head_meta=_head_meta,
    )
    assert len(previous.candidates) == 7
    assert len(selected.candidates) == 8 and not selected.uncertain_reports
    assert tuple(c for c in selected.candidates if c.source_id != "12345879") == previous.candidates
    target = next(c for c in selected.candidates if c.source_id == "12345879")
    raw = next(raw for raw in official_raw if raw.document_id == target.source_id)
    assert target.fiscal_year == 2026 and target.period_projection.identity_period == "H1"
    assert target.period_projection.covered_periods == ("H1",) and target.amended is False
    assert target.report_date is None
    assert (target.title, target.category_text, target.source_url, target.filing_date) == (
        _TITLE, _CATEGORY, raw.source_url, raw.filing_date,
    )
    assert hk_annual_end_date(title=raw.title, category_text=raw.category_text) is None


@pytest.mark.parametrize("title,year", (
    (_TITLE, 2026),
    ("2031中期报告及有关2030年度报告的补充资料", 2031),
    ("2020 年 半年度報告 及 有關 2019 年 年報 的 補充資料", 2020),
    ("二零二六年中期報告及有關二零二五年年度報告的補充資料", 2026),
))
def test_supported_relation_is_independent_of_year_and_script(title: str, year: int) -> None:
    """验证清晰关系的年份平移、字形和空白不改变主体事实。

    参数：title/year 为合成等价输入及预期年。
    返回：无。
    异常：owner 未解析或事实漂移时断言失败。
    """
    facts = resolve_hk_report_period(title=title, category_text=_CATEGORY, annual_ends=())
    assert facts is not None and facts.fiscal_year == year
    assert facts.projection.identity_period == "H1" and facts.projection.covered_periods == ("H1",)


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("left,right,connector,category", _PARALLEL_SUBJECT_PAIRS)
def test_parallel_subjects_are_unknown_in_either_order(
    left: str, right: str, connector: str, category: str, reverse: bool,
) -> None:
    """明确竞争主体的顺序、同期间或分类均不能使其成为单一报告。

    参数：left/right 为合成财期主体；connector 为连接词；category 为真实分类形态；
        reverse 控制两主体交换顺序。
    返回：无。
    异常：主体、日期、年度供证、候选或无 HEAD 的未决合同不成立时断言失败。
    """
    title = connector.join((right, left) if reverse else (left, right))
    assert hk_report_subject_title(title) is None
    assert hk_report_end_date(title) is None
    assert hk_annual_end_date(title=title, category_text=category) is None
    assert resolve_hk_report_period(title=title, category_text=category, annual_ends=()) is None
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(_hk_raw(document_id="parallel", title=title, category_text=category),),
        local_annual_ends=(), read_head_meta=_no_head,
    )
    assert not selected.candidates and len(selected.uncertain_reports) == 1
    assert selected.uncertain_reports[0].report_date is None


@pytest.mark.parametrize("title,category,year,period,coverage,end,amended", _SINGLE_SUBJECT_CASES)
def test_single_subject_connectors_preserve_owner_contract(
    title: str, category: str, year: int, period: CnFiscalPeriod,
    coverage: tuple[CnFiscalPeriod, ...], end: str | None, amended: bool,
) -> None:
    """普通连接词不是第二主体证据，候选、日期、供证及修订采用同一事实。

    参数：title/category 为合成普通标题及分类；其余参数为明确期望事实。
    返回：无。
    异常：普通报告被误拒、raw 被改写或任一 owner 消费事实漂移时断言失败。
    """
    assert hk_report_subject_title(title) == title
    facts = resolve_hk_report_period(title=title, category_text=category, annual_ends=())
    assert facts is not None and facts.fiscal_year == year
    assert facts.projection.identity_period == period and facts.projection.covered_periods == coverage
    direct = date.fromisoformat(end) if end is not None else None
    assert hk_report_end_date(title) == direct
    assert hk_annual_end_date(title=title, category_text=category) == (direct if period in {"FY", "Q4"} else None)
    raw = _hk_raw(document_id="single-subject", title=title, category_text=category)
    original = (raw.document_id, raw.title, raw.category_text, raw.source_url, raw.filing_date)
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(raw,), local_annual_ends=(), read_head_meta=_head_meta,
    )
    assert not selected.uncertain_reports and len(selected.candidates) == 1
    candidate = selected.candidates[0]
    assert candidate.fiscal_year == year and candidate.period_projection == facts.projection
    assert candidate.report_date == end and candidate.amended is amended
    assert (candidate.source_id, candidate.title, candidate.category_text, candidate.source_url, candidate.filing_date) == original
    assert (raw.document_id, raw.title, raw.category_text, raw.source_url, raw.filing_date) == original


@pytest.mark.parametrize("title,category", (
    ("2026中期報告及2025年度報告", _CATEGORY),
    ("2026中期報告及2026中期報告", _CATEGORY),
    ("2026中期報告及有關2026中期報告的補充資料", _CATEGORY),
    ("2026中期報告及有關的補充資料", _CATEGORY),
    ("2026中期報告及補充資料", _CATEGORY),
    ("2026中期報告及有關2025年度報告", _CATEGORY),
    ("2026中期報告及有關2025年度報告的補充資料及其他未明事項", _CATEGORY),
    ("2025及2026中期報告及有關2024年度報告的補充資料", _CATEGORY),
    ("2025/2026中期報告及有關2024年度報告的補充資料", _CATEGORY),
    ("2026中期報告及有關2024/2025年度報告的補充資料", _CATEGORY),
    ("2026中期報告及有關2025年度報告的修訂", _CATEGORY),
    ("有關2025年度報告的補充資料", "年報"),
    ("2025年度報告的補充資料", "年報"),
    ("有關截至2025年12月31日止年度報告的補充資料", "年報"),
    ("有關2026中期報告的補充資料", _CATEGORY),
    ("2026中期報告及有關", _CATEGORY),
    ("2026中期報告及", _CATEGORY),
    ("2026中期報告及2026中期業績公告", _CATEGORY),
    ("2026中期報告及2026第二季度報告", _CATEGORY),
    ("2025年度報告及業績公告", "年報"),
    ("2025年度報告及補充資料", "年報"),
    ("2026中期報告與2026中期報告", _CATEGORY),
    ("有關2025年報及2026年報", "年報"),
    ("2026中期報告與截至2025年12月31日止年度報告", _CATEGORY),
    ("2026中期業績及有關2025年度報告的補充資料", "中期業績"),
    (_TITLE, "年報"),
    ("截至2026年2月30日止中期報告及有關2025年度報告的補充資料", _CATEGORY),
    ("截至2026年6月30日及2026年5月31日止中期報告及有關2025年度報告的補充資料", _CATEGORY),
))
def test_ambiguous_relationship_remains_unknown_without_head(title: str, category: str) -> None:
    """验证不完整关系、并列主体和其它歧义均不借分类或首年确认。

    参数：title/category 为明确合成反例。
    返回：无。
    异常：解期、年度供证或调用 HEAD 时断言失败。
    """
    assert resolve_hk_report_period(title=title, category_text=category, annual_ends=()) is None
    assert hk_annual_end_date(title=title, category_text=category) is None
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(_hk_raw(document_id="synthetic", title=title, category_text=category),),
        local_annual_ends=(), read_head_meta=_no_head,
    )
    assert not selected.candidates
    assert len(selected.uncertain_reports) == 1 and selected.uncertain_reports[0].report_date is None


def test_conflicting_category_families_do_not_claim_a_report() -> None:
    """分类家族本身冲突时，不产生已确认候选或具有报告资格的未决。

    参数：无，使用明确冲突的合成分类。
    返回：无。
    异常：分类冲突被放宽、供证或请求 HEAD 时断言失败。
    """
    category = "年報 / 中期業績"
    assert resolve_hk_report_period(title=_TITLE, category_text=category, annual_ends=()) is None
    assert hk_annual_end_date(title=_TITLE, category_text=category) is None
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(_hk_raw(document_id="synthetic", title=_TITLE, category_text=category),),
        local_annual_ends=(), read_head_meta=_no_head,
    )
    assert not selected.candidates and not selected.uncertain_reports


@pytest.mark.parametrize("title,category", (
    ("有關截至2025年12月31日止年度之全年業績公告", "末期業績"),
    ("有關截至2025年12月31日止年度報告及財務報表", "年報"),
    ("截至2025年12月31日止年度報告及環境、社會及管治報告", "年報"),
))
def test_single_subject_annual_source_still_resolves_three_months(title: str, category: str) -> None:
    """普通年度来源仍向同窗三个月业绩供证，不因裸关系词削弱日历。

    参数：title/category 为合成年度原始标题及分类。
    返回：无。
    异常：无年度时误确认、供证后仍未知或候选日期错位时断言失败。
    """
    quarter = _hk_raw(document_id="quarter", title="截至2026年3月31日止三個月業績公告", category_text="季度業績")
    missing = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(quarter,), local_annual_ends=(), read_head_meta=_no_head,
    )
    assert not missing.candidates and len(missing.uncertain_reports) == 1
    annual = _hk_raw(document_id="annual", title=title, category_text=category)
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(quarter, annual), local_annual_ends=(), read_head_meta=_head_meta,
    )
    assert not selected.uncertain_reports and len(selected.candidates) == 2
    candidate = next(c for c in selected.candidates if c.source_id == "quarter")
    assert candidate.fiscal_year == 2026 and candidate.period_projection.identity_period == "Q1"
    assert candidate.report_date == "2026-03-31"


@pytest.mark.parametrize("category_present", (False, True))
@pytest.mark.parametrize("title,category,year,period,coverage,end,amended", _SINGLE_SUBJECT_CASES)
def test_single_subject_local_rebuild_and_annual_evidence_agree(
    tmp_path: Path, category_present: bool, title: str, category: str, year: int,
    period: CnFiscalPeriod, coverage: tuple[CnFiscalPeriod, ...], end: str | None, amended: bool,
) -> None:
    """真实 Fs 的年度供证和同版本重建共同消费普通主体，分类可缺省。

    参数：tmp_path 为隔离仓储；category_present 控制可选分类；其余为合成标题及期望事实。
    返回：无。
    异常：供证或重建与 resolver 不一致、身份/资产变化、重跑写入时断言失败。
    """
    raw = _hk_raw(document_id="single-subject", title=title, category_text=category)
    discovery = _RawDiscovery(tmp_path, (raw,))
    pipeline = _build_pipeline(tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=_FakeConverter())
    pipeline.download(ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date, start_is_explicit=True)
    entries, assets = _stored_sources(pipeline)
    assert len(entries) == 1
    entry = entries[0]
    internal_id = entry.source_meta["internal_document_id"]
    assert isinstance(internal_id, str)
    batch = pipeline.batching_repository.begin_batch("9633")
    pipeline.source_repository.update_source_document(FilingUpdateRequest(
        ticker="9633", document_id=entry.document_id, internal_document_id=internal_id, form_type=period,
        meta={**entry.source_meta, "source_category": category if category_present else None,
              "report_date": "2000-01-01", "report_date_source": "source_title"},
    ), SourceKind.FILING, batch=batch)
    pipeline.batching_repository.commit_batch(batch)
    before, before_assets = _stored_sources(pipeline)
    annual = {entry.document_id: date.fromisoformat(end)} if period in {"FY", "Q4"} and end is not None else {}
    anchors = local_hk_annual_ends(before)
    assert {key: anchor.end for key, anchor in anchors.items()} == annual
    assert all(anchor.publication is not None and anchor.source_id and anchor.source_url for anchor in anchors.values())
    windows = (PeriodDownloadWindow(fiscal_period=period, start_date=_QUERY.start_date, end_date=_QUERY.end_date),)
    rows, unknown, cancelled = rebuild_hk_periods(pipeline, "9633", windows, None)
    assert not unknown and not cancelled and len(rows) == 1
    assert rows[0]["form_type"] == period and rows[0]["report_date"] == end
    after, after_assets = _stored_sources(pipeline)
    assert after_assets == before_assets == assets
    meta = after[0].source_meta
    assert meta["fiscal_year"] == year and meta["fiscal_period"] == period
    assert meta["covered_fiscal_periods"] == list(coverage) and meta["amended"] is amended
    assert meta["report_date"] == end
    assert meta["report_date_source"] == ("source_title" if end is not None else None)
    for key in ("internal_document_id", "document_id", "source_id", "source_title", "source_category", "source_url", "source_fingerprint", "document_version"):
        assert meta[key] == before[0].source_meta[key]
    assert _manifest_row(tmp_path, entry.document_id, processed=False)["report_date"] == end
    stable = _tree(tmp_path / "portfolio")
    repeated, unknown, cancelled = rebuild_hk_periods(pipeline, "9633", windows, None)
    assert not unknown and not cancelled and repeated[0]["status"] == "skipped"
    assert _tree(tmp_path / "portfolio") == stable


@pytest.mark.parametrize("subject_amended", (False, True))
def test_reference_revision_and_date_never_become_subject_facts(subject_amended: bool) -> None:
    """引用报告的修订和日期不影响主体；主体修订仍参与选优和候选。

    参数：subject_amended 为是否明确修订主体。
    返回：无。
    异常：日期、amended、选优或年度证据泄漏时断言失败。
    """
    subject = "2026中期報告（修訂版）" if subject_amended else "2026中期報告"
    title = subject + "及有關截至2025年12月31日止年度報告（修訂版）的補充資料"
    target = _hk_raw(document_id="target", title=title, category_text=_CATEGORY, filing_date="2026-09-24")
    later = _hk_raw(document_id="later", title="2026中期報告", category_text=_CATEGORY, filing_date="2026-09-25")
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(target,), local_annual_ends=(), read_head_meta=_head_meta,
    )
    assert len(selected.candidates) == 1 and not selected.uncertain_reports
    candidate = selected.candidates[0]
    assert candidate.amended is subject_amended and candidate.report_date is None
    assert hk_annual_end_date(title=title, category_text=_CATEGORY) is None
    best = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(target, later), local_annual_ends=(), read_head_meta=_head_meta,
    )
    assert best.candidates[0].source_id == ("target" if subject_amended else "later")


def test_subject_direct_date_and_annual_evidence_have_same_scope() -> None:
    """主体日期供证，附属中期及其日期不能否决主体年度或泄漏到未决。

    参数：无，标题均为合成边界。
    返回：无。
    异常：供证、直接日期或未知投影错用引用事实时断言失败。
    """
    annual = "截至2025年12月31日止年度報告及有關2025中期報告的補充資料"
    assert hk_annual_end_date(title=annual, category_text="年報") == date(2025, 12, 31)
    unknown = "2024/2026中期報告及有關截至2025年12月31日止年度報告的補充資料"
    selected = select_hkexnews_report_candidates(
        query=_QUERY, announcements=(_hk_raw(document_id="synthetic", title=unknown, category_text=_CATEGORY),),
        local_annual_ends=(), read_head_meta=_no_head,
    )
    assert len(selected.uncertain_reports) == 1
    assert selected.uncertain_reports[0].report_date is None


@pytest.mark.parametrize("failure", ("none", "conversion", "cancel", "publication"))
def test_real_fs_publication_retry_idempotency_and_seven_preserved(
    tmp_path: Path, official_raw: tuple[HkexnewsRawAnnouncement, ...],
    failure: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实 Fs 增量、失败/取消重试和幂等，原七份完整 meta/revision/文件不变。

    参数：tmp_path 为隔离仓储；official_raw 为完整官方行；failure 为合成故障位置；
        monkeypatch 仅在真实仓储提交前注入发布失败。
    返回：无。
    异常：来源、身份、manifest、摘要或字节不一致时断言失败；仓储异常按生产行为传播。
    """
    discovery = _OfficialRawDiscovery(tmp_path, tuple(raw for raw in official_raw if raw.document_id != "12345879"))
    pipeline = _build_pipeline(tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=_FakeConverter())
    seeded = pipeline.download(ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date, start_is_explicit=True)
    assert seeded["uncertain_reports"] == []
    before, assets = _stored_sources(pipeline)
    assert len(before) == 7
    discovery.raw = official_raw
    if failure != "none":
        state = _CancelState()
        converter = _CancelAfterConvertConverter(state) if failure == "cancel" else _FailingConverter(RuntimeError("合成转换失败"))
        broken = pipeline if failure == "publication" else _build_pipeline(
            tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=converter,
        )
        if failure == "publication":
            monkeypatch.setattr(broken.source_repository, "create_source_document", _fail_publication)
        try:
            failed = broken.download(
                ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date,
                start_is_explicit=True, cancel_checker=state if failure == "cancel" else None,
            )
            summary = failed["summary"]
            assert isinstance(summary, dict)
            assert summary["downloaded"] == 0
        except OSError as error:
            assert failure == "publication" and str(error) == "合成发布失败"
        finally:
            monkeypatch.undo()
        assert _stored_sources(pipeline) == (before, assets)
    added = pipeline.download(ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date, start_is_explicit=True)
    summary = added["summary"]
    assert isinstance(summary, dict) and summary["downloaded"] == 1 and summary["skipped"] == 7
    assert summary["failed"] == 0 and added["uncertain_reports"] == []
    after, after_assets = _stored_sources(pipeline)
    assert len(after) == 8
    assert tuple(entry for entry in after if entry.document_id in {entry.document_id for entry in before}) == before
    assert {doc: after_assets[doc] for doc in assets} == assets
    target = next(entry for entry in after if entry.source_meta["source_id"] == "12345879")
    meta = target.source_meta
    assert meta["source_title"] == _TITLE and meta["source_category"] == _CATEGORY
    assert meta["fiscal_year"] == 2026 and meta["amended"] is False
    assert meta["fiscal_period"] == meta["form_type"] == "H1"
    assert meta["covered_fiscal_periods"] == ["H1"]
    assert meta["report_date"] is meta["report_date_source"] is None
    manifest = _manifest_row(tmp_path, target.document_id, processed=False)
    for key in ("fiscal_year", "fiscal_period", "form_type", "report_date"):
        assert manifest[key] == meta[key]
    rows = added["filings"]
    assert isinstance(rows, list)
    row = next(row for row in rows if isinstance(row, dict) and row["document_id"] == target.document_id)
    assert isinstance(row, dict) and row["form_type"] == "H1" and row["covered_fiscal_periods"] == ["H1"]
    stable = _tree(tmp_path / "portfolio")
    calls = discovery.download_calls
    repeated = pipeline.download(ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date, start_is_explicit=True)
    repeated_summary = repeated["summary"]
    assert isinstance(repeated_summary, dict) and repeated_summary["downloaded"] == 0 and repeated_summary["skipped"] == 8
    assert discovery.download_calls == calls
    assert _stored_sources(pipeline) == (after, after_assets)
    assert _tree(tmp_path / "portfolio") == stable


def _fail_publication(req: SourceDocumentUpsertRequest, source_kind: SourceKind, *, batch: BatchToken) -> DocumentHandle:
    """在真实提交前确定性抛错。

    参数：req 为实际写入请求，source_kind 为来源类型，batch 为实际仓储事务。
    返回：不返回。
    异常：OSError，模拟发布前失败。
    """
    del req, source_kind, batch
    raise OSError("合成发布失败")


def _stored_sources(
    pipeline: CnPipeline,
) -> tuple[tuple[SourceMetaIntegrityReadEntry, ...], dict[str, dict[str, bytes]]]:
    """通过仓储契约读取完整 meta/revision/integrity 及全部真实资产。

    参数：pipeline 为隔离仓储宿主。
    返回：严格稳定视图和 document ID 到文件字节映射。
    异常：不完整、文件哈希错误时断言失败；仓储异常透传。
    """
    entries = pipeline.source_repository.read_source_meta_integrity_view("9633", SourceKind.FILING, batch=None)
    assets: dict[str, dict[str, bytes]] = {}
    for entry in entries:
        assert entry.integrity.status is SourceIntegrityStatus.COMPLETE
        with pipeline.source_repository.read_source_snapshot(
            "9633", entry.document_id, SourceKind.FILING, materialize_files=True,
        ) as snapshot:
            assert snapshot.source_meta == entry.source_meta and snapshot.revision == entry.integrity.revision
            assert snapshot.primary_filename is not None
            files: dict[str, bytes] = {}
            for descriptor in snapshot.files:
                with snapshot.get_source(descriptor.name).open() as stream:
                    files[descriptor.name] = stream.read()
                assert hashlib.sha256(files[descriptor.name]).hexdigest() == descriptor.sha256
                assert len(files[descriptor.name]) == descriptor.size
            assets[entry.document_id] = files
    return entries, assets


@pytest.mark.parametrize("category_present", (False, True))
@pytest.mark.parametrize("title,expected_date,confirmed", (
    (_TITLE, None, True),
    ("截至2026年6月30日止中期報告及有關截至2025年12月31日止年度報告的補充資料", "2026-06-30", True),
    ("2024/2026中期報告及有關截至2025年12月31日止年度報告的補充資料", None, False),
    ("有關截至2026年6月30日止中期報告的補充資料", None, False),
    ("截至2026年6月30日止中期報告及2026中期報告", None, False),
    ("截至2026年6月30日止中期報告及有關的補充資料", None, False),
    ("2026中期業績及有關截至2025年12月31日止年度報告的補充資料", None, False),
    ("2026中期業績公告及2026年報", None, False),
    ("2026中期报告及2026第二季报告", None, False),
    ("截至2025年12月31日止年度報告及2025第三季報告", None, False),
    ("2025中期報告及截至2025年12月31日止全年業績公告", None, False),
))
def test_same_version_local_reparse_uses_subject_and_preserves_identity(
    tmp_path: Path, title: str, expected_date: str | None, confirmed: bool, category_present: bool,
) -> None:
    """同 v3 本地重解析消费同一主体；未知不泄漏引用日期、不改资产。

    参数：tmp_path 为隔离仓储；title/expected_date/confirmed 为合成标题和期望日期及确认状态；
        category_present 控制来源可选分类是否存在。
    返回：无。
    异常：resolver、元数据/manifest、身份、业务资产或幂等漂移时断言失败。
    """
    raw = _hk_raw(document_id="synthetic", title="2026中期報告", category_text=_CATEGORY, filing_date="2026-09-24")
    discovery = _RawDiscovery(tmp_path, (raw,))
    pipeline = _build_pipeline(tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=_FakeConverter())
    pipeline.download(ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date, start_is_explicit=True)
    entry = _stored_sources(pipeline)[0][0]
    internal_id = entry.source_meta["internal_document_id"]
    assert isinstance(internal_id, str)
    batch = pipeline.batching_repository.begin_batch("9633")
    pipeline.source_repository.update_source_document(FilingUpdateRequest(
        ticker="9633", document_id=entry.document_id, internal_document_id=internal_id, form_type="H1",
        meta={**entry.source_meta, "source_title": title, "period_resolution_version": "hk-period-v3",
              "source_category": _CATEGORY if category_present else None,
              "report_date": "2000-01-01", "report_date_source": "source_title"},
    ), SourceKind.FILING, batch=batch)
    pipeline.batching_repository.commit_batch(batch)
    before, assets = _stored_sources(pipeline)
    assert local_hk_annual_ends(before) == {}
    windows = (PeriodDownloadWindow(fiscal_period="H1", start_date=_QUERY.start_date, end_date=_QUERY.end_date),)
    rows, unknown, cancelled = rebuild_hk_periods(pipeline, "9633", windows, None)
    assert not cancelled
    if not confirmed:
        assert not rows and len(unknown) == 1 and unknown[0].report_date is None
        assert _stored_sources(pipeline) == (before, assets)
    else:
        assert not unknown and len(rows) == 1 and rows[0]["report_date"] == expected_date
        after, after_assets = _stored_sources(pipeline)
        assert after_assets == assets
        meta = after[0].source_meta
        for key in ("internal_document_id", "document_id", "source_title", "document_version", "source_fingerprint"):
            assert meta[key] == before[0].source_meta[key]
        assert meta["report_date"] == expected_date
        assert meta["report_date_source"] == ("source_title" if expected_date is not None else None)
        assert meta["fiscal_year"] == 2026 and meta["fiscal_period"] == "H1"
        assert meta["covered_fiscal_periods"] == ["H1"] and meta["period_resolution_version"] == "hk-period-v3"
        assert _manifest_row(tmp_path, entry.document_id, processed=False)["report_date"] == expected_date
        stable = _tree(tmp_path / "portfolio")
        repeated, repeated_unknown, cancelled = rebuild_hk_periods(pipeline, "9633", windows, None)
        assert not cancelled and not repeated_unknown and repeated[0]["status"] == "skipped"
        assert _tree(tmp_path / "portfolio") == stable


def test_local_annual_subject_without_category_uses_same_scope(tmp_path: Path) -> None:
    """真实仓储中的可选分类为空时，年度供证仍从同一主体投影产生。

    参数：tmp_path 为隔离仓储。
    返回：无。
    异常：引用中期否决主体年度、日期泄漏或来源不完整时断言失败。
    """
    title = "截至2025年12月31日止年度報告及有關2025中期報告的補充資料"
    raw = _hk_raw(document_id="synthetic", title=title, category_text="年報", filing_date="2026-04-17")
    discovery = _RawDiscovery(tmp_path, (raw,))
    pipeline = _build_pipeline(tmp_path=tmp_path, discovery=discovery, hk_discovery=discovery, converter=_FakeConverter())
    pipeline.download(ticker="9633", start_date=_QUERY.start_date, end_date=_QUERY.end_date, start_is_explicit=True)
    entries, assets = _stored_sources(pipeline)
    assert len(entries) == 1
    entry = entries[0]
    internal_id = entry.source_meta["internal_document_id"]
    assert isinstance(internal_id, str)
    batch = pipeline.batching_repository.begin_batch("9633")
    pipeline.source_repository.update_source_document(FilingUpdateRequest(
        ticker="9633", document_id=entry.document_id, internal_document_id=internal_id, form_type="FY",
        meta={**entry.source_meta, "source_category": None},
    ), SourceKind.FILING, batch=batch)
    pipeline.batching_repository.commit_batch(batch)
    after, after_assets = _stored_sources(pipeline)
    assert after_assets == assets
    assert {key: anchor.end for key, anchor in local_hk_annual_ends(after).items()} == {entry.document_id: date(2025, 12, 31)}
