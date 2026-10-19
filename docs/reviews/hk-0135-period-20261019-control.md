# 0135 四来源未决：追加 goal confirmation

状态：9633已完成final closeout；0135当前gate / next entry point = ready-to-open-draft-PR（完整审核及必要双路复审已通过，待重核远端base/head后提交独立delta并交付核对；尚非final closeout）。用户确认继续有效，无需重复请求确认。

确认回执：协调方全文读取后明确确认顺序独立单元、四来源目标/边界/验收、固定入口同参普通增量、原失败与四份资产身份保留、指定模型与适用计划审核/双路完整代码审核及必要复审、回归/pyright/入口核验。确认9633以PR203分支为base，0135在9633完整交付后以其已审最终分支/head另建分支/draft PR仅交0135 delta，开工重核远端，不改旧PR、不重复旧改动、不merge；无代码缺口不强造PR。确认没有其它已知重复派发，不保证未知全局同根因。此授权允许前置完成后自动推进，无需重复目标确认；无timer及其它范围扩大授权。

## 已核事实与动机

任务：`/Users/leo/workspace/portfolio-manager-v2/orch/workpapers/hk-g0-seed-20261018/dayu-0135-task.md`。

已读取限定原下载目录全部六文件及 `evidence/dayu-version.json`。原固定入口实测版本 `705c2dc2f6b4491edda0c6f0d2a4b1f8e2bf458d`，原工作区干净；argv 为固定 CLI、base `/Users/leo/workspace/portfolio-manager-v2/workspace`、`download --ticker 0135 --start 2025-01-01 --end 2026-10-19`，未传 forms/overwrite/rebuild。原运行 00:01:40 至 00:39:54，exit1/partial_failure，8 discovered、4 downloaded、4 uncertain，failed/rejected/skipped 均0，无省略。

未决来源：11584251、11801353、12065226、12299283，report_date及existing_document_id均null。原四份已下载ID已在diagnostics保存，stdout/dayu.log均有实际落盘完成记录。不能由其披露日期推定报告期间。

本轮只读官方发现（未调用生产base下载或存取生产财报）：公司为昆侖能源、provider identity `HKEX:229`、官方股票代码00135。原始请求、响应、HTTP状态、时间、SHA256在 `workspace/tmp/hk-0135-period-20261019/discovery-01/`；真实结果4 candidates/4 uncertain。四个官方标题均为“業績公佈”；原分类分别为中期业绩或末期业绩的组合分类，无标题年份/截止日。PDF URL已随原行保存，但正文尚未核证。

同源代码观察 `workspace/tmp/hk-0135-period-20261019/owner-observation.json`：对四条原行的 category/title，基线 selector 能得出类别投影，`_hk_title_years`为空，统一resolver均返回None。读取源码哈希与精确705c2dc2对象一致。这里只证明标题输入不足的失败路径；不把类别标签等同于确认财年/财期，不预断正文期间、产品缺陷或应采用的修复方案。

## 与 9633 的关系及建议工作单元

9633 的已证根因是复合标题把主报告和明确附属引用混合解析，已审方案只限定标题主体语义；0135 当前四条标题没有年份，不能靠隔离附属引用获得缺失事实。两者接近同一selection owner，但直接证据不支持认定同根因，也不支持把0135纳入9633既有计划。

建议**顺序独立单元，不合并当前修复**：

1. 9633 保持已确认目标、已审计划、单一writer和现有runner。已派双路计划审核均正常收取（ds pass-with-risks、mimo pass），总控已裁决并进入implementation/validation。原流程继续完整代码审核、必要修复/复审、新draft PR与交付核对。
2. 0135 此刻只登记并提交追加goal；确认后排队，待9633退出writer、完成其交付后，才派gpt-6-sol进行0135独立plan取证和适用双路review，不并发修改同owner。
3. 0135的目标是核四来源官方身份/正文期间及真实通用owner缺口；有直接证据修复通用路径，无据保留有证未决。若需要新正文事实输入、重要公共契约或架构变化，在0135 plan明确所有权与方案并执行适用planreview；超出本次确认边界再报告，不把PDF自动解析偷偷加入9633。

## PR 与依赖边界

当前Dayu分支 `fix/hk-9633-period-20261019`、HEAD705c2dc2；本次0135核查时远端唯一open PR仍为PR203（draft，head705c2dc2，base main）。本root仅维护本次0135记录和隔离tmp证据，不修改9633产品代码或其已审plan。

建议9633新PR仍以 `fix/hk-period-evidence-20261018` 为base，仅交9633 delta。0135后续再创建独立工作分支/draft PR，以**9633已审核交付的最终分支/head**为集成基线，仅交0135 delta，显式列明对9633及PR203的未合并基线依赖；这仅是顺序集成边界，不声称两问题同根因。开0135单元前核最终远端base/head及在途状态；不重复纳入9633或PR203提交，不改旧PR，不merge。如最终无需代码，交有证据的处置/实际回执，不强造补丁或PR。

## 新增范围的成功信号与非目标

- 四来源官方身份/报告期间与代码原因均有可取回直接证据；无法确认则保留未决，不强消unknown、不猜日期。
- 固定 `.venv/bin/dayu-cli`、同base/ticker0135/窗口、普通增量且不传forms/overwrite/rebuild，所有新日志独立路径；真实argv、版本、exit和完整回执可核。
- 原失败六文件哈希、既有四份真实资产、完整meta/revision及历史身份保持；仅经dayu.fins.storage存取受管财报。
- 受影响回归与全库pyright、必要README决策、指定gpt-6-sol实现/修复及mimo-flash/ds-flash并发独立review、必要受影响复审、真实commit/PR及固定入口一致性。
- 不调查TLS/沙箱/域名，不改调用方代码或文档，不并行同owner修复，不做未授权全库迁移，不merge，不创建周期timer。

协调方任务书确认没有这四source重复派发；当前尚不能声称全局无未知同根因。在途唯一产品writer是9633实施runner，不新增第二writer。

请确认上述顺序独立单元、目标/边界/验收及PR基线安排。确认前只推进原9633授权工作；0135不进入plan或implementation。

## 原失败指纹

目录 `/Users/leo/workspace/portfolio-manager-v2/orch/jobs/00135-fy2025-income-g0-20261019-000133/download/`，完整备份哈希表在本次 discovery-01/original-hashes.json。

| 文件 | SHA256 |
| --- | --- |
| command.json | 0f1871d51c84e34964074918484c4f17372ad77cded5b54402d8592f9044d455 |
| result.json | 320a3ffe307a6cd9448e6f46953c98c5e145931d36a3121d548ac7ef632f2be7 |
| diagnostics.json | a10a64ff03d06e0473cb276a783384832dbd5f8894513386e64f6a5341decfec |
| stdout.txt | 3803656b1e9e67765a7143a4e74125fab03256494bb92fa84b8ea70768acf41d |
| stderr.txt | d711db717a42dd582463607116a82726941af6c6a388b5bf8fc2840508b40646 |
| dayu.log | e2ddf1a18ed6ccef17360f9ca7dfa3c53e834494ed9b82de02b627d372cfe348 |


## 顺序前置完成 / 0135 plan入口

9633已完整交付：draft PR204 https://github.com/noho/dayu-agent-r/pull/204 ，最终已审产品+治理head `f975a9586261bf7750e632959848bb6392c2881b`，base PR203分支`fix/hk-period-evidence-20261018` / `705c2dc2f6b4491edda0c6f0d2a4b1f8e2bf458d`；最终远端diff、push、177入口文件与已审版本一致，见9633 `delivery-final-audit.json`及closeout。PR203和PR204均OPEN draft、未merge。全部9633runner实际退出，无同owner writer。已按协议向重新识别的portfolio-manager pane同任务回报，未clear。

