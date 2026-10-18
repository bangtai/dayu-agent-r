# HK:00388 两份季度来源财期证据计划

## 状态、依据与裁决摘要

- work unit：`hk-period-evidence-20261018`；分支 `fix/hk-period-evidence-20261018`；取证代码版本／base／HEAD 均为 `dbc9483df8a5cecfecc20cc61333eff0319e5982`。
- 原 plan 阶段已完整读取根 `AGENTS.md`、[任务书](/Users/leo/workspace/portfolio-manager-v2/orch/workpapers/hk-g0-seed-20261018/dayu-period-task.md)、[总控记录](hk-period-evidence-20261018-control.md) 与 `/Users/leo/.codex/skills/gateflow/SKILL.md`。goal confirmation 和无重复承接的确认复用总控记录。本轮 plan fix 已读根约束、control 当前裁决、原计划及两路完整审核；仅修本计划并新增短的 [planfix 记录](hk-period-evidence-20261018-planfix.md)，不改生产／测试代码、不执行真实发布、不 commit／push／PR、不通知他人、不再委派。
- 原 plan preflight：工作分支正确，初始仅总控文档未跟踪；未发现本任务范围内额外 `AGENTS.md`。本轮仍在指定分支和上述生产 HEAD；未读取 `.env`、模型配置或凭据，未调查 TLS／沙箱／域名现象，未直接遍历读取受管财报文件。
- **动机成立，但不是缺失 FY2025 年报，也不是官方无法证明两份报告身份。** 两份来源分别为香港交易所 **2025 年 Q1、2026 年 Q1 季度业绩公告**。官方原文明确称“第一季”，同窗官方末期业绩提供 12 月 31 日年度截止日。
- **直接根因是年度证据准入在 owner 内出现两套不一致的家族判断。** `cn_report_selection` 的期间分类已经从官方“末期業績”分类识别年度结果 `Q4 -> (FY,Q4)`，但 `hk_annual_end_date` 先经过另一个只检查标题期间词的 `is_hk_report_family`，将“截至…止年度的綜合財務報表”判成非报告家族。远端和本地年度证据同时被丢弃。三个月季度来源因此按正确的失败关闭规则保持 unknown。该标题条件还承担未决投影资格；修复须分清年度供证与未决投影两种资格，共享唯一 category-first 基础家族与既有期间分类，不能顺带扩大非目标 unknown 集合。
- 建议一个最小 implementation slice：在该语义 owner 统一 category-first 家族与年度证据准入，复用现有财政日历、身份和仓储发布链路。无需新增公共 schema、财政日历配置、公司特例或 PDF 解析能力。
- 当前交付状态：原计划 SHA256 `9bb2a20823c4a54ba22c1e13361e81ec2271f7463ac9781b4d6f12fdc4e02573` 已经 mimo-flash／ds-flash 双路独立 planreview，总控裁决进入 plan fix；**本修订待双路受影响面 plan re-review 及总控裁决，未通过 gate、未获实施放行**。尚未进入 implementation／validation，真实发布命令本轮未运行。下文原始取证和基线均为原 plan 阶段的历史记录，本轮未重新取证或复跑基线；不能以这些记录替代改后验收。

## 可取回证据与采集事实

原 plan 阶段的证据根目录为 `/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/`，下称 `E/`。本节保留当时的采集记录，本轮 plan fix 不重复采集。原始官方响应与 PDF 均保留完整字节；文本和 PNG 是派生观察。证据 hash 用于核对保存版本，不替代保存文件。

| 文件 | 用途 |
| --- | --- |
| [plan_probe.py](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan_probe.py) | 实际只读探针；复用 discovery 原始查询／解析入口及仓储协议，不运行 download workflow |
| [plan-discovery-01.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-discovery-01.json)、[02](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-discovery-02.json)、[03](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-discovery-03.json) | 原始 HKEX HTTP body，分别为年报、中期报告、全部 results group；`result` 保持原响应的字符串化 JSON |
| [plan-discovery-probe.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-discovery-probe.json) | 完整请求 URL、UTC 获取时间、HTTP 状态、body hash、27 条归一行、当前选择结果与受控输入对照 |
| [plan-probe-comparison.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-probe-comparison.json) | 与总控原 `discovery-probe.json` 独立比较：27 条 source ID／title／URL／stock codes／category／filing date／language 全同，差异为空 |
| [plan-pdf-manifest.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-pdf-manifest.json) | 四份完整官方 PDF 的原始 URL、200 状态、类型、字节数、页数、获取时间与 SHA-256 |
| [plan-local-facts.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-local-facts.json) | 通过 `FsSourceDocumentRepository.read_source_meta_integrity_view` 取得指定 base、ticker 的 9 份元数据／完整性事实；未拼接受管路径读取 |
| [plan-owner-proof.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-owner-proof.json) | 四条 raw 在当前 owner 下的 family／projection／annual end 直接输出及已知年结日对照 |
| [plan-original-run-manifest.json](/Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/plan-original-run-manifest.json) | 原始 download-02 七个 command／result／diagnostic／process／stdout／stderr／log 文件的路径、字节数、行数和 hash |

