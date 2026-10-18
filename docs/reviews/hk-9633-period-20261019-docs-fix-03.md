# 9633 文档承诺修正 docs-fix-03

状态：**CR-3 文字修正及验证完成，待 root 双路核文档、AST 与证据适用性**。control 末节已明确 re-review-02 双路收齐、CR-1/CR-2 核销并进入 docs-fix-03，才执行本轮。分支为 `fix/hk-9633-period-20261019`，HEAD/base 为 `705c2dc2f6b4491edda0c6f0d2a4b1f8e2bf458d`。

## 裁决与三文件 delta

动机成立：竞争主体检测只有有限中文词形和连接关系，不能承诺所有中文业绩主体一律未知。本轮按 root 对 CR-3 的裁决收窄说明，不扩语法、不改执行逻辑或测试行为，不重新打开已核销的 CR-2。

| 文件 | 本轮唯一变化 |
| --- | --- |
| `dayu/fins/README.md` | 按实际常量列出报告、季度、业绩词形与“及/與/与/和”关系；明确未支持词形/分隔符的复合标题不保证识别为竞争主体，仍可能按既有分类、年份等约束确认。 |
| `tests/README.md` | 收窄为现有测试覆盖的组合，区分识别词形范围与测试实际覆盖，明确没有穷举全部组合或所有中文业绩主体；不声称未支持输入一律未知。 |
| `cn_report_selection.py` 的 `hk_report_subject_title` 中文 docstring | 同步上述有限集合及剩余风险；未改常量、正则、表达式或注释。 |

语义 owner 仍为 Fins selection 的统一主体投影。完整目标关系解析、普通标题、已支持并列主体、独立补充规则及所有消费者均不变；没有通过文档修正引入行为变更，也未新增测试固化缺口。

已先核 README 职责：Fins README 只说明当前能力与稳定契约，tests README 只记录现有测试事实。本轮属于各自职责；未来单元及审核状态只记录于本报告，不加入 README。根 README 与架构 README 的入口、工作流、层次或装配均无变化，无需更新。

## AST 与字节不变证明

以下路径均相对 `workspace/tmp/hk-9633-period-20261019/`：

- 修改前九份 live 源码逐一等于 `fix-02-final/manifest-final.json` 及其 source；本轮三文件旧快照另存 `docs-fix-03-final/before/`，不覆盖 fix-02。
- `docs-fix-03-final/baseline.json` 保存修改前指纹；`ast-and-byte-proof.json` 保存逐模块结果。对 `dayu/`、`tests/`、`utils/` 的 **819 个 Python 模块**分别解析 AST，删除模块、类、同步/异步函数首条字符串 docstring，再对 `ast.dump(include_attributes=False)` 计算并比较 SHA256，**819/819 全等**。selection 只有 `hk_report_subject_title` 的 docstring 改变，其他 docstring 未变。
- 基线覆盖 952 个生产/测试/fixture/配置及约束文件；文件集合无新增/删除，除上述三处外 **949 个文件字节不变**。测试文件、fixture、rebuild、依赖声明及配置均不变；587 项已安装依赖元数据的文件集合及字节指纹也不变，未安装依赖。control 与 0135 control 字节保持。
- fix-02 九文件中的另外六份（rebuild、标题测试、四份 fixture）与 fix-02 字节全等。相对 fix-02 的三文件完整差异保存在 `docs-fix-03-final/doc-only-delta.patch`；最终九份全文在 `docs-fix-03-final/source/`。

| selection 指纹 | SHA256 |
| --- | --- |
| fix-02 原文件 | `d807933aafbd7de76221f833dfcec2861ba0f3201b6db1ca2f024a81e8b94663` |
| docs-fix-03 最终文件 | `ec29c01d1ef818261a76ebc5f22aa81d74e3977d29c3f809472f94cda9a0c0c6` |
| 两版去 docstring 后 AST（相同） | `5e6e3d6b15b877e5709c6b9ecb1f01c76bee8bcd2b0f71dee74d916f5ae4a9eb` |

## 验证与复用边界

所有测试及类型检查均先 `source .venv/bin/activate`。每项实际 argv、起止、exit、selection SHA 和独占日志保存在同名前缀的 `*-command.json` / `.log`。

| 回执前缀 | 命令 / 实际结果 |
| --- | --- |
| `docs-fix-03-title-tests-01` | `python -m pytest tests/fins/test_hk_report_title_scope.py -q --timeout=90`：**139 passed**，exit 0；仅三条既有 edgar 弃用提示。 |
| `docs-fix-03-pyright-01` | `pyright`：全库 **0 errors / 0 warnings / 0 informations**，exit 0。 |
| `docs-fix-03-scripts-pyright-01` | 最小复用的 check/incremental runner 与既有 snapshot/entry 工具显式 pyright：0 错误/告警，exit 0。 |
| `docs-fix-03-diff-check-01` | `git diff --check`：exit 0。 |

