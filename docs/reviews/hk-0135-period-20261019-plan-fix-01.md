# 0135 plan fix-01：v1→v2 修订回执

仅修计划，实施尚未开始。已读取 AGENTS、control 最后双路裁决、当前 plan、DS `plan-review-20261019-042343.md` 与 MiMo `plan-review-20261019-042959.md`；沿用已确认 goal/输入授权，不重新确认、不派 agent。两路原审核只覆盖冻结 v1，不代表 v2 已获复审或实施放行。

| 项目 / 对应审核 | 计划问题状态与 delta | 后续核验归属 |
| --- | --- | --- |
| P1 / MiMo1、DS1 | **计划已补，产品未修**。§1、§5.2、§6明确同批正文年度先确认/校验、统一建锚、中期后映射且排列无关；加入零本地/零标题年度正例、彻底无锚/冲突/非月末负例，正文中期禁用标题序数回退。四条确认保持有条件期望。 | selection；复审后由同 slice 实施/验证 |
| P2 / DS2、MiMo2 | **计划已补，产品未修**。§5.2、§5.3、§6指定 selection 唯一封闭 eligibility owner；缺事实与冲突/歧义分开，downloader 不得以 None 准入或跨接口重算。多主体、区间简写及显式冲突等断言正文获取次数0。 | selection 判定及 downloader 交互 |
| P3 / DS3 | **计划已补，产品未修**。§5.3、§6明确正文事实→source/公司/URL/SHA绑定→resolution/candidate/discovery 的 typed 链；models 公共校验负责交接，filing workflow 提交/skip 前复用，writer 内校验 revision/完整性。prepared/local 两路同 key 不同 bytes、等长损坏、A选期/B落盘均拒绝；CN FY 原校验全部保留。 | models / filing workflow / publication 边界 |
| P4 / root 新直接证据 | **计划已选机制，未实现验证**。§5.1、§6核 Fins 默认 Docling 在子进程、Web 有同进程调用及第三方其它 PDFium 用法，选择单请求单线程 spawn 提取 worker 隔离。documents 管 native target/句柄，Fins 管调用/取消，runtime 复用现有进程机制。无共享锁等待；进程等待/原生调用取消、异常/关闭/回收均须验证，不能换私锁自证安全。 | documents 提取边界 + Fins 编排；双路受影响面复审 |

其余必要契约已在原对应段落收敛：三页是支持边界；HK 日期来源由 `hk_fiscal_calendar` 唯一 typed 定义正文值 `source_document`；财年来源由 models 定义、selection 产生，正文年度 `source_document`，正文中期日历推导 `source_document_and_annual_end`。`local_hk_annual_ends` 保持纯事实输入，仓储接线归 workflow/rebuild；常规非十二月年结复用可信日历，不硬编码样本、不扩特殊财年。现有 `period_resolution_*` 仅 rebuild 写入：标题 v3 行为保留，正文拟用 `hk-period-body-v1` 规则标签与已校验年度 document_id 集合，普通下载不新增标签写入或迁移；新增正文锚随 resolution 保留 source/SHA 引用、可从已发布原件重核。值域/标签一并待复审，无新增持久字段、新库或旧库兼容；如必须有额外 durable schema 决策则报告 root，不自行实施。

§6已补现有 `test_f5_workflow_rebuild.py`、`test_f5_storage_calendar.py` 及进程相关回归命令，并要求新增 owner/交互断言。原报告/title 输入事实行为不扩大。所有建议仍归原单 slice。

证据适用性及保全：

- HEAD 仍为 `f975a9586261bf7750e632959848bb6392c2881b`；83/83旧取证清单的长度/SHA、8个原相关源码与 base 逐字一致。额外只读核对调用边界/已安装依赖，见 [源码观察](../../workspace/tmp/hk-0135-period-20261019/plan-fix-01/source-boundary-observation.json)；它不是并发或提取运行结果。
- 冻结 v1 SHA `179ae24ec34bcc2139b21d2b940d54e86a4963ae866b88b64529c128997be18d` 保持不变；control、两份审核、root PDFium 证据及9633受管文件未改。未重开原失败文件或生产资产，七份原证据副本随83项核验；四官方PDF及仓储读回链沿用旧证据，未重取或重提取。
- 336 passed / pyright 0仍仅证明 f975未修改基线，本次未重跑。产品/测试/依赖零 delta，不以旧结果宣称新契约通过；无生产 download/rebuild、外发、commit/push/merge，README无本次更新触发。

最终 plan SHA256：`208dee4ff52840367204eadc0a661d421a1042314729f678b92a670cef5ed469`。

可取回产物：[当前计划](hk-0135-period-20261019-plan.md)、[v2完整副本](../../workspace/tmp/hk-0135-period-20261019/plan-fix-01/plan-reviewed-v2.md)、[v1→v2完整delta](../../workspace/tmp/hk-0135-period-20261019/plan-fix-01/plan-v1-to-v2.patch)、[版本摘要](../../workspace/tmp/hk-0135-period-20261019/plan-fix-01/plan-versions.json)、[结束核验](../../workspace/tmp/hk-0135-period-20261019/plan-fix-01/final-audit.json)。所有新增 tmp 仅在 `workspace/tmp/hk-0135-period-20261019/plan-fix-01/`。

已闭合的是 P1–P4 的计划责任、最小机制和验证要求；未闭合的是 v2 双路受影响面复审/root 放行、全部实现及业务验收。原生隔离的开销、取消/关闭/IPC和全链一致性尚未实测；旧第三方其它路径的相互并发安全不在本次声称范围，新提取隔离不依赖它们共享锁。生产四资产 snapshot/真实转换及普通增量仍留待已审实施阶段；跨平台不扩大承诺。下一步由 root 派两路复审，本 runner 不派发。