开工只读重核PR204远端head/base、当前HEAD与工作区后，从精确`f975a958`创建`fix/hk-0135-period-20261019`。唯一既有dirty是root持有的本0135control；9633产品及治理已提交，旧分支未修改。本单元将以9633最终分支为base仅交0135 delta，明确对PR204及PR203的未合并依赖，不重复旧提交；无代码缺口则交证据处置，不强造PR。协调方原确认无四source重复派发仍有效，当前可见无其它Dayu执行者处理这四source，不能排除未知全局同根因。

现在仅派指定gpt-6-sol plan取证：核四来源官方身份、正文报告期间、当前输入和统一owner路径，判断有无通用缺口。四标题“業績公佈”及无年份只是已核输入不足，不预断正文期间或修复方向。新正文事实输入/契约/架构若必要，应在plan明确owner和最小方案并交适用双路planreview；超范围再报告，不在plan前偷偷实施。原失败与四资产保持，普通生产增量留到已审实施/处置验收阶段。


## Plan核收 / 独立planreview入口

gpt-6-sol实际outer/runtime退出0，session `01a15099-0aeb-7e11-ab72-be3f03e2ac06`。完整plan已读，冻结副本`workspace/tmp/hk-0135-period-20261019/plan-reviewed-v1.md`，SHA `179ae24ec34bcc2139b21d2b940d54e86a4963ae866b88b64529c128997be18d`。总控重算83项取证manifest、相关源码与HEAD一致，产品零delta；336基线测试与全库pyright0有真实日志，仅证明未改版本。原下载六文件及原版本文件七份保持；生产四资产尚未snapshot，不能冒称已验证其当前字节。

root独立亲看四份官方第1/2页并经storage读回全部PDF，HTTP/raw公司/source/URL/sha链闭合：11584251正文2024-12-31年度；11801353为2025-06-30六个月；12065226为2025-12-31年度；12299283为2026-06-30六个月。首页00135.HK与昆仑能源身份一致。见root-visual-evidence-review.json、root-source-chain-review.json和root-plan-intake.json。拟产品身份按既有results契约Q4/Q2，尚未发布，不把正文观察混作产品事实。

当前标题/分类无年份时unknown是正确失败关闭；真实缺口是正文事实尚无受控输入路径，而非标题已经有年份却解析错。计划提出窄正文事实owner、显式typed输入与统一resolution、受治理原件获取/交接、本地完整原件复用及rebuild/年度锚/持久结果一致性，不能只改下载入口。新输入与prepared/publication契约及来源语义属于重要决策，适用planreview；既有用户授权明确允许在plan提出此类变化并审核，不重复确认。

总控初核：四官方证据充分，方案目标在本次四来源/通用owner授权内；是否最小、三页作用域和正文准入是否安全、CN/HK运输契约扩展/来源字段/事务一致性是否完整，交两路独立对抗审核。未把条件性的“covered by later approved slice”视为实际已批准：当前这些验收项归本work unit拟单slice，实施放行仍待审核裁决；没有批准额外持久schema变更或自动兼容旧库。任何需新增schema/重大范围变动必须先明确补充计划及适用审核，超goal另报。

current gate / next entry point = plan / mimo-flash与ds-flash同时独立planreview。未实施、未跑生产增量、无新增PR或merge。


## 双路planreview裁决 / plan fix-01入口

两路同时派发并实际outer/runtime退出0：DS `plan-review-20261019-042343.md`、MiMo `plan-review-20261019-042959.md`均完整读取；同一plan SHA179ae24e，两者pass-with-risks且无架构阻断。总控不按票数放行，依直接契约与已选方案补最小计划修订，产品仍不改。

- **P1 accepted / 未修复**：MiMo1同批供证时序。年度锚必须包含同批已确认的正文年度事实，年度取证/冲突校验先于中期映射，输入顺序不影响结果；零本地/零标题年度情况下有同批年度正文可供证，若无可信年度锚，中期必须unknown。合并DS1无锚不得进入旧结束月份+季度序数回退的要求。owner Fins selection / 本单元plan fix及实施，fixed in current slice。注意MiMo将“四条全部确认”称已确认目标并不准确：用户明确不承诺消除unknown；这是当前证据不变且无失败前提下，所选方案的验收期望，不是强行unknown0授权。
- **P2 accepted / 未修复**：DS2/MiMo2准入的封闭判定与显式负例。由selection唯一owner区分缺事实与冲突/歧义，不许downloader把None当可获取信号，明确多主体/区间简写等连PDF获取都不得触发；表达式/类型拆分仍由实现者决定。owner selection / 同单元plan fix与实施，fixed in current slice。
- **P3 accepted / 未修复**：DS3原件与正文事实SHA绑定。plan明确typed事实如何到达prepared/本地见证的校验owner，discovery结果及提交前各自校验责任，单靠asset自身hash和candidate相等不够。CN FY验证不得放宽；同source不同bytes拒绝。owner models/filing workflow / plan fix与实施，fixed in current slice。
- **P4 accepted / 未修复（总控新增直接证据）**：PDFium包METADATA1011–1013明确非线程安全，FinsIngestionThreadExecutor在2286起每job建Thread，direct亦线程桥；同进程原生提取必须有明确并发/资源close/取消边界，不能以单次提取成功代替。`root-pdfium-concurrency-observation.json`保存证据；选择最小可行owner治理，不扩成平台。owner正文提取owner及直接生命周期边界 / plan fix、实施与并发/取消验证，fixed in current slice。

其余open questions处置：三页支持范围、正文日期来源唯一typed值、正文日期+年度日历推财年的来源语义、local_hk_annual_ends纯事实输入/不持仓储、period_resolution版本/供证来源含义，以及直接受影响F5两测试，均在同一plan修订明确；不据此增加schema迁移、强制自然年限定或外部issue。DS将非十二月年结概括为非目标不完全符合已审方向：本plan复用既有可信年度日历而非猜自然年，不应为了例子把通用逻辑硬编码成6月/12月；特殊/过渡财年按原边界保留未决，常规非十二月锚的逻辑与来源标记须真实一致并验证。

MiMo“三页安全下限”的结论只限该明示支持范围与四原件，不采纳为任意PDF安全/完备保证；预算外或缺支持的主体声明仍unknown。跨平台原生依赖未运行验证只如实记录，当前验收为固定本机入口；不扩大不必要平台工程。真实生产四资产snapshot、转换、完整审核等仍为后续实施验收义务，当前不宣称完成。

计划fix只补这些必要规则/责任与验证点，不穷举正则、不改变目标/架构方向；由指定gpt-6-sol修订，再两路并发受影响面planreview。当前无产品writer、无生产命令。


## Plan fix-01核收 / v2受影响面复审入口

gpt-6-sol实际outer/runtime退出0，session `01a150b8-bbda-7441-bab7-539c820972e3`。总控完整读取fix说明与v1→v2 delta，v2 SHA `208dee4ff52840367204eadc0a661d421a1042314729f678b92a670cef5ed469`；副本在plan-fix-01/plan-reviewed-v2.md。83旧取证及15新增源码/依赖观察hash独立重算通过；产品、测试、依赖零改动，旧336/pyright仅是未改基线，未假称实现通过。原报告及失败保留，最终审计取final-audit.json（含初次审计错误记录），root核收见root-plan-fix-01-intake.json。

P1–P3 writer已补同批年度供证/无锚关闭、selection封闭准入、typed公司/source/URL/正文SHA绑定及models交接/filing提交的职责；P4依据新增同进程Docling/Web及第三方调用观察选单请求spawn worker，documents拥有原生提取target，Fins持调用/取消，runtime只复用现有可中断进程机制，避免私锁假互斥。来源值域明确正文日期source_document、正文年度同值、中期source_document_and_annual_end；标题路径保持。正文rebuild拟标签hk-period-body-v1，无迁移/普通下载额外写标签。

这些仅是计划修订，不是产品修复或最终放行。进程机制、来源字段/标签及实际供证/绑定契约属于本轮受影响面，交两路明确实审；不采纳“只改文字即可免审”假设。当前gate / next entry point = plan v2受影响面双路复审，仍未实施、未操作生产base、未创建0135 PR。


