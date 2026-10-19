"""HK正文事实、封闭准入、同批年度及公共原件绑定的owner级回归。"""

from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from dayu.contracts.json_value import JsonValue
from dayu.fins.domain.document_models import SourceHandle, SourceDocumentRevision
from dayu.fins.storage import FsDocumentBlobRepository
from dayu.fins.pipelines.hk_body_facts import HkBodyFacts, HkBodyUnknown, HkBodyUnknownReason, parse_hk_body_pages, resolve_hk_body_facts
from dayu.fins.pipelines.cn_download_models import (
    CnReportQuery, CnReportHeadMeta, CnReportDiscoveryResult, CnReportPdf, CnReportPublication,
    HkAnnualAnchor, HkBodyEvidence, HkexnewsRawAnnouncement, DownloadedReportAsset,
)
from dayu.fins.pipelines.cn_report_selection import hk_body_eligibility, hk_body_requests, select_hkexnews_report_candidates, resolve_hk_report_period
from dayu.fins.pipelines.cn_download_pdf_gate import NoopCnDownloadPdfGate
from dayu.fins.downloaders.hkexnews_downloader import HkexnewsDiscoveryClient
import httpx

FIXTURE = Path(__file__).parents[1] / 'fixtures/hk_body_official'
QUERY = CnReportQuery('HK', '0135', '2025-01-01', '2026-10-19', ('FY','H1','Q1','Q2','Q3','Q4'))
_DIGEST = hashlib.sha256(b'%PDF-A').hexdigest()
_ISSUER_PREAMBLE = (
    '香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，'
    '並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。'
    '甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（'
)


def _head(url: str) -> CnReportHeadMeta:
    """合成HEAD。参数：url。返回：空传输头。异常：无。"""
    return CnReportHeadMeta(None,None,None)


def _raw(sid: str = 'A', category: str = '末期業績', title: str = '業績公佈') -> HkexnewsRawAnnouncement:
    """合成raw。参数：身份/分类/标题。返回：原行。异常：无。"""
    return HkexnewsRawAnnouncement(sid,title,'https://example.test/'+sid+'.pdf','00135',category,'2026-01-01','zh')


def official_inputs() -> tuple[tuple[HkexnewsRawAnnouncement, bytes], ...]:
    """仅经storage读正式fixture的四份完整官方原件。

    参数：无。返回：官方raw与原件。异常：SHA/HTTP/仓储错误透传。
    """
    rows = cast(list[dict[str, JsonValue]], json.loads((FIXTURE/'provenance.json').read_bytes()))
    blobs = FsDocumentBlobRepository(FIXTURE)
    result: list[tuple[HkexnewsRawAnnouncement, bytes]] = []
    for row in rows:
        sid, filename, record, raw = row['source_id'], row['filename'], row['http'], row['raw']
        assert isinstance(sid,str) and isinstance(filename,str) and isinstance(record,dict) and isinstance(raw,dict)
        payload = blobs.read_file_bytes(SourceHandle('0135','official-'+sid,'filing'),filename)
        assert record['status_code'] == 200 and record['sha256'] == hashlib.sha256(payload).hexdigest()
        title, category, url = raw['TITLE'], raw['LONG_TEXT'], record['url']
        assert isinstance(title,str) and isinstance(category,str) and isinstance(url,str)
        # 正式raw的披露时间只决定查询窗；不参与正文日期或财年断言。
        result.append((HkexnewsRawAnnouncement(sid,title,url,'00135',category,'2026-01-01','zh'),payload))
    return tuple(result)


@pytest.fixture(scope='module')
def official_bodies() -> tuple[tuple[HkexnewsRawAnnouncement, bytes, HkBodyEvidence], ...]:
    """真实spawn提取一次供纯owner组合验证。参数：无。返回：已核事实。异常：原错透传。"""
    result = []
    for raw,payload in official_inputs():
        facts = resolve_hk_body_facts(payload,'0135')
        assert isinstance(facts,HkBodyFacts)
        result.append((raw,payload,HkBodyEvidence('0135',raw.document_id,raw.source_url,facts)))
    return tuple(result)


def test_official_four_and_permutations(official_bodies: tuple[tuple[HkexnewsRawAnnouncement,bytes,HkBodyEvidence],...]) -> None:
    """零本地零标题年度下同批先供证；排列不影响四条实际产品结果。

    参数：正式事实fixture。返回：无。异常：任何日期、性质、来源或顺序依赖断言失败。
    """
    import itertools
    evidence = {r.document_id:e for r,_,e in official_bodies}
    expected = {'11584251':(2024,'Q4','2024-12-31'), '11801353':(2025,'Q2','2025-06-30'),
                '12065226':(2025,'Q4','2025-12-31'), '12299283':(2026,'Q2','2026-06-30')}
    for order in itertools.permutations(tuple(r for r,_,_ in official_bodies)):
        result = select_hkexnews_report_candidates(query=QUERY,announcements=order,local_annual_ends=(),read_head_meta=_head,body_evidence=evidence)
        assert not result.uncertain_reports
        assert {c.source_id:(c.fiscal_year,c.period_projection.identity_period,c.report_date) for c in result.candidates} == expected
        assert all(c.report_date_source=='source_document' for c in result.candidates)
        assert all(c.fiscal_year_source==('source_document' if c.period_projection.identity_period=='Q4' else 'source_document_and_annual_end') for c in result.candidates)
        assert all(b.resolution.annual_evidence for b in result.body_evidence if b.evidence.facts.kind=='six_months')
        assert all(anchor.source_id and anchor.source_url and anchor.body_facts is not None
            for b in result.body_evidence if b.evidence.facts.kind == 'six_months'
            for anchor in b.resolution.annual_evidence)


def test_narrow_window_preserves_local_annual_provenance_and_partial_date() -> None:
    """窄窗窗外本地年度仍带 publication 和正文见证；无锚只保留日期。

    参数：无。返回：无。异常：财年错认、引用丢失或日期误报断言失败。
    """
    raw = replace(_raw('interim', '中期業績'), filing_date='2026-08-25')
    facts = HkBodyFacts('0135', date(2026, 6, 30), 'six_months', _DIGEST, 2, '本期中期業績')
    evidence = HkBodyEvidence('0135', raw.document_id, raw.source_url, facts)
    query = replace(QUERY, start_date='2026-08-01', end_date='2026-09-01')
    missing = select_hkexnews_report_candidates(query=query, announcements=(raw,),
        local_annual_ends=(), read_head_meta=_head, body_evidence={raw.document_id: evidence})
    assert not missing.candidates and len(missing.uncertain_reports) == 1
    assert missing.uncertain_reports[0].report_date == '2026-06-30'
    assert '报告截止日也未确认' not in missing.uncertain_reports[0].reason_message
    publication = CnReportPublication('hkexnews', 'annual', 'local-annual', SourceDocumentRevision('revision'))
    annual_facts = HkBodyFacts('0135', date(2025, 12, 31), 'annual', _DIGEST, 2, '本期年度業績')
    anchor = HkAnnualAnchor(annual_facts.end, 'annual', 'https://example.test/annual.pdf', publication, annual_facts)
    selected = select_hkexnews_report_candidates(query=query, announcements=(raw,),
        local_annual_ends=(anchor,), read_head_meta=_head, body_evidence={raw.document_id: evidence})
    assert len(selected.candidates) == 1 and selected.candidates[0].fiscal_year == 2026
    assert selected.body_evidence[0].resolution.annual_evidence == (anchor,)


def test_same_window_title_annual_anchor_keeps_official_reference() -> None:
    """同窗标题年度锚保留实际 source 和 URL。参数：无。返回：无。异常：引用丢失断言失败。"""
    annual = replace(_raw('annual', '末期業績', '截至2025年12月31日止年度業績'), filing_date='2026-08-24')
    interim = replace(_raw('interim', '中期業績'), filing_date='2026-08-25')
    facts = HkBodyFacts('0135', date(2026, 6, 30), 'six_months', _DIGEST, 2, '本期中期業績')
    query = replace(QUERY, start_date='2026-08-01', end_date='2026-09-01')
    result = select_hkexnews_report_candidates(query=query, announcements=(annual, interim),
        local_annual_ends=(), read_head_meta=_head,
        body_evidence={interim.document_id: HkBodyEvidence('0135', interim.document_id, interim.source_url, facts)})
    resolution = result.body_evidence[0].resolution
    assert resolution.annual_evidence == (HkAnnualAnchor(date(2025, 12, 31), annual.document_id, annual.source_url),)


def test_models_rejects_interim_calendar_without_annual_reference(
    official_bodies: tuple[tuple[HkexnewsRawAnnouncement, bytes, HkBodyEvidence], ...],
) -> None:
    """models 的同源校验不能接受有年度日期而丢失实际来源引用。

    参数：正式原件及事实。返回：无。异常：无引用仍获交接断言失败。
    """
    from dayu.fins.pipelines.cn_download_models import require_matching_report_original
    selected = select_hkexnews_report_candidates(query=QUERY,
        announcements=tuple(raw for raw, _, _ in official_bodies), local_annual_ends=(),
        read_head_meta=_head, body_evidence={raw.document_id: evidence for raw, _, evidence in official_bodies})
    candidate = next(c for c in selected.candidates if c.source_id == '12299283')
    payload = next(pdf for raw, pdf, _ in official_bodies if raw.document_id == candidate.source_id)
    binding = next(e for e in selected.body_evidence if e.evidence.source_id == candidate.source_id)
    require_matching_report_original(candidate, payload, candidate.source_url, binding, '0135')
    without_reference = replace(binding, resolution=replace(binding.resolution, annual_evidence=()))
    with pytest.raises(ValueError, match='年度来源见证'):
        require_matching_report_original(candidate, payload, candidate.source_url, without_reference, '0135')


