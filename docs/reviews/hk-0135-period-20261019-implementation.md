# 0135 implementation / validation slice

状态：**本 slice 的实现与验证完成，交 root 对最终组合版本进行双路完整代码审核。未 commit / push / PR / merge，未外发。**

## 1. 范围、版本与依据

- 分支始终为 `fix/hk-0135-period-20261019`；HEAD 始终为 `f975a9586261bf7750e632959848bb6392c2881b`，未切换 base。继承已交付 PR204 / 未合并 PR203；本轮只产生 0135 工作树 delta。
- 开工产品、测试和依赖零 delta，仅七份 root / plan / review 治理文档未跟踪。已完整读取 AGENTS、control 末尾 root 放行裁决、v2 plan、fix-01、DS `044710` 和 MiMo `045031` 复审。v2 SHA 为 `208dee4ff52840367204eadc0a661d421a1042314729f678b92a670cef5ed469`。上述治理材料及 9633 治理材料未修改。
- 动机成立，但标题输入不足时 unknown 本身正确。修复的是受控正文事实输入缺口，没有放宽原标题解析，没有从披露日猜期，也没有写死公司、source ID 或四个日期。
- 唯一产品 writer；未派 agent。未调查 TLS、沙箱或域名，未改调用方，未创建 timer，未新增持久 schema、迁移或其它市场能力。

证据根统一记为 **E**：`workspace/tmp/hk-0135-period-20261019/implementation-01/`。

最终 37 份源码 / 测试 / README / 依赖文本快照：`E/source-before-production-v4/`；逐文件 SHA、删除路径与完整源码 patch 在其 `manifest.json` / `complete-source.patch`。patch SHA256：

```text
d5bd996f6d46c11d2ff2cf956e75376c8cecc66ab34d7891ef80560138163ba6
```

官方 fixture 仓储另外保留在 `tests/fixtures/hk_body_official/`，不是把受管 PDF 路径绕过 storage 读入源码 patch。`provenance.json` 逐份绑定官方 raw、URL、HTTP200、时间、长度与 SHA；四份完整原件均经 storage 写入和读回。源码 patch 包含全部代码变化，fixture 仓储和其来源清单构成另列的新增资产。最终审计为 `E/final-audit.json`，结束证据清单为 `E/final-manifest.json`；清单不包含自身或引用它的本报告，避免循环。

## 2. 实现及 P1–P4 闭环

| 项目 | 最终 owner 与实现 | 验证 / 状态 |
| --- | --- | --- |
| P1 同批年度先验 | selection 先确认全部正文年度及月末 / 性质 / 身份，再合并本地、标题和同批正文年度锚，最后映射中期。正文无可信锚绝不走旧标题季度回退；保留实际邻近正文锚的 source / URL / SHA / 本地 publication 引用。 | 正式四原件、24 种排列、零本地 / 零标题年度、无锚 / 冲突 / 非月末、常规非十二月年结均断言；已修复。 |
| P2 封闭准入 | selection 的 `HkBodyEligibility` 区分 confirmed / missing / blocked / non_target，带 typed 原因；`HkBodyRequest` 带 raw key 与已校验性质。downloader 只运输 missing 请求；正文 resolution 复用同一 guard。 | 多主体、财年区间、无效截止日、年份 / 标签冲突、多年份、分类歧义和投影冲突均断言 PDF GET 为 0；充分标题不取正文。正文不能冲洗冲突；已修复。 |
| P3 实际字节绑定 | `HkBodyFacts → HkBodyEvidence → HkBodySelection/HkPeriodResolution → candidate`。models 公共校验将本次规范 ticker、source ID、URL、日期、性质、财年来源和实际 PDF SHA 绑定；prepared 校验候选、长度、摘要、时间，本地交接携实际 bytes 和 exact publication。 | prepared / local 两路等长异 bytes、URL / 公司 / 年份 / 性质 / 来源标记、重复 / 缺失 / 两路并存、revision 错配和 prepared 运输错配均拒绝；直接构造 discovery 不能绕过。filing 提交 / skip 复用公共校验，writer 内核 revision / 完整性；真实 Fs revision 漂移反例拒绝且释放 batch。已修复。 |
| P4 原生生命周期 | documents 拥有单请求单线程 worker 及所有 PDFium 句柄，按 textpage→page→document 显式关闭。Fins 拥有调用、Host / Task 取消、同次输入和错误投影；只复用 runtime 现有 spawn / wait / close。未加私锁、进程池或第二套进程平台，runtime 零改动。 | 真实并行不同 PID、同线程关闭、实际 Docling 并行、启动 / 等待 / native / 结果 / close 取消、崩溃 / IPC / 提取 / 关闭 / 输入资源故障均验证；无确认或遗留 worker。启动管道实证及修复见下；已修复。 |

