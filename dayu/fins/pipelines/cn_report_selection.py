"""CN/HK raw announcement 到财报候选的业务选择真源。

下载器只负责 HTTP、JSON 与 provider raw 字段归一；本模块负责产品级财报
筛选、语言过滤、财期/财年推断、同 period/year 去重以及
``CnReportCandidate`` 构造。
"""

from __future__ import annotations

import re
import calendar
from dataclasses import dataclass
from enum import Enum
from datetime import date
from collections.abc import Callable, Mapping
from typing import Final, Literal, Optional, TypeAlias

from dayu.fins.pipelines.cn_download_models import (
    HkAnnualAnchor, HkBodyEvidence, HkBodySelection, HkPeriodResolution,
    CN_FISCAL_PERIOD_ORDER,
    CnFiscalPeriod,
    CnAnnualReportFacts,
    CnReportCandidate,
    CnReportPublication,
    CnReportDiscoveryResult,
    CnReportHeadMeta,
    CnReportPeriodProjection,
    CnReportQuery,
    CninfoRawAnnouncement,
    HkexnewsRawAnnouncement,
)


from dayu.fins.pipelines.hk_fiscal_calendar import (
    annual_end_dates,
    fiscal_quarter_at,
    has_unresolved_end_date,
    report_end_date,
    relevant_annual_end_dates,
)

from dayu.contracts.json_value import JsonValue
from dayu.fins.download_contract import FinsDownloadUncertainReport
from dayu.fins.storage import SourceMetaIntegrityReadEntry, SourceIntegrityStatus
from dayu.fins.ticker_normalization import normalize_ticker, ticker_to_company_id

ReadHeadMeta: TypeAlias = Callable[[str], CnReportHeadMeta]
"""读取 PDF HEAD 元数据的窄 callable 类型。"""

_PERIOD_SORT_KEY: Final[dict[CnFiscalPeriod, int]] = {
    period: index for index, period in enumerate(CN_FISCAL_PERIOD_ORDER)
}

_CNINFO_TITLE_BLOCKLIST: Final[tuple[str, ...]] = (
    "摘要",
    "已取消",
    "已撤销",
    "撤回",
    "取消",
    "更正前",
    "募集说明书",
    "ESG",
    "可持续发展",
    "审计报告",
    "财务报表",
    "意见",
    "（英文）",
    "(英文)",
    "英文)",
    "英文）",
    "英文版",
    "英文简版",
    "英文简本",
    "english",
    "港股公告",
    "h股公告",
    "h股",
)
_CNINFO_REPORT_NOTICE_TITLE_TOKENS: Final[tuple[str, ...]] = (
    "公告",
    "提示性公告",
    "自愿性披露公告",
)
_CNINFO_REPORT_TITLE_TOKENS: Final[tuple[str, ...]] = (
    "年度报告",
    "年报",
    "半年度报告",
    "一季度报告",
    "第一季度报告",
    "三季度报告",
    "第三季度报告",
)
_CNINFO_TITLE_AMENDED_TOKENS: Final[tuple[str, ...]] = ("更正", "更正后", "修订", "补充", "修正")
_CNINFO_REPORT_BODY_TOKEN: Final[str] = "正文"
_CNINFO_TITLE_FY_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d{4})\s*年[年度]?\s*(年度报告|年报)")
_CNINFO_TITLE_FISCAL_YEAR_FALLBACK: Final[re.Pattern[str]] = re.compile(r"(\d{4})\s*年")