@pytest.mark.parametrize('title,category',[
    ('2025年報及2026中期報告','末期業績'),('2024/25年度業績','末期業績'),
    ('截至2025年13月31日止年度業績','末期業績'),('2025年度業績FY2024','末期業績'),
    ('2024及2025年度業績','末期業績'),('業績公佈','年報 / 中期業績'),
    ('中期業績','末期業績'),('2025年度報告','年報'),('2025全年業績','末期業績'),
])
def test_closed_acquisition(title: str,category: str) -> None:
    """冲突/充分/非目标均不能触发正文运输。

    参数：合成负例。返回：无。异常：准入或downloader触发GET时失败。
    """
    item = _raw(title=title,category=category)
    assert hk_body_eligibility(item,()).state != 'missing'
    assert hk_body_requests(QUERY,(item,),()) == ()
    gets: list[str] = []
    def transport(request: httpx.Request) -> httpx.Response:
        """仅允许发现HTTP。参数：请求。返回：stock/raw。异常：PDF GET断言失败。"""
        gets.append(request.method+' '+str(request.url))
        if request.method == 'HEAD': return httpx.Response(200)
        if 'stock_sehk' in str(request.url):
            return httpx.Response(200,json=[{'stockCode':'00135','stockId':229,'name':'昆侖能源'}])
        return httpx.Response(200,json={'hasNextRow':False,'rowRange':int(request.url.params['rowRange']),'loadedRecord':1,'recordCnt':1,'result':json.dumps([{'NEWS_ID':'A','TITLE':title,'LONG_TEXT':category,'FILE_LINK':'/a.pdf','STOCK_CODE':'00135','DATE_TIME':'01/01/2026 12:00','FILE_TYPE':'PDF'}])})
    # 直接使用真实准入/selector；不以一个虚构候选授权PDF。
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider = HkexnewsDiscoveryClient(client=client,max_retries=1)
        from dayu.fins.pipelines.cn_download_models import CnCompanyProfile
        provider.list_report_candidates(QUERY,CnCompanyProfile('hkexnews','HKEX:229','昆侖能源','0135'),local_annual_ends=(),local_report_pdfs=(),pdf_download_gate=NoopCnDownloadPdfGate())
    assert not any(url.startswith('GET ') and url.endswith('.pdf') for url in gets)


@pytest.mark.parametrize('pages',[
    ('股份代號：00135.HK\n綜合全面收益表\n截至12月31日止年度\n2025年2024年',),
    ('股份代號：00135.HK\n股息截至2025年12月31日止年度',),
    ('股份代號：00999.HK\n綜合全面收益表截至2025年12月31日止年度',),
    ('股份代號：00135.HK','scan','scan','綜合全面收益表截至2025年12月31日止年度'),
    ('股份代號：00135.HK\n綜合全面收益表截至2025年12月31日止年度\n綜合全面收益表截至2024年12月31日止年度',),
    ('股份代號：00135.HK\n綜合全面收益表截至2025年13月31日止年度',),('',),
])
def test_unsupported_body(pages: tuple[str,...]) -> None:
    """无完整期间、错误身份、预算外或冲突均unknown。参数：合成页。返回：无。异常：猜期失败。"""
    assert isinstance(parse_hk_body_pages(pages,'0135',_DIGEST),HkBodyUnknown)


def test_comparison_columns_not_facts() -> None:
    """交换比较列不改本期。参数：无。返回：无。异常：误用年份顺序失败。"""
    for columns in ('2024年2025年','2025年2024年'):
        result=parse_hk_body_pages(('股份代號：00135.HK\n業績公佈\n本集團財務業績摘要 截至12月31日止年度'+columns,
            '綜合全面收益表截至2025年12月31日止年度'+columns),'0135',_DIGEST)
        assert isinstance(result,HkBodyFacts) and result.end==date(2025,12,31)


def test_historical_comparison_table_cannot_claim_current_period() -> None:
    """比较附录只有孤立表名日期时不能确认本期。参数：无。返回：无。异常：误认本期断言失败。"""
    pages=('股份代號0135\n以下僅列上年度比較資料，並非本期業績。\n綜合全面收益表\n截至2024年12月31日止年度',)
    assert parse_hk_body_pages(pages, '0135', _DIGEST) == HkBodyUnknown(HkBodyUnknownReason.PERIOD)


@pytest.mark.parametrize('prefix', ('', '業績公佈\n'))
@pytest.mark.parametrize('historical', (
    '本集團財務業績摘要（上年度比較資料）截至12月31日止年度2024年',
    '以下僅重列上年度比較資料，並非本期業績。\n本集團財務業績摘要\n截至12月31日止年度2024年',
    '以下引述上年度公告，僅供比較，並非本期業績：\n本集團截至2024年12月31日止年度本期綜合業績如下：',
    '本集團截至2024年12月31日止年度非本期綜合業績如下：',
    '本集團截至2024年12月31日止年度本期以外綜合業績如下：',
    '本集團財務業績摘要（謹供比較，並非本期）截至12月31日止年度2024年',
    '「本集團財務業績摘要截至12月31日止年度2024年」',
))
def test_qualified_or_quoted_scope_never_authorizes_selection(prefix: str, historical: str) -> None:
    """历史限定的位置、标点和公告标题均不能把局部摘要或本期变成当前声明。

    参数：公告前缀及限定段落。返回：无。异常：正文误认或真实 selector 产出候选时断言失败。
    """
    pages = ('股份代號0135\n' + prefix + historical + '\n綜合全面收益表截至2024年12月31日止年度',)
    facts = parse_hk_body_pages(pages, '0135', _DIGEST)
    raw = _raw()
    evidence = {raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, facts)} if isinstance(facts, HkBodyFacts) else {}
    selected = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,),
        local_annual_ends=(), read_head_meta=_head, body_evidence=evidence)
    assert isinstance(facts, HkBodyUnknown)
    assert selected.candidates == () and len(selected.uncertain_reports) == 1


@pytest.mark.parametrize('context', (
    '以下引述上年度公告，僅供比較，並非本期業績：',
    '以下僅重列上年度比較資料。', '「', '本期以外：',
))
@pytest.mark.parametrize('separator', ('\n', '。\n', '：\n'))
def test_opening_does_not_authorize_nested_old_declaration(context: str, separator: str) -> None:
    """当前摘要不把后续历史引用中的宣告升级为本期日期见证。

    参数：引用限定和相邻分隔。返回：无。异常：越过限定匹配内部本期时断言失败。
    """
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至6月30日止六個月\n2025年2024年',
        context + separator + '甲有限公司（「本公司」）之董事（「董事」）謹此宣佈，'
        '本公司及其附屬公司（統稱「本集團」）截至2025年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：')
    assert isinstance(parse_hk_body_pages(pages, '0135', _DIGEST), HkBodyUnknown)


@pytest.mark.parametrize('scope', ('以下引述上年度公告：', '上年度比較資料。', '「', '本期以外：'))
def test_scope_before_identity_is_not_discarded_as_header(scope: str) -> None:
    """页首说明不能因位于股票代码之前就被当作无关页眉丢弃。

    参数：外围历史作用域。返回：无。异常：引用内的完整公告结构被确认时断言失败。
    """
    pages = (scope + '股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年',
        '綜合全面收益表截至2024年12月31日止年度2024年2023年')
    assert isinstance(parse_hk_body_pages(pages, '0135', _DIGEST), HkBodyUnknown)


@pytest.mark.parametrize('tag', ('本期', '本期內', '非本期', '本期以外', '上年度本期'))
@pytest.mark.parametrize('issuer', ('甲乙', '丙丁', '以下引述上年度公告中甲乙'))
def test_complete_direct_declaration_requires_owned_current_tag(tag: str, issuer: str) -> None:
    """完整公司董事宣告才可定义本期；否定或历史局部标签不被子串匹配授权。

    参数：期间定义标签及宣告公司名。返回：无。异常：标签或声明归属判定不符时断言失败。
    """
    pages = (_ISSUER_PREAMBLE + '股份代號0987）\n業績公佈\n本集團財務業績摘要截至9月30日止六個月2031年2030年',
        '2' + issuer + '有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）'
        '截至2031年09月30日止六個月（「' + tag + '」）之未經審核綜合中期業績如下：')
    result = parse_hk_body_pages(pages, '0987', _DIGEST)
    if tag in ('本期', '本期內') and issuer == '甲乙':
        assert isinstance(result, HkBodyFacts) and result.end == date(2031, 9, 30) and result.page == 2
    else:
        assert isinstance(result, HkBodyUnknown)


@pytest.mark.parametrize(('following', 'reason'), (
    ((), HkBodyUnknownReason.PERIOD),
    (('不支持的段落', '綜合全面收益表截至2031年12月31日止年度'), HkBodyUnknownReason.PERIOD),
    (('綜合全面收益表截至2031年13月31日止年度',), HkBodyUnknownReason.PERIOD),
    (('綜合全面收益表截至2031年11月30日止年度',), HkBodyUnknownReason.CONFLICT),
    (('綜合全面收益表截至2031年12月31日止年度', '綜合全面收益表截至2030年12月31日止年度'), HkBodyUnknownReason.CONFLICT),
    (('綜合全面收益表（上年度）截至2031年12月31日止年度',), HkBodyUnknownReason.PERIOD),
    (('綜合全面收益表截至2031年12月31日止年度（比較資料）',), HkBodyUnknownReason.PERIOD),
))
def test_primary_statement_cannot_skip_unknown_scope_or_conflict(
    following: tuple[str, ...], reason: HkBodyUnknownReason,
) -> None:
    """只认连续主报表开头，不能跳过未知说明，也不能从互相冲突的报表任选日期。

    参数：后续页及预期原因。返回：无。异常：失败关闭原因不符时断言失败。
    """
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年', *following)
    assert parse_hk_body_pages(pages, '0135', _DIGEST) == HkBodyUnknown(reason)


@pytest.mark.parametrize('scope', (
    '以下引述上年度公告，僅供比較，並非本期業績：',
    '以下僅重列上年度比較資料。', '本期以外：', '「',
))
@pytest.mark.parametrize('place', ('before_rows', 'after_rows', 'after_note'))
def test_summary_scope_cannot_leak_across_page_boundary(scope: str, place: str) -> None:
    """历史限定留在摘要页时，不能把下一页旧宣告或旧表当作当前事实。

    参数：限定段及其在数值行/附注前后的位置。返回：无。异常：跨页误认或 selector 产出候选时断言失败。
    """
    rows = ['收入 100 90', '核心溢利（附註1） 20 18', '人民幣分 人民幣分']
    note = ['附註：', '1 核心溢利指不包括', '非經常收益之溢利。']
    position = {'before_rows': 0, 'after_rows': len(rows), 'after_note': len(rows) + len(note)}[place]
    tail = rows + note
    tail.insert(position, scope)
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2026年2025年\n' + '\n'.join(tail),
        '綜合全面收益表截至2025年12月31日止年度2025年2024年')
    result = parse_hk_body_pages(pages, '0135', _DIGEST)
    raw = _raw()
    body = {raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, result)} if isinstance(result, HkBodyFacts) else {}
    selection = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,),
        local_annual_ends=(), read_head_meta=_head, body_evidence=body)
    assert isinstance(result, HkBodyUnknown) and not selection.candidates