正文能力严格限定领先三个物理页的可识别股票身份及明确本期综合收益表期间 / 本集团业绩宣告。比较列表头、股息日期、缺完整日期、扫描 / 空文本、冲突声明、错误身份、第 4 页才有决定性声明均关闭。网络 / 协议 / 提取执行失败与正常正文 unknown 分离；取消原样传播。

同步 discovery 由受取消治理的线程运行，Task 取消会通知线程并等待它及提取 worker 收口；已有 event loop 的同步提取调用使用独立线程拥有整个异步生命周期，不嵌套 `asyncio.run`。结果接收及资源关闭后均再次检查取消。输入、startup、result、crash、IPC、native、close、cleanup 有明确错误分支，未伪装成 unknown。

CN/HK 运输类型一次迁为 `CnReportPdf` / `CnReportPublication`、`local_report_pdfs` / `local_publications`，本地交接不再只有无字节 witness；原件读取 owner 迁为 `report_original_source`。所有生产、测试及受影响验证工具构造点同步迁移，无旧导入 re-export、别名或兼容 shim。CN FY 原 provider / FY / 原文来源 / candidate / 长度 / SHA / 时间及全文原文校验保留，原 CN locator 行为未扩大或放宽。

## 3. 来源、年度供证与 rebuild

- 年度正文财年来源为 `source_document`；中期为 `source_document_and_annual_end`。后者明确表示直接正文日期加可信年度日历推导财年，未声称正文直接给出中期财年。
- HK 日期来源由 calendar 定义封闭类型，resolution 显式产生 `source_document` / `source_title` / None，upsert 与 rebuild 消费该结果，不从非空日期反推。models 的财年来源封闭类型同时保留 CN/title、`source_title_and_annual_end` 及新正文值。
- `local_hk_annual_ends` 保持纯事实函数；仓储读取及 snapshot→正文事实接线由本地原件 owner 完成。普通增量只读已发布完整正文来源的 HK 原件，不为既有标题来源读取或重传 PDF。
- 本地 rebuild 先通过同一原件 owner 取得 snapshot；writer 再校验同一 revision / 完整性，年度先供证、中期后映射。缺失正文事实不退回标题，不静默擦除正文日期。纯本地、不联网。
- 标题 `hk-period-v3` 和原 sources 语义保持；正文显式 rebuild 为 `hk-period-body-v1`，sources 为本次校验并输入日历的年度 document ID 去重排序集合。普通下载不新增标签或迁移。
- 真实 Fs normal→普通 skip→rebuild 测试核对 source、完整性 / manifest 契约、已有 processed 及其 manifest 查询、结果日期、财年、覆盖与来源；sections / tables / financials 字节、source fingerprint 与身份保持。生产 base 未运行 rebuild。

## 4. 验证回执与版本适用性

所有 Python / pytest / coverage / pyright 命令均先 `source .venv/bin/activate`，cwd 为本仓库。各 `*-receipt` / 测试目录保留实际 argv、cwd、开始结束、exit、HEAD / dirty、入口 / import SHA、stdout / stderr。下面不是旧 336 基线的复述。

