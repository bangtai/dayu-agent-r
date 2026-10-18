# HK 财期证据计划修正记录

- 日期／work unit：2026-10-18／`hk-period-evidence-20261018`；分支 `fix/hk-period-evidence-20261018`；生产 base／HEAD `dbc9483df8a5cecfecc20cc61333eff0319e5982`。
- 依据：[control 当前裁决](hk-period-evidence-20261018-control.md)、[DS 完整审核](plan-review-20261018-220929.md)、[MiMo 完整审核](plan-review-20261018-221727.md)。已读根 `AGENTS.md` 和原计划；只修改 [plan](hk-period-evidence-20261018-plan.md) 并新增本记录，未改 control、原审核、生产／测试代码或 README。
- 原 plan SHA256：`9bb2a20823c4a54ba22c1e13361e81ec2271f7463ac9781b4d6f12fdc4e02573`。
- 新 plan SHA256：`c60c1f4f96f3a6cf3dcb3bd8d6fbc518cc904c028cecde8a22e3a64f5c5a16df`。

## 修正项与裁决落实

| 项目／裁决 | 计划修正与后续验证 | 分类／owner／destination |
| --- | --- | --- |
| DS finding 1：accepted | 共享唯一 category-first 基础家族与既有期间分类；年度资格以已确认 FY/Q4 投影、唯一直接截止日及既有冲突规则判断，不受仅标题信号的未决资格否决。未决资格保留原标题条件，明确其不是第二套家族真源；实现者可最小拆 helper。补 owner 断言：results＋无标题信号且不可解仍忽略；已支持报告标题缺依据仍 unknown；纯股息／董事会忽略；两年度 raw 供证、两 Q1 确认 | fixed in current slice（仅计划已补，待复审／实现）；`cn_report_selection` owner → 双路受影响面复审、owner 回归与最终 code review |
| 组合分类：按总控有界准入裁决 | 官方末期业绩可与股息组合，标题唯一明确年度截止日且无中期／期间冲突时供日期；标题含股息不自动否决。新增组合年度正例、缺日／多日及冲突反例，保留 Q4／[FY,Q4]，不冒充完整 FY 年报；不以纯股息测试替代组合测试 | fixed in current slice（待实现验证）；Fins 财期 owner → 组合 contract 回归／最终 code review |
| 版本 open question：保持现有版本 | 日期／季度算法、366 天、持久 schema、身份与 skip 语义不变，目标两来源尚未入库；保持下载版本及 hk-period-v3。补隔离断言：同 v3 来源仍经原始年度输入和新准入重新投影，不因版本缓存跳过；实际代码身份记录 Git HEAD／证据 hash，不运行真实 base rebuild | fixed in current slice（待验证）；rebuild／财期 owner → 隔离回归／最终 code review |
| MiMo finding 1：rejected-with-reason | 遵从 control 对同一日志 SHA 的字节复核：splitlines 含 CR 计数为 249／510／511，LF 为 243／500／501；补分行口径及 document_id＋download_committed／汇总事件定位，不把它认定为证据或版本错误 | 文档可追溯性澄清，待受影响面复审；原日志／manifest 不改 |
| 外部错误分类／日期污染：后续 work unit | 当前无实际 provider 异常证据；保留现有日期／冲突／无依据失败关闭和本轮冲突反例，不新增纠错框架 | assigned to later work unit；Fins 财期 owner → 取得具体来源证据后另开 work unit |
| 真实 CLI、fresh 快照、Docling、fixture：本 slice 未完成项 | 保留经仓储协议取 fresh 快照、fixture provenance 固化、固定 CLI 同 base／ticker／filing-date 窗口两次普通增量及幂等／失败诊断验收 | fixed in current slice（未执行）；implementation／validation → 总控验收，不能以计划审核代替 |

## 验证适用性与剩余风险

- 本轮仅修 Markdown：核对裁决覆盖、历史记录与待执行事项、文档空白、分支／HEAD 和 SHA256；control 与两份审核 hash 未变，生产／测试无改动。未重新读取巨大日志／PDF、未重开取证或全量基线；未读取 `.env`、凭据或用户模型配置。
- pytest／pyright 不在本次文档修正轮重跑；原 232 测试及类型检查仅保留为原 plan 阶段未改码基线。实现后的 owner／链路测试、同 v3 回归、全项目 pyright 和覆盖率要求仍按修订计划执行，当前均不能声称通过。
- 目标／非目标、一个 implementation slice 和真实同参两次 CLI 验收不变。生产修复、fixture、fresh 仓储快照、Docling／真实发布与幂等尚未验证；外部变化须保留实际结果交总控裁决。52／53 周、过渡期、跨历史迁移及 TLS 调查继续归后续 owner，本轮不扩展日历、原因码、PDF 生产解析或调用方。
- 未执行真实发布／真实 base rebuild，未 commit／push／PR、未通知他人、未再委派。

**状态：plan fix 文档已交付，待 mimo-flash／ds-flash 双路受影响面 plan re-review 及总控裁决；未自行通过 gate，未放行 implementation。**
