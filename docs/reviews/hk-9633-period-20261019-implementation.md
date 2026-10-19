# 9633 / 12345879 单 slice implementation / validation

状态：**实现及验证已完成；待父总控双路完整 deepreview**。本报告不代表 code review、PR 或 Gateflow work unit 完成。

已先读取 `AGENTS.md`、[control 最新裁决](hk-9633-period-20261019-control.md) 与[计划](hk-9633-period-20261019-plan.md)。control 明确 `plan gate pass`，下一入口为本 slice。按 Gateflow 执行，经直接官方证据确认动机成立：整标题扫描把主体中期报告与被引用年报的年份、财期、修订性质混合；没有改变缺证据时失败关闭的要求。

分支 `fix/hk-9633-period-20261019`，起点/当前 HEAD 均为 `705c2dc2f6b4491edda0c6f0d2a4b1f8e2bf458d`。本地依赖分支 `fix/hk-period-evidence-20261018` 仍指向该 OID；未来 PR base 按已批准计划取该分支，只交独立 delta。未 commit/push/merge、未操作 PR203、未派 agent、未发送外部消息。未读凭据或调用方无关资料，未调查 TLS/沙箱/域名，未改调用方文件或手改受管财报。期间出现其它任务的未跟踪 control 文件，未读取或纳入本任务。

## 实际改动与 owner

- `cn_report_selection.py` 增加小型纯函数 `hk_report_subject_title`：完整识别中文“唯一主体报告及有关另一报告的补充资料”，主体与引用均须完整匹配已支持的报告语法，有唯一年份或有效直接截止日。繁简、空白及逐位中文年份可用；没有公司、年份、source 特例。
- 不能解释完整关系、存在并列主体、范围年、无引用对象、未消费尾部、引用修饰作用域不明或同年同财期引用时，不取首年、不截尾、不猜另一报告。主体本身的修订仍保留；附属报告的修订不参与主体 amended 或选优。
- `resolve_hk_report_period` 从同一主体解析财年/身份/覆盖；candidate、未决日期、年度供证与 `hk_download_rebuild.py` 的直接日期通过 `hk_report_end_date` 消费该投影。选优和 candidate 共用主体 amended 判断；排序键移到模块级函数。
- 可选本地分类缺失时，年度供证与重解析也只用该主体作分类依据，避免又从整标题引入引用报告。存在 provider 分类时仍按其 family 与主体共同校验；语言门槛、窗口、同 source 冲突及原有日历约束保留。
- 官方 raw 标题/分类/URL/来源 ID 不改写。本例为 **2026 H1 / coverage 仅 H1 / amended=false / report_date=null / report_date_source=null**。未从 PDF 或披露日期自动产生日期；无 schema、迁移、版本 bump 或兼容层改动。
- 新增 `tests/fins/test_hk_report_title_scope.py` 与四份正式 fixture。三份官方响应保持完整 2+2+16 行，来源 URL/采集时间/HTTP 状态/字节数/SHA256 见 `fixtures/hk_report_title_scope_20261019/provenance.json`。无预计算财期输入；HEAD 显式 stub；workflow PDF/Docling 明确为合成资产。真实生产转换单独核验。

## Red → green 与本轮失败记录

证据根目录统一为 `workspace/tmp/hk-9633-period-20261019/`，下文文件名均相对它。旧轮次均保留，不覆盖或重新标为新版。

| 证据 | 实际结果与适用性 |
| --- | --- |
| `implementation-red-01.log` | 首次测试有缺少合成 raw document_id 的夹具错误，不作为语义 red 依据。已修正测试输入。 |
| `implementation-red-02.log` | **未修改生产代码**时 12 failed / 11 passed；直接复现官方 7+1 unknown、关系变体、误解并列主体、附属修订/日期及年度供证缺口。 |
| `implementation-green-01.log` | 初版 owner 与原 selection 共 108 passed。 |
| `implementation-red-03.log` | 补同年同财期引用反例，1 failed / 15 passed；修复为保持 unknown。 |
| `implementation-red-04.log` | 真实 Fs 可选分类为空的 owner 反例：3 failed / 4 passed。重解析和本地年度供证仍误用完整标题，随后改为同一主体。 |
| `implementation-green-02.log` | 旧测试在替换 commit 时绕过事务清理，发生测试锁等待；该进程已精确终止（130）。改为在真实 create_source_document 边界注入发布失败，使生产 rollback 实际执行。该轮不作 pass。 |
| `implementation-green-03.log` | 修改故障注入位置后，专项 30 passed；最终范围已由后述 294 项重新覆盖。 |
| `implementation-pyright-01.log` | 测试 raw JSON 使用了错误的同名 JsonValue 契约，1 error；已改为 provider 的严格类型，后续全库为零。 |
| `snapshot-isolated-validation-01.log` | 临时脚本首次缺少测试包搜索路径，未触及生产 base。后续显式 `PYTHONPATH="$PWD"` 真正完成隔离验证。 |