| 回执 | 实际结果与范围 |
| --- | --- |
| `coverage-tests-02` | **1485 passed**，3 个既有 edgar deprecation warnings。完整 argv 在 command.json，包含计划 §6 主清单以及 CN 原件 / 美的、pipeline、CLI、Service wait 回归。此时已具备本轮完整产品链路、来源 / 绑定 / rebuild 及取消收口。 |
| `coverage-tests-05` | **80 passed**，对最终同次输入描述符版本重验全部 HK 正文、真实 Fs normal / skip / processed rebuild、公共绑定、writer revision 及原生 / 取消 / IPC / 启动失败断言，开启 multiprocessing + thread 覆盖率。 |
| `native-docling-02` | 最终版本真实 ProcessDoclingConverter 转换与两个真实正文 worker 并行通过。Docling PID73924；正文 PID73926 / 73927，与父进程不同；两次提取结束时 Docling 仍运行；全部回收。详细时间、摘要在 `native-docling-data-02/result.json`。转换输出未用 fake 替代。 |
| `pyright-closeout` | 全库 **0 errors / 0 warnings**。另 `validation-scripts-pyright-01.log` 对实际执行 / 审计 / coverage 脚本显式检查为 0 错误。 |
| `coverage-final` | 16 个受影响生产 owner 文件**各自 ≥85.5%**，总计约92%；native worker100%、正文事实96%、提取编排93%、models94%、selection94%、rebuild91%。全部生产行计数，无新增 omit / pragma。 |
| `final-audit-receipt` | exit0；最终源码快照 / SHA、三次 CLI、官方原件 SHA、原七证据、原四资产、新四资产及入口版本全部核对。 |

coverage 保留完整原始 child 数据及 combine 警告；故意终止 / 崩溃的 worker 可留下未完成 coverage 数据文件，未删除或伪造。`coverage-final/provenance.json` 说明版本合并：02 的未变 owner 数据保留，变更的 documents worker / Fins extraction 两文件旧行数据全部替换为最终05数据，其余有效05数据补充；没有排除任何生产行。raw 数据与合并脚本均可重核。

版本复用严格限定：1485 回归之后只变更 PDF 输入运输和相应测试 / 文档；事实 parser、selection、models、publication、Docling 转换代码及持久 schema 未再变化。80 项及真实 native 并行验证覆盖这次影响。首次四份实际 Docling 结果沿用其真实原件、转换代码及 SHA 证据；最终普通增量与 storage 审计用最终提取 worker 重新取得事实，核其与这四份实际结果及身份一致。`transport-v3-to-final.patch` 保存实际差异，未把生产01或旧源码冒称最终版本。

### 实证失败及处置

所有红测、失败和旧回执保留，不覆盖。`tests-red-*`、`pyright-red-*` 记录契约迁移过程中的旧夹具 / tuple 断言等失败；正式 fixture 首次缺 `ingest_method` 的创建失败及补正分别在 `fixture-create` / `fixture-create-02`。processed 内容保全断言曾把应更新的元数据快照当内容，已改为明确断言 sections / tables / financials，同时单独核元数据更新。

首轮只读审计脚本缺 spawn main guard，子进程在反序列化 target 前报 FileExistsError。其父侧同步 start 写入较大 PDF pickle 阻塞；native sample 显示 FileIO write，CPython `popen_spawn_posix.py` 的 spawn→向管道写 pickle→关闭 child fd 顺序提供直接同源证据。失败旧审计经两次 SIGINT 清理，exit130；`audit-first-startup-pipe-trace.txt` / `failed-audit-native-stack.txt` 保留真实回溯与采样。没有中断或因慢重跑任何真实 Docling 转换。

修复落在 Fins 调用 / documents 输入边界：只把小的同次临时输入描述符送入既有 spawn helper，worker 读取该次输入、用实际 bytes 打开 PDFium 并回传实际 SHA，父侧与原件 SHA 再核；进程关闭后清理输入。这是已审 IPC 形状的具体落实，不改 runtime 平台、仓储读取或持久 schema。正式 `hk_broken_spawn_entry.py` 以 1MB 输入真实触发 target 解包前 main 导入失败，父侧在测试预算内 typed crash 收口，进程和输入均回收。创建 / 读取 / cleanup 故障也有 owner 断言。修正 guard 的只读审计 `audit-first-02` 及最终 `audit-final` 均通过；旧失败 PID73602 已不存在。

## 5. 真实固定 CLI 与四条最终产品事实

实际三次 argv 除全新 log-file 外完全相同，均无 forms / overwrite / rebuild：

```text
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli --base /Users/leo/workspace/portfolio-manager-v2/workspace --log-file <E内该次全新dayu.log绝对路径> download --ticker 0135 --start 2025-01-01 --end 2026-10-19
```

| 回执 | UTC 起止 | exit / 实际计数 |
| --- | --- | --- |
| `production-01` | 21:18:51 →21:20:11，2026-10-18 | 0；discovered8，downloaded4，skipped4，failed0，uncertain0 |
| `production-02` | 21:23:33 →21:23:55 | 0；discovered8，downloaded0，skipped8，failed0，uncertain0 |
| `production-03-final` | 21:29:17 →21:29:37 | 最终版本0；discovered8，downloaded0，skipped8，failed0，uncertain0 |