采集命令实际为：

```sh
source .venv/bin/activate
PYTHONPATH=. python workspace/tmp/hk-period-evidence-20261018/plan_probe.py
```

首次仓储读因指定 base 在可写范围外，无法取得 storage publication 读锁；随后通过批准的提权执行同一脚本成功，未绕过仓储读锁或读取受管文件。此事实只记录取证执行条件，不用它解释财期问题。HTTPX 使用默认 TLS 校验，官方请求成功；未关闭校验。

独立 discovery 于 `2026-10-18T13:51:50.959945Z`、`13:51:54.448326Z`、`13:51:56.901252Z` 获取三个 200 响应；公司 profile 为 `HKEX:781 / 香港交易所 / 0388`。原探针时间为 `13:48:52.796091Z`，本轮没有只引用其结论。

实际请求 endpoint 为 `https://www1.hkexnews.hk/search/titleSearchServlet.do`，共同参数为：

```text
lang=zh&category=0&market=SEHK&stockId=781&searchType=1&documentType=-1
fromDate=20250101&toDate=20261018&MB-Daterange=0
sortByOptions=DateTime&sortDir=0&rowRange=100
```

分类参数依次是 `(t1code,t2Gcode,t2code)=(40000,-2,40100)`、`(40000,-2,40200)`、`(10000,3,-2)`。各响应 `hasNextRow=false`，`loadedRecord=recordCnt=len(rows)` 分别为 `2/2/23`，符合当前 downloader 的完整快照规则；没有以截断搜索结果证明全集。第三个 body SHA-256 为 `5e57e9bea03225f1dde71e39597a0a80dee9ba3d4c1f2c12283db85735a5a17a`。

### 来源 11655015：2025 年第一季度业绩

原始 discovery 行（完整行见 `E/plan-discovery-03.json` 的 `NEWS_ID=11655015`）：

```text
NEWS_ID: 11655015
STOCK_CODE: 00388<br/>80388
STOCK_NAME: 香港交易所<br/>香港交易所－Ｒ
TITLE: 截至2025年3月31日止三個月的季度業績
LONG_TEXT: 公告及通告 - [季度業績]
DATE_TIME: 30/04/2025 12:02
FILE_LINK: /listedco/listconews/sehk/2025/0430/2025043000614_c.pdf
FILE_TYPE: PDF
```

官方原文 URL：<https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0430/2025043000614_c.pdf>。

- `2026-10-18T13:51:57.448020Z` 完成获取和文本提取，HTTP 200、`application/pdf`，1,258,001 bytes、24 页；原件 `E/official-11655015.pdf`，SHA-256 `5eb09ff3a4038e35e3768e31088551792908a1b401ffa910b6d0beb07fb44054`。
- 已提取全件文本至 `E/official-11655015.txt`，并以 Poppler 渲染核对第 1、3 页。首页公司名称为“香港交易及結算所有限公司 / HONG KONG EXCHANGES AND CLEARING LIMITED”，股份代号 388／80388，标题“截至2025年3月31日止三個月的季度業績”。
- 第 2 页管理层原话：“2025 年第一季創下集團歷來最佳季度業績”；第 3 页财务摘要：“集團 2025 年第一季收入和其他收益及溢利創歷季新高”，主表列名“2025 年 第一季”，与首页三个月截止日一致。
- 结论：该来源为 **2025 Q1 季度业绩公告**；报告截至 `2025-03-31`，结合“第一季”、三个月范围与下述年度证据，报告期间为 `2025-01-01` 至 `2025-03-31`，财年结束年份为 2025。报告类型保持季度业绩／`Q1`，coverage 为 `[Q1]`；不是 FY 年报。原文与 discovery 共同证明身份，不凭 4 月披露日期或 3 月月末猜测。

### 来源 12131985：2026 年第一季度业绩

原始 discovery 行：

```text
NEWS_ID: 12131985
STOCK_CODE: 00388<br/>80388
STOCK_NAME: 香港交易所<br/>香港交易所－Ｒ
TITLE: 截至2026年3月31日止三個月的季度業績
LONG_TEXT: 公告及通告 - [季度業績]
DATE_TIME: 29/04/2026 12:04
FILE_LINK: /listedco/listconews/sehk/2026/0429/2026042900420_c.pdf
FILE_TYPE: PDF
```

官方原文 URL：<https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0429/2026042900420_c.pdf>。