最终测试覆盖官方完整 raw、新旧七份候选逐项相等、繁简/空白/年份平移、并列和残缺关系、同年同财期引用、主体与附属修订/选优、分类冲突、范围年/坏日期/多日期、引用日期不泄漏、年度供证、真实 Fs 转换/发布失败和取消后重试、七份 meta/revision/primary/资产保全、增量幂等、同 v3 重解析及可选分类缺失。既有三个月缺证/冲突、英文年度与窗口行为随关联 owner 套件实际运行。

## 最终源码验证

均在仓库根目录 `source .venv/bin/activate` 后真实运行；最后一轮源码对应下节最终 SHA，未用计划阶段基线代替。

```bash
python -m pytest tests/fins/test_hk_report_title_scope.py tests/fins/test_cn_report_selection.py tests/fins/test_hk_period_evidence.py tests/fins/test_f5_storage_calendar.py tests/fins/test_f5_workflow_rebuild.py tests/fins/test_hk_period_rebuild.py tests/fins/test_hkexnews_downloader.py -q --timeout=90 --cov=dayu.fins.pipelines.cn_report_selection --cov=dayu.fins.pipelines.hk_download_rebuild --cov-report=term-missing --cov-report=json:workspace/tmp/hk-9633-period-20261019/implementation-coverage-03.json --cov-fail-under=80
python -m pytest tests/fins/test_cn_download_identity.py tests/fins/test_cn_download_workflow.py tests/fins/test_cn_download_runtime.py tests/fins/test_f5_result_contract.py tests/fins/test_download_failure_diagnostics.py tests/cli/test_fins_commands.py tests/service/test_fins_wait_adapter.py -q --timeout=90
pyright
```

| 检查 | 最终结果 | 日志 |
| --- | --- | --- |
| owner / 仓储 / provider 回归 | 294 passed，exit 0，13.30s | `implementation-tests-03.log` |
| 关联身份/workflow/runtime/CLI/Service 回归 | 730 passed，exit 0，97.29s | `implementation-associated-tests-03.log` |
| 全库 pyright | 0 errors / 0 warnings，exit 0 | `implementation-pyright-04.log` |
| 临时验证脚本显式 pyright | 两次均 0 errors / 0 warnings，exit 0 | `implementation-script-pyright-01.log`、`02.log` |
| diff 空白检查 | `git diff --check` exit 0 | 交回前再次核验 |

测试各有三条既有 edgar deprecation warning；pyright 仅提示可用新版本，没有类型告警。未扩展为全库 pytest，已运行计划要求的受影响集合。

逐修改生产文件覆盖率：`cn_report_selection.py` **311/333 = 93.3934%**；`hk_download_rebuild.py` **89/98 = 90.8163%**，均无 excluded lines。JSON 明细 `implementation-coverage-03.json`，总阈值没有替代逐文件核对。

## 固定入口真实增量与版本区分

`snapshot_history.py` 始终通过 storage 读取完整 meta/revision/primary 及每份实际文件的 size/SHA，不拼受管财报路径。已先在隔离真实 Fs 中分别验证七份和八份快照、读取不写入、原七份逐项相等。最终版本隔离结果位于 `snapshot-isolated-20261018T165628963359Z/`，命令为：

```bash
PYTHONPATH="$PWD" python workspace/tmp/hk-9633-period-20261019/validate_snapshot_implementation.py
```

日志 `snapshot-isolated-validation-04.log`；内部快照命令、起止时间、exit/stdout/stderr 在 `seven-receipt.json` / `eight-receipt.json`。前轮隔离结果另存，未覆盖。