_HK_TITLE_AMENDED_TOKENS: Final[tuple[str, ...]] = (
    "更正",
    "修訂",
    "修订",
    "補充",
    "补充",
    "REVISED",
    "SUPPLEMENTAL",
)
_HK_ENGLISH_REPORT_TITLE_TOKENS: Final[tuple[str, ...]] = (
    "ANNUAL REPORT",
    "INTERIM REPORT",
    "QUARTERLY REPORT",
    "QUARTERLY RESULTS",
    "FIRST QUARTER",
    "SECOND QUARTER",
    "THIRD QUARTER",
    "FOURTH QUARTER",
)
_HK_CATEGORY_RESULTS_MARKERS: Final[tuple[str, ...]] = ("業績", "业绩", "RESULTS")
_HK_CATEGORY_REPORT_MARKERS: Final[tuple[str, ...]] = (
    "年報",
    "年报",
    "年度報告",
    "年度报告",
    "REPORT",
    "中期報告",
    "中期报告",
    "半年報",
    "半年报",
    "半年度報告",
    "半年度报告",
)
_HK_REPORT_FY_TOKENS: Final[tuple[str, ...]] = (
    "ANNUAL REPORT",
    "FULL YEAR REPORT",
    "FULL-YEAR",
    "FULL YEAR",
    "年報",
    "年报",
    "年度報告",
    "年度报告",
    "全年",
)
_HK_REPORT_H1_TOKENS: Final[tuple[str, ...]] = (
    "INTERIM REPORT",
    "HALF-YEAR REPORT",
    "HALF YEAR REPORT",
    "HALF-YEAR",
    "HALF YEAR",
    "中期報告",
    "中期报告",
    "半年報",
    "半年报",
    "半年度報告",
    "半年度报告",
    "半年",
)
_HK_REPORT_FORBIDDEN_RESULT_TOKENS: Final[tuple[str, ...]] = (
    "QUARTER",
    "RESULTS",
    "季度",
    "季業績",
    "季业绩",
)
_HK_QUARTER_LENGTH_TOKENS: Final[tuple[str, ...]] = (
    "三個月",
    "三个月",
    "3個月",
    "3个月",
    "THREE MONTHS",
    "3 MONTHS",
)
_HK_RESULTS_PERIOD_TOKENS: Final[dict[CnFiscalPeriod, tuple[str, ...]]] = {
    "Q1": (
        "Q1",
        "FIRST QUARTER",
        "FIRST QUARTERLY",
        "第一季度",
        "第一季",
        "一季度",
        "一季",
    ),
    "Q2": (
        "INTERIM RESULTS",
        "SECOND QUARTER",
        "SECOND QUARTERLY",
        "SIX MONTHS",
        "6 MONTHS",
        "HALF YEAR",
        "Q2",
        "第二季度",
        "第二季",
        "二季度",
        "二季",
        "六個月",
        "六个月",
        "半年",
        "中期業績",
        "中期业绩",
    ),
    "Q3": (
        "Q3",
        "THIRD QUARTER",
        "THIRD QUARTERLY",
        "NINE MONTHS",
        "9 MONTHS",
        "第三季度",
        "第三季",
        "三季度",
        "三季",
        "九個月",
        "九个月",
    ),
    "Q4": (
        "FINAL RESULTS",
        "FOURTH QUARTER",
        "FOURTH QUARTERLY",
        "TWELVE MONTHS",
        "12 MONTHS",
        "FULL YEAR",
        "Q4",
        "第四季度",
        "第四季",
        "四季度",
        "四季",
        "十二個月",
        "十二个月",
        "全年",
        "ANNUAL RESULTS",
        "末期業績",
        "末期业绩",
    ),
}
_HK_TITLE_YEAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"(20\d{2}|19\d{2})")
_HK_TITLE_CHINESE_YEAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"([零〇一二三四五六七八九]{4})年")
_HK_FISCAL_YEAR_LABEL: Final[re.Pattern[str]] = re.compile(
    r"FY\s*(19\d{2}|20\d{2})|(19\d{2}|20\d{2})\s*(?:財年|财年|FISCAL YEAR)",
    re.IGNORECASE,
)
_HK_CHINESE_DIGIT_TO_INT: Final[dict[str, int]] = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
# 只为能够完整解释的中文关系限定作用域；未识别的尾部不能被截掉。
_HK_CHINESE_REPORT: Final[str] = r"(?:中期[報报]告|半年度[報报]告|半年[報报]|年度[報报]告|年[報报])"
_HK_SCOPED_YEAR: Final[str] = r"(?:19\d{2}|20\d{2}|[零〇一二三四五六七八九]{4})年?"
_HK_SCOPED_REVISION: Final[str] = r"(?:更正|修[訂订]|[補补]充)(?:[後后])?(?:版)?"
_HK_SCOPED_REPORT: Final[re.Pattern[str]] = re.compile(
    rf"(?:{_HK_SCOPED_REVISION})?"
    rf"(?:{_HK_SCOPED_YEAR}|截至(?:19|20)\d{{2}}年\d{{1,2}}月\d{{1,2}}日止"
    r"(?:(?:六[個个]月|年度)[之的]?)?)"
    rf"{_HK_CHINESE_REPORT}"
    rf"(?:{_HK_SCOPED_REVISION}|（{_HK_SCOPED_REVISION}）|\({_HK_SCOPED_REVISION}\))?"
)
_HK_SUPPLEMENT_RELATION: Final[re.Pattern[str]] = re.compile(
    r"(?P<subject>.+)及有[關关](?P<reference>.+)的[補补]充[資资]料"
)
# 竞争主体共用同一词形，不随报告/业绩的前后顺序改变；季报告包含既有季度信号的简称。
_HK_CHINESE_QUARTER: Final[str] = r"(?:第?[一二三四]季(?:度)?|季度)"
_HK_CHINESE_PERIOD_SUBJECT: Final[str] = (
    rf"(?:{_HK_CHINESE_REPORT}|{_HK_CHINESE_QUARTER}[報报]告|"
    rf"(?:中期|全年|末期|{_HK_CHINESE_QUARTER})[業业][績绩]|[業业][績绩](?:公告|[報报]告))"
)
_HK_UNRESOLVED_RELATION: Final[re.Pattern[str]] = re.compile(
    # 补充资料指向引用对象；悬空连接词没有对象。普通前置“有关”和非财期附件不是歧义证据。
    rf"[補补]充[資资]料|[及與与和](?:有[關关])?$|"
    # 连接词两侧都有明确财期主体才构成竞争，不以裸连接词拒绝普通附载资料。
    rf"{_HK_CHINESE_PERIOD_SUBJECT}.*[及與与和].*{_HK_CHINESE_PERIOD_SUBJECT}"
)


def hk_report_subject_title(title: str) -> str | None:
    """确定标题中唯一主体报告的语义文本，不改写原始来源。

    参数：title 为完整来源标题。
    返回：普通标题原文，或完整识别“主体及有关另一报告的补充资料”后的主体。
        完整补充关系之外，去除空白后按以下有限词形检测竞争主体：
        报告为中期报告、半年度报告、半年报、年度报告、年报；季度报告为季度词形加报告。
        季度词形为可省略“第”的“一/二/三/四”加“季/季度”，或单独“季度”。
        业绩为“中期/全年/末期”或季度词形加业绩，以及业绩公告、业绩报告；
        “报、业、绩”各字支持简繁字符。连接关系仅为“及/與/与/和”，两侧命中上述词形时
        不论顺序、是否同年同期间均返回 None；多个上述年报/中报词形也返回 None。
        未支持词形或分隔符的复合标题不保证被识别为竞争主体，仍可能沿既有分类、年份等
        约束确认，不能一律视为未知；例如无公告/报告后缀的年度/半年度/时长加业绩、
        首季、阿拉伯数字季度词形或顿号组合。
        已识别报告引用或补充关系但不能完整解释、悬空连接词及独立补充引用也返回 None。
        普通前置“有关”或“及有关资料”没有第二财期主体或补充引用信号时保留完整原文，
        继续交既有约束判断；“年度报告及补充资料”修饰对象不明，返回 None。
    异常：无；完整关系隔离仅支持有明确年份或截止日的上述中文关系，不解释任意自然语言附件。
    """
    compact = re.sub(r"\s+", "", title)
    relation = _HK_SUPPLEMENT_RELATION.fullmatch(compact)
    if relation is not None:
        subject, reference = relation.group("subject", "reference")
        if all(
            _HK_SCOPED_REPORT.fullmatch(part) is not None
            and len(_hk_title_years(part)) == 1
            and not has_unresolved_end_date(part)
            for part in (subject, reference)
        ):
            # 同年同财期仍可能是在补充主体本身，不能宣称附属的是另一份报告。
            if _hk_title_years(subject) == _hk_title_years(reference) and (
                _classify_hk_period_projection(title=subject, category_text=subject)
                == _classify_hk_period_projection(title=reference, category_text=reference)
            ):
                return None
            return subject
        return None
    if _HK_UNRESOLVED_RELATION.search(compact) or len(re.findall(_HK_CHINESE_REPORT, compact)) > 1:
        return None
    return title