- `2026-10-18T13:51:57.933771Z` 完成获取和文本提取，HTTP 200、`application/pdf`，1,223,491 bytes、22 页；原件 `E/official-12131985.pdf`，SHA-256 `0bd0d0d506a62e5c0bf453c34fc9b7164742e4b96b081232bf0cd71182711621`。
- 已提取全件文本至 `E/official-12131985.txt`，并渲染核对第 1、3 页。首页同公司、同股份代号，明确“截至2026年3月31日止三個月的季度業績”。
- 第 2 页标题“2026 第一季戰略摘要”；第 3 页“香港交易所 2026 年第一季收入及其他收益和溢利創歷季新高”，主表列名“2026 年 第一季”，比较列为 2025 年第一季。
- 结论：该来源为 **2026 Q1 季度业绩公告**；报告截至 `2026-03-31`，报告期间 `2026-01-01` 至 `2026-03-31`，财年结束年份为 2026；身份与 coverage 为 `Q1/[Q1]`。2025 比较列不改变本报告财年，不能把两份不同年度来源合并。

### 权威年结日来源及其报告类型

以下两条也来自完全相同的原始 results group 响应，股票代码均为 `00388<br/>80388`、官方分类均为 **`公告及通告 - [末期業績]`**：

| source ID | 官方标题、披露时间 | 官方 PDF URL |
| --- | --- | --- |
| 11548890 | 截至2024年12月31日止年度的綜合財務報表；27/02/2025 18:10 | <https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0227/2025022700760_c.pdf> |
| 12030670 | 截至2025年12月31日止年度的綜合財務報表；26/02/2026 17:56 | <https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0226/2026022600691_c.pdf> |

- 11548890：`2026-10-18T13:51:59.406990Z`，200／PDF，1,821,599 bytes、95 页，SHA-256 `2af259612a4649d72ed62d4b39affccfdfa59145f841e78b404bb42a7a67634e`。
- 12030670：`2026-10-18T13:52:00.701274Z`，200／PDF，1,778,269 bytes、98 页，SHA-256 `935fede3ce5f8108c908239c2bd52fdc3d388a59ce89976d1c9620b443b61b94`。
- 两份 PDF 首页均已渲染核对公司名称、388／80388 及对应年度截止日；第 2 页分别为“綜合收益表／截至2024年12月31日止年度”和“綜合收益表／截至2025年12月31日止年度”。首页说明该文件的年度财务资料“並不構成…法定年度綜合財務報表，但乃源自該等財務報表”，因此不能冒充完整年报身份；这不否定其明示的年度范围／年结日。
- 两个年度日期 `2024-12-31`、`2025-12-31` 是同公司原始标题和权威原文的直接事实，分别为相邻季度提供 366 天范围内证据；均为规则月末、年结月份一致，没有本轮证据中的年结日变更冲突。当前公开投影仍保持末期业绩 `Q4 -> [FY,Q4]`，不改为 FY 年报。

### 本地事实和原始运行

指定 base `/Users/leo/workspace/portfolio-manager-v2/workspace` 的 `0388` 仓储于 `2026-10-18T13:51:44.646219Z` 经严格同窗仓储读取：9 份均 `complete`，均为本公司下载来源且未删除；两个待调查 source ID 均不存在，`local_hk_annual_ends(entries)` 却为 `{}`。

其中年度结果已存在：11548890 绑定 `fil_cn_bcf2f6f0742728a99dae5fe8f68a66878817e472`，2024／Q4／`[FY,Q4]`／`2024-12-31`；12030670 绑定 `fil_cn_a51900baa92898b7fa892f5465c638a2bdbf2453`，2025／Q4／`[FY,Q4]`／`2025-12-31`。这两个 complete 文档的**原始标题／分类**仍被年度提取门槛拒绝；并非资产缺失或不完整。不能读取其派生 `fiscal_period=Q4` 来补证。

FY2025 年报为另一独立来源 12052684，绑定 `fil_cn_420ac77e1cccabb3fd680e938604f4f6f0e64399`，`2025年年報`、FY／`[FY]`、complete。其标题没有直接截止日，`report_date=null` 不能拿来猜年结日；不需要重新下载该年报来修复本问题。

已完整读取原始目录 `/Users/leo/workspace/portfolio-manager-v2/orch/jobs/hk00388-fy2025-income-g0-20261018-211756/download-02/` 的 `command.json`、`process.json`、`result.json`、`diagnostics.json`、stdout、stderr 及全部日志内容并提取相关记录。原始 invocation：

```sh
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli \
  --base /Users/leo/workspace/portfolio-manager-v2/workspace \
  --log-file /Users/leo/workspace/portfolio-manager-v2/orch/jobs/hk00388-fy2025-income-g0-20261018-211756/download-02/dayu.log \
  download --ticker HK:00388 --start 2025-01-01 --end 2026-10-18
```

原进程 3107，`21:34:57.813756+08:00` 启动，`21:40:12.951321+08:00` 完成，exit 1。diagnostics 明确 `partial_failure`，11 discovered／5 downloaded／4 skipped／0 failed／0 rejected／2 uncertain。两个 uncertain 均 `existing_document_id=null`，分别保留 `2025-03-31`／`2026-03-31` 与 filing date。失败原因是 `execution`，transport 为 null；没有把未决报成 PDF 下载失败。