生产 base 在仓库外，实际执行前按现有授权申请了工具权限，没有改 base 或绕过沙箱。每轮均新目录，固定实际 argv 为：

```text
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli --base /Users/leo/workspace/portfolio-manager-v2/workspace --log-file <该轮全新目录>/dayu.log download --ticker 9633 --start 2025-01-01 --end 2026-10-19
```

未传 forms/overwrite/rebuild。每轮的 `command.json`、`result.json`、`exit-code.txt`、stdout/stderr/dayu.log、从同一 CLI 诊断物理行提取的 `diagnostics.json`、history-before/after、entry-before/after 及原失败六文件 before/after 哈希均保留。helper 子命令也有独立 argv/时间/exit/双流记录。时间以下为 UTC（上海加八小时）。

| 新目录 | 实际开始 → 结束 | exit | discovered / downloaded / skipped / failed / uncertain | 源码版本 |
| --- | --- | --- | --- | --- |
| `incremental-implementation-20261018T165408495106Z` | 16:54:10.559089 → 16:55:38.734346 | 0 | **8 / 1 / 7 / 0 / 0** | V1：完整标题主体修复，随后补本地缺分类路径 |
| `incremental-implementation-20261018T165657448476Z` | 16:56:59.552192 → 16:57:16.136737 | 0 | **8 / 0 / 8 / 0 / 0** | 最终 V2 |
| `incremental-implementation-20261018T165742058178Z` | 16:57:43.991185 → 16:57:59.963819 | 0 | **8 / 0 / 8 / 0 / 0** | 最终 V2，同版本再次重复 |

**不把首轮真实转换标为 V2 执行。** V1 可取回源码保存在 `source-first-incremental/`。V1→V2 只补本地可选分类缺失时的主体输入及对应 import/docstring；首轮实际七份、目标和后两轮八份的来源分类均非空，`or` 右侧新逻辑不在这些来源上执行；ordinary download 不执行 rebuild。主体识别、candidate/identity/publication/Docling 路径没有改变。最终源码 owner/Fs 回归已实际重跑；最终固定 CLI 又两次实跑，完整八份持久状态及转换资产逐字节相等。由此复用的是未改转换链的真实证据，未声称 V2 强制重新下载或重新转换。

三轮每轮源码前后完全一致；最终两轮全部 177 个实际导入 Dayu/入口文件指纹相同。固定 CLI shebang 和实际解释器均为本仓库 `.venv/bin/python`。完整指纹见各轮 `entry-*.json`，包括修改模块；无新增生产模块。

| 生产文件 | V1 SHA256 | 最终 V2 SHA256 |
| --- | --- | --- |
| `cn_report_selection.py` | `3a2eceee6be49cb7cbd55e7a999e6561d2b9d9c048c1542aa5a8d85e643667eb` | `9816248d2a21ac9bae44fc2da49a49d7ea29dc29ce53e135f311ba76e4701c52` |
| `hk_download_rebuild.py` | `a880ad160adfa507c5489db985769680f8b3919f9f6b0ff75daf743713e1da47` | `ba8bd773bfc568356878f518ca5b144008fe7c3babc591f351aa1fcb1712a5b9` |

最终源码/测试/README/fixture 可取回副本为 `source-final/`，精确清单见 `final-source-manifest.json`；最终新测试 SHA256 为 `31ee427f63c602199bf65d13315e508b61e6b6a6c754fd1e2b28f5455bd1cc01`。`final-tracked-delta.patch` 是 tracked delta，新增测试和 fixture 的完整内容另在 `source-final/`，不将该 patch 称作包含 untracked 文件的完整 diff。

## 仓储事实与真实 Docling 核回

首轮 seven→eight，新增唯一 source `12345879`，document ID 为 `fil_cn_4c886e0d7f2b4df8ccb23c411e5b0325a447c8fa`，internal ID 为 `cn_4c886e0d7f2b4df8ccb23c411e5b0325a447c8fa`。来源标题/分类/URL/ID 对应正式原行，2026 H1、覆盖 `[H1]`、amended=false，两日期字段均 null。source completion、summary H1 及 coverage 一致；通过完整性 owner 核查 shared manifest 与 canonical meta 投影一致。