## Plan v2复审裁决 / 实施入口

两路并发独立受影响面复审均实际outer/runtime退出0：DS `plan-review-20261019-044710.md` pass-with-risks（session d1db33bd-e067-4b9d-9610-2ec4369df108），MiMo `plan-review-20261019-045031.md` pass（session 206781ab-ad66-4e73-99c2-22febbf2edac）。root已读取两份全文及完整final，独立重算v2 SHA208dee4f及报告hash，保存root-plan-pass.json；无新material finding或blocker，未将退出0或票数替代契约核对。

裁决：P1、P2、P3、P4均accepted / 已修复（严格限计划层），由v2实际delta及两路复审核销。产品落实与实际验收尚未做，不假称产品已修。所选单请求spawn隔离、selection封闭准入与同批年度先验、models实际bytes绑定/filing复用、来源值域与rebuild同源投影足以指导本已确认目标，放行一个闭合implementation/validation slice；无需再问goal或做空fix循环。

两路Open Questions全部交本slice实现+完整代码审核：local witness必须携带并校验实际bytes，封闭财年类型包含全部旧CN/title合法值；同步discovery与async runtime桥接不得错误嵌套event loop且取消及时；全部report_date_source消费者显式同源；typed eligibility/resolution接线、IPC协议/关闭参数以实际代码核验。这些是已定契约下的实现形状，不构成额外公共承诺或未决计划阻断，分类fixed in current slice、owner相应Fins/models/documents及实现runner，未完成不得通过实施/完整review。

生产原四资产完整storage快照、七原证据保全、真实普通增量/转换、entry/import版本、受影响测试/pyright/coverage和§6进程验证同属fixed in current slice；固定平台之外、任意正文/OCR/特殊财年为assigned to later work unit，owner Fins/documents，非本轮承诺。官方原件变化须按新证据裁决，不强消unknown。现在只派指定gpt-6-sol单writer实施，完成后按既定mimo-flash/ds-flash并发完整代码审核；不改旧PR，不merge，不timer。


## 实施核收 / 完整代码审核入口

gpt-6-sol实际outer/runtime退出0，session `01a150ca-91f4-7a52-8fd4-b7be018ad0c5`。root完整读取implementation报告与final、最终审计和覆盖率合并脚本，独立重算816项证据清单、37份源码快照/当前工作树及删除项，完整source patch SHA `d5bd996f6d46c11d2ff2cf956e75376c8cecc66ab34d7891ef80560138163ba6`，报告SHA `12204545e00079533fb614c474586b9edaf61bcc0f20a4cc9599c59cb8a4f563`。冻结目录implementation-01/source-before-production-v4；官方fixture仓储单列且只能storage读取。root核收在root-implementation-intake.json。

实际1485回归通过；最终运输修复80针对测试/真实Docling并行探针通过，全库pyright0，16生产owner覆盖率85.5%以上。核收对应实际回执和当前SHA，不把旧336基线或首转版本冒称最终版；完整审核仍需实质检查测试有效性/版本适用性与遗漏。第一次CLI 4新增4skip、第二次8skip、最终修复版8skip，三次exit0/uncertain0且参数完全固定；四原件SHA与官方证据一致、真实Docling均有内容。root重算原七原件当前hash，与四次保存保全快照比较原四资产全等；新增四份首读与最终全meta/revision/files全等，最终入口8关键import匹配当前代码。生产base未rebuild/overwrite。

实施过程发现真实spawn启动失败时大PDF pickle管道写阻塞：错误审计脚本缺main guard是触发器，FileIO write原生栈及CPython同源路径已保存。runner修为单次临时输入描述符、worker实际bytes摘要回传并父校验，保持已审单请求spawn与现有runtime；属已审IPC具体形状及本范围启动错误治理，非新schema/平台/目标。两次SIGINT清理的是失败只读审计进程，未中断真实Docling或agent。最终80测试包含真实1MB main导入失败/取消/输入清理；旧失败130保留。完整review必须核该实际新形状的存取边界、绑定与资源关闭，不只信报告。

P1–P4实现writer自报已修，root仅核收证据，最终产品修复状态交本轮完整代码审核实判，不据此提前code-review pass。风险：支持范围以外/OCR/特殊财年/跨平台为assigned to later work unit，owner Fins/documents；已确认范围内正确性和生命周期继续由本单元审核/必要fix闭合。当前无产品writer；现在同时派mimo-flash和ds-flash独立完整deepreview，禁止读彼此本轮材料，不重纳PR203/204 delta。


## 完整代码审核裁决 / fix-01入口

两路并发独立完整审核均实际outer/runtime退出0：DS `code-review-20261019-060025.md`（native a21a7738-06fa-4572-81d2-90326eb888e9）未通过，MiMo `code-review-20261019-064313.md`（native ff148162-5afa-4364-85fe-9eda74988cbe）有1项低级finding并未代root放行。root已读两份全文及完整final，保存root-code-review-01-decision.json；不按票数或退出码放行。总控独立反例见root-review-observations.md及指向的三份probe，绑定冻结源码SHA。MiMo“未发现P1–P4实质违反”的笼统结论不能覆盖DS与root直接反例，产品当前未通过code review。

正式合并findings（均**accepted / 未修复**，分类fixed in current slice，owner / destination为本单元指定gpt-6-sol fix及双路受影响面复审）：

- **CR1 / 中**：DS1 + root4。本地/同窗标题年度锚被压为date，resolution丢失source/URL及本地document_id/revision；正文锚另需SHA/页见证。窄窗真实中期+本地年度反例得到annual_evidence空但可确认财年，违反已审§5.2/5.4。workflow已提取的本地正文又在discovery重复spawn，合并在同一typed事实交接修复，复用一次已核证据；正确owner为Fins年度事实输入/selection/models/rebuild。所有实际用于映射的锚有诚实引用，不能按日期回猜来源。
- **CR2 / 中**：DS2。正文直接日期已确认但无可信年度锚等映射失败时，unknown丢日期并错误称日期未确认。由唯一owner产出partial事实/未决状态，selection与rebuild同源投影；不对不准入/冲突body做无条件fallback，不分配身份或发布。
- **CR3 / 低**：DS3 + MiMo1。正文skip的_require_hk_body_meta提前ValueError，使period_metadata_mismatch/rebuild提示不可达。先严核实际原件/来源/完整性，再按真实语义区分财期/派生投影漂移与SHA/来源破坏；writer内相同分类，保持不覆盖/不手修旧资产。禁止对字节或身份冲突误提示rebuild可修复。
- **CR4 / 中**：root1。正文_STATEMENT在全页任意匹配，明确标为“上年度比較資料，並非本期業績”的表仍确认HkBodyFacts。DS将相关风险列为理论残余，root的可重复owner级合成反例已使其成为实际支持边界缺陷；不能因不是当前四件样本就视为范围外。正文owner必须确认本期作用域，历史/比较/引用不可冒充本期；不能只补几个否定词黑名单或下游过滤。保留正式四原件及清晰支持边界。
- **CR5 / 中**：root2 + DS临时资源残余。连续第二次Task.cancel可穿透第二次shield，外层已结束但close任务未完成；discovery同形。取消与cleanup错误并发也须诚实收口。由资源生命周期owner确保重复取消仍等待线程/worker回收后传播，补实际进程/线程组合验证，不仅单次fake。
- **CR6 / 中**：root3。HK本地前置local_hk_body_evidence在async工作流中同步调用，再经ThreadPoolExecutor.result阻塞原loop；反例0.2s期间其它协程不能运行，Task取消不能及时调度。远端_discover_reports线程治理未覆盖本地段，需在Fins异步编排统一处理，不靠同步桥内再套线程证明可取消。
- **CR7 / 低（root裁决DS来源标记OQ）**：已审§5.4要求来源标记投影到workflow filing result/event，当前_build_filing_result及rebuild相应结果缺这两标记。按既有内部Json payload从同一resolution/candidate投影report_date_source/fiscal_year_source并覆盖事件一致性；此处result指既有workflow/filing事件结果。公共FinsDownloadDocumentResult仍是既有字段的业务摘要，不为本修复新增公共typed结果字段或持久manifest字段；manifest仅核既有日期/财年/覆盖等投影一致。没有新增durable schema授权。