日志第 1 行为 `form_type=None`、正确窗口、`overwrite=False`；第 4 行为 FY2025 年报 `integrity_complete` skip。两条 `download_committed` 事件分别以 document_id `fil_cn_a51900baa92898b7fa892f5465c638a2bdbf2453`（2025 年度结果）和 `fil_cn_bcf2f6f0742728a99dae5fe8f68a66878817e472`（2024 年度结果）定位；汇总事件为 `total=9 downloaded=5 skipped=4`。原 manifest 按 Python `str.splitlines()`（含 CR 分行）计数，以上三处为 249／510／511；按 LF 计数则为 243／500／501。总控已对同一 SHA 原始字节复核，这是分行口径差异，不是证据或事件版本错误。stderr／diagnostics 的 11 discovered 包含两份独立未决，日志 total=9 不构成漏下载根因。原 diagnostics SHA-256 为 `d4be0a72650d25ad653b4ba27dc5a9fcd2ccc6f72f6ad522f8c2c06766b46a2d`，日志 SHA-256 为 `b873faa1b7d5ac95111524b15067c54a3482bf154e90be6ad6bc1aeab9a84986`。原失败记录应继续保留，后续成功不回写历史结果。

## 根因和语义 owner

直接代码链路（均为上述 base 版本）：

1. `hkexnews_downloader.py:397` 起的 `_query_period_announcements`／`_fetch_complete_title_search_rows` 负责 HTTP、完整快照、raw 归一；本轮原始行与归一值一致，两个 source ID、官方分类、URL 均完整。此层不是期间推断 owner，不应追加公司特例。
2. `cn_report_selection.py:312` 的 `select_hkexnews_report_candidates` 对同查询窗去重 raw 取 `hk_annual_end_date`，与独立本地年度证据合并，再调用统一 resolver。`cn_download_workflow.py:273` 经仓储严格读取并调用 `local_hk_annual_ends`；其 `cn_report_selection.py:1002` 起也复用 `hk_annual_end_date`。
3. `cn_report_selection.py:988` 的 `hk_annual_end_date` 先调用 `is_hk_report_family`。后者虽然从 category 确立唯一 results family，随后仅从 `title` 查含“全年／業績／季度／期间长度”等词；“年度的綜合財務報表”未命中，于是年度证据提前返回 None。
4. 同模块 `:650` 起的 `_classify_hk_period_projection` 则共同解释 category 与 title：官方 category 的“末期業績”已唯一命中 Q4。这两条年度 raw 因而同时出现 **family=False、projection=Q4、report_end=明确日期、annual_end=None**，见 `plan-owner-proof.json`。年度证据与候选分类对同一事实产生相反判断，是最早的实际失真点。
5. 标题纯函数 `hk_fiscal_calendar.annual_end_dates` 的独立年度词表也不识别“年度的”，但**仅扩充该正则不能修复第 3 步的先行拒绝**，还可能将脱离 category 的年度股息标题当证据。生产 HK annual 准入应以 category-first 语义真源为准。
6. `hk_fiscal_calendar.fiscal_quarter_at` 没有收到年度日历；两条目标标题只提供“三個月”，`_resolve_hk_results_identity` 不从长度默认 Q1，所以 resolver 为 None、产生 `uncertain_hk_period`。这部分失败关闭行为正确，不能弱化。

总控接受的修正边界：原 `is_hk_report_family` 混用了基础家族和“无法解期但已有报告标题信号”的未决资格。年度准入误用后者作为前置门槛才是本轮要消除的耦合；未决资格保留现有标题证据条件，不另立第二套家族真源，也不把所有 category 为 results 的不可解输入都新增为 uncertain。

只读受控对照：冻结同一 27 条 raw、同一 query、同一当前代码，不发送 HEAD、不进行 workflow 发布。原输入（远端提取为空、本地提取为空）得到 9 candidates／2 uncertain；仅将已经由官方年度 PDF 核对的 `(2024-12-31, 2025-12-31)` 传入现有 `local_annual_ends` 参数，得到 11 candidates／0 uncertain，目标分别为 `(2025,Q1,[Q1])`、`(2026,Q1,[Q1])`。该输入对照证明缺的是**现有证据的 owner 准入**；它不是向真实仓储注入日期的修复办法，也不等于已完成真实 CLI 验收。

唯一职责划分：