def hk_report_end_date(title: str) -> date | None:
    """只从唯一主体标题提取直接截止日，供候选、未决、年度与重解析共用。

    参数：title 为完整来源标题。
    返回：主体唯一有效截止日；主体不明或没有直接日期时返回 None。
    异常：无，不从附属引用或披露日期补造报告日期。
    """
    subject = hk_report_subject_title(title)
    return report_end_date(subject) if subject is not None else None


def select_cninfo_report_candidates(
    *,
    query: CnReportQuery,
    announcements_by_period: Mapping[CnFiscalPeriod, tuple[CninfoRawAnnouncement, ...]],
    read_head_meta: Callable[[str], CnReportHeadMeta],
    annual_facts_by_source: Mapping[str, CnAnnualReportFacts],
) -> tuple[CnReportCandidate, ...]:
    """从巨潮 raw announcements 选择财报候选。

    Args:
        query: 单次 CN download 查询。
        announcements_by_period: downloader 按巨潮 category 拉回的 raw 公告。
        read_head_meta: 读取 PDF HEAD 元数据的 HTTP 边界函数。

    Returns:
        已按 fiscal year 降序、period 稳定顺序排序的候选 tuple。

    Raises:
        无。
    """

    eligible_annual = tuple(item for item in announcements_by_period.get("FY", ())
                            if "FY" in query.discovery_periods
                            and query.start_date <= item.announcement_date <= query.end_date
                            and is_cninfo_report_title_admissible(item.title))
    if len({item.announcement_id for item in eligible_annual}) != len(eligible_annual):
        raise ValueError("年度 raw 来源重复")
    if set(annual_facts_by_source) != {item.announcement_id for item in eligible_annual}:
        raise ValueError("年度原文事实必须精确覆盖准入来源")
    per_period_year: dict[tuple[CnFiscalPeriod, int], list[CninfoRawAnnouncement]] = {}
    for period in query.discovery_periods:
        for item in announcements_by_period.get(period, ()):
            if not is_cninfo_report_title_admissible(item.title):
                continue
            if period == "FY":
                if not query.start_date <= item.announcement_date <= query.end_date:
                    continue
                facts = annual_facts_by_source[item.announcement_id]
                if facts.kind == "summary":
                    continue
                fiscal_year = facts.fiscal_year
            else:
                fiscal_year = _infer_cninfo_fiscal_year(item.title, item.announcement_date)
            if fiscal_year is None:
                continue
            per_period_year.setdefault((period, fiscal_year), []).append(item)

    candidates: list[CnReportCandidate] = []
    for (period, fiscal_year), items in per_period_year.items():
        best = _pick_best_cninfo_announcement(items)
        if best is None:
            continue
        candidates.append(
            _build_cninfo_candidate(
                announcement=best,
                period=period,
                fiscal_year=fiscal_year,
                head_meta=read_head_meta(best.source_url),
            )
        )
    candidates.sort(key=lambda item: (-item.fiscal_year, _PERIOD_SORT_KEY[item.period_projection.identity_period]))
    return tuple(candidates)


def select_hkexnews_report_candidates(
    *,
    query: CnReportQuery,
    announcements: tuple[HkexnewsRawAnnouncement, ...],
    local_annual_ends: tuple[HkAnnualAnchor, ...],
    read_head_meta: Callable[[str], CnReportHeadMeta],
    body_evidence: Mapping[str, HkBodyEvidence] | None = None,
) -> HkReportSelection:
    """从披露易 raw announcements 选择财报候选。

    Args:
        query: 单次 HK download 查询。
        announcements: downloader 拉回的 raw 公告。
        read_head_meta: 读取 PDF HEAD 元数据的 HTTP 边界函数。
        local_annual_ends: 同公司可信本地年度证据；body_evidence 为按原来源绑定的直接正文事实。

    Returns:
        按财年/财期排序的完整候选和按来源排序的独立未知集合。

    Raises:
        ValueError: 同 source ID 核心事实冲突或未知引用非法时抛出。
        Exception: HEAD 边界的原异常透传。
    """

    bodies = body_evidence if body_evidence is not None else {}
    resolutions: dict[str, HkPeriodResolution] = {}
    grouped: dict[tuple[CnFiscalPeriod, int], list[HkexnewsRawAnnouncement]] = {}
    projection_by_document_id: dict[str, CnReportPeriodProjection] = {}
    # 先校验全响应的同来源冲突，再以同一查询窗集合供年度证据与候选选择。
    # 可信本地年度是独立输入，不按本次远端披露日期窗口裁掉。
    scoped = tuple(
        item for item in _deduplicate_hk_announcements(announcements)
        if query.start_date <= item.filing_date <= query.end_date
    )
    by_id = {item.document_id: item for item in scoped}
    for key, evidence in bodies.items():
        item = by_id.get(key)
        if (item is None or evidence.source_id != key or evidence.source_url != item.source_url
            or evidence.ticker != query.normalized_ticker or evidence.facts.ticker != query.normalized_ticker):
            raise ValueError("正文输入与本次公司/官方来源不匹配")
    title_anchors = tuple(HkAnnualAnchor(end, item.document_id, item.source_url)
        for item in scoped if (end := hk_annual_end_date(title=item.title, category_text=item.category_text)) is not None)
    # 先确认全部正文年度，再构建统一锚，不能由输入顺序决定中期结果。
    body_anchors = tuple(HkAnnualAnchor(e.facts.end, e.source_id, e.source_url, e.publication, e.facts)
        for item in scoped if (e := bodies.get(item.document_id)) is not None
        and e.facts.kind == "annual"
        and resolve_hk_report_period(title=item.title, category_text=item.category_text, annual_ends=(), body=e) is not None)
    anchors = _merge_hk_annual_anchors((*local_annual_ends, *title_anchors, *body_anchors))
    annual_ends = tuple(sorted({anchor.end for anchor in anchors}))
    uncertain: list[FinsDownloadUncertainReport] = []
    for item in scoped:
        if _is_english_hk_announcement(item):
            continue
        body = bodies.get(item.document_id)
        outcome = (resolve_hk_body_period_state(item.title, item.category_text, annual_ends, body, anchors)
            if body is not None else resolve_hk_report_period(
                title=item.title, category_text=item.category_text, annual_ends=annual_ends))
        if not isinstance(outcome, HkPeriodResolution):
            if _has_hk_unresolved_report_signal(title=item.title, category_text=item.category_text):
                end = hk_report_end_date(item.title)
                if isinstance(outcome, HkBodyPeriodPartial) and outcome.report_date is not None:
                    end = outcome.report_date
                uncertain.append(FinsDownloadUncertainReport(
                    source_id=item.document_id, filing_date=item.filing_date,
                    report_date=end.isoformat() if end is not None else None,
                    existing_document_id=None, reason_category="uncertain_hk_period",
                ))
            continue
        facts = outcome
        fiscal_year, period_projection = facts.fiscal_year, facts.projection
        resolutions[item.document_id] = facts
        if period_projection.identity_period not in query.discovery_periods:
            continue
        projection_by_document_id[item.document_id] = period_projection
        grouped.setdefault((period_projection.identity_period, fiscal_year), []).append(item)

    candidates: list[CnReportCandidate] = []
    for (period, fiscal_year), items in grouped.items():
        best = _pick_best_hk_announcement(items)
        if best is None:
            continue
        candidates.append(
            _build_hk_candidate(
                announcement=best,
                period_projection=projection_by_document_id[best.document_id],
                fiscal_year=fiscal_year,
                head_meta=read_head_meta(best.source_url),
                resolution=resolutions[best.document_id],
            )
        )
    candidates.sort(key=lambda item: (-item.fiscal_year, _PERIOD_SORT_KEY[item.period_projection.identity_period]))
    return HkReportSelection(tuple(candidates), tuple(sorted(uncertain, key=lambda r: (r.filing_date or "", r.source_id))), tuple(HkBodySelection(bodies[c.source_id], resolutions[c.source_id]) for c in candidates if c.report_date_source == "source_document"))


