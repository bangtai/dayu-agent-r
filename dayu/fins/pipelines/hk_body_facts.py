"""领先三物理页内明确本期声明的港股业绩事实 owner；不获取网络或推断财年。"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from typing import Literal

from dayu.fins.pipelines.hk_body_extraction import extract_hk_pages, HK_BODY_PAGE_LIMIT

HkBodyKind = Literal["annual", "six_months"]
_CODE = re.compile(r"股[份票](?:代[號号]|[編编][號号])[:：]?([0-9]{1,5})(?:\.HK)?", re.IGNORECASE)
# 有页首公司头时，只接受已支持的交易所免责声明与发行人头结构；任意前置说明不当作页眉跳过。
_ISSUER_HEADER = re.compile(
    r"香港交易及結算所有限公司及香港聯合交易所有限公司對本公告之內容概不負責，對其準確性或完整性亦不發表任何聲明，"
    r"並明確表示概不就因本公告全部或任何部份內容而產生或因倚賴該等內容而引致之任何損失承擔任何責任。"
    r"(?P<issuer>[\u3400-\u9fff]+有限公司)[A-Z]+LIMITED\(incorporatedin[A-Za-z]+withlimitedliability\)[（(]?"
)
_PERIOD = r"截至(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日止(?P<kind>年度|六[個个]月)"
_OPENING = re.compile(
    r"[）)]?[業业][績绩]公[佈布]本集[團团][財财][務务][業业][績绩]摘要"
    r"截至(?P<month>\d{1,2})月(?P<day>\d{1,2})日止(?P<kind>年度|六[個个]月)"
    r"(?P<years>(?:\d{4}年){2})"
)
_STATEMENT_TITLE = (
    r"(?:未[經经][審审]核)?(?:綜合|综合)(?:中期)?(?:全面)?(?:收益表|損益表|损益表)"
    r"(?:[（(][續续][）)])?"
)
_STATEMENT = re.compile(_STATEMENT_TITLE + _PERIOD + r"(?P<years>(?:\d{4}年){2})?")
_SHORT_STATEMENT = re.compile(
    _STATEMENT_TITLE + r"截至(?P<month>\d{1,2})月(?P<day>\d{1,2})日止(?P<kind>年度|六[個个]月)"
    r"(?P<years>(?:\d{4}年){2})"
)
# 只支持公司董事直接发布的完整宣告句；不在任意引文内寻找“本集团/本期”。
_DECLARATION = re.compile(
    r"(?P<issuer>[\u3400-\u9fffA-Za-z·]+有限公司)（「本公司」）之董事（「董事」）謹此宣佈，"
    r"本公司及其附屬公司（統稱「本集團」）" + _PERIOD
    + r"（「本期(?:內)?」）之未經審核綜合中期業績如下[：:]"
)
_VALUES = r"(?:\(?-?\d[\d,.]*\)?|–)(?:\s+(?:\(?-?\d[\d,.]*\)?|–))+"
_SUMMARY_ROW = re.compile(r"(?P<label>.+?)\s+" + _VALUES + r"\s*")
_SUMMARY_UNIT = re.compile(r"(?:人民幣(?:百萬元|分)\s*){2}")
_NOTE_REFERENCE = re.compile(r"[（(]附[註注](?P<number>\d+)[）)]")
# 字形只约束可读形式；归属另由下述句法规则及表格/引用结构共同校验。
_NOMINAL_FORM = re.compile(r"[\u3400-\u9fffA-Za-z0-9、－，,╱/（）()]+")
_NOMINAL_LABEL = re.compile(
    r"[\u3400-\u9fffA-Za-z0-9－][\u3400-\u9fffA-Za-z0-9、－，,╱/]*"
    r"(?:(?:（[\u3400-\u9fffA-Za-z0-9、－，,╱/]+）|\([\u3400-\u9fffA-Za-z0-9、－，,╱/]+\))"
    r"[\u3400-\u9fffA-Za-z0-9、－，,╱/]*)*"
)
# 篇章标记与句级副词不属于此处支持的名词复合结构；不是历史词/指标表。
_CLAUSE_SYNTAX = re.compile(
    r"以[上下]|[上下]列|[前後后]述|[上下本]文|如[上下]"
    r"|[並并但而故則则僅仅只是為为]|不[是屬属]|非(?:本|此|該|该)"
    r"|以(?:外|前|後|后)(?![之的])"
    r"|(?:引|轉|转|援)(?:述|用|載|载)"
)
# 按已支持的谓词构造检查整段，而不要求命中某个完整非本期句子：
# 判断/表征、关系、来源与用途。关系允许介词前置或否定关系前置，来源将动词形态与介词分开，
# 用途支持“之用”和“用途”名词形态；宾语可变，也覆盖跨行拼接后的片段。
# “附屬”是名词修饰构词，不能因其中的“屬”误拒；不据往年/比较或数值判定作用域。
_PREDICATE_SYNTAX = re.compile(
    r"代表|反映|(?<!附)[屬属]|[係系乃即]"
    r"|[與与].*(?:[無无]|有|非)[關关]|(?:[無无]|非)[關关]"
    r"|(?:摘[錄录]?|[選选][錄录]|[節节][錄录]|取|[來来]|源)(?:自|[於于])"
    r"|列[作為为]|供.+(?:之用|用途)"
)
_DEFINITION_OPENING = re.compile(r"指不包括|乃根據")
_METRIC_DEFINITION = re.compile(
    r"(?:指不包括[\u3400-\u9fffA-Za-z0-9、]+之[\u3400-\u9fffA-Za-z0-9、]+"
    r"|乃根據[\u3400-\u9fffA-Za-z0-9、]+計算)。"
)


def _nominal_fragment(text: str) -> bool:
    """校验受支持的名词复合片段，不以全汉字或无句读证明其归属。

    参数：text 为去空白的标签或定义内名词参数。返回：形式合法且不含支持的句法标记时为真。
    异常：无。有限构造规则不承诺识别全部中文谓词或名词；表格位置/附注引用另行校验。
    """
    return (_NOMINAL_FORM.fullmatch(text) is not None
        and _CLAUSE_SYNTAX.search(text) is None and _PREDICATE_SYNTAX.search(text) is None)


def _definition_fragment(text: str, *, opening: bool = False) -> bool:
    """分开校验定义句框与名词参数，整句闭合另由定义语法负责。

    参数：text 为去空白片段；opening 表示必须先消费固定定义开头。
    返回：固定开头之后只有名词参数及可选句末时为真。异常：无。
    """
    content = text.removesuffix("。")
    if opening:
        frame = _DEFINITION_OPENING.match(content)
        if frame is None:
            return False
        content = content[frame.end():]
        if not content:
            return True
    return _nominal_fragment(content)


def _following_lines(text: str, compact_end: int) -> tuple[str, ...]:
    """保留匹配终点所在行的剩余文本和后续非空物理行。

    参数：text 为原页；compact_end 为去空白文本匹配终点。
    返回：剩余行，首行即使为空也保留。异常：调用者终点越界时抛 IndexError。
    """
    nonspace = tuple(re.finditer(r"\S", text))
    lines = text[nonspace[compact_end - 1].end():].splitlines()
    return tuple(line.strip() for index, line in enumerate(lines) if index == 0 or line.strip())


def _metric_row_label(line: str) -> str | None:
    """校验完整数值标签的形式及已支持的句法构造。

    参数：line 为保留列分隔的物理行。返回：标签或 None。异常：无。
    """
    row = _SUMMARY_ROW.fullmatch(line.strip())
    if row is None:
        return None
    label = re.sub(r"\s+", "", row['label'])
    nominal = _NOTE_REFERENCE.sub("", label)
    if _NOMINAL_LABEL.fullmatch(nominal) is None or not _nominal_fragment(nominal):
        return None
    return label


def _table_lines_are_closed(lines: tuple[str, ...]) -> bool:
    """逐行校验有界表格，数值首行不结束其后作用域的检查。

    参数：lines 为表头后的非空行或下一页的连续表体。
    返回：只有单位、名词分组、完整数值行与合计，且没有悬空标签时为真。异常：无。
    """
    pending = ""
    for line in lines:
        if not line.strip():
            continue
        compact_line = re.sub(r"\s+", "", line)
        if not pending and _SUMMARY_UNIT.fullmatch(line.removeprefix("附註").strip()) is not None:
            continue
        label = _metric_row_label(pending + line)
        if label is not None or (not pending and re.fullmatch(_VALUES, line.strip()) is not None):
            pending = ""
            continue
        if _SUMMARY_ROW.fullmatch(pending + line) is not None:
            return False
        # 分组标题和折行标签都使用同一名词语法；引号、句子、未支持段落不跳过。
        combined = pending + compact_line.removesuffix("：").removesuffix(":")
        if not _nominal_fragment(combined):
            return False
        pending = "" if compact_line.endswith(("：", ":")) else combined
    return not pending


def _statement_tail_is_closed(text: str, header_end: int) -> bool:
    """表头同行闭合后校验全部剩余表体；页末由外层继续校验下一页。

    参数：text 为原页；header_end 为去空白表头终点。返回：表头及本页表体均受支持时为真。
    异常：终点越界时抛 IndexError；调用者保证终点来自同页匹配。
    """
    lines = _following_lines(text, header_end)
    return not lines or (not lines[0] and _table_lines_are_closed(lines[1:]))


def _year_columns_are_consistent(columns: str | None, year: int) -> bool:
    """年份列只校验完整日期相容性，不从任一列产生日期。

    参数：columns 为已匹配的列或无列；year 为直接日期年。
    返回：无列或至少一列与日期相同为真。异常：无。
    """
    return columns is None or year in tuple(int(value) for value in re.findall(r"\d{4}", columns))


def _summary_scope_is_closed(text: str, opening_end: int) -> bool:
    """确认摘要到页末只有受支持的数值行和这些数值行引用的完整定义附注。

    参数：text 为保留换行的首页；opening_end 为去空白后摘要表头的终点。
    返回：没有未归属说明或未结束附注时为真。异常：无，调用者保证终点来自同页匹配。
    """
    # 保留行边界；定义名词参数和数值标签共用准入，不用历史词或单个否定字推期。
    lines = _following_lines(text, opening_end)
    if not lines:
        return True
    if lines[0].strip() not in ("", "變動%"):
        return False
    note_labels: dict[str, str] = {}
    notes_started = False
    pending = ""
    for line in lines[1:]:
        compact_line = re.sub(r"\s+", "", line)
        if pending:
            # 换行只能延续受支持定义的名词片段；独立语句、引述或作用域说明不可并入。
            if not _definition_fragment(compact_line):
                return False
            pending += compact_line
        else:
            label = _metric_row_label(line)
            if not notes_started and label is not None:
                reference = _NOTE_REFERENCE.search(label)
                if reference is not None:
                    note_labels[reference['number']] = _NOTE_REFERENCE.sub("", label)
                continue
            if not notes_started and _SUMMARY_UNIT.fullmatch(line.strip()) is not None:
                continue
            if not notes_started and compact_line == "附註：":
                notes_started = True
                continue
            for number, label in note_labels.items():
                prefix = number + label
                if compact_line.startswith(prefix):
                    definition = compact_line[len(prefix):]
                    if _definition_fragment(definition, opening=True):
                        pending = definition
                        break
            if not pending:
                return False
            notes_started = True
        # 只允许一个闭合的指标定义；定义后的独立说明不能继承为主报表作用域。
        if "。" in pending:
            if _METRIC_DEFINITION.fullmatch(pending) is None or not _definition_fragment(pending, opening=True):
                return False
            pending = ""
    return not pending


class HkBodyUnknownReason(str, Enum):
    """正文可读取但事实不足的封闭原因。"""

    IDENTITY = "identity_unconfirmed"
    PERIOD = "period_unconfirmed"
    CONFLICT = "conflicting_statements"


@dataclass(frozen=True, slots=True)
class HkBodyUnknown:
    """正常失败关闭；与提取执行错误区分。"""

    reason: HkBodyUnknownReason


@dataclass(frozen=True, slots=True)
class HkBodyFacts:
    """直接截止日、性质及原件/物理页见证；不声称中期财年。"""

    ticker: str
    end: date
    kind: HkBodyKind
    pdf_sha256: str
    page: int
    witness: str

    def __post_init__(self) -> None:
        """校验封闭事实。参数：无。返回：无。异常：ValueError 为非法见证。"""
        if (not self.ticker.isdigit() or self.kind not in ("annual", "six_months")
            or not re.fullmatch(r"[0-9a-f]{64}", self.pdf_sha256)
            or not 1 <= self.page <= HK_BODY_PAGE_LIMIT or not self.witness):
            raise ValueError("HK body fact 非法")


def parse_hk_body_pages(pages: tuple[str, ...], ticker: str, digest: str) -> HkBodyFacts | HkBodyUnknown:
    """从公告开头及紧随的主报表确认唯一支持声明。

    参数：pages 为领先物理页；ticker 为预期规范股票代码；digest 为实际原件 SHA。
    返回：有页见证的事实或封闭 unknown。异常：无；日期/声明冲突均关闭。
    支持身份后直接开始的业绩公告、无附加限定的摘要期间，及下一页开头的完整报表日期
    或董事直接宣告。年份列只校验完整日期是否相容，不供证或按列序猜期。
    标签/定义以有限词法和句法构造准入，不承诺任意中文语义完备；物理页不关闭作用域。
    """
    if not pages:
        return HkBodyUnknown(HkBodyUnknownReason.IDENTITY)
    compact = tuple(re.sub(r"\s+", "", p) for p in pages[:HK_BODY_PAGE_LIMIT])
    codes = {int(m) for m in _CODE.findall(compact[0])}
    if codes != {int(ticker)}:
        return HkBodyUnknown(HkBodyUnknownReason.IDENTITY)
    identity = _CODE.search(compact[0])
    assert identity is not None  # 上述身份集合已经证明存在唯一的预期代码。
    header = compact[0][:identity.start()].removeprefix("1")
    issuer_header = _ISSUER_HEADER.fullmatch(header)
    if header not in ("", "（", "(") and issuer_header is None:
        return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
    opening = _OPENING.match(compact[0], identity.end())
    if opening is None or not _summary_scope_is_closed(pages[0], opening.end()):
        return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
    # 封闭开头 grammar 的连续性就是作用域边界；不跳过说明、限定或引用去寻找子串。
    # 首页摘要只给出月/日及性质；年份必须由紧随主报表的完整日期直接提供。
    matches: list[tuple[date, HkBodyKind, int, str]] = []
    for page, compact_page in enumerate(compact[1:], 2):
        text = compact_page.removeprefix(str(page))
        page_prefix = len(compact_page) - len(text)
        raw_page = pages[page - 1]
        match = _STATEMENT.match(text)
        if match is not None:
            if not _statement_tail_is_closed(raw_page, page_prefix + match.end()):
                return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
            if not _year_columns_are_consistent(match['years'], int(match['year'])):
                return HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
        else:
            continuation = _SHORT_STATEMENT.match(text)
            if continuation is not None and matches:
                # 简写续表只校验已有完整见证；绝不由年份列补出一个本期日期。
                if not _statement_tail_is_closed(raw_page, page_prefix + continuation.end()):
                    return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
                known_end, known_kind, _, _ = matches[0]
                continued_kind = "annual" if continuation['kind'] == "年度" else "six_months"
                if ((int(continuation['month']), int(continuation['day']), continued_kind)
                    != (known_end.month, known_end.day, known_kind)
                    or not _year_columns_are_consistent(continuation['years'], known_end.year)):
                    return HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
                continue
            if re.match(_STATEMENT_TITLE, text) is not None:
                return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
            match = _DECLARATION.match(text)
            # 宣告里的“本公司”只能指向同一公告头的发行人，不能由引文自己声明归属。
            if match is not None and (issuer_header is None or match['issuer'] != issuer_header['issuer']):
                return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
            if match is not None:
                # 宣告整句先在物理行闭合；后接报表时须直接进入同期间的完整表头。
                lines = _following_lines(raw_page, page_prefix + match.end())
                if lines and lines[0]:
                    return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
                if text[match.end():]:
                    table = _SHORT_STATEMENT.match(text, match.end())
                    if table is None or not _statement_tail_is_closed(raw_page, page_prefix + table.end()):
                        return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
                    if ((int(table['month']), int(table['day']), table['kind'])
                        != (int(match['month']), int(match['day']), match['kind'])
                        or not _year_columns_are_consistent(table['years'], int(match['year']))):
                        return HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
        if match is None:
            # 完整见证后的物理页可能延续同一表格；不能 break 后保留未经校验的事实。
            raw_lines = tuple(line.strip() for line in raw_page.splitlines() if line.strip())
            if raw_lines and raw_lines[0] == str(page):
                raw_lines = raw_lines[1:]
            if not matches or not _table_lines_are_closed(raw_lines):
                return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
            continue
        try:
            end = date(int(match['year']), int(match['month']), int(match['day']))
        except ValueError:
            return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
        if ((end.month, end.day, match['kind']) != (int(opening['month']), int(opening['day']), opening['kind'])
            or not _year_columns_are_consistent(opening['years'], end.year)):
            return HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
        kind: HkBodyKind = "annual" if match['kind'] == "年度" else "six_months"
        matches.append((end, kind, page, match.group()))
    if not matches:
        return HkBodyUnknown(HkBodyUnknownReason.PERIOD)
    if len({(end, kind) for end, kind, _, _ in matches}) != 1:
        return HkBodyUnknown(HkBodyUnknownReason.CONFLICT)
    end, kind, page, witness = matches[0]
    return HkBodyFacts(ticker, end, kind, digest, page, witness)


def resolve_hk_body_facts(pdf_bytes: bytes, ticker: str, checkpoint: Callable[[], None] | None = None) -> HkBodyFacts | HkBodyUnknown:
    """从隔离 worker 的实际原件确认正文事实。

    参数：pdf_bytes 为原件；ticker 为规范身份；checkpoint 为取消观察。
    返回：直接事实或 unknown。异常：提取执行失败 typed 透传；取消原样传播。
    """
    extracted = extract_hk_pages(pdf_bytes, checkpoint)
    return parse_hk_body_pages(extracted.pages, ticker, extracted.sha256)