| 语义 | owner／本次方向 |
| --- | --- |
| HKEX raw 身份、官方分类、URL、查询完整性 | downloader；保持严格协议，不修改 raw 来凑匹配 |
| report/results 基础家族、期间分类、年度证据资格、未决投影资格、候选选择 | `cn_report_selection`；共享唯一 category-first 基础家族与既有期间分类，明确两种资格的不同条件 |
| 标题直接日期、邻近证据窗口、规则财年／季度计算 | `hk_fiscal_calendar`；复用，不新增默认年结日或放宽冲突 |
| 来源稳定 ID 与同 source 复用 | `cn_download_identity`；沿用 `(provider,source_id)`，不按新期间重命名已有来源 |
| 原子 source／manifest／blob／processed／revision 与历史 | `dayu.fins.storage` 及现有 workflow；不直接写文件，不触碰调用方 |
| uncertain／failure／cancelled／摘要的公共投影 | `download_contract`／workflow／既有 CLI 投影；保持同一结果真源，不在 CLI 消 unknown |

## 一个 implementation slice

**行为结果：原始官方末期业绩的明确年度截止日被远端 discovery、本地 complete 来源和本地 resolver/rebuild 一致信任；真实普通增量将两份已证明季度来源以各自 Q1 正确发布。符合原有未决资格而无法证明或有冲突的来源继续未决；原来不满足该资格的输入继续忽略。** 代码、fixture、测试、必要 README 在同一个 slice 完成，没有中间依赖需要拆分。

最小方向和约束：

- 在 `cn_report_selection` 共享唯一 category-first 的 report/results 基础家族判断及既有期间分类。家族存在不意味着期间已确认；年度证据资格和未决投影资格分别在该基础上判断，不保留错误多真源。实现者可最小拆分窄纯 helper，具体拆分与算法细节由实现者决定。
- 年度证据资格：基础家族有效、既有期间分类已确认 `FY/Q4` 投影、原标题有唯一明确截止日，且通过既有冲突规则，才提供年度日期。官方“末期業績”＋唯一明确年度截止日的上述两条 raw 不得再被仅标题信号的未决资格否决；不得用缓存的 Q4／财年标签代替重解析原始分类和标题。
- 未决投影资格：沿用原有报告标题证据条件，语义为“属于报告家族、无法解期但已有报告标题信号”，不是另一套家族定义。category 为 results 但 title 无现有期间／家族信号且不可解者仍忽略；已支持的报告标题因缺依据无法解期者仍 unknown。不能为了年度供证把前一类新增为 uncertain，也不能把后一类吞掉。
- 组合分类：纯股息／董事会类别无财报家族，不供年度证据且仍忽略；官方“末期業績”可与“股息或分派”等分类组合。同标题有唯一明确年度截止日、既有投影确认为 FY/Q4 且没有中期／期间冲突时，其官方年度结果日期可供证；标题含“股息”不自动抹除同来源官方末期业绩事实。组合分类缺日、多日或中期／期间冲突不供证。此裁决只涉及可信年度日期，不把公告投影成完整 FY 年报；不靠全局词表加入“年度”放宽准入。
- `resolve_hk_report_period`、远端选择、本地 `local_hk_annual_ends`／rebuild 消费相同 owner；不得在 downloader、CLI、单一 ticker 分支、本地 fixture 或调用方补默认日期。保留原始标题、分类、source ID 和 URL。
- 不引入独立 HK PDF facts／公司日历配置或新 schema。官方 PDF 用于本轮取证和离线 fixture 的权威核验；生产所需截止日已在官方 raw 中，无需每次额外下载 PDF 来推断日历。
- 当前两个目标来源未入库，已有九份来源投影无需改变。本修复不改日期／季度算法、366 天阈值、持久 schema、身份或 skip 版本语义，保持 `CN_PIPELINE_DOWNLOAD_VERSION` 和 `hk-period-v3`。rebuild 每次重新解析原始年度输入，不以当前 v3 标签短路；该标签是既有审计／算法标识，不是每次 bugfix 的代码指纹，实际运行以 Git HEAD 和证据 hash 留档。用隔离测试验证已标 v3 的来源仍能经新年度准入重新投影；不在真实 base 运行 rebuild，不让普通增量变成 rebuild／overwrite。若实现实际改变上述契约，先交总控重新核对，不能隐含扩大承诺。
- 将本轮必要官方 raw／provenance 固化到 `tests/fins/fixtures/` 的本任务 fixture；保存完整来源 URL、取得时间、原始 hash、必要行与原件／派生件区别。测试直接消费真实 category/title，不让 fake 预先注入两个日期而跳过准入缺陷。无需把完整 PDF 二进制机械加入仓库；如采用首页派生 PDF，须明确其派生 provenance。

### 重要契约与边界