最终八份完整 meta/revision/primary/逐文件 SHA 均在最后一轮 `history-after.json`，不是只保存数量或部分字段。摘要如下；全部 amended=false、COMPLETE：

| source_id | 财年/身份 | coverage | report_date |
| --- | --- | --- | --- |
| 11584123 | 2024 Q4 | FY,Q4 | 2024-12-31 |
| 11644015 | 2024 FY | FY | null |
| 11809841 | 2025 Q2 | H1,Q2 | null |
| 11851176 | 2025 H1 | H1 | null |
| 12065001 | 2025 Q4 | FY,Q4 | 2025-12-31 |
| 12110702 | 2025 FY | FY | null |
| 12298462 | 2026 Q2 | H1,Q2 | null |
| 12345879 | 2026 H1 | H1 | null |

首轮原七份的 document/internal identity、全部 provenance、first_ingested/created/updated、revision、primary、所有原件与派生资产 bytes/hash **完整相等**。后两轮八份 before=after；跨三轮前后衔接的完整记录也相等。原失败目录六文件每轮 before/after SHA 都等于 control，不覆盖原失败、历史身份或七份资产。

`verify_assets_implementation.py` 经 storage snapshot 两次回读，最终结果位于最后一轮 `assets-verification.json`，日志 `assets-validation-02.log`：

- 官方 PDF：**2,467,514 bytes / 86 页**，SHA256 `01725ee4d55c352e89fa83eaf1b3e62bc82d7b98be596e78cdde63c64a76637b`，与计划取得的公开原件相同。
- 实际 primary 为 `fil_cn_4c886e0d7f2b4df8ccb23c411e5b0325a447c8fa_docling.json`：**4,383,071 bytes**，SHA256 `a6e55929feeb139866888c901b4b1c6341a010b91461d2505501db43c91db398`。经真实 `DoclingDocument.model_validate_json` 校验，**86 页 / 1,373 texts / 42 tables / 1,303 body children**；不是合成测试的 18-byte JSON。
- 八份来源的真实完整性均 COMPLETE，target 唯一、ingest_complete=true。实际转换开始/结束、两文件提交及各 skip 在首轮 dayu.log 中可核；没有以 exit 0 或 summary 单独充当完成证据。

跨轮审计为 `implementation-evidence-audit.json` / `.log`，核对所有实际入口指纹与可取回源码、原六文件哈希、各轮 full snapshot 及预期真实计数。最终证据清单为 `final-evidence-manifest.json`。

## README 决策

已读取 `dayu/fins/README.md` 的 Agent 更新约束和 `tests/README.md` 的现有写作职责。Fins README 只补已实现的主体/引用作用域、同源消费及 unknown 边界；tests README 只补实际存在的 fixture 和 owner/Fs 回归。无用户入口参数、工作流、目录位置或分层变化，根 README 与 `dayu/README.md` 不触发实际修改。

## 风险、未覆盖与交回

| 项目 | 分类 / owner / destination |
| --- | --- |
| 主体作用域、amended/选优/年度/日期/缺分类本地重解析；真实增量与七份保全 | **fixed in current slice**；本实施者；上述最终源码、测试与仓储证据已闭合，父总控完整审核核验。 |
| 任意复合标题、混合/多语言关系语法、未知历史 amended、PDF 自动日期/财期、过渡或 52/53 周财年 | **assigned to later work unit**；Fins selection 维护方；将来有明确证据与授权的独立 work unit。本 slice 不新增上述承诺，不扫描其它公司。 |
| 统一 unknown 重试提示仍可能只提示补年度资料 | 沿用 control 的 **assigned to later work unit / deferred-with-owner**；Fins 维护方；后续诊断文案 work unit，未改 runtime/展示契约。目标本次已成功，不影响本 slice 验收。 |

未执行全库 pytest、显式生产 rebuild、overwrite、历史批量修复或最终源码的强制重新转换；后三者未获本任务授权且无需用其证明增量恢复。真实转换的 V1 / 最终 V2 证据适用边界已明确，不重新标记旧版。无当前实现或验证阻断。

下一入口为 **code review：由父总控派发指定双路完整 deepreview**，审核最终组合 delta 及 V1→V2 证据适用性；之后必要 fix/re-review、commit/draft PR 与真实 head/base 核对均由总控继续。本实施者到此退出，不自称审核或 PR 已完成。