def is_cninfo_report_title_admissible(title: str) -> bool:
    """判断巨潮标题是否命中财报候选排除规则。

    Args:
        title: 公告标题。

    Returns:
        准入返回 `True`。

    Raises:
        无。
    """

    lowered = title.lower()
    if any(token.lower() in lowered for token in _CNINFO_TITLE_BLOCKLIST):
        return False
    if _has_cninfo_report_language_marker(title):
        return False
    has_report_title = any(token in title for token in _CNINFO_REPORT_TITLE_TOKENS)
    has_notice_title = any(token in title for token in _CNINFO_REPORT_NOTICE_TITLE_TOKENS)
    return not (has_report_title and has_notice_title)


def _has_cninfo_report_language_marker(title: str) -> bool:
    """判断巨潮财报标题是否带英文语言标记。

    Args:
        title: 公告标题。

    Returns:
        带英文语言标记时返回 `True`。

    Raises:
        无。
    """

    if "英文" not in title:
        return False
    return any(token in title for token in _CNINFO_REPORT_TITLE_TOKENS)


def _infer_cninfo_fiscal_year(title: str, announcement_date: str) -> Optional[int]:
    """从巨潮标题与披露日期推断财年。

    Args:
        title: 公告标题。
        announcement_date: 披露日期。

    Returns:
        推断财年；无法解析返回 `None`。

    Raises:
        无。
    """

    matched = _CNINFO_TITLE_FY_PATTERN.search(title)
    if matched is not None:
        return int(matched.group(1))
    fallback = _CNINFO_TITLE_FISCAL_YEAR_FALLBACK.search(title)
    if fallback is not None:
        return int(fallback.group(1))
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", announcement_date):
        return int(announcement_date[:4])
    return None


def _pick_best_cninfo_announcement(items: list[CninfoRawAnnouncement]) -> Optional[CninfoRawAnnouncement]:
    """从同一巨潮 fiscal period/year 中挑选最佳公告。

    Args:
        items: 同组 raw 公告。

    Returns:
        最佳公告；空列表返回 `None`。

    Raises:
        无。
    """

    if not items:
        return None

    return max(items, key=_cninfo_announcement_sort_key)


def _cninfo_announcement_sort_key(announcement: CninfoRawAnnouncement) -> tuple[bool, str, bool, str, str]:
    """在修订状态及公告日期相同时优先完整报告，并稳定裁决平手。

    Args:
        announcement: 已通过财报标题与语言过滤的巨潮公告。

    Returns:
        修订优先、较新日期优先、非正文优先及来源身份组成的排序键。
        来源 ID 和 URL 仅用于确定性平手，不代表版本先后或报告质量。

    Raises:
        无。
    """

    # 正文仍可作为唯一历史来源；不能让旧全文盖过真正修订或较新报告。
    return (
        _is_cninfo_amended_title(announcement.title),
        announcement.announcement_date,
        _CNINFO_REPORT_BODY_TOKEN not in announcement.title,
        announcement.announcement_id,
        announcement.source_url,
    )


def _is_cninfo_amended_title(title: str) -> bool:
    """统一判定巨潮报告修订标记，供排序与候选投影共用。

    Args:
        title: 已归一化的公告标题。

    Returns:
        标题包含修订标记时返回 True。

    Raises:
        无。
    """

    return any(token in title for token in _CNINFO_TITLE_AMENDED_TOKENS)


def _build_cninfo_candidate(
    *,
    announcement: CninfoRawAnnouncement,
    period: CnFiscalPeriod,
    fiscal_year: int,
    head_meta: CnReportHeadMeta,
) -> CnReportCandidate:
    """把巨潮 raw announcement 构造为候选对象。

    Args:
        announcement: 已选择 raw 公告。
        period: 财期。
        fiscal_year: 财年。
        head_meta: PDF HEAD 元数据。

    Returns:
        CNInfo candidate。

    Raises:
        无。
    """

    return CnReportCandidate(
        provider="cninfo",
        source_id=announcement.announcement_id,
        source_url=announcement.source_url,
        title=announcement.title,
        language="zh",
        filing_date=announcement.announcement_date,
        fiscal_year=fiscal_year,
        fiscal_year_source="source_document" if period == "FY" else "title_or_category_inferred",
        period_projection=CnReportPeriodProjection(identity_period=period, covered_periods=(period,)),
        amended=_is_cninfo_amended_title(announcement.title),
        content_length=head_meta.content_length,
        etag=head_meta.etag,
        last_modified=head_meta.last_modified,
    )


def _infer_hk_fiscal_year(title: str, annual_ends: tuple[date, ...] = ()) -> int | None:
    """从标题和有依据的年结日识别财年，日期标题采用财年结束年份。

    Args:
        title: 公告标题。
        annual_ends: 同公司年度截止日证据。

    Returns:
        推断财年；无法解析返回 `None`。

    Raises:
        无。
    """

    end = report_end_date(title)
    if end is not None:
        if end in annual_end_dates((title,)):
            return end.year
        calendar_period = fiscal_quarter_at(end, annual_ends)
        return calendar_period[0] if calendar_period is not None else None
    years = _hk_title_years(title)
    return next(iter(years)) if len(years) == 1 else None