fix-02 的 **398 owner + 227 pipeline = 625 项**当前行为证据按上述 AST、测试/fixture、依赖及配置不变复用。本轮 139 项是其中子集，其他 486 项未重跑；不把旧 625 计作本轮执行。逐文件覆盖率沿用 fix-02 的 93.43% / 90.82%，没有重新生成覆盖率。

未变 runtime/result/diagnostics/CLI/Service 等关联面继续沿 fix-02 已审适用性复用 `fix-01-associated-tests-01.log` 的真实 **730 passed**，不声称本轮重跑730。旧复审 upload CLI 四项失败及 root 同版四项复跑通过仍按 control 保留，不合并成单次执行、不扩展调查。上述 owner、pipeline、coverage、730 日志与回执已按 fix-02 manifest 重算指定 SHA，清单引用原文件，不复制历史报告。

## 唯一一次正式固定入口普通增量

正式目录：`docs-fix-03-incremental-20261018T193331696826Z/`。实际命令：

```text
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli --base /Users/leo/workspace/portfolio-manager-v2/workspace --log-file /Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-9633-period-20261019/docs-fix-03-incremental-20261018T193331696826Z/dayu.log download --ticker 9633 --start 2025-01-01 --end 2026-10-19
```

UTC **2026-10-18 19:33:33.536447 → 19:33:50.916382**，exit **0**；**8 discovered / 0 downloaded / 8 skipped / 0 failed / 0 rejected / 0 uncertain**，stderr 为空。未传 forms/overwrite/rebuild，未删除资产重造首轮。argv、起止、exit、双流、dayu.log 与同一物理诊断行提取的 diagnostics 全部保存。

- 复用已审 `snapshot_history.py` 与 `verify_entry_implementation.py`；八份完整 meta、revision、primary 与逐资产大小/SHA 在本轮前后及相对 fix-02 完全一致，快照只差采集时间；原失败六文件哈希全部保持。
- 固定解释器/shebang 指向本仓库 `.venv/bin/python`。177 个实际入口/Dayu 文件前后相同且与 live 指纹一致；相对 fix-02 只有 selection 的 docstring 文件 SHA 改变，可执行 AST 不变。
- source `12345879` 仍为原身份、2026 H1、coverage `[H1]`、amended=false，report_date/report_date_source 均 null，raw 标题/分类/URL/披露日及历史七份均保持。
- 本轮 storage 完整快照实际读取并校验全部资产字节；目标 PDF 为 2,467,514 bytes / SHA `01725ee4d55c352e89fa83eaf1b3e62bc82d7b98be596e78cdde63c64a76637b`，Docling 为 4,383,071 bytes / SHA `a6e55929feeb139866888c901b4b1c6341a010b91461d2505501db43c91db398`。页数、结构及真实转换事实复用 fix-02 `assets-verification.json` 与原 V1 转换证据；**首次真实转换已在 V1 完成，本轮只有重复增量，没有重新转换或渲染 PDF，也不把首次转换列作未来义务**。

前置失败原样保留：`docs-fix-03-incremental-20261018T193255993276Z/` 的 snapshot-before 在 storage 取锁时 exit 1，尚未生成正式 command.json、未执行 download；runner 失败日志为 `docs-fix-03-incremental-runner-01.log`。随后按用户授权使用目录权限，另开全新目录/日志完成上述唯一正式 download，runner-02 exit 0。没有调查 TLS、沙箱或域名，也未改 helper 的失败语义。

完整离线核对见 `docs-fix-03-final/entry-and-reuse-audit.json`。最终 `manifest-final.json` 只收集已经关闭的证据日志、九源码及报告；不 hash 自身、活动 runner 日志或后置核验日志，无循环 hash。

## 风险 owner / destination 与下一入口

| 项目 | 状态、owner / destination |
| --- | --- |
| CR-3 过度文字承诺 | writer 已修正，**fixed in current slice**；owner 本 work unit/root，destination 双路文档、AST、入口及证据适用性复审；尚不自行宣称 review pass。 |
| 年度/半年度业绩、时长加业绩、首季、简称省略“告”、阿拉伯序数、顿号等未支持形态 | 能力缺口仍未修复，**deferred-with-owner / assigned to later work unit**；owner Fins selection 维护方，destination 后续“HK复合标题词形覆盖”独立单元。仍可能按分类确认，不把文案修正当作行为修复；未创建外部 issue。 |
| 真实空分类样本、未支持补充关系/任意自然语言附件及复合多语言、中文数字完整截止日、PDF 解期、52/53 周等 | 沿 control 既有边界，**assigned to later work unit**；owner Fins selection，destination 有官方样本和明确范围的后续单元。 |
| unknown 提示细分、生产 rebuild/overwrite 或历史批处理 | 沿既定延期；owner Fins 维护方，destination 后续诊断文案或独立授权单元。 |

本轮未派 agent、未外发、未 commit/push/merge、未操作 PR203 或 0135，未修改 control。到此 writer 结束，由 root 按 control 并行双路核对文档与 AST/验证适用性；未覆盖能力继续明确保留。