@pytest.mark.parametrize(('note', 'valid'), (
    ('附註：\n1 核心溢利指不包括\n非經常收益之溢利。', True),
    ('1 核心溢利乃根據本期已確認數字計算。', True),
    ('1 核心溢利指不包括非經常收益之溢利', False),
    ('1 核心溢利指不包括非經常收益之溢利。以下僅列歷史資料。', False),
    ('1 另一項目指歷史數字。', False),
))
def test_summary_allows_only_closed_referenced_metric_definitions(note: str, valid: bool) -> None:
    """摘要附注只有被数值行引用的闭合指标定义可留在当前摘要内。

    参数：附注与支持性。返回：无。异常：忽略未归属说明或错误排除合法定义时断言失败。
    """
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年\n'
        '核心溢利（附註1） 20 18\n' + note,
        '綜合全面收益表截至2031年12月31日止年度2031年2030年')
    assert isinstance(parse_hk_body_pages(pages, '0135', _DIGEST), HkBodyFacts) is valid


@pytest.mark.parametrize('ends', [(), (date(2025,12,31),date(2026,3,31)), (date(2025,12,30),)])
def test_no_or_conflicting_anchor(ends: tuple[date,...]) -> None:
    """正文中期无锚/冲突/非月末不得走标题序数回退。参数：年度锚。返回：无。异常：错误确认失败。"""
    body=HkBodyEvidence('0135','A','url',HkBodyFacts('0135',date(2026,6,30),'six_months',_DIGEST,2,'synthetic'))
    assert resolve_hk_report_period(title='業績公佈',category_text='中期業績',annual_ends=ends,body=body) is None


def test_non_december_calendar() -> None:
    """常规非十二月财年保持诚实推导来源。参数：无。返回：无。异常：自然年猜测失败。"""
    body=HkBodyEvidence('0135','A','url',HkBodyFacts('0135',date(2025,9,30),'six_months',_DIGEST,2,'synthetic'))
    anchor=HkAnnualAnchor(date(2025,3,31),'annual','https://example.test/annual.pdf')
    result=resolve_hk_report_period(title='業績公佈',category_text='中期業績',annual_ends=(anchor.end,),body=body,annual_anchors=(anchor,))
    assert result is not None and result.fiscal_year==2026 and result.fiscal_year_source=='source_document_and_annual_end'
    assert result.annual_evidence==(anchor,)


@pytest.mark.parametrize('local',(False,True))
@pytest.mark.parametrize('mismatch',('none','bytes','url','company','date','kind','year','missing','duplicate','both','revision','source_marker'))
def test_models_binding(official_bodies: tuple[tuple[HkexnewsRawAnnouncement,bytes,HkBodyEvidence],...],local: bool,mismatch: str) -> None:
    """prepared/local都核实际bytes；直接构造discovery无法绕过。

    参数：正式事实、交接路径和错配。返回：无。异常：错误接受或合法拒绝断言失败。
    """
    raw,payload,evidence=official_bodies[0]
    selection=select_hkexnews_report_candidates(query=QUERY,announcements=(raw,),local_annual_ends=(),read_head_meta=_head,body_evidence={raw.document_id:evidence})
    candidate=selection.candidates[0]; binding=selection.body_evidence[0]
    witness=CnReportPublication('hkexnews',raw.document_id,'doc',SourceDocumentRevision('r'))
    if local: binding=replace(binding,evidence=replace(binding.evidence,publication=witness))
    source_url=candidate.source_url
    ticker='0135'
    if mismatch=='bytes':payload=payload[:-1]+bytes([payload[-1]^1])
    elif mismatch=='url':source_url='https://other.test/a.pdf'
    elif mismatch=='company':ticker='9999'
    elif mismatch=='date':candidate=replace(candidate,report_date='2000-01-01')
    elif mismatch=='kind':candidate=replace(candidate,fiscal_year_source='source_document_and_annual_end')
    elif mismatch=='year':candidate=replace(candidate,fiscal_year=2000)
    elif mismatch=='source_marker':candidate=replace(candidate,report_date_source=None)
    elif mismatch=='revision' and local:witness=replace(witness,revision=SourceDocumentRevision('other'))
    asset=DownloadedReportAsset(candidate,payload,hashlib.sha256(payload).hexdigest(),len(payload),'2026-10-19T00:00:00+00:00')
    originals=(CnReportPdf(witness,source_url,payload),) if local else ()
    assets=() if local else (asset,)
    if mismatch=='url' and not local:binding=replace(binding,evidence=replace(binding.evidence,source_url=source_url))
    bindings=(binding,) if mismatch!='missing' else ()
    if mismatch=='duplicate':bindings=(binding,binding)
    if mismatch=='both':assets=(asset,);originals=(CnReportPdf(witness,source_url,payload),)
    if mismatch=='none' or (mismatch=='revision' and not local):
        result=CnReportDiscoveryResult((candidate,),(),assets,originals,bindings,ticker)
        assert result.candidates==(candidate,)
    else:
        with pytest.raises(ValueError):CnReportDiscoveryResult((candidate,),(),assets,originals,bindings,ticker)


class _OfficialTransport:
    """离线HTTP运输真实官方raw/全原件；不替代生产CLI验收。"""

    def __init__(self) -> None:
        """参数：无。返回：无。异常：fixture错误透传。"""
        self.inputs=official_inputs()
        self.gets: list[str]=[]
        self.rows=cast(list[dict[str,JsonValue]],json.loads((FIXTURE/'provenance.json').read_bytes()))

    def __call__(self,request: httpx.Request) -> httpx.Response:
        """参数：请求。返回：真实官方bytes或对应发现响应。异常：无匹配拒绝。"""
        url=str(request.url)
        if request.method=='HEAD':return httpx.Response(200)
        for raw,payload in self.inputs:
            if url==raw.source_url:
                self.gets.append(raw.document_id)
                return httpx.Response(200,content=payload,headers={'content-type':'application/pdf'})
        if 'stock_sehk' in url:
            return httpx.Response(200,json=[{'stockCode':'00135','stockId':'229','name':'昆侖能源'}])
        return httpx.Response(200,json={'hasNextRow':False,'rowRange':int(request.url.params['rowRange']),
            'loadedRecord':len(self.rows),'recordCnt':len(self.rows),'result':json.dumps([r['raw'] for r in self.rows])})


def test_real_fs_normal_skip_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """真实Fs普通→普通skip→纯本地rebuild同源且不改内容。

    参数：隔离仓储。返回：无。异常：重复GET、日期丢失、来源漂移、bytes/revision异常断言失败。
    """
    from tests.fins.test_cn_download_workflow import _build_pipeline,_FakeConverter
    from dayu.fins.domain.enums import SourceKind
    transport=_OfficialTransport()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider=HkexnewsDiscoveryClient(client=client,max_retries=1)
        pipeline=_build_pipeline(tmp_path=tmp_path,discovery=provider,hk_discovery=provider,converter=_FakeConverter())
        first=pipeline.download(ticker='0135',start_date=QUERY.start_date,end_date=QUERY.end_date,start_is_explicit=True)
        first_summary=first['summary']
        assert isinstance(first_summary,dict)
        assert first_summary['downloaded']==4 and not first['uncertain_reports']
        assert sorted(transport.gets)==sorted(r.document_id for r,_ in transport.inputs)
        entries=pipeline.source_repository.read_source_meta_integrity_view('0135',SourceKind.FILING,batch=None)
        before={e.document_id:dict(e.source_meta) for e in entries}
        revisions={e.document_id:e.integrity.revision for e in entries}
        from dayu.fins.pipelines import hk_body_extraction
        starts: list[int] = []
        original_start = hk_body_extraction.InterruptibleProcessHandle.start
        def counted_start(handle: hk_body_extraction.InterruptibleProcessHandle) -> None:
            """记录真实进程启动。参数：本次句柄。返回：无。异常：原错透传。"""
            starts.append(1)
            original_start(handle)
        monkeypatch.setattr(hk_body_extraction.InterruptibleProcessHandle, 'start', counted_start)
        second=pipeline.download(ticker='0135',start_date=QUERY.start_date,end_date=QUERY.end_date,start_is_explicit=True)
        assert len(starts) == 4
        second_summary=second['summary']
        assert isinstance(second_summary,dict)
        assert second_summary['skipped']==4 and len(transport.gets)==4
        second_rows = second['filings']
        assert isinstance(second_rows, list)
        for row in second_rows:
            assert isinstance(row, dict)
            assert row['report_date_source'] == 'source_document'
            assert row['fiscal_year_source'] in ('source_document', 'source_document_and_annual_end')
        again=pipeline.source_repository.read_source_meta_integrity_view('0135',SourceKind.FILING,batch=None)
        assert {e.document_id:e.integrity.revision for e in again}==revisions
        assert {e.document_id:dict(e.source_meta) for e in again}==before
        from dayu.fins.domain.document_models import ProcessedCreateRequest, DocumentQuery
        token=pipeline.batching_repository.begin_batch('0135')
        for entry in entries:
            internal=entry.source_meta['internal_document_id']
            assert isinstance(internal,str)
            pipeline.processed_repository.create_processed(ProcessedCreateRequest(
                ticker='0135',document_id=entry.document_id,internal_document_id=internal,source_kind='filing',
                form_type=str(entry.source_meta['fiscal_period']),meta={'report_date':'2000-01-01','report_date_source':'old'},
                sections=[{'id':'s','text':'synthetic processed content'}],tables=[],financials={'preserved':1}),batch=token)
        pipeline.batching_repository.commit_batch(token)
        processed_content={}
        for entry in entries:
            handle=pipeline.processed_repository.get_processed_handle('0135',entry.document_id)
            processed_content[entry.document_id]={f.name:pipeline.blob_repository.read_file_bytes(handle,f.name)
                for f in pipeline.blob_repository.list_entries(handle) if f.name in ('sections.json','tables.json','financials.json')}
        rebuilt=pipeline.download(ticker='0135' ,start_date=QUERY.start_date,end_date=QUERY.end_date,start_is_explicit=True,rebuild=True)
        assert not rebuilt['uncertain_reports'] and len(transport.gets)==4
        rebuilt_rows = rebuilt['filings']
        assert isinstance(rebuilt_rows, list)
        for row in rebuilt_rows:
            assert isinstance(row, dict)
            assert row['report_date_source'] == 'source_document'
            assert row['fiscal_year_source'] in ('source_document', 'source_document_and_annual_end')
        annual_ids=sorted(e.document_id for e in entries if e.source_meta['fiscal_period']=='Q4')
        for e in pipeline.source_repository.read_source_meta_integrity_view('0135',SourceKind.FILING,batch=None):
            meta=e.source_meta
            assert 'period_resolution_version' not in before[e.document_id]
            assert meta['period_resolution_version']=='hk-period-body-v1'
            processed=pipeline.processed_repository.get_processed_meta('0135',e.document_id)
            for field in ('report_date','report_date_source','fiscal_year','fiscal_year_source','covered_fiscal_periods'):
                assert processed[field]==meta[field]
            handle=pipeline.processed_repository.get_processed_handle('0135',e.document_id)
            assert {f.name:pipeline.blob_repository.read_file_bytes(handle,f.name)
                for f in pipeline.blob_repository.list_entries(handle) if f.name in ('sections.json','tables.json','financials.json')}==processed_content[e.document_id]
            projected=pipeline.processed_repository.list_processed_documents('0135',DocumentQuery())
            assert next(d for d in projected if d.document_id==e.document_id).report_date==meta['report_date']
            assert meta['period_resolution_sources']==annual_ids
            for field in ('source_id','source_url','pdf_sha256','fiscal_year','fiscal_period','covered_fiscal_periods','report_date','report_date_source','fiscal_year_source','source_fingerprint'):
                assert meta[field]==before[e.document_id][field]
            with pipeline.source_repository.read_source_snapshot('0135',e.document_id,SourceKind.FILING,materialize_files=True) as snapshot:
                for descriptor in snapshot.files:
                    with snapshot.get_source(descriptor.name).open() as stream:
                        assert hashlib.sha256(stream.read()).hexdigest()==descriptor.sha256