- filing-date 窗口保持包含边界。HK bare 命令虽然摘要 filters 为 FY／H1 baseline，discovery 必须覆盖 FY、H1、Q1～Q4；不得加 `--forms` 隐藏目标季度。
- FY 年报／H1 中期报告与 Q4 末期业绩／Q2 中期业绩保持独立 identity；`Q4->[FY,Q4]`、`Q2->[H1,Q2]` 只表示 coverage，不能满足独立年报基线。目标 Q1 的 form／report_kind／fiscal_period 均 Q1、coverage 仅 `[Q1]`。
- 财年为报告财年结束年份。report_date 仍来自明确原标题，原文中比较年度不能覆盖当前年。年度日期须是同公司、有唯一直接截止日的原始事实；年报名“2025年年報”、披露日期、已缓存的 Q4 标签均不能反推日历。
- 年度 raw 与远端候选共用同一实际查询窗；本地可信年度独立于远端 filing 窗口，但仍受同公司、download provider、未删除、COMPLETE、严格元数据及 366 天邻近规则约束。保留英文材料可供年度证据、仅中文主候选的规则。
- 属于报告家族且满足原有标题证据条件的来源，无年度证据且无明确序号的“三个月”仍 unknown。多日期、坏日期、不同年结月份、非月末、不在季度边界、明确序号与日历冲突仍失败关闭；不得提高邻近阈值或默认 12 月年结。无标题期间／家族信号且不可解的 results 输入保持忽略，不因本修复扩大 uncertain 集合。
- 同 source ID 核心事实冲突继续 typed／原失败路径；同来源已存在时复用既有外部／内部 ID，不因财期重新创建或删除历史；不同来源不按同年度结果互相覆盖。本轮本地两份目标均缺席，无需历史迁移。
- unresolved 保留 source ID／filing date／可确认 report_date／可空既有 document ID，不给其填入未经证明的财年／财期。公共 `uncertain_hk_period` 六字段 JSON 和安全说明保持；本次无需新增原因码或 LLM-facing schema。
- uncertain 与下载／转换失败、rejected 是不同集合；有未决时保留确定来源处理成果及 `partial_failure`／exit 1，不能以零 failed 假报整体成功。
- 取消继续由 workflow 的 checkpoint 和既有控制异常驱动；取消／整体中止时尚未返回结果的候选不判成功、跳过或失败。当前 slice 不增加网络阶段，不改 Host 取消所有权。
- 转换／写入失败按现有 per-filing 诊断，原子 rollback 保留已有版本；成功重试以 source ID 幂等，重复执行保持资产、revision、版本历史和其他九份来源。不能用“最终成功”回写原失败记录。
- 无法证明／网络失败必须保留实际失败或未决，禁止关闭 TLS 校验、手工修受管文件或用不相关参数把验收跑绿。

## 验证计划与实际基线

### 原 plan 阶段已执行的只读验证

- 上述探针实际返回：`rows=27, local_entries=9, annual_ends=[], current_candidates=9, current_uncertain=2, supplied_candidates=11, supplied_uncertain=0, pdfs=4`；使用当前 base，无生产修改。
- 实际命令和结果：

```sh
source .venv/bin/activate
pytest -q tests/fins/test_cn_report_selection.py tests/fins/test_f5_storage_calendar.py tests/fins/test_f5_workflow_rebuild.py tests/fins/test_hkexnews_downloader.py
# 232 passed，3 项既有 edgar DeprecationWarning，3.52s

source .venv/bin/activate
pyright
# 0 errors, 0 warnings, 0 informations

source .venv/bin/activate
pyright --project workspace/tmp/hk-period-evidence-20261018/plan-probe-pyrightconfig.json
# 临时探针单独纳入检查：0 errors, 0 warnings, 0 informations
```

项目 pyright 默认排除 workspace，所以额外配置显式检查临时脚本；没有拿“被排除所以零错误”作脚本通过证据。工具提示 pyright 有新版本不属于类型告警。

既有测试覆盖三个月非默认 Q1、日历冲突、同窗／本地证据、真实 Fs、unknown、重建和取消；测试均通过仍未抓到本次年度原标题，因此须补真实 raw 回归。基线通过仅描述当前版本，不可替代改后验证。

### 改后 owner 级和链路断言