这些是已审契约的正确落实，不是新目标；保持单slice闭合。P1/P4产品状态至少部分修复（年度引用与取消未完成），不再沿用writer自报“已修复”；P2/P3未变部分已有直接证据，但最终组合仍待必要修复复审。指定writer可决定最小类型/函数拆分；若真正必须改变重要已审架构/新增持久schema，先报告root补计划/适用审核，超goal再报，不擅换私锁/平台或新迁移。

OQ及residual裁决：

1. 提取执行错误维持现有typed discovery/batch中止，不吞成unknown或空成功；plan只要求保留执行失败未承诺来源级隔离。单来源失败状态机改造为assigned to later work unit，owner Fins/documents，非本轮阻断，不据此扩公共结果协议。
2. 本地URL冲突当前拒绝且不发布，裸ValueError为内部绑定违约而非HTTP协议错误；未承诺专用外部reason，作为blocking finding rejected-with-reason。细分可观察性归assigned to later work unit / Fins；CR3若使用既有typed边界可一并保持分类清晰，不另搭异常框架。
3. 标题hk-period-v3指既有解析规则，不承诺未来输入年度集合冻结；新可信body年度可以进入统一日历，标题sources仍是同样的已校验年度document_id集合投影。混合title/body本地rebuild需由CR1测试核诚实来源/标签，正文解析规则仍hk-period-body-v1；不全库bump或迁移。
4. 对标题已充分的来源，正文获取/注入不能绕过已审eligibility。直接提供正文证据仍失败关闭，不引入旧body→title自动迁移；未来标题规则/官方raw实质变化的迁移语义为assigned to later work unit / Fins，非当前四件稳定raw的阻断。
5. local_hk_annual_ends的body输入在当前生产唯一上游已筛download/非deleted，未找到可触发错误供证的当前调用路径；不将未来调用者假设当material finding。CR1统一typed锚资格时应保持同一真源的已有guard，不复制漂移规则。
6. DS独立生产snapshot权限缺口已由root经仓储实际重读取回闭合，root-storage-readback-audit.json记录原4+7与新4完整相等，未改资产。首次默认权限失败及空审计目录保留；后续已授权读取lock通过，没有扩调查范围。
7. 官方四份首转属v3、最终skip属v4，Docling源码与原件未变且实际运输delta可取回，跨版本复用成立，不能冒称最终版首转。固定CLI与8关键import由同解释器recorder绑定且root重算源码/入口，未承诺进程内自证；后续最终版本继续绑定真实入口及源码SHA，不机械为此覆盖重转资产。
8. uncovered分支按实际fix影响补关键断言：typed锚/混合rebuild、partial未知、元数据漂移与完整性区别、重复取消/cleanup/本地loop是本slice必需。其它未变防御分支不因coverage缺行机械全测；完整owner覆盖>=80%仍必需。三页外/OCR/特殊财年/跨平台及未来官方变化继续assigned to later work unit，owner Fins/documents/root，均非当前承诺。

当前gate / next entry point = fix-01。两路reviewer均已退出，无并发产品writer；现在派指定gpt-6-sol修复CR1–CR7，完成后mimo-flash/ds-flash同时独立受影响面复审，不再完整重扫未变37文件或重复取证。八份当前合法资产都应保全，原七证据保持；最终同参普通增量验收，新日志，不merge、不timer。


## fix-01前置尝试与接续

首fix runner实际outer/runtime退出0，native `01a15132-4c90-7f83-aff9-7b87e27d6acc`，仅完成37源码/816旧证据/8资产/7原证据保全，未改产品/测试；CR1–CR7仍未修。完整final和fix-01/preflight-status.md保留，未把退出0算作fix完成。

子runner额外要求客户端型号自证，root曾据此增加型号路由核验。用户随后明确“按照$sub-agents SKILL执行就好了”。按skill以指定provider派发、等待实际退出、读完整final；子Agent无需自报runtime/provider/model，也不要求用户另确认客户端型号。撤销该额外型号确认关卡及回溯性型号自证要求，历史provider路由/原回执照实保留。相关临时核验材料只作前置尝试记录，不作为业务gate。

当前已派接续runner正常收取，不clear、不并发writer、不再增加型号自证或重复goal/plan gate；按已审plan与CR1–CR7继续实施验证，实际必要修复完成后进入双路受影响面复审。


## fix-01最终核收 / 双路受影响面复审入口

gpt-6-sol实际outer/runtime退出0，native `01a15138-d181-7e52-970f-7defd0605b81`；root已读完整final、fix-01报告、实际v4→最终delta及最终审计。冻结源码`fix-01/model-pinned-01/source-final-v2`，完整patch SHA `1c0143add8f236ed3567dd69d3d6ddcd4ec1d20cac1a5a8692276db00b4124c6`，54文件含原官方fixture、1删除项；root逐一重算当前/副本/patch和732新证据均通过，正式核收`root-fix-01-intake.json`。相对v4实际改动为23份文本（含1新生命周期helper）；fixture只是这次纳入完整快照，不假称四原件发生变化。旧source-final/production-final及临时失败全保留，最终以-v2为准。

最终1503受影响回归及6项反例对应定点验证通过，全库pyright0；16owner覆盖率至少80.27%。最终同固定CLI/base/0135/2025-01-01至2026-10-19普通增量，无forms/overwrite/rebuild，exit0、8发现/8skip/0unknown，8明细无省略，10关键import及入口SHA对应最终冻结版本。root独立storage重读原4+新4完整meta/revision/primary/provenance/descriptor/bytes与原七证据，和writer最终-v2保全全等。官方首转/Docling仍复用已核v3原件与转换代码，不冒称最终版首转。

CR1–CR7 writer自报已修，root当前只核收实现与证据，不提前code-review pass；现在同时派mimo-flash/ds-flash独立受影响面复审，逐条核销accepted finding及实际delta。CR3收尾另补form_type/report_kind漂移分类并重验，CR4正面本期作用域、CR5重复取消/cleanup、CR6真实async编排、CR1typed年度引用/同次复用和CR2partial日期与CR7事件来源均须实审。未变官方取证、原Docling和完整审核按版本适用性复用，不机械重扫37旧文件或重复全套732/816证据；有新直接反例再扩大。README及风险分类见fix报告，未扩大public摘要或durable manifest。

当前产品writer已退出，无并发writer。下一入口为收取两路actual退出+完整final/report，root裁决后必要fix/复审或进入ready-to-open-draft-PR。META已另获goal confirmation，仍排0135完整交付后；本META control不得纳0135提交。


## 受影响面复审01正式裁决 / fix-02入口

两路并发已正常收齐actual outer/runtime退出0及完整final/report：DS `code-review-20261019-075115.md`（native7917f29d-eefc-4910-9696-6b1ac8288054），MiMo `code-review-20261019-075737.md`（native2a8273f0-c974-4980-9f37-3e4d422e5936）。root已全文读取并核源码/直接反例，裁决`root-code-rereview-01-decision.json`。MiMo笼统七项pass不覆盖DS及root的同源反例；不按票数/exit0/测试数放行。当前尚未进入draft PR gate。

