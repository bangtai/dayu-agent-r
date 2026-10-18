# HK 年度证据 code finding 修复记录

## 裁决、范围与版本

- 已完整读取根 `AGENTS.md`、[control 最新完整裁决](hk-period-evidence-20261018-control.md)、[DS code review](code-review-20261018-225801.md)、[MiMo code review](code-review-20261018-231300.md) 和[实现记录](hk-period-evidence-20261018-implementation.md)。control 明确进入 **fix → 受影响面双路 re-review**，仅接受 DS code finding 1，严重度由总控裁决为中；MiMo 无 finding，不以其 pass 覆盖 DS 反例。
- 仅修年度准入绕过统一财年歧义校验的问题。分支 `fix/hk-period-evidence-20261018`，base／HEAD 仍为 `dbc9483df8a5cecfecc20cc61333eff0319e5982`；没有新日历支持、schema／版本／身份／调用方变化，也没有委派、通知、commit／push／PR／merge。
- 旧被审生产 SHA256：`7db0e55c452ad2e69e941ff4d631d52ee4cb6f9bcd9eabf08afff82fa6ecef3d`。**新版生产 SHA256：`063216ce51738cf6a608d1ff537f36fabfbeb875b3f169b824e3eaf6dc812fdf`**；[code-fix-code-fingerprint.json](../../workspace/tmp/hk-period-evidence-20261018/code-fix-code-fingerprint.json) 的八文件聚合指纹为 `cbfe57f9e798007b4d8ef8beb5d11c2b31cbc4ba6ed334f1541e629ad65d99f0`。本轮最终测试、全项目 pyright、fresh 快照和真实 CLI 的逐文件代码指纹一致。
- 只新增 `code-fix-` 前缀证据和 `code-fix.coverage`，不覆盖旧证据；未读取凭据、`.env`、模型配置、其他任务或无关文件。下文 `E/` 均指 `workspace/tmp/hk-period-evidence-20261018/`。

## Accepted finding 的实际修复

| finding／裁决 | 直接问题、修复与验证 | 状态／owner／destination |
| --- | --- | --- |
| DS code finding 1：accepted | `hk_annual_end_date` 原先只消费局部期间分类，能从统一 resolver 已拒绝的财年区间／标签冲突／多年份标题取得年度日期。现在以空外部年度集合调用同一个 `resolve_hk_report_period`，完整确认后才接受 FY/Q4 和唯一直接截止日。没有复制 regex 或另造冲突规则 | 代码修复及本轮验证完成，**待双路受影响面 re-review／总控裁决**；`cn_report_selection` owner |

动机有直接证据：新增五个 owner 反例在旧生产代码上全部失败，统一 resolver 对它们已返回 None，而旧年度入口仍供证。修复落在年度准入 owner，未改下游或测试替身以补偿。

先确认无递归：`resolve_hk_report_period` 只调用既有日期／期间／财年 helper；其 `_infer_hk_fiscal_year → hk_fiscal_calendar.annual_end_dates` 是纯标题日期逻辑，不调用 `hk_annual_end_date` 或 selection。新调用链为 `hk_annual_end_date → resolve_hk_report_period → 既有纯 helper`，不自借年度证据。唯一基础 category-first 家族与仅服务未决投影的标题门槛均未改；两个真实年度 raw 不会重新被标题信号拒绝。

新增五个反例覆盖完整／简写 `2024/2025`、`2024/25` 财年区间，英文 `FY2025` 与 2024 截止日冲突，中文显式财年冲突，以及直接日期之外的比较年度歧义。每例经过真实 `hk_annual_end_date` 和 selection：不供年度日期，真实三个月来源 `11655015` 保持 `uncertain_hk_period`、`existing_document_id=None`，无候选且 HEAD 零调用；没有向 fixture／入口注入已知年结日。