1. 年度资格：两条真实年度 raw `11548890`／`12030670` 从同一基础家族／既有期间分类分别提取 `2024-12-31`／`2025-12-31`，不因“末期業績”只在 category 而拒绝；纯股息／董事会类别不供证且忽略，无分类、同时 report/results、期间冲突、中期来源不被错误采纳。
2. 未决资格：独立于 0388 的 27 行回归，补 category 为 results、title 无现有期间／家族信号且期间不可解的反例，断言不供年度证据且继续忽略、不新增 uncertain；已支持的报告标题缺年度依据仍 unknown，且维持 `partial_failure` 语义。这些断言落在 owner 的真实 selection contract，不在 fixture 或 CLI 设补偿分支。
3. 组合分类：新增官方“末期業績／股息或分派”＋标题含股息且唯一明确年度截止日的正例，断言 FY/Q4 投影无冲突时可供该年度日期，仍保持末期业绩 Q4／`[FY,Q4]`，不成为完整 FY 年报；另补同组合缺日、多日以及中期／期间冲突反例，均不供年度日期。不能只测纯股息来替代组合边界。
4. 冻结 27 条原始响应经真实 downloader parser→selection，年结日先于期间过滤产生；11 个确定候选、0 未决，目标 `11655015`／`12131985` 分别确认 2025／2026 Q1，原标题／分类／source ID／URL／report_date 不变，Q4 与 FY 仍各自独立。未知不触发 HEAD；同 ID 核心事实冲突仍拒绝。
5. 真实 Fs complete 年度来源与远端同 raw 得到相同年结日；窄窗口只有季度也能消费本地可信年度。逻辑删除、非 COMPLETE、跨公司、非下载来源仍不提供证据；不能读取派生 fiscal 字段补证。
6. 用实际 workflow 证明上述两份季度从 uncertain 变为候选和正常发布；仓储 meta／manifest／typed/public result／CLI 期间一致。符合未决资格而无年度或有矛盾证据的反例保留 uncertain＋partial_failure，不伪造 Q1。rebuild 复用同一 resolver；隔离测试保留来源当前 `hk-period-v3` 标签，断言仍重新解析原始年度输入，经新年度准入重新投影出原始输入支持的正确期间，不因版本相同而缓存跳过，且不改版本标签；不能只断言标签未变。**不在真实 base 运行 rebuild**。
7. 重复普通增量、一个转换失败后重试、取消发生在 discovery／单文档提交前后的边界：既有版本与已提交前缀保留，未决不变成下载失败，未开始候选不伪造结论。复用仍适用的既有取消测试，在新增真实 raw 情形补关键 owner／交互断言，不重做全套状态机。

实现后至少重跑上述四个测试文件，并按实际受影响面覆盖 `tests/fins/test_cn_download_workflow.py`、`tests/fins/test_f5_result_contract.py`、`tests/cli/test_output.py`；如修改 shared contract／导入，还跑对应边界守护。运行全项目 `pyright`。新增或修改 owner 文件单文件覆盖率目标 >=80%，不能靠镜像实现的测试凑数；临时取证脚本不作为产品测试。

### 后续真实普通增量验收（本 plan 未执行）

先通过仓储协议保存指定 base 的当前 identity／revision／document_version／fingerprint／资产 hash 与必要历史快照；原始 download-02 不改动。用实际固定 CLI，以下只有日志落点换成本任务证据目录，业务参数完全相同：

```sh
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli \
  --base /Users/leo/workspace/portfolio-manager-v2/workspace \
  --log-file /Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/validation-01-dayu.log \
  download --ticker HK:00388 --start 2025-01-01 --end 2026-10-18
```

保存真实 argv、运行 HEAD、进程起止时间、stdout／stderr 原文、exit code、完整 diagnostics JSON、对应 log；通过仓储和 typed result 核对全集，不能只看有界摘要。此命令会发布，只能在 plan 获总控和双路审核放行后由 implementation 执行。

在官方 raw 与本地基线未变、两个新 PDF／Docling 转换和提交都成功的条件下，预期 `exit=0`、11 discovered／2 downloaded／9 skipped／0 failed／0 rejected／0 uncertain、missing 为空，terminal 为 `succeeded`。不是把这些数字写死进产品；网络或新增披露改变时保存差异、核对实际 raw 后裁决。

仓储必须新增 source 11655015→2025 Q1、12131985→2026 Q1，report_date 分别 `2025-03-31`、`2026-03-31`，coverage `[Q1]`；当前无身份占用时现有 ID owner 预期分配 `fil_cn_ede631a4c5f5f8d7a0846a30a0c1e976d0da1303`、`fil_cn_92402294f583ce80f85e1144a3d6181d93a8285d`。以 fresh 身份观察为准，ID 仅是引用，不作业务证据。两个来源的 PDF／Docling／原文／primary／meta／manifest 必须同版且 COMPLETE；其他九份 source 尤其 FY2025 年报的身份、资产和内容版本不能被覆盖或丢失。

再执行完全相同业务参数，日志换 `validation-02-dayu.log`，预期 0 downloaded／11 skipped／0 uncertain／exit 0；检查 source ID 绑定、revision／版本／资产 hash／历史未变。若首次转换失败：允许真实 exit 1 和完整失败诊断，修复范围内原因或有据记录外部阻塞；重试不得重复建 source、删除旧版或将失败算跳过。若官方来源撤回、冲突或缺年结日，必须有据保留未决，不能以验收预期倒逼判 Q1。

**不采纳“无需改码，只补本地年报或直接重试”方案。** 当前本地已 complete 的年度结果仍被相同 owner 拒绝，且同窗远端已经有直接年结日证据。无代码普通重试会重现 9 确定／2 未决（已由纯选择复现）；不会因年报已存在而自动取得日历。若总控最终裁决无需改码，仍须解释并证明哪条允许的上游输入能通过现有 owner，并运行上述同参真实 CLI；手工写入年结日不能算替代验收。

## README 决策、影响面与审核要求