- **CR1/CR2/CR3/CR5/CR6 accepted / 已修复**：当前已验证触发范围的年度引用与有效本地事实复用、partial日期、合法漂移分类、重复取消与本地前置async责任已由两路实审及owner测试核销。未改变的最终-v2证据可按实际影响复用，不让下一窄修复重扫全部旧范围。
- **CR4 accepted / 部分修复，fixed in current slice**：旧孤立表反例已关闭、官方四件仍正确，但摘要带明确上年度限定、限定作用域在摘要之前、以及引用旧公告内部“本期”仍产生HkBodyFacts并可进入selection。root独立重现三类排列变体，证据`root-rereview-01-scope-counterexample.json`/`root-rereview-01-scope-variants.json`绑定冻结版本；DS另证“非本期”“本期以外”。owner为正文声明归属/事实解析，必须继续在owner收束正面当前声明与其作用域，不能仅列否定词黑名单或在下游过滤。原CR4不能改称非目标或仅残余。
- **CR7 accepted / 部分修复，fixed in current slice**：filing builder/rebuild已补字段，但workflow外层完整性abort和通用Exception路径的`_build_candidate_failed_result`仍不投影candidate已有report_date_source/fiscal_year_source，展开/嵌套FILING_FAILED事件一起丢失。root读实际435/463调用点、874–925构造/投影链与DS探针确认。owner为已有workflow结果投影，直接补同源字段并用真实异常路径验证；不新增公共typed摘要或durable字段，不搭新结果框架。

OQ/residual正式处置（均不把CR4/7延期）：

1. 标题rebuild的既有`source_title_and_annual_end`与一般标题resolution值差异：本轮CR7落实正文来源和新增内部事件投影，不改变原有标题rebuild认证/来源标签契约；rebuild当前结果与同次meta更新同源，无当前body财期错误。作为本轮blocker **rejected-with-reason**，统一历史标题来源标签的契约核查为**deferred-with-owner / assigned to later work unit**，owner Fins来源契约，destination后续独立标题来源语义单元；当前不得为通过本轮擅改所有标题标签/迁移。
2. 相同source年度日期/URL冲突batch拒绝符合原先“同来源冲突先拒绝”，未承诺来源级隔离；新增细分状态机 **deferred-with-owner / assigned to later work unit**，owner Fins discovery。
3. 本地正文unknown时未缓存正常失败结果、可能重复提取：现CR1已证的有效本地事实重复spawn已修；未知输入有界重复不改变事实/发布/取消正确性，未承诺通用提取缓存。该性能扩展 **deferred-with-owner / assigned to later work unit**，owner Fins正文事实输入，destination后续未知结果复用核查；不把它伪称全部输入零重复。
4. direct_fact_conflict保守不承诺不受支持的日期、resolve_company同步HTTP、旧rebuild同步编排与需要跨平台全取消组合，未属于本轮原触发缺口，**deferred-with-owner / assigned to later work unit**，owner Fins/documents异步编排；当前Host cooperative取消/实际worker回收仍须保持，下一修复若实质触及这些行为再按影响重验。三页外/OCR/特殊财年/未来官方变更等沿原later分类。
5. MiMo docstring旧参数名为非blocking措辞；若fix-02触及同函数随实际变化修正，不为此扩大审核或单独产品变更。

两路均已退出，无同owner writer。现在派指定gpt-6-sol单writer做CR4/7窄fix-02；保持8资产+7原证据、正式四原件、固定普通增量入口/实际版本，按本次影响补测试/coverage/pyright和必要README，再同时双路复审CR4/7及实际delta。前次1503/16owner/Docling证据按未变版本适用性复用，不能机械重复全套。META继续等0135完整交付，不merge、不timer。


## fix-02最终核收 / 受影响面复审02入口

gpt-6-sol实际outer/runtime退出0，native `01a15175-e507-7d90-ae57-16ffa1afd3b6`；root已完整读final、fix-02报告、六文件实际delta及真正最终-v2审计。冻结`fix-02/source-final-v2`完整patch SHA `0e4e2374823c29d8f4f387947facec4a43ff610fb594c2baf8853cda6bb4f318`，相对fix-01的delta SHA `71dfa87980469e6e129e8c21e809216880d64ed2826b4c2390c3a6ff171151bf`。54源码/保存副本与307项本轮新证据由root全量重算通过；只改正文owner、workflow失败投影、对应测试及三README，未变48文件/删除项可取回。核收`root-fix-02-intake.json`。

root独立经storage重读8资产完整发布态与bytes及原7证据，与writer真正最终-v2保全全等。最后修改后296受影响测试通过，全库pyright0；两修改owner完整文件coverage96.69%/88.55%，14未改owner的前次有效覆盖证据逐SHA复用。最终固定入口同参普通增量exit0，8发现8skip/0unknown/8明细无省略，入口及10关键import对应真正最终保存版本。无覆盖/重转/生产rebuild。无-v2的本轮中间CLI/快照在发现跨页历史作用域反例前，只作历史证据，不能冒称最终。

CR4 writer以连续公告头、无附加限定的摘要与受控摘要页闭合、紧随主报表/同发行人董事直接宣告收束声明归属；真实root反例/引用/限定位置及新增跨页反例均关闭，正式四原件仍支持。此为既定owner内支持语法收窄，不是通用NLP/任意版式承诺。CR7外层通用与完整性异常builder直接投影同一candidate的两来源，并经真实workflow失败/abort及完整资产保全验证；无公共或durable新字段。writer自验不代复审，当前仅核收，仍不可PR pass。

现在同时派mimo-flash/ds-flash独立核CR4/7及六文件delta，特别核新scope是否真实防跨页/引用、是否因与身份无关的页头/数值行/单位/附注规则过度耦合而违反通用owner目标、证据支持与关闭边界是否诚实；测试/退出0不能替判断。其余已核销项仅按实际交互影响复核，不重扫54文件或重复307/732/816全部证据、整组1503。当前无产品writer；META仍排队，未启动plan；无merge/timer。


## 受影响面复审02正式裁决 / fix-03入口

两路actual outer/runtime均退出0并已读完整final及报告：DS `code-review-20261019-095849.md`（native9d15de60-9ab3-44de-821f-8bcb0aa28f25），MiMo `code-review-20261019-100515.md`（native938befa4-3df6-423a-bc11-bfeb47dceb66）。核收`root-code-rereview-02-decision.json`。两路均自报通过，同时各给出可重复产出旧日期事实的探针却称“crafted/无真实官方样本”而不阻塞。root不采纳这种范围解释：已审owner契约要求显式历史/比较/引用和直接冲突失败关闭，原CR4本就通过合成owner反例成立；输入自相矛盾是关闭理由，不是丢掉矛盾仍产事实的豁免。无需证明四官方当前样本已触发，亦不声称它们出现财期错误。

- **CR7 accepted / 已修复**：两外层失败路径与展开/嵌套事件直接投影candidate已有来源，真实Fs失败/完整性abort、元数据/全部字节及锁保全已双路实核。未改公共/持久契约。后续若本轮不触及该实现，复用当前证据。
- **CR4 accepted / 部分修复，fixed in current slice**：root独立重现并保存4组绑定同一最终-v2版本的输入/输出：`root-rereview-02-statement-suffix.json`（完整日期/年份列后的上年度/非本期表头限定被忽略）；`root-rereview-02-numeric-scope.json`（明确历史说明因带两列数字被当财务行）；`root-rereview-02-pending-note-scope.json`（MiMo P-A，未闭合附注pending吞入独立历史引用说明，随后旧宣告被确认）；`root-rereview-02-year-consistency.json`（摘要两年与完整日期年份完全不相容仍给HkBodyFacts）。根因仍在正文owner丢失/弱化完整声明及直接冲突，而非selection/仓储或四原件运输。继续窄修完整见证边界、限定/附注归属和一致性，不按特定反例字串加黑名单；不得以结构前缀优先而掩盖同一作用域的矛盾。年份列仅能校验已确认完整日期的一致性，不从首列/MAX/披露日期猜当前年。

裁决其余OQ/残余：