def _hk_title_years(title: str) -> set[int]:
    """参数为原始标题；返回所有有效中英文年份；无异常，不按出现顺序挑年份。"""
    years = {int(value) for value in _HK_TITLE_YEAR_PATTERN.findall(title)}
    years.update(
        year
        for value in _HK_TITLE_CHINESE_YEAR_PATTERN.findall(title)
        if (year := _parse_chinese_digit_year(value)) is not None
    )
    return years


def resolve_hk_report_period(
    *,
    title: str,
    category_text: str,
    annual_ends: tuple[date, ...],
    body: HkBodyEvidence | None = None,
    annual_anchors: tuple[HkAnnualAnchor, ...] = (),
) -> HkPeriodResolution | None:
    """为发现与本地重建统一解析港股财年和财期。

    参数：title/category_text 为来源事实；annual_ends 为同公司年度截止日；body/body_anchors 为本条正文与年度正文来源。
    返回：财年和身份/覆盖投影；缺少或冲突返回 None。异常：无。
    """
    if body is not None:
        outcome = resolve_hk_body_period_state(title, category_text, annual_ends, body, annual_anchors)
        return outcome if isinstance(outcome, HkPeriodResolution) else None
    subject = hk_report_subject_title(title)
    if subject is None:
        return None
    title = subject
    if has_unresolved_end_date(title):
        return None
    # 财年区间简写与普通日期不同；没有明确命名规则时不选择区间中的某一年。
    if re.search(r"\d{4}\s*/\s*\d{2,4}(?![/\d])", title):
        return None
    end = report_end_date(title)
    annual_ends = relevant_annual_end_dates(end, annual_ends) if end is not None else annual_ends
    projection = _classify_hk_period_projection(
        title=title,
        category_text=category_text,
        annual_ends=annual_ends,
    )
    year = _infer_hk_fiscal_year(title, annual_ends)
    end = report_end_date(title)
    if year is None and end is not None and projection is not None and not annual_ends:
        ordinal = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "H1": 2, "FY": 4}[projection.identity_period]
        year = end.year + (end.month + (4 - ordinal) * 3 - 1) // 12
    labelled = {int(value) for match in _HK_FISCAL_YEAR_LABEL.finditer(title) for value in match.groups() if value}
    if labelled and (len(labelled) != 1 or year not in labelled):
        return None
    if not labelled and len(_hk_title_years(title)) > 1:
        return None
    if year is None or projection is None:
        return None
    return HkPeriodResolution(year, projection, end.isoformat() if end is not None else None,
                              "source_title" if end is not None else None, "title_or_category_inferred")


def _parse_chinese_digit_year(value: str) -> int | None:
    """解析逐位中文数字年份。

    Args:
        value: 四位中文数字年份。

    Returns:
        公历年份；格式异常返回 `None`。

    Raises:
        无。
    """

    if len(value) != 4:
        return None
    digits: list[str] = []
    for char in value:
        digit = _HK_CHINESE_DIGIT_TO_INT.get(char)
        if digit is None:
            return None
        digits.append(str(digit))
    year = int("".join(digits))
    if 1900 <= year <= 2099:
        return year
    return None


def _classify_hk_period_projection(
    *,
    title: str,
    category_text: str,
    annual_ends: tuple[date, ...] = (),
) -> CnReportPeriodProjection | None:
    """先按披露易分类确定报告家族，再从分类与标题投影身份和覆盖财期。

    Args:
        title: 公告标题。
        category_text: 分类文本。
        annual_ends: 同公司有明确截止日的年度业绩证据。

    Returns:
        分类与标题共同形成的财期投影；任何歧义返回 ``None``。

    Raises:
        无。
    """

    if has_unresolved_end_date(title):
        return None
    family = _hk_report_family(category_text)
    if family is None:
        return None
    normalized_material_facts = f"{category_text} {title}".upper()
    if family == "report":
        has_h1 = _contains_any_token(normalized_material_facts, _HK_REPORT_H1_TOKENS)
        facts_without_h1_phrases = _remove_tokens(normalized_material_facts, _HK_REPORT_H1_TOKENS)
        has_fy = _contains_any_token(facts_without_h1_phrases, _HK_REPORT_FY_TOKENS)
        has_results_period = _contains_any_token(
            normalized_material_facts,
            _HK_REPORT_FORBIDDEN_RESULT_TOKENS,
        )
        if has_results_period or has_fy == has_h1:
            return None
        identity: CnFiscalPeriod = "FY" if has_fy else "H1"
        end = report_end_date(title)
        if end is not None and annual_ends:
            calendar_period = fiscal_quarter_at(end, annual_ends)
            if calendar_period is None or calendar_period[1] != (4 if has_fy else 2):
                return None
        return CnReportPeriodProjection(identity_period=identity, covered_periods=(identity,))

    matched: set[CnFiscalPeriod] = {
        period
        for period, tokens in _HK_RESULTS_PERIOD_TOKENS.items()
        if _contains_any_token(normalized_material_facts, tokens)
    }
    end = report_end_date(title)
    calendar_period = fiscal_quarter_at(end, annual_ends) if end is not None else None
    if calendar_period is not None:
        if not matched and not _contains_any_token(normalized_material_facts, _HK_QUARTER_LENGTH_TOKENS):
            return None
        calendar_identity: CnFiscalPeriod = ("Q1", "Q2", "Q3", "Q4")[calendar_period[1] - 1]
        matched.add(calendar_identity)
    elif end is not None and annual_ends:
        return None
    result_identity = _resolve_hk_results_identity(matched)
    if result_identity is None:
        return None
    if result_identity == "Q2":
        return CnReportPeriodProjection(identity_period="Q2", covered_periods=("H1", "Q2"))
    if result_identity == "Q4":
        return CnReportPeriodProjection(identity_period="Q4", covered_periods=("FY", "Q4"))
    return CnReportPeriodProjection(identity_period=result_identity, covered_periods=(result_identity,))