相对已审版本的限定改动见 [code-fix-delta.diff](../../workspace/tmp/hk-period-evidence-20261018/code-fix-delta.diff)，SHA256 `cd002074b58c4d2fe573d737aae3dbae5d0e1dd29725b763dd61c4931eb719de`。除生产 owner 和新增反例外，仅最小更新两个 README：已重新读取维护约束，Fins README 明确年度源遵守同一财年歧义／标签校验；tests README 说明该反例覆盖。根 README、`dayu/README.md` 无用户入口或架构变化，不触发实质更新。官方 fixture 四文件保持原 hash，原实现记录也逐字保留，不重标旧结果。

## 本轮实际测试与类型检查

所有命令均经 `E/run_capture.py` 留存完整 argv、cwd、HEAD、产品文件 hash、UTC 起止、stdout／stderr 和真实 process exit。下面列出实际子命令；旧日志不被覆盖。

```sh
source .venv/bin/activate
pytest -q tests/fins/test_hk_period_evidence.py -k ambiguous_annual_source
# 修复前：code-fix-owner-before，exit 1，5 failed / 16 deselected

source .venv/bin/activate
pytest -q tests/fins/test_hk_period_evidence.py
# 修复后：code-fix-owner-after，exit 0，21 passed

source .venv/bin/activate
COVERAGE_FILE=workspace/tmp/hk-period-evidence-20261018/code-fix.coverage pytest -q \
  tests/fins/test_hk_period_evidence.py tests/fins/test_cn_report_selection.py \
  tests/fins/test_f5_storage_calendar.py tests/fins/test_f5_workflow_rebuild.py \
  tests/fins/test_hkexnews_downloader.py tests/fins/test_cn_download_workflow.py \
  tests/fins/test_f5_result_contract.py tests/cli/test_output.py \
  tests/fins/test_cn_download_identity.py tests/fins/test_hk_period_rebuild.py \
  --cov=dayu.fins.pipelines.cn_report_selection --cov-report=term-missing \
  --cov-report=json:workspace/tmp/hk-period-evidence-20261018/code-fix-coverage.json

source .venv/bin/activate
pyright

source .venv/bin/activate
pyright --project workspace/tmp/hk-period-evidence-20261018/code-fix-scripts-pyrightconfig.json
```

| 新证据前缀／文件 | 实际退出／结果 |
| --- | --- |
| `code-fix-owner-before` | exit 1；五个新增反例复现年度入口缺口；失败原文保留 |
| `code-fix-owner-after` | exit 0；21 passed，原 16 个正负例全部保留 |
| `code-fix-tests-final` | exit 0；**562 passed**，19.00s；3 项既有 edgar DeprecationWarning |
| `code-fix-coverage.json`／`code-fix.coverage` | 完整生产文件 301 条语句、278 覆盖、23 未覆盖、0 排除，**92.3588%**，达到 >=80% 目标；未过滤生产行 |
| `code-fix-pyright-final` | exit 0；全项目 0 errors／0 warnings／0 informations |
| `code-fix-scripts-pyright-final` | exit 0；本轮捕获器／仓储快照／核对脚本显式 strict 检查，0 errors／0 warnings／0 informations |
| `code-fix-verification` | exit 0；CLI、十一份完整观察、代码版本与旧证据保全断言全部通过 |

新版重新验证了两条真实年度日期、27 条官方 raw 的 11 确定／0 未决选择、两 Q1、组合分类、独立 unknown 门槛、本地来源资格、隔离真实 Fs 从 unknown 到年度供证再 fresh 发布两 Q1、失败重试和幂等，以及同 v3 重新投影。该 fresh 发布用例与旧真实首次发布证据的层级不同：其网络输入为正式官方 raw，转换资产明确为合成；本轮没有谎称重新完成生产 base 的首次下载。

## 新旧真实证据的适用性与本轮增量

旧 `validation-01` 的 **2 downloaded／9 skipped** 和旧 `validation-02` 的 **11 skipped**，只属于旧生产 SHA `7db0e55c…ef3d`。本次只使统一 resolver 已判歧义的年度输入不能供证；官方两条年度 raw 没有该类区间／标签／年份冲突，空外部年度解析仍得到相同 FY/Q4 投影和直接日期。故旧官方身份／原件／真实 Docling／首次发布观察可作为历史证据复用，不能当新版首次发布结果；新版另外用上述官方 raw 与 fresh Fs 测试，以及下面实际增量补验。