1. DS residual2及MiMo P-A中上述显式限定/未知段落被接受，作为CR4同一缺口 **accepted / 部分修复**，不能延期。修复应仍在owner并保持未知关闭，不建设通用NLP或金融指标平台。
2. MiMo P-B“同发行人完整宣告无任何历史前言”不能仅因审计者称该页旧，就把输入中的无歧义完整日期当错误。对没有文本限定/直接冲突、年份仍与可用输入相容的情况，不从列顺序或外部旧页标签推定另一期；该额外真实性保证作为blocker **rejected-with-reason**，一般伪造/未表达上下文真实性为**assigned to later work unit / Fins来源事实**。这不豁免上文年份完全不相容的实际冲突。
3. 既有人民币单位/精确免责声明/支持句式等未支持版式仍为unknown，无单公司/source/年月特判；扩大支持范围 **deferred-with-owner / assigned to later work unit / Fins正文事实**。本轮修复不得靠再硬编码指标/币种提高通过率，可按最小必要逻辑收束或简化。
4. 两builder字段清单重复、原有旧标题标签/unknown缓存/来源级隔离/异步编排等维持之前裁决，不为此搭新框架。新parser被触及的同行剩余文本分支可按实际影响补测试，不为未变覆盖缺行机械扩测试。

两路均已退出，无并发reader/writer。现在派指定gpt-6-sol唯一writer做fix-03，仅CR4及实际受影响测试/README；CR1/2/3/5/6/7闭合及有效未变证据复用。按实际修改owner覆盖、受影响回归/pyright、真正最终固定普通增量、八资产七原证据与实际入口核验后，再同时双路受影响面复审。不新增goal、schema、调用方改动、META实现、merge或timer。


## fix-03最终核收 / 受影响面复审03入口

gpt-6-sol实际outer/runtime退出0，native `01a151ed-07ac-7c43-bb73-34c68c21fc14`；root已读完整final、报告及五文件实际delta。唯一最终`fix-03/source-final`完整patch SHA `abf017c7034097c347c0a9ce4d880a28949db837dbb8e258950493ce18dfa87e`，fix02→fix03 delta SHA `3240315776098c30d3c21674980d3405a16bd59582a2fa98e6a449cb70fad246`。54源码当前/副本及239新证据逐SHA核对通过，实际仅正文owner、对应测试、三README有变化，其余49文件与删除项不变；中间失败源码/测试/pyright与原始红测全部保留，不计最终通过。核收`root-fix-03-intake.json`。

最后修改后321受影响回归通过，全库pyright0，修改owner完整文件覆盖96.57%；15未变owner依逐SHA适用复用有效覆盖/审核，未机械重跑旧全集。固定CLI同参普通增量实际exit0，8发现8skip/0unknown/无明细省略，入口及10关键import的实际路径/字节SHA与真正最终版一致。root另经storage独立重读八资产完整meta/revision/primary/provenance/descriptor与全部字节及七原证据，与writer最终保全全等；没有覆盖/重转/生产rebuild。首转与Docling仍复用适用的implementation-v3证据，不冒称当前首转。

CR4 writer自验关闭四组正式反例并增加完整表头、标签/定义片段、一致性校验与宣告/续表边界；仍待独立实审是否真正区分作用域，不能把有限字符集直接等同业务名词，亦不能因测试通过、两票或自报pass放行。现在同时派指定mimo-flash/ds-flash受影响面复审CR4及五文件delta；CR1/2/3/5/6/7未变沿已核销裁决。无同owner产品writer，尚未PR gate，META继续排队，不merge/timer。


## 受影响面复审03正式裁决 / fix-04入口

两路均actual outer/runtime退出0，完整final与报告已root全文核收：DS `code-review-20261019-103750.md`（native9196048b-75fb-4afc-b0fa-90e373d29734）、MiMo `code-review-20261019-104920.md`（native9a42fc23-9af3-4130-af91-14318b926a6e）。root裁决`root-code-rereview-03-decision.json`，当前CR4仍**accepted / 部分修复**，不可PR pass。四组前次正式反例已关闭且四官方正例/排列/来源/固定CLI与八资产七原证据有效，这些事实不掩盖剩余直接反例。没有实际当前四官方财期错误的声明。

- **CR4a accepted / 部分修复，fixed in current slice**：DS1/2与MiMo1同源。只去独立历史/非本期说明的句读，摘要/报表首行仍被判财务名词，pending仍拼入定义；有限字符集只是字符合法，不是业务名词或定义归属证明。root独立`root-rereview-03-punctuation-scope-v2.json`与`...-anchored.json`重现年度和有可信年度锚的中期真实selector各一候选。首版`root-rereview-03-punctuation-scope.json`的pending探针错误全局移除了免责声明标点，其unknown不作已修复证据；历史尝试保留。
- **CR4b accepted / 未修复，fixed in current slice**：DS3及root独立`root-rereview-03-crosspage.json`证明，页尾完整表头/董事宣告之后下一页的明确历史/非本期限定，以及同页合法首行后紧随限定，被页循环break/只查首行忽略。物理页边界或首个数值行不是业务作用域闭合证明。本轮至少闭合这些完整输入，不要求任意全文语义完备。
- **DS4测试责任 accepted / 部分修复**：合并为CR4必要owner contract回归，补上述真实接受路径与实际修改一致性分支；不因missing行机械扩测所有防御分支。CR1/2/3/5/6/7未变仍已修复，证据按影响复用。

OQ正式裁决：用户/已审plan从未要求“只能用纯结构、禁止一切词法知识”。一般化、可文档化的词法/句法作用域规则可由正文owner采用；禁的是为反例字串加黑名单、下游补偿、单公司/年月/指标/币种特判或不必要的NLP/模板平台。将契约改称“只识别带标点的历史说明”会豁免同一已接受缺口，作为当前改法 **rejected-with-reason**；不重复goal confirmation。MiMo建议至少两行成表/限定续行数不是强制方案：行数不证明归属，可制造新脆弱阈值，具体最小连贯修复由writer选择。若确需重要输入/公共/持久契约或架构变化，先以证据交root补计划/适用审核；纯owner内部规则无需停在型号/目标确认。

无任何文本限定/直接冲突且年列相容的P-B仍按原裁决，不能用外部“旧页”标签改期；未表达真实性、任意自然语言/未支持版式、三页外/OCR/特殊财年/平台等沿assigned to later work unit，owner Fins正文事实/来源事实/documents，destination后续有证支持范围单元。旧标题标签/unknown缓存/来源隔离等维持原deferred裁决。范围内缺口不因合成或无当前四官方触发而延期。

当前无在途reviewer或产品writer，下一入口fix-04：指定gpt-6-sol唯一writer落实CR4a/b和对应回归/README，最终验证和固定入口保全后再同时双路受影响面复审。禁止继续用字符集/标点替代语义归属，禁止全仓重设计或机械重复旧全集。META仍排0135 final closeout后；不merge/timer/改旧PR。


## fix-04最终核收 / 受影响面复审04入口

gpt-6-sol实际outer/runtime退出0，native `01a15214-2311-7cb2-9b48-f036c94ad406`；完整final、报告与五文件实际delta已root全文读取。唯一最终`fix-04/source-final`，完整patch SHA `c32cc7f917ab9e817169c24104abde73b2152b9b75aee6e4c8df2869aadc3025`，fix03→fix04 delta SHA `7a5678ea1c7308dbdbd900c142fac73c9e82a791e1a5901e4772f565e2c2b76f`，owner SHA `37211ec831d591dc86986a39a9aa90901cf9461cbeec258bbb18dbd40b5490e1`。54保存源码/当前/manifest与186新证据逐SHA核对通过；实际仍只正文owner、对应测试、三README变化，49文件/删除项不变。核收`root-fix-04-intake.json`。

最后修改后393受影响回归通过、全库pyright0，修改owner195/199=97.99%且无排除行；15未变owner按SHA与实际影响复用已审有效覆盖/行为证据。26个正式输入本轮有效红测14failed/12passed，最终全部unknown/零候选/一未决；早期DTO错误、探针公司/锚配置不适用、首版实现及所有失败完整保留，不冒充有效通过。四官方正例、24排列、比较列交换/P-B及Fs交互仍支持。