def _contains_any_token(text: str, tokens: tuple[str, ...]) -> bool:
    """判断大写文本是否包含任一业务 token。

    Args:
        text: 已大写的待匹配文本。
        tokens: 可匹配 token。

    Returns:
        命中任一 token 返回 ``True``。

    Raises:
        无。
    """

    return any(
        (
            bool(re.search(r"(?<![A-Z])" + token + r"(?![A-Z0-9])", text))
            if re.fullmatch(r"Q[1-4]", token)
            else token.upper() in text
        )
        for token in tokens
    )


def _remove_tokens(text: str, tokens: tuple[str, ...]) -> str:
    """移除已确认为更具体语义的短语，避免中文子串产生伪冲突。

    Args:
        text: 已大写的事实文本。
        tokens: 需要优先消费的更具体短语。

    Returns:
        移除 token 后的文本。

    Raises:
        无。
    """

    remaining = text
    for token in tokens:
        remaining = remaining.replace(token.upper(), " ")
    return remaining


def _resolve_hk_results_identity(matched: set[CnFiscalPeriod]) -> CnFiscalPeriod | None:
    """只接受唯一季度事实；期间长度三个月不产生独立季度信号。

    Args:
        matched: 标题命中的季度候选集合。

    Returns:
        唯一季度身份；缺失或相互冲突返回 ``None``。

    Raises:
        无。
    """

    return next(iter(matched)) if len(matched) == 1 else None


def _deduplicate_hk_announcements(
    announcements: tuple[HkexnewsRawAnnouncement, ...],
) -> tuple[HkexnewsRawAnnouncement, ...]:
    """按 source ID 去重，并对同 ID 核心事实冲突 fail closed。

    Args:
        announcements: provider 返回的 raw 公告。

    Returns:
        保持首次出现顺序的唯一公告。

    Raises:
        ValueError: 同一 document ID 的核心事实不一致时抛出。
    """

    unique: dict[str, HkexnewsRawAnnouncement] = {}
    for announcement in announcements:
        previous = unique.get(announcement.document_id)
        if previous is None:
            unique[announcement.document_id] = announcement
            continue
        if _hk_announcement_core_facts(previous) != _hk_announcement_core_facts(announcement):
            raise ValueError(f"披露易同一 document_id 核心事实冲突: {announcement.document_id}")
    return tuple(unique.values())


def _hk_announcement_core_facts(
    announcement: HkexnewsRawAnnouncement,
) -> tuple[str, str, str, str, str]:
    """提取同一 HK source ID 必须一致的 provider 核心事实。

    Args:
        announcement: raw 公告。

    Returns:
        URL、分类、标题、披露日期与语言组成的不可变事实 tuple。

    Raises:
        无。
    """

    return (
        announcement.source_url,
        announcement.category_text,
        announcement.title,
        announcement.filing_date,
        announcement.language,
    )


def _pick_best_hk_announcement(items: list[HkexnewsRawAnnouncement]) -> HkexnewsRawAnnouncement | None:
    """从同一披露易 fiscal period/year 中挑选最佳公告。

    Args:
        items: 同组 raw 公告。

    Returns:
        最佳公告；空列表返回 `None`。

    Raises:
        ValueError: 已确认公告没有唯一主体时抛出。
    """

    if not items:
        return None

    return max(items, key=_hk_announcement_sort_key)


def _hk_announcement_sort_key(item: HkexnewsRawAnnouncement) -> tuple[bool, str]:
    """以主体修订性质及披露日期为同财期公告选优。

    参数：item 为已确认财期的 raw 公告。
    返回：修订优先、日期次之的排序键。
    异常：唯一主体不成立时抛 ValueError，拒绝用附属修订参与选优。
    """
    return _is_hk_amended_title(item.title), item.filing_date


def _is_hk_amended_title(title: str) -> bool:
    """判断披露易标题是否为更正/修订版本。

    Args:
        title: 已确认财期公告的完整标题。

    Returns:
        是修订版本返回 `True`。

    Raises:
        ValueError: 唯一主体不成立。
    """

    subject = hk_report_subject_title(title)
    if subject is None:
        raise ValueError("已确认报告必须有唯一主体标题")
    upper = subject.upper()
    return any(token.upper() in upper for token in _HK_TITLE_AMENDED_TOKENS)


def _is_english_hk_announcement(announcement: HkexnewsRawAnnouncement) -> bool:
    """判断披露易公告是否为英文财报副本。

    Args:
        announcement: raw 公告。

    Returns:
        英文财报副本返回 `True`。

    Raises:
        无。
    """

    if announcement.language == "en":
        return True
    subject = hk_report_subject_title(announcement.title)
    # 无唯一主体的来源仍按原有语言门槛处理，不能借附属关系让英文来源准入。
    title = subject if subject is not None else announcement.title
    if _looks_like_english_report_text(title):
        return True
    if not _contains_cjk(title) and _looks_like_english_report_text(
        f"{title} {announcement.category_text}"
    ):
        return True
    return False


def _looks_like_english_report_text(text: str) -> bool:
    """判断文本是否像英文财报标题。

    Args:
        text: 待判断文本。

    Returns:
        像英文财报标题时返回 `True`。

    Raises:
        无。
    """

    upper = text.upper()
    return any(token in upper for token in _HK_ENGLISH_REPORT_TITLE_TOKENS)


def _contains_cjk(text: str) -> bool:
    """判断文本是否包含 CJK 字符。

    Args:
        text: 待判断文本。

    Returns:
        包含 CJK 字符返回 `True`。

    Raises:
        无。
    """

    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _build_hk_candidate(
    *,
    announcement: HkexnewsRawAnnouncement,
    period_projection: CnReportPeriodProjection,
    fiscal_year: int,
    head_meta: CnReportHeadMeta,
    resolution: HkPeriodResolution,
) -> CnReportCandidate:
    """把披露易 raw announcement 构造为候选对象。

    Args:
        announcement: 已选择 raw 公告。
        period_projection: 已分类的身份与覆盖财期。
        fiscal_year: 财年。
        head_meta: PDF HEAD 元数据。

    Returns:
        HKEXNews candidate。

    Raises:
        ValueError: 已确认公告没有唯一主体时抛出。
    """

    return CnReportCandidate(
        provider="hkexnews",
        source_id=announcement.document_id,
        source_url=announcement.source_url,
        title=announcement.title,
        language=announcement.language,
        category_text=announcement.category_text,
        report_date=resolution.report_date,
        report_date_source=resolution.report_date_source,
        filing_date=announcement.filing_date,
        fiscal_year=fiscal_year,
        fiscal_year_source=resolution.fiscal_year_source,
        period_projection=period_projection,
        amended=_is_hk_amended_title(announcement.title),
        content_length=head_meta.content_length,
        etag=head_meta.etag,
        last_modified=head_meta.last_modified,
    )