本轮先以仓储协议保存当前十一份 fresh 快照，再实际运行一次完全相同业务参数的普通增量，仅使用新的日志落点：

```sh
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli \
  --base /Users/leo/workspace/portfolio-manager-v2/workspace \
  --log-file /Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/code-fix-validation-01-dayu.log \
  download --ticker HK:00388 --start 2025-01-01 --end 2026-10-18
```

- 实际 UTC：**2026-10-18 15:18:50.833141 → 15:19:13.256140**，process exit **0**；诊断为 **11 discovered／0 downloaded／11 skipped／0 failed／0 rejected／0 uncertain**，missing=[]，terminal=succeeded。无 forms／overwrite／rebuild，未删除或回滚真实来源重造下载计数。
- 原始命令／进程／stdout／stderr／dayu.log 和从原通道解析另存的完整诊断，均为 `E/code-fix-validation-01-*`。公开诊断保持既有 10 行＋omitted_count=1；两 Q1 的公开财期／日期／coverage 与仓储一致，全集补核了 11 条实际 skipped 完成事件及全部仓储观察，未改公开 schema。
- 前后快照命令均先激活 `.venv`，以 `PYTHONPATH=. python E/storage_snapshot.py code-fix-before`／`code-fix-after` 实际执行，均 exit 0。指定 base 的正常读锁及 CLI 写能力经精确权限执行；没有手改文件或绕锁。
- [code-fix-verification.json](../../workspace/tmp/hk-period-evidence-20261018/code-fix-verification.json) 证明前后十一份与旧 `validation-after-02-storage.json` 完全相同：当前公共 source meta、identity、revision、内容版本、fingerprints、时间／元数据、声明／实际资产 hash 和 processed 事实保持；两目标仍分别为 2025／2026 Q1、2025-03-31／2026-03-31、[Q1]、COMPLETE。
- `E/code-fix-protected-before.json` 的 105 项旧证据／上下文文件全部保持原 hash；旧 review manifest／product diff／冻结源码快照逐文件核对不变，原失败 download-02 七文件也未变。原实现记录 SHA 仍 `f92534e2…4e5f10`。这是当前公共仓储事实与明确文件保全核对，**没有冒称枚举或审核内部历史 revision 归档**。

本轮没有真实运行失败需要隐去或重造成功；唯一预期失败是修复前五个新增反例的 red 轮，完整保存。真实增量无漂移且全部跳过，不需要再次运行以制造额外结果。

## 风险分类与待复审事项

| 项目 | 分类／实际状态 | owner／destination |
| --- | --- | --- |
| Accepted DS finding 1 | fixed in current slice：代码与上述验证已完成，尚未复审放行 | Fins 财期 owner／总控 → DS、MiMo 双路受影响面 code re-review；不自行宣布 code-review-pass |
| 官方正例、新版 fresh 发布与真实增量、旧证据适用性 | fixed in current slice：新版已重新验证正例和正常增量；旧真实首次发布明确绑定旧 SHA | 本 work unit → 双路复审核对新旧版本／证据关系 |
| 23 条未覆盖语句、真实 base 未注入取消／转换失败、公开诊断有界 | verification limitation：完整文件覆盖达标，失败／取消复用受影响隔离回归；没有新增穷尽或真实破坏试验承诺 | 最终 reviewer 核对本修复适用性；后续修改对应 owner 时补必要测试 |
| 内部历史 revision 归档枚举 | assigned to later work unit，遵守 control 的独立历史观察裁决 | storage owner → 有明确契约／需求时另验，本轮不扩展 |
| 52／53 周、过渡期、年结变更、全历史迁移、无实际证据的 provider 异常 | assigned to later work unit，仍不新增支持或来源调查 | Fins 财期／仓储 owner → 有具体需求与证据的后续 work unit |
| TLS／沙箱／域名及调用方 | 非目标；未调查、未修改 | 原报修方／调用方 owner → 各自后续范围 |

**下一入口：交付总控，待双路受影响面 re-review 与总控裁决；无 commit／push／PR／merge，不自行宣布任务完成。**