@pytest.mark.parametrize('field',('sha','length','time','candidate'))
def test_prepared_transport_is_checked_by_public_owner(official_bodies: tuple[tuple[HkexnewsRawAnnouncement,bytes,HkBodyEvidence],...],field: str) -> None:
    """正文prepared不只校事实SHA，也校实际运输声明。

    参数：正式原件及错运输字段。返回：无。异常：错配接受断言失败。
    """
    raw,payload,evidence=official_bodies[0]
    selected=select_hkexnews_report_candidates(query=QUERY,announcements=(raw,),local_annual_ends=(),read_head_meta=_head,body_evidence={raw.document_id:evidence})
    candidate=selected.candidates[0]
    asset=DownloadedReportAsset(candidate,payload,hashlib.sha256(payload).hexdigest(),len(payload),'2026-10-19T00:00:00+00:00')
    if field=='sha':asset=replace(asset,sha256='0'*64)
    elif field=='length':asset=replace(asset,content_length=1)
    elif field=='time':asset=replace(asset,downloaded_at='')
    else:asset=replace(asset,candidate=replace(candidate,source_id='other'))
    with pytest.raises(ValueError):CnReportDiscoveryResult((candidate,),(),(asset,),(),selected.body_evidence,'0135')


def test_body_nature_and_source_conflicts_close(official_bodies: tuple[tuple[HkexnewsRawAnnouncement,bytes,HkBodyEvidence],...]) -> None:
    """正文不得覆盖标题/分类冲突，跨公司/来源/URL输入由owner拒绝。

    参数：正式事实。返回：无。异常：错误确认断言失败。
    """
    raw,_,evidence=official_bodies[0]
    conflict=replace(raw,category_text='中期業績')
    selected=select_hkexnews_report_candidates(query=QUERY,announcements=(conflict,),local_annual_ends=(),read_head_meta=_head,body_evidence={raw.document_id:evidence})
    assert not selected.candidates and len(selected.uncertain_reports)==1
    for wrong in (replace(evidence,ticker='9999'),replace(evidence,source_id='other'),replace(evidence,source_url='https://other.test/x.pdf')):
        with pytest.raises(ValueError):select_hkexnews_report_candidates(query=QUERY,announcements=(raw,),local_annual_ends=(),read_head_meta=_head,body_evidence={raw.document_id:wrong})


def test_writer_rejects_revision_drift(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    """真实writer不能用陈旧正文snapshot授权skip，并释放batch。

    参数：隔离Fs和writer边界注入。返回：无。异常：漂移接受、旧资产变化或锁泄漏断言失败。
    """
    from dayu.fins.domain.document_models import BatchToken
    from dayu.fins.domain.enums import SourceKind
    from dayu.fins.storage.source_integrity import SourceIntegrityClassification,SourceIntegrityRevisionConflictError
    from dayu.fins.pipelines.cn_download_filing_workflow import _validate_hk_body_skip
    from tests.fins.test_cn_download_workflow import _build_pipeline,_FakeConverter
    transport=_OfficialTransport()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider=HkexnewsDiscoveryClient(client=client,max_retries=1)
        pipeline=_build_pipeline(tmp_path=tmp_path,discovery=provider,hk_discovery=provider,converter=_FakeConverter())
        pipeline.download(ticker='0135',start_date=QUERY.start_date,end_date=QUERY.end_date,start_is_explicit=True)
        entries=pipeline.source_repository.read_source_meta_integrity_view('0135',SourceKind.FILING,batch=None)
        raw,payload=transport.inputs[0]
        facts=resolve_hk_body_facts(payload,'0135');assert isinstance(facts,HkBodyFacts)
        evidence=HkBodyEvidence('0135',raw.document_id,raw.source_url,facts)
        selected=select_hkexnews_report_candidates(query=QUERY,announcements=(raw,),local_annual_ends=(),read_head_meta=_head,body_evidence={raw.document_id:evidence})
        target=next(e for e in entries if e.source_meta['source_id']==raw.document_id)
        original=pipeline.source_repository.classify_staged_source_integrity
        def drift(ticker: str,document_id: str,source_kind: SourceKind,*,batch: BatchToken) -> SourceIntegrityClassification:
            """参数：真实staging身份与capability。返回：变化revision。异常：原仓储错透传。"""
            return replace(original(ticker,document_id,source_kind,batch=batch),revision=SourceDocumentRevision('drift'))
        monkeypatch.setattr(pipeline.source_repository,'classify_staged_source_integrity',drift)
        with pytest.raises(SourceIntegrityRevisionConflictError):_validate_hk_body_skip(pipeline.batching_repository,pipeline.source_repository,
            '0135',target.document_id,target.integrity,selected.candidates[0],payload)
        after=pipeline.source_repository.read_source_meta_integrity_view('0135',SourceKind.FILING,batch=None)
        assert entries==after
        token=pipeline.batching_repository.begin_batch('0135');pipeline.batching_repository.rollback_batch(token)


def test_body_skip_separates_period_drift_from_original_breakage(
    official_bodies: tuple[tuple[HkexnewsRawAnnouncement, bytes, HkBodyEvidence], ...],
) -> None:
    """合法正文财期漂移要求 rebuild；来源或摘要破坏不能误导修旧资产。

    参数：正式原件和事实。返回：无。异常：分类错误断言失败。
    """
    from dayu.fins.pipelines.cn_download_filing_workflow import (
        HkPeriodMetadataMismatchError, _build_filing_result, _filing_event_payload,
        _require_hk_body_meta, project_cn_filing_failure,
    )
    raw, payload, evidence = official_bodies[0]
    selected = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,),
        local_annual_ends=(), read_head_meta=_head, body_evidence={raw.document_id: evidence})
    candidate = selected.candidates[0]
    meta: dict[str, JsonValue] = {
        'source_provider': candidate.provider, 'source_id': candidate.source_id,
        'source_url': candidate.source_url, 'pdf_sha256': hashlib.sha256(payload).hexdigest(),
        'report_date': candidate.report_date, 'report_date_source': candidate.report_date_source,
        'fiscal_year': candidate.fiscal_year, 'fiscal_year_source': candidate.fiscal_year_source,
        'fiscal_period': candidate.period_projection.identity_period,
        'form_type': candidate.period_projection.identity_period,
        'report_kind': candidate.period_projection.identity_period,
        'covered_fiscal_periods': list(candidate.period_projection.covered_periods),
    }
    assert not _require_hk_body_meta(meta, candidate, payload)
    assert _require_hk_body_meta({**meta, 'fiscal_year': candidate.fiscal_year - 1}, candidate, payload)
    assert _require_hk_body_meta({**meta, 'report_kind': 'Q1'}, candidate, payload)
    assert project_cn_filing_failure(HkPeriodMetadataMismatchError())[0] == 'period_metadata_mismatch'
    for changed in ({**meta, 'source_url': 'https://other.test/x.pdf'}, {**meta, 'pdf_sha256': '0' * 64}):
        with pytest.raises(ValueError):
            _require_hk_body_meta(changed, candidate, payload)
    row = _build_filing_result(document_id='local', status='skipped', candidate=candidate,
        reason_code='integrity_complete', reason_message='完整', downloaded_files=0, skipped_files=2)
    event = _filing_event_payload(row)
    assert event['report_date_source'] == row['report_date_source'] == candidate.report_date_source
    assert event['fiscal_year_source'] == row['fiscal_year_source'] == candidate.fiscal_year_source