def _hk_report_family(category_text: str) -> Literal["report", "results"] | None:
    """只从官方分类确定唯一财报家族，供期间分类和未决资格共同使用。

    参数：category_text 为来源原分类，不用标题信号否决已知分类。
    返回：唯一报告或业绩家族；缺失或冲突时返回 None。
    异常：无。
    """
    category = category_text.upper()
    results = _contains_any_token(category, _HK_CATEGORY_RESULTS_MARKERS)
    report = _contains_any_token(category, _HK_CATEGORY_REPORT_MARKERS)
    if results == report:
        return None
    return "results" if results else "report"


def _has_hk_unresolved_report_signal(*, title: str, category_text: str) -> bool:
    """判断无法解期的来源是否已有报告标题信号，应投影为未决。

    参数：title 为原标题；category_text 为来源原分类。
    返回：属于唯一财报家族且命中既有标题信号时为 True，不代表期间已确认。
    异常：无。
    """
    if _hk_report_family(category_text) is None:
        return False
    subject = hk_report_subject_title(title)
    # unknown 的资格只表示原文提到报告；主体不明时仍应保留可追溯未决。
    facts = (subject if subject is not None else title).upper()
    return (
        _contains_any_token(facts, _HK_REPORT_FY_TOKENS + _HK_REPORT_H1_TOKENS + _HK_CATEGORY_RESULTS_MARKERS + _HK_QUARTER_LENGTH_TOKENS)
        or any(_contains_any_token(facts, tokens) for tokens in _HK_RESULTS_PERIOD_TOKENS.values())
    )


def hk_annual_end_date(*, title: str, category_text: str) -> date | None:
    """提取原始年度报告或全年业绩的直接截止日。

    参数：title 为原标题；category_text 为来源原分类。
    返回：财年与期间无歧义的 FY/全年 Q4 直接截止日；没有唯一年度事实时为 None。
    异常：无，不按语言排除可信年度证据。"""
    # 年度源独立通过统一解析的完整歧义校验，不向外部或自身借用年度证据。
    # 未决标题资格不参与供证，不能否决已确认的官方末期业绩事实。
    facts = resolve_hk_report_period(title=title, category_text=category_text, annual_ends=())
    if facts is None or facts.projection.identity_period not in {"FY", "Q4"}:
        return None
    return hk_report_end_date(title)


def _merge_hk_annual_anchors(anchors: tuple[HkAnnualAnchor, ...]) -> tuple[HkAnnualAnchor, ...]:
    """合并同一官方来源的年度见证，保留已核原件的最完整引用。

    参数：anchors 为本地、标题和正文的同公司年度见证。
    返回：每个来源一次的有序锚。异常：ValueError 为同来源日期或 URL 冲突。
    """
    by_source: dict[str, HkAnnualAnchor] = {}
    for anchor in anchors:
        previous = by_source.get(anchor.source_id)
        if previous is not None and (previous.end != anchor.end or previous.source_url != anchor.source_url):
            raise ValueError("同一 HK 年度来源的截止日或 URL 冲突")
        if previous is None or (anchor.body_facts is not None and previous.body_facts is None) or (
            anchor.publication is not None and previous.publication is None):
            by_source[anchor.source_id] = anchor
    return tuple(by_source.values())


def local_hk_annual_ends(entries: tuple[SourceMetaIntegrityReadEntry, ...], body_evidence: tuple[HkBodyEvidence, ...] = ()) -> dict[str, HkAnnualAnchor]:
    """从同窗原始来源与完整性分类取得可信年度证据。

    参数：entries 为同一稳定根元数据与完整性观察，body_evidence 为已核原件的绑定事实；分类缺失只用主体标题。
    返回：可信同公司原始年度文档 ID 到直接截止日的映射。
    异常：必填来源文本缺失原样抛 KeyError；字段类型或文本非法抛 ValueError。"""
    result: dict[str, HkAnnualAnchor] = {}
    for entry in entries:
        meta = entry.source_meta
        if entry.integrity.status is not SourceIntegrityStatus.COMPLETE:
            continue
        if meta.get("source_provider") != "hkexnews" or meta.get("ingest_method") != "download":
            continue
        if type(meta.get("is_deleted")) is not bool:
            raise ValueError("HK source is_deleted must be bool")
        if meta["is_deleted"]:
            continue
        ticker = _hk_source_text(meta, "ticker")
        company_id = _hk_source_text(meta, "company_id")
        if ticker != entry.integrity.ticker or company_id != ticker_to_company_id(normalize_ticker(ticker)):
            continue
        title = _hk_source_text(meta, "source_title")
        category_value = meta.get("source_category")
        if category_value is not None and not isinstance(category_value, str):
            raise ValueError("HK source_category must be text or null")
        category = category_value or hk_report_subject_title(title)
        if category is not None and (end := hk_annual_end_date(title=title, category_text=category)) is not None:
            source_id = _hk_source_text(meta, "source_id")
            source_url = _hk_source_text(meta, "source_url")
            if entry.integrity.revision is None:
                continue
            result[entry.document_id] = HkAnnualAnchor(end, source_id, source_url,
                CnReportPublication("hkexnews", source_id, entry.document_id, entry.integrity.revision))
    for evidence in body_evidence:
        publication = evidence.publication
        if publication is None or evidence.facts.kind != "annual":
            continue
        entry = next((e for e in entries if e.document_id == publication.document_id), None)
        if entry is None or entry.integrity.status is not SourceIntegrityStatus.COMPLETE or entry.integrity.revision != publication.revision:
            continue
        meta = entry.source_meta
        if (meta.get("ticker") != evidence.ticker or meta.get("source_provider") != "hkexnews"
            or meta.get("source_id") != evidence.source_id or meta.get("source_url") != evidence.source_url
            or meta.get("pdf_sha256") != evidence.facts.pdf_sha256
            or meta.get("ingest_method") != "download" or meta.get("is_deleted") is not False):
            continue
        facts = resolve_hk_report_period(title=_hk_source_text(meta, "source_title"),
            category_text=_hk_source_text(meta, "source_category"), annual_ends=(), body=evidence)
        if facts is not None:
            result[publication.document_id] = HkAnnualAnchor(evidence.facts.end, evidence.source_id,
                evidence.source_url, publication, evidence.facts)
    return result