- 本次 plan 不改任何 README，避免将未实施能力写入开发文档。
- implementation 触及 `dayu/fins`：已读 `dayu/fins/README.md` 的“Agent更新约束”和 Downloaders／report selection 段。落地后在该职责范围补清“原始 category/title 的统一年度准入，远端与本地同源、缺失／冲突仍未决”；不加入本任务过程、公司特例、运行命令或路线图。
- 已读 `tests/README.md` 的维护／更新边界。只在新增真实官方 raw fixture／回归定位需要时更新对应既有 Fins 测试说明，记录当前覆盖及 provenance，不机械复制测试清单或未来计划。
- 预期不触及用户命令、安装、输出通道、工作区位置、分层或装配，不触发根 README 和 `dayu/README.md` 实质更新；无 Engine／Host／config 修改。若实现实际改变这些承诺，须按触发规则重新检查。
- 直接影响：HK raw→annual end、local annual extraction、resolver／selection／rebuild；间接影响：新 Q1 候选发布、typed result／CLI 的 uncertain 数和终态。CNInfo、US、调用方 G0 财报提取逻辑不属于本 slice。
- 原双路完整 planreview 已完成，结论和裁决见 control；本轮不重开全量取证或基线。受影响面双路 plan re-review 待独立核对：① 年度资格与未决资格是否共享唯一基础家族／既有期间分类，且非目标 unknown 不扩大；② 组合末期业绩／股息的年度、缺日和冲突边界及 Q4／FY 身份；③ 同 v3 重解析、HEAD／证据 hash 的留档语义；④ 日志分行／事件引用与单 slice、真实同参两次 CLI 验收是否仍一致。总控裁决复审结果后才可授权 implementation；本修订不代替 reviewer 给 pass。

## 风险、未覆盖项与下一入口

| 风险／未覆盖项 | 分类 | owner／destination |
| --- | --- | --- |
| 当前 raw 已证明的年度证据被丢弃；真实 CLI 尚未改后运行 | fixed in current slice（计划归类，尚未修复） | 本 work unit implementation／真实 validation；没有通过前不得报完成 |
| 年度供证与未决投影误用同一资格，可能扩大其他 results 标题的 unknown 集合 | fixed in current slice（计划边界已补，待复审／实现） | `cn_report_selection` owner；共享基础家族，未决保留标题证据条件，反例锁定继续忽略／仍 unknown；双路受影响面复审及最终 code review |
| 组合末期业绩／股息的日期准入可能被错误放宽或过度排除 | fixed in current slice（总控已裁决，待实现） | Fins 财期 owner；组合年度正例、缺日／多日／中期冲突反例及 Q4 非 FY 身份断言；最终 code review |
| 同 v3 来源被版本缓存跳过，或把版本标签误当 bugfix 代码指纹 | fixed in current slice（总控已裁决，待验证） | rebuild／财期 owner；隔离测试锁定同 v3 重新解析年度输入，实际运行记录 HEAD／证据 hash，不改版本、不跑真实 rebuild |
| 官方分类自身错误或年度日期污染的推测性外部异常 | assigned to later work unit | Fins 财期 owner；当前无实际 provider 异常证据，本轮保留日期／冲突／无依据失败关闭，覆盖已有冲突反例；有具体来源证据再开 work unit，不新增纠错框架 |
| 年结日变更、过渡期、52／53 周财年不能由当前规则月末财政日历证明 | assigned to later work unit | Fins 财期 owner；本次保持有据 unknown，不新增支持承诺；本两来源已有正证据无需以此阻塞 |
| 历史已被错误标签命名的其他来源或需迁移的旧库 | assigned to later work unit | Fins 仓储／财期 owner；本地本次 9 个 source 已核，不作跨公司／全历史扫描，不调用真实 rebuild |
| 原始 HTTP／PDF 后续可能变化；E/ 是本地临时证据，不能作为永久测试依赖 | fixed in current slice（计划归类） | implementation 固化最小官方 fixture/provenance；审核使用当前保存原件，未来网络差异另行核对 |
| fresh 仓储快照、Docling／网络获取／磁盘写入的真实结果尚未验证 | fixed in current slice（计划归类） | implementation 经仓储协议取得 fresh 快照，执行真实同参 CLI 两次；保留原始失败，必要外部阻塞交总控明确裁决 |
| TLS／沙箱／域名现象 | assigned to later work unit | 原报修方既有证据记录；明确非目标，本轮不归因不调查 |

没有尚未取得而阻止上述最小修复设计的身份／原文／代码证据。总控已接受 owner 根因、单 slice 及上述边界裁决；本轮只把裁决落实到计划。所有“fixed in current slice”是待实现／验证的工作归类，当前生产问题仍未修复，不是完成声明。尚待双路受影响面 plan re-review 和总控裁决，不得把原双路 pass-with-risks 或本 plan fix 当作实施放行。

**current gate / next entry point：plan fix 已交付，待 mimo-flash／ds-flash 双路受影响面 plan re-review 及总控裁决。** 本 Agent 不自行通过 gate，不推进 implementation、真实发布、commit／push／PR、外部通知或再次委派。