def test_writer_classifies_legal_period_drift_without_mutating_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实 Fs writer 的合法原件期漂移分类并回滚，不触及已发布字节。

    参数：隔离仓储与 staged 元数据注入。返回：无。异常：分类或资产变化断言失败。
    """
    from dayu.fins.domain.document_models import BatchToken
    from dayu.fins.domain.enums import SourceKind
    from dayu.fins.storage import SourceMetaIntegrityReadEntry
    from dayu.fins.pipelines.cn_download_filing_workflow import (
        HkPeriodMetadataMismatchError, _validate_hk_body_skip,
    )
    from tests.fins.test_cn_download_workflow import _build_pipeline, _FakeConverter
    transport = _OfficialTransport()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider = HkexnewsDiscoveryClient(client=client, max_retries=1)
        pipeline = _build_pipeline(tmp_path=tmp_path, discovery=provider,
            hk_discovery=provider, converter=_FakeConverter())
        pipeline.download(ticker='0135', start_date=QUERY.start_date, end_date=QUERY.end_date,
            start_is_explicit=True)
        raw, payload = transport.inputs[0]
        body = resolve_hk_body_facts(payload, '0135')
        assert isinstance(body, HkBodyFacts)
        selection = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,),
            local_annual_ends=(), read_head_meta=_head,
            body_evidence={raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, body)})
        entry = next(e for e in pipeline.source_repository.read_source_meta_integrity_view(
            '0135', SourceKind.FILING, batch=None) if e.source_meta.get('source_id') == raw.document_id)
        view = pipeline.source_repository.read_source_meta_integrity_view

        def drift(ticker: str, source_kind: SourceKind, *, batch: BatchToken | None = None
            ) -> tuple[SourceMetaIntegrityReadEntry, ...]:
            """仅在 writer staging 中投影错误财年。参数：查询身份与 batch。返回：错投影。异常：原错透传。"""
            entries = view(ticker, source_kind, batch=batch)
            return tuple(replace(e, source_meta={**e.source_meta, 'fiscal_year': 1900})
                if e.document_id == entry.document_id else e for e in entries)

        with monkeypatch.context() as patch:
            patch.setattr(pipeline.source_repository, 'read_source_meta_integrity_view', drift)
            with pytest.raises(HkPeriodMetadataMismatchError):
                _validate_hk_body_skip(pipeline.batching_repository, pipeline.source_repository,
                    '0135', entry.document_id, entry.integrity, selection.candidates[0], payload)
        exact = pipeline.source_repository.read_source_meta_integrity_view('0135', SourceKind.FILING, batch=None)
        assert next(e for e in exact if e.document_id == entry.document_id).source_meta == entry.source_meta
        token = pipeline.batching_repository.begin_batch('0135')
        pipeline.batching_repository.rollback_batch(token)


def test_mixed_title_and_body_local_rebuild_keeps_anchor_identity(tmp_path: Path) -> None:
    """真实 Fs 混合标题年度与正文中期重建时保留同一年度文档引用。

    参数：tmp_path 为隔离仓储。返回：无。异常：来源标签或资产身份漂移断言失败。
    """
    from dayu.fins.domain.document_models import FilingUpdateRequest
    from dayu.fins.domain.enums import SourceKind
    from tests.fins.test_cn_download_workflow import _build_pipeline, _FakeConverter
    from dayu.fins.pipelines.cn_form_utils import PeriodDownloadWindow
    from dayu.fins.pipelines.hk_download_rebuild import rebuild_hk_periods
    transport = _OfficialTransport()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider = HkexnewsDiscoveryClient(client=client, max_retries=1)
        pipeline = _build_pipeline(tmp_path=tmp_path, discovery=provider,
            hk_discovery=provider, converter=_FakeConverter())
        pipeline.download(ticker='0135', start_date=QUERY.start_date, end_date=QUERY.end_date,
            start_is_explicit=True)
        entries = pipeline.source_repository.read_source_meta_integrity_view('0135', SourceKind.FILING, batch=None)
        annual = next(entry for entry in entries if entry.source_meta.get('source_id') == '12065226')
        meta = dict(annual.source_meta)
        internal = meta['internal_document_id']
        assert isinstance(internal, str)
        meta.update(source_title='截至2025年12月31日止年度業績', source_category='末期業績',
            report_date_source='source_title', fiscal_year_source='source_title_and_annual_end')
        batch = pipeline.batching_repository.begin_batch('0135')
        pipeline.source_repository.update_source_document(FilingUpdateRequest(
            ticker='0135', document_id=annual.document_id, internal_document_id=internal,
            form_type='Q4', meta=meta), SourceKind.FILING, batch=batch)
        pipeline.batching_repository.commit_batch(batch)
        windows = (PeriodDownloadWindow('Q4', QUERY.start_date, QUERY.end_date),
            PeriodDownloadWindow('Q2', QUERY.start_date, QUERY.end_date))
        rows, unknown, cancelled = rebuild_hk_periods(pipeline, '0135', windows, None)
        assert not unknown and not cancelled and len(rows) == 4
        current = pipeline.source_repository.read_source_meta_integrity_view('0135', SourceKind.FILING, batch=None)
        by_source = {entry.source_meta['source_id']: entry.source_meta for entry in current}
        assert by_source['12065226']['period_resolution_version'] == 'hk-period-v3'
        assert by_source['12299283']['period_resolution_version'] == 'hk-period-body-v1'
        sources = by_source['12299283']['period_resolution_sources']
        assert isinstance(sources, list) and annual.document_id in sources
        assert by_source['12299283']['report_date_source'] == 'source_document'
        remove_anchors = pipeline.batching_repository.begin_batch('0135')
        for entry in current:
            if entry.source_meta.get('source_id') not in ('11584251', '12065226'):
                continue
            internal_id = entry.source_meta['internal_document_id']
            assert isinstance(internal_id, str)
            pipeline.source_repository.update_source_document(FilingUpdateRequest(
                ticker='0135', document_id=entry.document_id, internal_document_id=internal_id,
                form_type='Q4', meta={**entry.source_meta, 'is_deleted': True},
            ), SourceKind.FILING, batch=remove_anchors)
        pipeline.batching_repository.commit_batch(remove_anchors)
        no_rows, unresolved, cancelled = rebuild_hk_periods(pipeline, '0135',
            (PeriodDownloadWindow('Q2', QUERY.start_date, QUERY.end_date),), None)
        assert not cancelled and not no_rows
        assert {item.report_date for item in unresolved} == {'2025-06-30', '2026-06-30'}
        assert all('报告截止日也未确认' not in item.reason_message for item in unresolved)


@pytest.mark.parametrize('integrity_abort', (False, True))
def test_workflow_outer_failure_keeps_body_sources_without_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, integrity_abort: bool,
) -> None:
    """实际 skip writer 漂移或完整性异常进入外层后，失败行与双层事件仍投影同一来源。

    参数：隔离 Fs、writer 注入和异常种类。返回：无。异常：来源丢失、发布变化或未释放 batch 时断言失败。
    """
    import asyncio
    from dayu.fins.domain.document_models import BatchToken
    from dayu.fins.domain.document_models import SourceDocumentProvenance
    from dayu.fins.domain.enums import SourceKind
    from dayu.fins.storage import SourceMetaIntegrityReadEntry
    from dayu.fins.storage.repository_protocols import SourceSnapshotFileDescriptor
    from dayu.fins.storage.source_integrity import SourceIntegrityRevisionConflictError
    from dayu.fins.pipelines.cn_download_workflow import CnDownloadIntegrityAbort
    from dayu.fins.pipelines.download_events import DownloadEvent, DownloadEventType
    from tests.fins.test_cn_download_workflow import _build_pipeline, _FakeConverter

    transport = _OfficialTransport()
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider = HkexnewsDiscoveryClient(client=client, max_retries=1)
        converter = _FakeConverter()
        pipeline = _build_pipeline(tmp_path=tmp_path, discovery=provider,
            hk_discovery=provider, converter=converter)
        pipeline.download(ticker='0135', start_date=QUERY.start_date, end_date=QUERY.end_date,
            start_is_explicit=True)
        before = pipeline.source_repository.read_source_meta_integrity_view('0135', SourceKind.FILING, batch=None)
        asset_bytes: dict[tuple[str, str], bytes] = {}
        snapshots: dict[str, tuple[SourceDocumentRevision, str, SourceDocumentProvenance, tuple[SourceSnapshotFileDescriptor, ...]]] = {}
        for entry in before:
            with pipeline.source_repository.read_source_snapshot('0135', entry.document_id,
                SourceKind.FILING, materialize_files=True) as snapshot:
                snapshots[entry.document_id] = (snapshot.revision, snapshot.primary_filename, snapshot.provenance, snapshot.files)
                for descriptor in snapshot.files:
                    with snapshot.get_source(descriptor.name).open() as stream:
                        asset_bytes[(entry.document_id, descriptor.name)] = stream.read()
        view = pipeline.source_repository.read_source_meta_integrity_view
        conversion_count, get_count = converter.calls, len(transport.gets)

        def drift(ticker: str, source_kind: SourceKind, *, batch: BatchToken | None = None
            ) -> tuple[SourceMetaIntegrityReadEntry, ...]:
            """只在真实 writer staging 注入异常。参数：仓储查询。返回：错财年投影。异常：指定完整性冲突。"""
            entries = view(ticker, source_kind, batch=batch)
            if batch is None:
                return entries
            if integrity_abort:
                raise SourceIntegrityRevisionConflictError()
            return tuple(replace(entry, source_meta={**entry.source_meta, 'fiscal_year': 1900}) for entry in entries)

        events: list[DownloadEvent] = []

        async def consume() -> None:
            """保存实际工作流事件。参数：无。返回：无。异常：工作流完整性 abort 原样传播。"""
            async for event in pipeline.download_stream(ticker='0135', start_date=QUERY.start_date,
                end_date=QUERY.end_date, start_is_explicit=True):
                events.append(event)

        with monkeypatch.context() as patch:
            patch.setattr(pipeline.source_repository, 'read_source_meta_integrity_view', drift)
            if integrity_abort:
                with pytest.raises(CnDownloadIntegrityAbort) as raised:
                    asyncio.run(consume())
                result = raised.value.result
            else:
                asyncio.run(consume())
                result = next(event.payload for event in events if event.event_type is DownloadEventType.PIPELINE_COMPLETED)
                result = cast(dict[str, JsonValue], result['result'])
        rows = result['filings']
        assert isinstance(rows, list) and len(rows) == (1 if integrity_abort else 4)
        failed = [event for event in events if event.event_type is DownloadEventType.FILING_FAILED]
        assert len(failed) == len(rows)
        expected = {entry.document_id: entry.source_meta for entry in before}
        for event, row in zip(failed, rows, strict=True):
            assert isinstance(row, dict) and event.payload['filing_result'] == row
            assert row['reason_code'] == ('source_integrity_failed' if integrity_abort else 'period_metadata_mismatch')
            assert event.document_id is not None
            for field in ('report_date_source', 'fiscal_year_source', 'report_date', 'fiscal_year'):
                assert event.payload[field] == row[field] == expected[event.document_id][field]
        assert pipeline.source_repository.read_source_meta_integrity_view('0135', SourceKind.FILING, batch=None) == before
        for (document_id, filename), payload in asset_bytes.items():
            assert pipeline.blob_repository.read_file_bytes(SourceHandle('0135', document_id, 'filing'), filename) == payload
        for document_id, previous in snapshots.items():
            with pipeline.source_repository.read_source_snapshot('0135', document_id,
                SourceKind.FILING, materialize_files=True) as snapshot:
                assert (snapshot.revision, snapshot.primary_filename, snapshot.provenance, snapshot.files) == previous
        assert converter.calls == conversion_count and len(transport.gets) == get_count
        token = pipeline.batching_repository.begin_batch('0135')
        pipeline.batching_repository.rollback_batch(token)


@pytest.mark.parametrize('columns', ('', '2024年', '2024年2023年', '2023年2024年'))
@pytest.mark.parametrize('separator', ('', '\n', '\r\n'))
@pytest.mark.parametrize('scope', ('（上年度比較資料，並非本期業績）', '以下僅供歷史比較：', '「非本期」'))
def test_statement_header_requires_complete_unqualified_witness(columns: str, separator: str, scope: str) -> None:
    """日期及比较列不能遮蔽同一表头的限定，包括下一物理行。

    参数：年份列、换行及限定。返回：无。异常：丢掉限定产出日期时断言失败。
    """
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2024年2023年',
        '綜合全面收益表截至2024年12月31日止年度' + columns + separator + scope)
    assert isinstance(parse_hk_body_pages(pages, '0135', _DIGEST), HkBodyUnknown)


@pytest.mark.parametrize('scope', (
    '以下僅列上年度比較資料，並非本期業績', '以下僅供歷史比較：',
    '以下僅列歷史資料;並非本期', '「以下僅列歷史資料」',
))
@pytest.mark.parametrize('numbers', ('2024 2023', '2024 2023 0'))
@pytest.mark.parametrize('place', ('before', 'after'))
def test_numeric_scope_clause_is_not_a_metric(scope: str, numbers: str, place: str) -> None:
    """数值不能把独立作用域说明授权为指标标签。

    参数：完整说明、数值列及位置。返回：无。异常：误认说明为指标时断言失败。
    """
    rows = ['收入 100 90']
    rows.insert(0 if place == 'before' else len(rows), scope + ' ' + numbers)
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2024年2023年\n' + '\n'.join(rows),
        '綜合全面收益表截至2024年12月31日止年度2024年2023年')
    assert isinstance(parse_hk_body_pages(pages, '0135', _DIGEST), HkBodyUnknown)


@pytest.mark.parametrize('scope', (
    '以下引述上年度公告，僅供比較，並非本期業績：',
    '以下僅供歷史比較：', '「以下引述上年度公告」', '以下僅列歷史資料;並非本期',
))
def test_pending_metric_definition_cannot_swallow_scope(scope: str) -> None:
    """未闭合指标定义不能消费独立引述段落并授权下一页旧宣告。

    参数：插入的独立说明。返回：无。异常：pending 吞掉作用域时断言失败。
    """
    pages = (_ISSUER_PREAMBLE + '股份代號0987）\n業績公佈\n本集團財務業績摘要截至9月30日止六個月2031年2030年\n'
        '核心溢利（附註1） 20 18\n附註：\n1 核心溢利指不包括\n' + scope + '\n非經常收益之溢利。',
        '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）'
        '截至2030年9月30日止六個月（「本期內」）之未經審核綜合中期業績如下：')
    assert isinstance(parse_hk_body_pages(pages, '0987', _DIGEST), HkBodyUnknown)


@pytest.mark.parametrize('columns', ('2031年2030年', '2030年2031年'))
@pytest.mark.parametrize('year', (2024, 2030, 2031))
def test_summary_year_columns_only_check_complete_date_consistency(columns: str, year: int) -> None:
    """年份列只否决直接冲突，完整日期在任一列相容时不据新旧或顺序猜期。

    参数：摘要列排列及完整日期年。返回：无。异常：忽略冲突或按 MAX 选年时断言失败。
    """
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度' + columns,
        f'綜合全面收益表截至{year}年12月31日止年度{year}年{year - 1}年')
    result = parse_hk_body_pages(pages, '0135', _DIGEST)
    if year == 2024:
        assert result == HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
    else:
        assert isinstance(result, HkBodyFacts) and result.end == date(year, 12, 31)


@pytest.mark.parametrize('year', (2024, 2030, 2031))
def test_direct_declaration_year_consistency_and_unqualified_pb_boundary(year: int) -> None:
    """同发行人完整宣告仍须年列相容；无明确限定的旧列年遵循 P-B 裁决。

    参数：宣告的完整日期年。返回：无。异常：丢冲突或把外部旧页标签当事实时断言失败。
    """
    pages = (_ISSUER_PREAMBLE + '股份代號0987）\n業績公佈\n本集團財務業績摘要截至9月30日止六個月2031年2030年',
        '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）'
        f'截至{year}年9月30日止六個月（「本期內」）之未經審核綜合中期業績如下：')
    result = parse_hk_body_pages(pages, '0987', _DIGEST)
    if year == 2024:
        assert result == HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
    else:
        assert isinstance(result, HkBodyFacts) and result.end == date(year, 9, 30)


@pytest.mark.parametrize(('tail', 'reason'), (
    ('（上年度比較資料）', HkBodyUnknownReason.PERIOD),
    ('\n以下僅供比較：', HkBodyUnknownReason.PERIOD),
    ('\n綜合中期全面收益表截至9月30日止六個月2024年2023年', HkBodyUnknownReason.CONFLICT),
    ('\n綜合中期全面收益表截至8月31日止六個月2031年2030年', HkBodyUnknownReason.CONFLICT),
    ('\n綜合中期全面收益表截至9月30日止六個月2031年2030年（僅供比較）', HkBodyUnknownReason.PERIOD),
))
def test_direct_declaration_cannot_discard_qualified_or_conflicting_table(tail: str, reason: HkBodyUnknownReason) -> None:
    """完整宣告不能掩盖同行限定或紧随表头的直接冲突。

    参数：宣告余文及预期原因。返回：无。异常：局部宣告越过冲突时断言失败。
    """
    pages = (_ISSUER_PREAMBLE + '股份代號0987）\n業績公佈\n本集團財務業績摘要截至9月30日止六個月2031年2030年',
        '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）'
        '截至2031年09月30日止六個月（「本期內」）之未經審核綜合中期業績如下：' + tail)
    assert parse_hk_body_pages(pages, '0987', _DIGEST) == HkBodyUnknown(reason)


@pytest.mark.parametrize(('header', 'valid'), (
    ('綜合全面收益表（續）截至12月31日止年度2031年2030年', True),
    ('綜合全面收益表（續）截至12月31日止年度2024年2023年', False),
    ('綜合全面收益表（續）截至11月30日止年度2031年2030年', False),
    ('綜合全面收益表（續）截至12月31日止年度2031年2030年（僅供比較）', False),
    ('綜合全面收益表（續）未知期間', False),
))
def test_short_continuation_only_checks_existing_complete_witness(header: str, valid: bool) -> None:
    """续表不可丢限定或冲突，也不可在缺完整日期时自行按年列猜期。

    参数：简写续表和与完整见证的相容性。返回：无。异常：错误授权或忽略冲突时断言失败。
    """
    opening = '股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年'
    complete = '綜合全面收益表截至2031年12月31日止年度2031年2030年\n收入 100 90'
    assert isinstance(parse_hk_body_pages((opening, complete, header), '0135', _DIGEST), HkBodyFacts) is valid
    assert isinstance(parse_hk_body_pages((opening, header), '0135', _DIGEST), HkBodyUnknown)


@pytest.mark.parametrize(('case_name', 'pages', 'ticker', 'anchor', 'reason'), (
    ('numeric-scope-without-clause-punctuation', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年\n以下僅列上年度比較資料並非本期業績 2024 2023\n收入 100 90', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('pending-note-scope-without-clause-punctuation', ('1香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。昆侖能源有限公司KUNLUNENERGYCOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號：00135.HK）\n業績公佈\n本集團財務業績摘要\n截至6月30日止六個月\n2026年 2025年 變動%\n核心溢利（附註1） 20 18\n人民幣分 人民幣分\n附註：\n1 核心溢利指不包括\n以下引述上年度公告僅供比較並非本期業績\n非經常收益之溢利。', '2昆侖能源有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2025年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0135', date(2025, 12, 31), HkBodyUnknownReason.PERIOD),
    ('statement-qualifier-after-first-row', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n收入 100 90\n（上年度比較資料，並非本期業績）'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('crosspage-statement-qualifier', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年', '（上年度比較資料，並非本期業績）\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('crosspage-declaration-qualifier', ('香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號0987）\n業績公佈\n本集團財務業績摘要截至6月30日止六個月2024年2023年', '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2024年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：', '（上年度比較資料，並非本期業績）\n收入 100 90'), '0987', date(2024, 12, 31), HkBodyUnknownReason.PERIOD),
    ('formal-statement-suffix', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年（上年度比較資料，並非本期業績）'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('formal-numeric-scope', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年\n以下僅列上年度比較資料，並非本期業績 2024 2023\n收入 100 90', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('formal-pending-note-scope', ('1香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。昆侖能源有限公司KUNLUNENERGYCOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號：00135.HK）\n業績公佈\n本集團財務業績摘要\n截至6月30日止六個月\n2026年 2025年 變動%\n核心溢利（附註1） 20 18\n人民幣分 人民幣分\n附註：\n1 核心溢利指不包括\n以下引述上年度公告，僅供比較，並非本期業績：\n非經常收益之溢利。', '2昆侖能源有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2025年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('formal-year-consistency', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2031年2030年', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.CONFLICT),
    ('scope-row-ideographic-comma', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年\n上年度比較資料、並非本期業績 2024 2023\n收入 100 90', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('scope-row-3-numbers-no-punct', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年\n以下僅列上年度比較資料並非本期業績 2024 2023 0\n收入 100 90', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('scope-row-after-real-row-no-punct', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年\n收入 100 90\n以下僅列上年度比較資料並非本期業績 2024 2023', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('statement-first-row-punctuated', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n（上年度比較資料，並非本期業績）\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('statement-first-row-no-punct', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n上年度比較資料並非本期業績 2024 2023\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('pending-note-punctuated', ('香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號0987）\n業績公佈\n本集團財務業績摘要截至9月30日止六個月2031年2030年\n核心溢利（附註1） 20 18\n附註：\n1 核心溢利指不包括\n上年度比較資料，並非本期業績\n非經常收益之溢利。', '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2030年9月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0987', None, HkBodyUnknownReason.PERIOD),
    ('pending-note-no-punct', ('香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號0987）\n業績公佈\n本集團財務業績摘要截至9月30日止六個月2031年2030年\n核心溢利（附註1） 20 18\n附註：\n1 核心溢利指不包括\n上年度比較資料並非本期業績\n非經常收益之溢利。', '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2030年9月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0987', date(2031, 3, 31), HkBodyUnknownReason.PERIOD),
    ('statement-columns-self-conflict', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2023年2022年'), '0135', None, HkBodyUnknownReason.CONFLICT),
    ('B1-tail-nextline-depunct-note-with-2num', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n以下僅列上年度比較資料並非本期業績 2024 2023\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('B1c-tail-nextline-depunct-note-with-3num', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n以下僅列上年度比較資料並非本期業績 2024 2023 0\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('B1n-tail-nextline-depunct-split', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n以下僅列上年度比較資料\n並非本期業績 2024 2023\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('B1x-tail-sameline-depunct-note-with-2num', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年以下僅列上年度比較資料並非本期業績 2024 2023\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('B2no-summary-depunct-note-no-num', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年\n以下僅列上年度比較資料並非本期業績\n收入 100 90', '綜合全面收益表截至2024年12月31日止年度2024年2023年'), '0135', None, HkBodyUnknownReason.PERIOD),
    ('B3-pending-swallow-depunct-quote', ('香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號0987）\n業績公佈\n本集團財務業績摘要\n截至6月30日止六個月\n2026年 2025年 變動%\n核心溢利（附註1） 20 18\n人民幣分 人民幣分\n附註：\n1 核心溢利指不包括\n以下引述上年度公告僅供比較並非本期業績\n非經常收益之溢利。', '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2025年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0987', date(2025, 12, 31), HkBodyUnknownReason.PERIOD),
    ('B3s-pending-swallow-depunct-split', ('香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號0987）\n業績公佈\n本集團財務業績摘要\n截至6月30日止六個月\n2026年 2025年 變動%\n核心溢利（附註1） 20 18\n人民幣分 人民幣分\n附註：\n1 核心溢利指不包括\n以下引述上年度公告僅供比較\n並非本期業績\n非經常收益之溢利。', '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2025年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0987', date(2025, 12, 31), HkBodyUnknownReason.PERIOD),
    ('B3p-pending-swallow-punctuated-quote', ('香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。甲乙有限公司EXAMPLECOMPANYLIMITED(incorporatedinBermudawithlimitedliability)（股份代號0987）\n業績公佈\n本集團財務業績摘要\n截至6月30日止六個月\n2026年 2025年 變動%\n核心溢利（附註1） 20 18\n人民幣分 人民幣分\n附註：\n1 核心溢利指不包括\n以下引述上年度公告，僅供比較，並非本期業績：\n非經常收益之溢利。', '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）截至2025年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'), '0987', date(2025, 12, 31), HkBodyUnknownReason.PERIOD),
    ('B4-tail-nextline-depunct-note-no-num', ('股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年', '綜合全面收益表截至2024年12月31日止年度2024年2023年\n以下僅列上年度比較資料並非本期業績\n收入 100 90'), '0135', None, HkBodyUnknownReason.PERIOD),
))
def test_review03_scope_contract_fails_closed_in_owner_and_selector(
    case_name: str, pages: tuple[str, ...], ticker: str, anchor: date | None, reason: HkBodyUnknownReason,
) -> None:
    """原样固定 root/DS/MiMo 同源反例；中期供可信年度锚，避免无锚掩盖错误事实。

    参数：原反例名、完整物理页、公司、年度锚及失败原因。返回：无。异常：owner 或 selector 接受时断言失败。
    """
    facts = parse_hk_body_pages(pages, ticker, _DIGEST)
    raw = replace(_raw(category='中期業績' if anchor else '末期業績'), stock_code_payload=ticker)
    query = replace(QUERY, normalized_ticker=ticker)
    evidence = {raw.document_id: HkBodyEvidence(ticker, raw.document_id, raw.source_url, facts)} if isinstance(facts, HkBodyFacts) else {}
    anchors = () if anchor is None else (HkAnnualAnchor(anchor, 'trusted-annual', 'https://example.test/annual.pdf'),)
    selected = select_hkexnews_report_candidates(query=query, announcements=(raw,), local_annual_ends=anchors,
        read_head_meta=_head, body_evidence=evidence)
    assert not selected.candidates and len(selected.uncertain_reports) == 1, case_name
    assert facts == HkBodyUnknown(reason), case_name


@pytest.mark.parametrize('scope', (
    '以上數字是過往披露資料', '此表只供參照', '所列資料為過往披露資料',
    '該段轉載原公告', '所列資料不是當期結論', '非該期財務表現', '本期以外資料',
))
@pytest.mark.parametrize('position', ('summary', 'first_row', 'later_row', 'next_page', 'definition'))
def test_clause_grammar_cannot_become_nominal_scope(scope: str, position: str) -> None:
    """篇章指代、判断/转述谓词及限定结构不能凭数值或定义包裹变成名词。

    参数：不同句法的说明及五个归属位置。返回：无。异常：owner 或真实 selector 接受时断言失败。
    """
    opening = '股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年'
    statement = '綜合全面收益表截至2031年12月31日止年度2031年2030年'
    row = scope + ' 100 90'
    if position == 'summary':
        pages = (opening + '\n' + row + '\n收入 100 90', statement)
    elif position == 'first_row':
        pages = (opening, statement + '\n' + row + '\n收入 100 90')
    elif position == 'later_row':
        pages = (opening, statement + '\n收入 100 90\n' + row)
    elif position == 'next_page':
        pages = (opening, statement, '3\n收入 100 90\n' + row)
    else:
        pages = (opening + '\n核心溢利（附註1） 20 18\n1 核心溢利指不包括\n' + scope
            + '\n非經常收益之溢利。', statement)
    facts = parse_hk_body_pages(pages, '0135', _DIGEST)
    raw = _raw()
    bodies = {raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, facts)} if isinstance(facts, HkBodyFacts) else {}
    result = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,), local_annual_ends=(),
        read_head_meta=_head, body_evidence=bodies)
    assert not result.candidates and len(result.uncertain_reports) == 1
    assert facts == HkBodyUnknown(HkBodyUnknownReason.PERIOD)


@pytest.mark.parametrize('tail', (
    '收入 100 90\n上年度比較資料並非本期業績',
    '收入 100 90\n以\n下資料 20 18',
    '收入 100 90\n上年度比較資料並非本期業績：\n費用 20 18',
    '收入 100 90\n不支持的段落',
    '收入 100 90\n（上年度比較資料） 20 18',
))
def test_table_scope_does_not_end_at_first_row_or_page(tail: str) -> None:
    """未归属段落、折行句法和括号说明在页内/页间都关闭完整日期见证。

    参数：合法首行后的尾部。返回：无。异常：页边界掩盖说明时断言失败。
    """
    opening = '股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年'
    statement = '綜合全面收益表截至2031年12月31日止年度2031年2030年'
    for pages in ((opening, statement + '\n' + tail), (opening, statement, '3\n' + tail)):
        facts = parse_hk_body_pages(pages, '0135', _DIGEST)
        raw = _raw()
        bodies = {raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, facts)} if isinstance(facts, HkBodyFacts) else {}
        selected = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,), local_annual_ends=(),
            read_head_meta=_head, body_evidence=bodies)
        assert not selected.candidates and facts == HkBodyUnknown(HkBodyUnknownReason.PERIOD)


@pytest.mark.parametrize('note', (
    '1 核心溢利指不包括非經常收益之溢利。另列資料。',
    '1 核心溢利指不包括\n以\n下資料之溢利。',
    '1 核心溢利指不包括\n上年度資料。\n非經常收益之溢利。',
))
def test_definition_requires_one_owned_sentence_across_fragments(note: str) -> None:
    """定义不是跨行任意文本容器；完整拼接后仍须同一受支持定义句。

    参数：多句或跨行说明。返回：无。异常：错误闭合时断言失败。
    """
    pages = ('股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年\n'
        '核心溢利（附註1） 20 18\n' + note,
        '綜合全面收益表截至2031年12月31日止年度2031年2030年')
    assert parse_hk_body_pages(pages, '0135', _DIGEST) == HkBodyUnknown(HkBodyUnknownReason.PERIOD)


@pytest.mark.parametrize('tail', (
    '收入 100 90\n費用 20 18\n80 72',
    '附註 人民幣百萬元 人民幣百萬元\n其他收益，淨額 2 1\n非控制性權益 3 2',
    '其他全面收益：\n不可重新分類至損益之項目：\n金融資產\n（虧損）╱收益 (2) 1',
))
def test_supported_table_continuation_and_nominal_negation_keep_witness(tail: str) -> None:
    """有界表体跨页仍可连续校验；名词内否定/名词化不等同句级否定。

    参数：完整表体、合计及折行名词正例。返回：无。异常：误拒或由数值改期时断言失败。
    """
    opening = '股份代號0135\n業績公佈\n本集團財務業績摘要截至12月31日止年度2031年2030年'
    statement = '綜合全面收益表截至2031年12月31日止年度2031年2030年'
    for pages in ((opening, statement + '\n' + tail), (opening, statement, '3\n' + tail)):
        facts = parse_hk_body_pages(pages, '0135', _DIGEST)
        assert isinstance(facts, HkBodyFacts) and facts.end == date(2031, 12, 31)
        assert facts.page == 2 and facts.witness == statement


_REVIEW04_WORDINGS = (
    '與本期無關', '不代表本期業績', '屬過往披露資料', '係過往年度數字',
    '數字取自上年度公告', '資料反映上年度表現', '供比較之用', '即上年度數字',
    '有關資料乃上年度數字', '數字來自上年度',
)
_REVIEW04_OPENING = '股份代號0135\n業績公佈\n本集團財務業績摘要\n截至12月31日止年度2024年2023年'
_REVIEW04_STATEMENT = '綜合全面收益表截至2024年12月31日止年度2024年2023年'
_REVIEW04_INTERIM_OPENING = (
    _ISSUER_PREAMBLE + '股份代號0987）\n業績公佈\n本集團財務業績摘要截至6月30日止六個月2024年2023年'
)
_REVIEW04_DECLARATION = (
    '甲乙有限公司（「本公司」）之董事（「董事」）謹此宣佈，本公司及其附屬公司（統稱「本集團」）'
    '截至2024年6月30日止六個月（「本期內」）之未經審核綜合中期業績如下：'
)


def _assert_review04_scope_unknown(pages: tuple[str, ...], ticker: str, anchor: date | None) -> None:
    """同时断言真实正文owner及有足够年度供证的selector关闭。

    参数：完整页、身份及同公司可信年度锚。返回：无。异常：误授权事实或候选时断言失败。
    """
    facts = parse_hk_body_pages(pages, ticker, _DIGEST)
    raw = replace(_raw(category='中期業績' if anchor else '末期業績'), stock_code_payload=ticker)
    evidence = {raw.document_id: HkBodyEvidence(ticker, raw.document_id, raw.source_url, facts)} if isinstance(facts, HkBodyFacts) else {}
    anchors = () if anchor is None else (HkAnnualAnchor(anchor, 'trusted-annual', 'https://example.test/annual.pdf'),)
    selected = select_hkexnews_report_candidates(query=replace(QUERY, normalized_ticker=ticker),
        announcements=(raw,), local_annual_ends=anchors, read_head_meta=_head, body_evidence=evidence)
    assert not selected.candidates and len(selected.uncertain_reports) == 1
    assert facts == HkBodyUnknown(HkBodyUnknownReason.PERIOD)


def _predicate_scope_pages(clause: str, position: str) -> tuple[tuple[str, ...], str, date | None]:
    """构造共享准入的完整七位置输入，定义和宣告使用可映射的中期。

    参数：clause 为待判句；position 为既有接受路径。返回：物理页、身份和可信年度锚。
    异常：未知位置抛 AssertionError。
    """
    row = clause + ' 2024 2023'
    ticker = '0135'
    anchor = None
    if position == 'summary_before':
        pages = (_REVIEW04_OPENING + '\n' + row + '\n收入 100 90', _REVIEW04_STATEMENT)
    elif position == 'summary_after':
        pages = (_REVIEW04_OPENING + '\n收入 100 90\n' + row, _REVIEW04_STATEMENT)
    elif position == 'first_row':
        pages = (_REVIEW04_OPENING, _REVIEW04_STATEMENT + '\n' + row + '\n收入 100 90')
    elif position == 'later_row':
        pages = (_REVIEW04_OPENING, _REVIEW04_STATEMENT + '\n收入 100 90\n' + row)
    elif position == 'next_page':
        pages = (_REVIEW04_OPENING, _REVIEW04_STATEMENT, '3\n' + row + '\n收入 100 90')
    elif position == 'definition':
        ticker, anchor = '0987', date(2024, 12, 31)
        pages = (_REVIEW04_INTERIM_OPENING + '\n核心溢利（附註1） 20 18\n附註：\n1 核心溢利指不包括\n'
            + clause + '\n非經常收益之溢利。', _REVIEW04_DECLARATION)
    else:
        assert position == 'declaration_next'
        ticker, anchor = '0987', date(2024, 12, 31)
        pages = (_REVIEW04_INTERIM_OPENING, _REVIEW04_DECLARATION, '3\n' + clause + '\n收入 100 90')
    return pages, ticker, anchor


@pytest.mark.parametrize('clause', _REVIEW04_WORDINGS)
@pytest.mark.parametrize('position', (
    'summary_before', 'summary_after', 'first_row', 'later_row', 'next_page', 'definition', 'declaration_next',
))
def test_review04_predicate_scope_owner_and_selector(clause: str, position: str) -> None:
    """固定review04已演示谓词家族和真实接受路径，数字/换行不能将句子转作名词。

    参数：原探针谓词句与归属位置。返回：无。异常：owner或selector误接受时断言失败。
    """
    pages, ticker, anchor = _predicate_scope_pages(clause, position)
    _assert_review04_scope_unknown(pages, ticker, anchor)


@pytest.mark.parametrize('clause', (
    '該等數據係往年比較數字', '摘錄自往年業績', '上年度數字列作比較用途',
    '往年數據供比較之用', '比較資料取自往年公告', '资料反映本期表现', '与本期无关',
    '不代表本期業績、數字', '不代表本期業績 2024',
))
def test_review04_judgment_source_and_purpose_are_clauses(clause: str) -> None:
    """判断/摘录/来源/用途按语法关闭，不以提及往年或附带三列数字作为理由。

    参数：DS判断/摘录句、实际用途句及同家族正字/数字变体。返回：无。异常：误接受时断言失败。
    """
    pages = (_REVIEW04_OPENING + '\n' + clause + ' 2024 2023\n收入 100 90', _REVIEW04_STATEMENT)
    _assert_review04_scope_unknown(pages, '0135', None)


@pytest.mark.parametrize('clause', ('不代\n表本期業績', '與本期無\n關', '摘錄\n自往年業績', '供比較\n之用'))
def test_review04_split_predicates_do_not_become_definition_arguments(clause: str) -> None:
    """定义最终拼接仍校验同一谓词规则，跨行切开语法标记不能绕过。

    参数：已演示家族的折行片段。返回：无。异常：误拼为受支持定义时断言失败。
    """
    pages = (_REVIEW04_INTERIM_OPENING + '\n核心溢利（附註1） 20 18\n1 核心溢利指不包括\n'
        + clause + '\n非經常收益之溢利。', _REVIEW04_DECLARATION)
    _assert_review04_scope_unknown(pages, '0987', date(2024, 12, 31))


@pytest.mark.parametrize('label', (
    '上年度比較資料', '上年度之比較數字', '非控制性權益', '未分配溢利',
    '無形資產', '無抵押借款', '不動產', '未實現收益',
    '附屬公司應佔溢利', '附屬權益', '附属公司应占溢利', '附属权益',
))
@pytest.mark.parametrize('position', ('summary', 'table', 'next_page', 'definition'))
def test_review04_comparison_nouns_and_nominal_negation_are_positive(label: str, position: str) -> None:
    """裸比较名词和普通否定构词保留完整当前见证，财务数值可以恰等于年列。

    参数：名词标签及表格/附注位置。返回：无。异常：仅因历史词、否定字或数值拒绝时断言失败。
    """
    row = label + ' 2024 2023'
    if position == 'summary':
        pages = (_REVIEW04_OPENING + '\n' + row, _REVIEW04_STATEMENT)
    elif position == 'table':
        pages = (_REVIEW04_OPENING, _REVIEW04_STATEMENT + '\n' + row)
    elif position == 'next_page':
        pages = (_REVIEW04_OPENING, _REVIEW04_STATEMENT, '3\n' + row)
    else:
        pages = (_REVIEW04_OPENING + '\n核心溢利（附註1） 20 18\n1 核心溢利指不包括\n'
            + label + '\n非經常收益之溢利。', _REVIEW04_STATEMENT)
    facts = parse_hk_body_pages(pages, '0135', _DIGEST)
    assert isinstance(facts, HkBodyFacts) and facts.end == date(2024, 12, 31) and facts.kind == 'annual'
    raw = _raw()
    selected = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,), local_annual_ends=(),
        read_head_meta=_head, body_evidence={raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, facts)})
    assert len(selected.candidates) == 1 and not selected.uncertain_reports
    assert selected.candidates[0].report_date == '2024-12-31'


_REVIEW05_CLAUSES = (
    '該等數據系往年比較數字', '摘自往年業績', '無關本期業績',
    '非關本期業績', '供比較用途', '資料源於往年',
)


@pytest.mark.parametrize('clause', _REVIEW05_CLAUSES)
@pytest.mark.parametrize('position', (
    'summary_before', 'summary_after', 'first_row', 'later_row', 'next_page', 'definition', 'declaration_next',
))
def test_review05_shared_construct_variants_close_owner_and_selector(clause: str, position: str) -> None:
    """同一系词字形及关系顺序、来源介词、用途形态在各接受路径均不能成为名词。

    参数：已演示谓词及七个位置。返回：无。异常：误授权事实或真实候选时断言失败。
    """
    pages, ticker, anchor = _predicate_scope_pages(clause, position)
    _assert_review04_scope_unknown(pages, ticker, anchor)


@pytest.mark.parametrize('position', ('summary_before', 'next_page'))
@pytest.mark.parametrize('label,valid', (('该等数据系往年比较数字', False), ('附属公司应占溢利', True)))
def test_review05_simplified_header_reaches_shared_admission(position: str, label: str, valid: bool) -> None:
    """全简体可解析公告的正反对照，防止其它不支持表头伪装关闭字形缺口。

    参数：位置、全简体标签及预期。返回：无。异常：owner或selector不符时断言失败。
    """
    opening = '股份代号0135\n业绩公布\n本集团财务业绩摘要\n截至12月31日止年度2024年2023年'
    statement = '综合全面收益表截至2024年12月31日止年度2024年2023年'
    row = label + ' 2024 2023'
    pages = (opening + '\n' + row, statement) if position == 'summary_before' else (opening, statement, '3\n' + row)
    if not valid:
        _assert_review04_scope_unknown(pages, '0135', None)
        return
    facts = parse_hk_body_pages(pages, '0135', _DIGEST)
    assert isinstance(facts, HkBodyFacts) and facts.end == date(2024, 12, 31) and facts.kind == 'annual'
    raw = _raw()
    selected = select_hkexnews_report_candidates(query=QUERY, announcements=(raw,), local_annual_ends=(),
        read_head_meta=_head, body_evidence={raw.document_id: HkBodyEvidence('0135', raw.document_id, raw.source_url, facts)})
    assert len(selected.candidates) == 1 and not selected.uncertain_reports
    assert selected.candidates[0].report_date == '2024-12-31'


@pytest.mark.parametrize('clause', (
    '该等数据系往年比较数字', '无关本期业绩', '非关该期数字', '資料與本期非關',
    '資料與本期有關', '摘录于往年业绩', '摘錄於往年業績', '摘於往年業績',
    '資料源于往年', '資料源自往年', '资料供比较用途', '供本期分析之用',
))
def test_review05_constructs_allow_variable_arguments_and_orthography(clause: str) -> None:
    """构造内的宾语、关系顺序及来源介词可变，不依赖完整历史原句。

    参数：同构造变体。返回：无。异常：owner或selector错误接受时断言失败。
    """
    pages, ticker, anchor = _predicate_scope_pages(clause, 'summary_before')
    _assert_review04_scope_unknown(pages, ticker, anchor)


@pytest.mark.parametrize('clause', ('該等數據\n系往年比較數字', '摘\n自往年業績', '無\n關本期業績', '供比較用\n途', '資料源\n於往年'))
def test_review05_split_constructs_cannot_become_definition_arguments(clause: str) -> None:
    """折行后整体仍校验同一构造，不把拆开的谓词拼成定义名词参数。

    参数：跨行构造。返回：无。异常：误授权事实或候选时断言失败。
    """
    pages, ticker, anchor = _predicate_scope_pages(clause, 'definition')
    _assert_review04_scope_unknown(pages, ticker, anchor)


@pytest.mark.parametrize('label', ('附屬公司應佔溢利', '附屬權益'))
def test_review05_subsidiary_nominals_keep_interim_candidate_with_anchor(label: str) -> None:
    """附屬修饰构词也可用于有可信年度锚的中期续页，正例必须实际产生候选。

    参数：真实财报名词标签。返回：无。异常：owner或selector误拒绝时断言失败。
    """
    pages = (_REVIEW04_INTERIM_OPENING, _REVIEW04_DECLARATION, '3\n' + label + ' 2024 2023')
    facts = parse_hk_body_pages(pages, '0987', _DIGEST)
    assert isinstance(facts, HkBodyFacts) and facts.end == date(2024, 6, 30) and facts.kind == 'six_months'
    raw = replace(_raw(category='中期業績'), stock_code_payload='0987')
    selected = select_hkexnews_report_candidates(query=replace(QUERY, normalized_ticker='0987'), announcements=(raw,),
        local_annual_ends=(HkAnnualAnchor(date(2024, 12, 31), 'trusted-annual', 'https://example.test/annual.pdf'),),
        read_head_meta=_head, body_evidence={raw.document_id: HkBodyEvidence('0987', raw.document_id, raw.source_url, facts)})
    assert len(selected.candidates) == 1 and not selected.uncertain_reports
    assert selected.candidates[0].report_date == '2024-06-30'