最终同固定CLI/base/0135/窗口普通增量真实exit0，8发现8skip/0unknown/8明细无省略；entry、解释器与10关键import真实路径/字节SHA对应冻结版。root独立经storage重读八资产完整meta/revision/primary/provenance/descriptor及全部bytes与七原证据，与writer最终保全全等。没有生产overwrite/rebuild/重转/手修原件。首转/Docling未变证据按implementation-v3适用复用，不称本轮首转。

本次writer在既定正文owner引入窄词法/句法准入并逐行校验有界表体/后续物理页，未新增输入/公共/持久schema或架构契约。writer自验不代实审，当前CR4a/b尚未正式核销。现在同时派指定两路受影响面复审CR4a/b、必要回归及实际五文件delta，核实一般化规则是否连贯、正反行为和支持边界是否诚实；不是仅按26反例或393计数放行，也不把任意未来语言假想扩大为通用NLP目标。CR1/2/3/5/6/7未变已核销沿既有裁决，当前无产品writer。META仍排0135完整交付后，不merge/timer。


## 受影响面复审04正式裁决 / fix-05入口

DS `code-review-20261019-111402.md`（native2d73d751-1c2f-4cf3-9944-fb310adef084）与MiMo `code-review-20261019-113040.md`（natived7da54a5-2d32-4daf-86ec-056e6cdeda6f）均actual outer/runtime0，完整final/report已全文核收。root裁决`root-code-rereview-04-decision.json`，并独立`root-rereview-04-explicit-scope.json`重现「不代表本期業績」「與本期無關」在摘要及续页各一真实selector候选。26前次正式输入确已关闭，四官方及正例仍有效；不能据此覆盖新的同类明确限定。当前CR4a/b仍**accepted / 部分修复**，不可PR pass。

成立的缺口：共享名词/定义准入仍接受未覆盖的否定判断/关系、指代判断、摘录/来源与用途谓词；MiMo中明确「不代表本期」「与本期无关」是原「并非本期」同一语义家族，不能延期。DS N8判断句/N9摘录句须按此实际语法归属核，不靠词中出现过去来推期。CR4b页循环/全表体结构闭合已被双路验证有效，剩余同根在共享词法/句法门，不再另造跨页机制。对应必要测试及README类别级过宽表述合并在同一fix05。

不成立的合并论证：DS把「上年度比较资料/数字」「往年数据」「比较资料来自往年公告」等全部等同整表非本期限定，作为泛化blocker **rejected-with-reason**。比较列/指标及其来源可以提及往年，删除「以下/仅/并非本期/引用」不是单纯去句读；裸比较名词本身不能推翻完整当前日期或证明整个声明是旧引用。root对照`root-rereview-04-nominal-scope.json`保留完整输入及不同语法的输出。不能要求所有历史名词unknown，亦不按新的源/年份特判。DS「数值恰等于年份列则拒绝」作为实现要求 **rejected-with-reason**：合法财务数值可以巧合相同，偶然数值不证明语义归属。

一般化词法/句法方向本身合规，无新增输入/公共/持久schema或架构契约；下一窄修覆盖已演示的明确谓词家族、让规则/文档的实际边界一致，不能仅将完整反例串列黑名单，也不能声称任意中文语义完备。把已发现的明确非本期家族改称「枚举token范围外」而保留错误Facts，作为当前延期理由 **rejected-with-reason**。任意未覆盖语言/版式及未表达真实性仍沿assigned to later work unit，owner Fins正文事实/来源事实/documents，destination后续有证支持范围单元；不将有限目标变成无限中文词表工程。

当前两reviewer均已退出，无产品writer。next entry=fix-05，指定gpt-6-sol唯一writer，只修共享谓词归属及对应回归/README；保留跨页结构、四官方/比较列/P-B/来源绑定和八资产七原证据。CR1/2/3/5/6/7未变已核销按影响复用，最终真实受影响验证/pyright/入口/普通增量保全后再同时双路复审。不重开goal，不并发writer、不改调用方/META/旧PR、不merge/timer。


## fix-05最终核收 / 受影响面复审05入口

gpt-6-sol实际outer/runtime退出0，native `01a1523a-3fe8-76d3-9836-5f09e5e3c16e`；完整final、报告及五文件实际delta已root全文读取。唯一最终`fix-05/source-final`完整patch SHA `f5335dbf0f773f17c5fc528e5ceef490c8fe6afe3fc34b5eceaf463e054af703`，fix04→fix05 delta SHA `4f8311ee6e4a77865882c30b0ad62cbd3b24e8c7bad9a17039cafbba327978a5`，owner SHA `59e733b738ba3618743522a91641e68ebc3164cf4ce8048b3e7d278bf5f62b27`。54保存源码/当前/manifest与274新证据逐SHA核对通过，实际只正文owner、对应测试及三README变化，49文件/删除项未变。核收`root-fix-05-intake.json`。

本轮按谓词构造收束共享准入，并分开定义句框与名词参数；保留附屬等名词构词、裸比较名词与数值恰等于年列的正例。有效红测74Facts/真实候选及1unknown可取回，75最终输入均unknown/零候选/一未决。MiMo旧宣告不相容年列/缺锚或分类不适用之处已按其v2输入和同公司可信年度锚纠正适用性，不冒称全是产品修复。早期失败/首轮回归/旧快照全部保留。

最后修改后508受影响回归通过、全库pyright0，owner204/209=97.61%且无排除行；四官方/24排列/P-B/比较列交换/来源绑定/Fs交互通过，15未改owner逐SHA适用复用有效证据。固定CLI同参普通增量真实exit0、8发现8skip/0unknown/8明细无省略，entry/解释器与10import实际路径/SHA对应真正最终。root另经storage独立重读八资产全发布态/全部字节及七原证据，与writer最终全等；没有覆盖/重转/生产rebuild，首转/Docling沿implementation-v3适用复用，不称本轮首转。

README与报告已如实区分已支持构造及任意未覆盖语言：有限词法/句法检查不证明所有中文语义，未支持措辞可能仍未区分，也可能将合法复合名词保守降为unknown。此为既有不承诺任意自然语言完备的诚实表述；已演示的明确非本期家族已在本轮实现/自验关闭，不以改文档延期它们。是否真的核销仍交两路实审及root裁决。现在同时派指定双路受影响面复审CR4共享谓词/必要文档回归与五文件delta，不机械重扫未改责任/所有证据；当前无产品writer，不进入PR gate。META仍排0135完整交付后，不merge/timer。


## 受影响面复审05正式裁决 / fix-06入口

DS `code-review-20261019-115337.md`（nativef8f19a40-ced4-456f-9969-23aa8cad8409）与MiMo `code-review-20261019-121954.md`（native89cfe531-78b4-47fb-b34c-02712d9a2021）均actual outer/runtime0；完整final/report已全文核收，裁决`root-code-rereview-05-decision.json`。前75/旧26、已文档构造、正常/裸比较名词正例、真实selector及跨页闭合确已修复，有限规则文档诚实；但CR4整体仍**accepted / 部分修复**。不按一路pass或退出码放行。

本轮必要fix06合并三项：

- **DS05字形finding accepted / 未修复**：同一已支持系词「係」漏简体「系」。root独立`root-rereview-05-copula.json`对照仅换字形，summary/next_page由unknown/零候选变Facts/一候选；全简体头也能达到该门。属于已演示构造，不是新谓词/NLP要求。
- **MiMo05五个具体OQ accepted / 未修复**：`摘自往年業績`、`無關本期業績`、`非關本期業績`、`供比較用途`、`資料源於往年`的完整输入/输出已实测。root独立`root-rereview-05-neighbors.json`逐项重现Facts及一候选；它们是共享关系/来源/用途构造的具体顺序/介词/形态残余。仅以「未文档化」把当前已直接演示的问题移交later，作为当前处置 **rejected-with-reason**；不把有限目标扩大为任意中文完备，但也不将owner正确性改成仅列出过的完整字串。实现者需最小连贯地处理已证构造，不能继续只追加整句黑名单；仍无新输入/架构/schema需求。
- **MiMo05附屬正例回归 accepted / 未修复**：当前名词行为正确，但新增修饰构词规则及README承诺无owner回归锁定。补真实owner/selector正例，不为断言私有正则文本写镜像测试，也不为它增加新生产机制。