def _hk_source_text(meta: Mapping[str, JsonValue], key: str) -> str:
    """读取 HK 来源必填文本。

    参数：meta 为来源元数据；key 为必填字段名。
    返回：未经转换的非空原文本。
    异常：缺字段时原样抛 KeyError；空或非文本值抛 ValueError。
    """
    value = meta[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"HK source {key} must be non-empty text")
    return value


class HkEligibilityReason(str, Enum):
    """正文获取准入的封闭原因，不能用 resolver None 代替。"""

    SUFFICIENT = "title_sufficient"
    MISSING = "missing_period_facts"
    CONFLICT = "conflict_or_unsupported"
    NON_TARGET = "non_target"


@dataclass(frozen=True, slots=True)
class HkBodyEligibility:
    """selection 唯一生成的准入结果，运输方只消费 missing 分支。"""

    state: Literal["confirmed", "missing", "blocked", "non_target"]
    reason: HkEligibilityReason
    source_id: str
    projection: CnReportPeriodProjection | None


def hk_body_eligibility(item: HkexnewsRawAnnouncement, annual_ends: tuple[date, ...]) -> HkBodyEligibility:
    """封闭判定正文准入。

    参数：item 为同窗去重 raw；annual_ends 为可信日历。返回：封闭判定及已校验性质。
    异常：无。冲突、歧义、不支持与缺事实分开，已充分标题不请求正文。
    """
    if _is_english_hk_announcement(item) or not _has_hk_unresolved_report_signal(title=item.title, category_text=item.category_text):
        return HkBodyEligibility("non_target", HkEligibilityReason.NON_TARGET, item.document_id, None)
    facts = resolve_hk_report_period(title=item.title, category_text=item.category_text, annual_ends=annual_ends)
    if facts is not None:
        return HkBodyEligibility("confirmed", HkEligibilityReason.SUFFICIENT, item.document_id, facts.projection)
    subject = hk_report_subject_title(item.title)
    projection = _classify_hk_period_projection(title=subject, category_text=item.category_text, annual_ends=annual_ends) if subject is not None else None
    # 只开放经过所有标题 guard 且确实缺少直接期间的 results；任何已有年份/截止日的未决都不能被正文冲洗。
    if (subject is None or has_unresolved_end_date(subject)
        or re.search(r"\d{4}\s*/\s*\d{2,4}(?![/\d])", subject)
        or _hk_title_years(subject) or report_end_date(subject) is not None
        or _hk_report_family(item.category_text) != "results" or projection is None
        or projection.identity_period not in ("Q2", "Q4")):
        return HkBodyEligibility("blocked", HkEligibilityReason.CONFLICT, item.document_id, None)
    return HkBodyEligibility("missing", HkEligibilityReason.MISSING, item.document_id, projection)


def hk_body_requests(query: CnReportQuery, announcements: tuple[HkexnewsRawAnnouncement, ...], annual_ends: tuple[HkAnnualAnchor, ...]) -> tuple[HkBodyRequest, ...]:
    """仅输出携带封闭判定的同窗原件请求。

    参数：query/raw/annual_ends 为发现输入。返回：允许取原件的来源。异常：同 key 冲突 ValueError。
    """
    scoped = tuple(item for item in _deduplicate_hk_announcements(announcements) if query.start_date <= item.filing_date <= query.end_date)
    ends = tuple(sorted({anchor.end for anchor in annual_ends} | {end for item in scoped if (end := hk_annual_end_date(title=item.title, category_text=item.category_text)) is not None}))
    return tuple(HkBodyRequest(item, decision) for item in scoped if (decision := hk_body_eligibility(item, ends)).state == "missing"
                 and decision.projection is not None and decision.projection.identity_period in query.discovery_periods)


@dataclass(frozen=True, slots=True)
class HkBodyPeriodPartial:
    """正文 owner 对未能分配财年/身份的直接日期判定。"""

    report_date: date | None
    reason: Literal["ineligible", "direct_fact_conflict", "fiscal_year_unconfirmed"]


def resolve_hk_body_period_state(title: str, category: str, annual_ends: tuple[date, ...], body: HkBodyEvidence,
    annual_anchors: tuple[HkAnnualAnchor, ...] = ()) -> HkPeriodResolution | HkBodyPeriodPartial:
    """以同一准入和正文事实产生完整或部分期间状态，不进入标题季度回退。

    参数：标题/分类/年度日期/本条正文/带引用年度锚。返回：完整结果或带原因的未决事实。异常：无。
    """
    raw = HkexnewsRawAnnouncement(body.source_id, title, body.source_url, body.ticker, category, "", "zh")
    eligibility = hk_body_eligibility(raw, annual_ends)
    if eligibility.state != "missing" or eligibility.projection is None or body.facts.ticker != body.ticker:
        return HkBodyPeriodPartial(None, "ineligible")
    end = body.facts.end
    annual = body.facts.kind == "annual"
    if end.day != calendar.monthrange(end.year, end.month)[1] or eligibility.projection.identity_period != ("Q4" if annual else "Q2"):
        return HkBodyPeriodPartial(None, "direct_fact_conflict")
    if annual:
        return HkPeriodResolution(end.year, eligibility.projection, end.isoformat(), "source_document", "source_document")
    mapped = fiscal_quarter_at(end, annual_ends)
    if mapped is None or mapped[1] != 2:
        return HkBodyPeriodPartial(end, "fiscal_year_unconfirmed")
    nearby = relevant_annual_end_dates(end, annual_ends)
    return HkPeriodResolution(mapped[0], eligibility.projection, end.isoformat(), "source_document", "source_document_and_annual_end",
                              tuple(anchor for anchor in annual_anchors if anchor.end in nearby), nearby)


@dataclass(frozen=True, slots=True)
class HkReportSelection:
    """尚未交接原件的纯业务选择结果；不冒充已校验 discovery。"""

    candidates: tuple[CnReportCandidate, ...]
    uncertain_reports: tuple[FinsDownloadUncertainReport, ...]
    body_evidence: tuple[HkBodySelection, ...]


@dataclass(frozen=True, slots=True)
class HkBodyRequest:
    """已准入的raw/source key与业绩性质；downloader无需解释标题。"""

    announcement: HkexnewsRawAnnouncement
    eligibility: HkBodyEligibility