每次均保留 command / receipt / result / diagnostics JSON、完整 stdout / stderr / dayu.log，无省略的8条 document 结果及原始 CLI diagnostics。最终入口脚本 SHA 为 `ab7d7ba9f7ac8595296b8c53fb139a2af3267616cb0ce5088e3ce6f4a8071691`；shebang 为 `#!/Users/leo/workspace/dayu-agent-r/.venv/bin/python`；解释器真实路径为 Homebrew Python3.11.15。pypdfium2=5.7.0、Docling=2.127.0；直接依赖与既有 common lock 一致。`entry-version-final.json` 记录实际 import 路径 / SHA，final audit 与最终工作树逐项比较通过。

以下来自最终普通增量及最终 storage 读回，不是用取证表写入：

| source_id | 财年 / identity / coverage | report_date | fiscal_year_source |
| --- | --- | --- | --- |
| 11584251 | 2024 / Q4 / FY,Q4 | 2024-12-31 | source_document |
| 11801353 | 2025 / Q2 / H1,Q2 | 2025-06-30 | source_document_and_annual_end |
| 12065226 | 2025 / Q4 / FY,Q4 | 2025-12-31 | source_document |
| 12299283 | 2026 / Q2 / H1,Q2 | 2026-06-30 | source_document_and_annual_end |

四条 report_date_source 均为 `source_document`。完整 document ID、opaque revision、全 meta、locator、primary、全部文件描述 / bytes / SHA、页见证、Docling schema / 实际文本数量在 `new-assets-final/new-assets.json`。四份 PDF SHA 与先前官方 HTTP200原件完全一致；四份主文件均为真实 DoclingDocument 且有文本，不是只验证退出0。

## 6. 原资产保全

在任何生产 download 前，使用 `build_fs_repository_set(create_directories=False)`、storage full source snapshot 和 `snapshot.get_source(...).open()` 保存原四 ID 全 meta、revision、primary、provenance、全部文件描述及实际长度 / SHA；file locator 保留于全 meta 的 URI。没有遍历或直接读取生产受管路径。原失败六文件和版本文件七份原件在开工 / 生产前 / 首次后 / 最终再读并校验 SHA。

`preservation-before.json`、`preservation-pre-cli.json`、`preservation-after-first.json`、`preservation-final.json` 的 documents / originals 全等；最终 audit 已机器断言。原四份资产的全部字节摘要 / 长度、完整 meta、revision 和身份保持，原七证据不变。新四份在第一次读回和最终读回之间同样全 meta / revision / files / 身份全等，且可由 storage 取回原件及真实 Docling。生产未 overwrite、未 rebuild、未修旧资产。

## 7. 文档、风险与下一入口

已先阅读职责约束并更新 `dayu/fins/README.md`（正文准入、owner、来源与本地重解析边界）、`tests/README.md`（真实覆盖与 fixture / native 验证），根 README 仅补充最终用户可见的正文支持限制。UI→Service→Host→Engine 分层及装配边界未变，不触发 dayu/README 的内容变更。

| 风险 / 未覆盖 | Gateflow 分类 | owner / destination |
| --- | --- | --- |
| P1–P4、输入绑定、同批供证、native 取消 / startup、保全 / 真实增量 | fixed in current slice | Fins / documents；本报告及全部可取回证据 |
| 领先三页以外、扫描 / OCR、任意语言 / 合订主体、特殊 / 过渡 / 52–53周财年 | assigned to later work unit | Fins / documents；若扩大支持另立 work unit，本次正常关闭 unknown |
| 当前固定本机入口之外的平台依赖 / native 行为 | assigned to later work unit | documents / 平台维护者；跨平台验证，不属于本次验收承诺 |
| 未来官方原件 / 响应变化及本轮之外未知同根因 | assigned to later work unit | root / 来源维护者；重新以新原件和来源事实核证 |

没有尚需机械延期的范围内实现 / 验收项。独立代码审核尚未执行，**下一入口由 root 按既定双路完整代码审核及必要复审推进**；本 writer 未派 reviewer，未声称 code-review pass、draft PR 交付或整个 work unit closeout。