纠正风险方向：报告把未识别措辞产Facts与候选也合称availability、不产生错误事实并不准确；未知措辞可有误归属/错误财期事实风险，保守拒绝合法名词才是可用性/unknown风险，必须分别记录。当前五个已实证同族残余修在本slice；任意未覆盖语言/未来构造与三页外/OCR/特殊财年/未表达真实性仍依原非目标 **assigned to later work unit**，owner Fins正文事实/来源事实/documents，destination后续有原件证据的支持范围单元；不承诺无误识别或消除unknown。

跨页结构及CR1/2/3/5/6/7未变已核销，下一修复仅共享准入/必要定义参数校验及对应测试/README，避免重复已核设计。保留裸比较名词/正常否定名词、四官方/24排列/P-B/日期与原件绑定；不用年份数值偶然关系推语义。两路均已退出、无产品writer，next entry=指定gpt-6-sol唯一fix06；完成实际必要验证/入口/普通增量保全后再同时双路受影响复审。不重复goal，不改调用方/META/旧PR，不merge/timer。


## fix-06最终核收 / 受影响面复审06入口

gpt-6-sol实际outer/runtime退出0，native `01a15268-e975-7b51-8dea-e8afa54a77de`；完整final、报告及190行五文件实际delta已root全文读取。唯一最终`fix-06/source-final`，完整patch SHA `0b0cfa187130c7d50dd76a798caee04961590bfd9c1725748636a671cbf72145`，fix05→fix06 delta SHA `b75c996bb71e1003d47362ae7631b07ecfa9af4530925c3b3b6c78b3d116540b`，owner SHA `b69d8842bd770b863889478a977383940f77301162042555784b9436db18ee68`。54源码当前/副本/manifest及203新证据逐SHA核对通过。root独立AST比较证明生产代码除_PREDICATE_SYNTAX规则常量外全部AST不变；测试七位置输入提取前后主体AST相等，未弱化旧断言。核收`root-fix-06-intake.json`。

85完整输入红绿可取回：65负例中旧owner60个错误Facts/单候选，5个已关闭；20正例正常。最终65负例全unknown/零候选/一未决，20正例全Facts/单候选。新增/扩充81回归含同构字形/全简体正反、关系顺序/来源介词/用途形态组合、折行、16附屬繁简名词及2有锚中期正例。源/参数/框架未变。

最后修改后241真正受影响测试通过、233未选（命令与选择理由可取回），覆盖owner/四官方/24排列/比较列/P-B/原件绑定及真实Fs交互。原508及更早未受影响断言按AST/实际影响适用复用，不冒称本版重跑508。全库pyright0，owner201/209=96.17%无排除行；15未改owner及责任继续逐SHA复用有效覆盖/审核。最终固定同参普通增量exit0、8发现8skip/0unknown/8明细无省略，entry/解释器与10import真实路径/SHA对应冻结版。root独立经storage重读八资产全发布态/全部字节及七原证据，与writer最终全等；无覆盖/重转/生产rebuild，不冒称本版首转/Docling重验。

规则按字形、关系顺序/否定、来源动词与自/於/于、用途之用/用途作同一门组合；没有完整句黑名单、业务名词特判或新平台。README分别诚实说明有限规则的误归属/错误事实方向与保守unknown方向，已知六构造自验闭合但仍待实审，不以文档重述代修复。现在同时指定双路受影响面复审仅规则常量及对应回归/文档真实delta，不重做已核销的跨页结构/完整系统/无限中文词法探索；新直接证据按实际影响实判。CR1/2/3/5/6/7未变已核销，当前无产品writer。META仍排0135完整交付后，不merge/timer。


## 受影响面复审06正式裁决 / ready-to-open-draft-PR

DS `code-review-20261019-124220.md`（natived9347b0e-f7f9-4f70-ad82-69c194d92f1f）与MiMo `code-review-20261019-124605.md`（native73d15163-ea75-4d7e-b758-2dc04436184d）均actual outer/runtime0；完整final/report已全文核收。两路均将CR4-glyph、CR4-concrete-neighbors、CR4-nominal-positive-test判为已修复。root依据实际delta/AST、同源红绿输入、原样重放/实际selector、固定入口与资产保全裁决`root-code-rereview-06-decision.json`，不以票数/exit0代判断。此前完整代码审核及后续每项accepted修复均已有对应独立复审：**CR1–CR7及其本轮子项 accepted / 已修复**，无未决accepted或needs-more-evidence blocker。当前code-review gate通过，next=ready-to-open-draft-PR，不等于work unit已完成。

验证适用：root最终241真实受影响测试/pyright0/owner96.17%/入口与10import/8skip/八资产七证据全等保持；DS独立135定向及474完整owner文件测试通过，root已从其实际tool command/stdout取回`root-ds06-test-readback.json`（不把pipe tail当独立pytest进程回执），MiMo196定向及原样探针通过。其余15owner、508/更早完整组合、首转/Docling按未变SHA/AST及实际影响复用，不冒称最终版全量重跑或首次转换。

风险正式分类：有限语言仍可能误归属并产生错误期间候选，保守名词拒绝则增加unknown；两类都真实存在，不能只称可用性。报告中未支持来源动词/介词/修饰顺序/用途新句型（如选自、無任何關聯、作比較用途）作为**deferred-with-owner / assigned to later work unit**，owner Fins正文事实/来源事实，destination独立有原件证据的正文支持范围单元。非阻断依据：当前已确认目标为四官方来源与有界结构/具体已接受构造的owner修复，不承诺任意中文谓词或词性完备；本次明确接受的字形、五句与名词回归全部实测闭合，未以改文档豁免它们。扩充未支持语言需要另立支持语法与真实语料验证，不将本单元变成无限词表工程。README/报告/PR须直接披露误归属方向，不宣称零错误解析。保守unknown归同一later owner，目标明确允许未决，四官方/已支持正例未被误拒。其它OCR/特殊财年/三页外/外部真实性/旧标签/缓存/隔离等维持既有owner/destination，不新增平台或issue。

两路已退出，无产品writer。现在核当前分支/dirty归属和远端PR204最终base/head；只提交0135 intended代码/fixture/治理证据，排除META control；推送并新建依赖PR204/203的独立draft PR。随后必须按实际OID完整diff/身份/标题正文/CI/push作总控交付核对，再draft-PR-pass和实质final closeout。不得merge/mark-ready/request-review/修改旧PR或timer。0135完整交付后才进入已确认META独立preflight/plan。


## 提交前归档属性核验

首次暂存检查在提交前停止：四份官方 PDF 的前段字节被 Git 启发式识别为文本，原始 CR 换行被 `git diff --cached --check` 报为空白错误。完整失败 stdout（528516字节）保留于 `delivery-preflight-01/staged-diff-check-before.stdout`，未提交、未格式化原件。新增 `tests/fixtures/hk_body_official/.gitattributes` 的 `*.pdf binary`，只声明二进制归档/不做行尾规范化。root重核54份已审文件SHA全等，四PDF属性binary set、text/diff/merge unset；后续核索引blob原字节及文本diff检查。当前intended为84路径，META control仍排除。

已阅读tests README职责和fixture段落；现有说明已记录完整官方原件及URL/SHA/storage读回。本次仅Git归档属性，不改变测试层级、入口、运行期契约或官方证据，不机械增写README，不重跑无受影响的代码审核/pytest/pyright。产品与fixtures按fix06已审冻结版验证继续有效；只补归档属性、索引SHA及staged diff check。current gate=必要提交/push，尚未draft-PR-pass。
