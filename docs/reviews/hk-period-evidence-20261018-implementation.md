# HK 财期证据单 slice 实现与验证

## 授权、版本与交付状态

- 已完整读取根 `AGENTS.md`、[control 当前裁决](hk-period-evidence-20261018-control.md)、[计划](hk-period-evidence-20261018-plan.md) 及 control 指定的两路受影响面复审。control 的最后裁决为 **plan gate pass，放行一个 implementation slice**；原计划末尾的待审状态作为历史保留，未擅自修改。
- 计划 SHA256：`c60c1f4f96f3a6cf3dcb3bd8d6fbc518cc904c028cecde8a22e3a64f5c5a16df`。分支 `fix/hk-period-evidence-20261018`；base／测试／两轮真实 CLI 的 HEAD 均为 `dbc9483df8a5cecfecc20cc61333eff0319e5982`，代码尚未提交。
- 实际运行代码以 HEAD 加未提交文件指纹识别：[implementation-code-fingerprint.json](../../workspace/tmp/hk-period-evidence-20261018/implementation-code-fingerprint.json)，聚合 SHA256 `435bf58f5ab5afb20319df31d198b2508ea9f79d08fb055f4ff2ca926152a523`；生产文件 SHA256 `7db0e55c452ad2e69e941ff4d631d52ee4cb6f9bcd9eabf08afff82fa6ecef3d`。该清单包含八个源码／README／测试／fixture 文件，测试最终轮与两轮 CLI 的逐文件 hash 完全相同；tracked diff 另存 `implementation-diff.patch`，SHA256 `90e18cb1c57039f243c218292ef2948600d38104f35b51b67e61330c874f9e3c`。
- 未读取 `.env`、凭据或用户模型配置；未委派、通知他人、commit／push／PR／merge；未修改 control、计划或审核产物。真实指定 base 的动作仅为已授权仓储快照与两次固定普通增量，均通过正常仓储锁执行，未手改受管文件或绕锁。
- **本交付供总控进入最终 mimo-flash／ds-flash 完整 deepreview；未执行或代替该审核，未自行宣布 work unit／PR 完成。**

证据目录下称 `E/`：`workspace/tmp/hk-period-evidence-20261018/`。命令捕获器 `E/run_capture.py` 保存真实 argv、cwd、UTC 起止、HEAD、改动文件 hash、原始 stdout／stderr 和子进程退出码；没有用计划预期覆盖实际结果。

## 实际修复与边界

动机成立且 owner 明确：原年度准入把仅用于未决投影的标题信号当成家族门槛，提前丢弃已由官方分类确认的末期业绩。唯一生产修改位于 [cn_report_selection.py](../../dayu/fins/pipelines/cn_report_selection.py)：

- 抽取 `_hk_report_family`，仅从 category 判定唯一 report／results 家族，供既有期间分类与未决资格共享；缺失或冲突仍关闭。消除原 `is_hk_report_family` 混用资格的接口，不保留兼容 wrapper。
- 年度准入直接消费既有期间分类的 FY/Q4 投影和唯一直接截止日，不再经过未决标题门槛。远端、本地 COMPLETE 及 rebuild 仍使用同一 owner；未改财政日历或日期解析算法。
- `_has_hk_unresolved_report_signal` 明确只服务不可解期间的未决投影，保留原标题信号条件：results 分类但无标题信号且不可解者仍忽略；已有支持的报告标题缺依据仍 unknown。
- 官方末期业绩可与股息组合，唯一明确年度截止日且投影无冲突时供证；纯股息／董事会不供证，组合缺日、多日、坏日期或中期／期间冲突不供证。Q4／`[FY,Q4]` 不变成完整 FY 年报。
- 保留同公司、语言／窗口、366 天、无依据／冲突关闭、来源身份、原子发布、取消和版本语义。`cn_pipeline_download_v1.0.0`、`hk-period-v3` 均未改；没有公司特例、财年默认值、PDF 生产解析、schema／原因码／调用方变化，没有运行真实 base rebuild。

新增 [test_hk_period_evidence.py](../../tests/fins/test_hk_period_evidence.py) 的 16 个用例：官方 raw→年度日期→两 Q1、独立非目标 unknown 反例、组合正负例、真实 Fs 本地资格／发布／转换失败重试／幂等，以及已标 v3 的旧投影仍重新解析。v3 用例仅在隔离 Fs 中通过仓储 API 构造旧投影，保留官方 raw，再验证重新投影且来源身份、业务字节、内容版本和指纹不变；不是只断言版本标签。

正式 fixture [hk_period_evidence_20261018](../../tests/fins/fixtures/hk_period_evidence_20261018/provenance.json) 固化三份完整官方响应原始字节（1229／1360／14535 bytes，共 27 条），逐件核对原 SHA256。provenance 保存完整请求 URL、获取时间、状态、原件 hash 和四份完整 PDF 的官方引用；没有打包或伪装派生 PDF。离线 workflow 的 PDF／Docling 是明确合成资产，真实转换由下述 CLI 验收另证。

README 已先读维护约束再最小更新：`dayu/fins/README.md` 的 Downloaders 章节说明统一家族及不同资格；`tests/README.md` 增补正式 fixture／回归边界。不触发用户入口／参数／输出通道／工作区位置或架构变化，根 README、`dayu/README.md` 无需修改。

## 测试、覆盖率与类型检查的实际结果

所有测试及类型检查均先激活 `.venv`。最终测试命令如下，外层实际 argv 见 `E/implementation-tests-final-command.json`：

```sh
source .venv/bin/activate
COVERAGE_FILE=workspace/tmp/hk-period-evidence-20261018/implementation.coverage pytest -q \
  tests/fins/test_hk_period_evidence.py tests/fins/test_cn_report_selection.py \
  tests/fins/test_f5_storage_calendar.py tests/fins/test_f5_workflow_rebuild.py \
  tests/fins/test_hkexnews_downloader.py tests/fins/test_cn_download_workflow.py \
  tests/fins/test_f5_result_contract.py tests/cli/test_output.py \
  tests/fins/test_cn_download_identity.py tests/fins/test_hk_period_rebuild.py \
  --cov=dayu.fins.pipelines.cn_report_selection --cov-report=term-missing \
  --cov-report=json:workspace/tmp/hk-period-evidence-20261018/implementation-coverage.json

source .venv/bin/activate
pyright
```

| 验证／证据前缀 | 真实退出／结果 |
| --- | --- |
| `implementation-owner-01`：生产修改后原四个 owner／链路文件 | 0；232 passed、3 项既有 edgar DeprecationWarning |
| `implementation-regression-03`：新增测试修正后 | 0；16 passed、3 项同类警告 |
| `implementation-tests-final`：上述十文件、完整生产文件覆盖率 | 0；557 passed、3 项同类警告，17.45s |
| `implementation-coverage.json`／`implementation.coverage` | 完整文件 301 条语句、279 覆盖、22 未覆盖、0 排除，**92.691%**，达到 >=80% 目标；没有过滤生产行 |
| `implementation-pyright-final`：全项目 | 0；0 errors／0 warnings／0 informations |
| `implementation-scripts-pyright-final-03`：另行显式纳入本轮三个临时脚本的 strict 检查 | 0；0 errors／0 warnings／0 informations；没有把 workspace 默认排除当作脚本通过证据 |
| `validation-verification-final`：CLI／仓储／历史证据交叉核对 | 0；全部断言通过 |
| `git diff --check` 与最终文档／新增文件检查 | 无空白错误；分支／HEAD／代码指纹与实际验证版本一致 |

原始迭代失败全部保留，没有覆盖：`implementation-regression-01/02` 均为 exit 1、13 passed／3 failed，原因是新增测试构造 REPAIR_REQUIRED 时遗漏必需原因、把 metadata 当业务资产比较，以及误断言 manifest 拥有 schema 未定义的 coverage 字段；按真实仓储 contract 修正测试，没有生产 fallback。`implementation-pyright-01` exit 1 的三处错误也在新增测试（JSON 类型边界及错误文件字段），最终全项目检查已归零。

临时脚本检查的失败亦保留：`implementation-scripts-pyright-01` 的绝对 include 被 pyright 忽略而误纳入绑定旧 base 的归档探针；改为相对 include，未改归档探针或为其保留旧接口。`-02` 两脚本通过；新增核对脚本后 `-final/-final-02` 分别报 3／1 个严格 JSON 类型错误，修正字符串身份收窄和 JSON 列表类型后 `-final-03` 通过。上述均有原始 stdout／stderr／process，未用它们替代最终检查。

## 两次真实同参普通增量

固定业务 argv 实际执行两次；只有 `--log-file` 分别为 `validation-01-dayu.log` 和 `validation-02-dayu.log`：

```sh
/Users/leo/workspace/dayu-agent-r/.venv/bin/dayu-cli \
  --base /Users/leo/workspace/portfolio-manager-v2/workspace \
  --log-file /Users/leo/workspace/dayu-agent-r/workspace/tmp/hk-period-evidence-20261018/validation-01-dayu.log \
  download --ticker HK:00388 --start 2025-01-01 --end 2026-10-18
```

| 轮次 | 实际 UTC 起止／进程退出 | 原始诊断计数／终态 |
| --- | --- | --- |
| 01 | 14:44:22.993278 → 14:45:25.514364，exit 0 | 11 discovered／2 downloaded／9 skipped／0 failed／0 rejected／0 uncertain，missing=[]，succeeded |
| 02 | 14:47:01.112855 → 14:47:18.445470，exit 0 | 11 discovered／0 downloaded／11 skipped／0 failed／0 rejected／0 uncertain，missing=[]，succeeded |

日期均为 2026-10-18。原始业务参数确实没有 forms／overwrite／rebuild；公开 filters 的 FY/H1 是既有 bare default，两 Q1 仍被 discovery 正确处理。两轮 `*-command.json`、`*-process.json`、`*-stdout.txt`、`*-stderr.txt`、`*-dayu.log` 和从原通道解析另存的完整 `*-diagnostics.json` 均在 E/，原通道字节未改。两份来源均完成真实 PDF 下载和 Docling 子进程转换，没有 mock、关闭 TLS 或手工补发布。

| source ID | 实际 document ID | 财年／身份／截止日／coverage |
| --- | --- | --- |
| 11655015 | `fil_cn_ede631a4c5f5f8d7a0846a30a0c1e976d0da1303` | 2025／Q1／2025-03-31／[Q1] |
| 12131985 | `fil_cn_92402294f583ce80f85e1144a3d6181d93a8285d` | 2026／Q1／2026-03-31／[Q1] |

两份 form_type／fiscal_period／report_kind 均 Q1、document_version 均 v1，原始标题／官方类别／URL／filing date 保留；外部和内部身份均由现有 owner 分配。两份原 PDF 实际 hash 分别为 `5eb09ff3…4054`、`0bd0d0d5…1621`，与冻结官方原件完整 hash 相同。source 中 PDF／Docling 共两项声明及实际 hash／size 一致，primary 为对应 Docling JSON，COMPLETE 校验通过；没有另行执行 preprocess 或伪造 processed 产物。

## 仓储、全集与失败历史核对

三次快照实际命令（由 run_capture 留存 argv／退出和双通道）：

```sh
source .venv/bin/activate
PYTHONPATH=. python workspace/tmp/hk-period-evidence-20261018/storage_snapshot.py validation-before
PYTHONPATH=. python workspace/tmp/hk-period-evidence-20261018/storage_snapshot.py validation-after-01
PYTHONPATH=. python workspace/tmp/hk-period-evidence-20261018/storage_snapshot.py validation-after-02
PYTHONPATH=. python workspace/tmp/hk-period-evidence-20261018/verify_validation.py
```

- 三次快照均 exit 0；分别 9／11／11 份，全部通过 `read_source_meta_integrity_view` 和 materialized `read_source_snapshot`，同一文档 revision 与 meta 一致，逐个实际读取声明资产并核对 hash／size。指定 base 的锁动作经精确权限执行；没有拼接或遍历读取受管财报目录。
- [validation-01-storage-comparison.json](../../workspace/tmp/hk-period-evidence-20261018/validation-01-storage-comparison.json) 与 [validation-verification.json](../../workspace/tmp/hk-period-evidence-20261018/validation-verification.json) 断言：首轮原九份完整公共 meta、revision、身份、内容版本、fingerprints、历史时间／元数据、资产声明和实际 bytes hash 及 processed 事实完全不变；仅新增两份正确 Q1。重跑后十一份上述事实全部相等，FY2025 独立年报未重下载或覆盖。
- manifest 没有被测试或脚本臆造新字段：COMPLETE 由 storage owner 校验其实际 schema 与 source meta／revision／业务字节的同版投影；隔离 Fs 用例还直接断言 manifest 既有财年／财期／日期字段与 source 同源。coverage 由 source meta／workflow result／公开诊断自身契约断言。
- 两轮公开诊断均实际含 10 条 document rows 和 `omitted_count=1`，不是无界 typed-result 内存 dump。已保存完整发出的 JSON；两目标都在公开行内，财期／日期／coverage／disposition 与仓储同源。全集另以两轮各 11 条实际 pipeline 完成事件、计数守恒和全部 11 份仓储观察交叉核对，未仅看有界摘要。未把日志重新构造成业务结果；owner／typed／CLI 契约的生产链路由上述回归另行验证。
- 原 download-02 的 command／result／diagnostics／process／stdout／stderr／dayu.log 七文件 SHA256 均与原 manifest 相同，原 exit 1／两 unknown 历史未回写。该项仅做 hash 比较，不重开原日志取证。原日志 hash 仍 `b873faa1…9a84986`，原 diagnostics 仍 `d4be0a72…66b46a2d`。

## 风险分类、owner 与下一入口

| 项目 | 实际状态／分类 | owner／destination |
| --- | --- | --- |
| 年度供证／未决资格、组合边界、同 v3 重解析、fixture、fresh 快照、两次 CLI 与外部变化核对 | fixed in current slice；实现与上述验证已完成，待独立 code review 确认 | 本 work unit Fins owner／总控 → 最终双路完整 deepreview；本报告不作 gate pass |
| 当前官方输入或 PDF 相对冻结证据漂移 | 本次候选身份／日期和两 PDF 原件 hash 无漂移；未来来源变化需重新核对 | Fins 来源／财期 owner → 有具体新证据的 work unit，不能复用本次数字作产品常量 |
| 公开诊断有界与测试覆盖范围 | verification limitation：真实 CLI 未导出无界内存 typed result；11 份全集已由仓储／完整完成日志补核。语句覆盖 92.691% 仍有 22 条未覆盖，不声称穷尽输入；真实取消／失败未在生产 base 人为注入，复用隔离回归 | 最终 reviewer 核对证据适用性；后续修改对应 owner 时扩展必要回归，不以改参数或真实破坏试验补验 |
| 52／53 周、过渡期、年结变更、全历史错误标签迁移 | assigned to later work unit；未增加支持，仍按既有规则有据 unknown | Fins 财期／仓储 owner → 后续具体需求和证据；本次未跑真实 rebuild |
| 无实际证据的 provider 错误分类／年度日期污染框架 | assigned to later work unit；本轮只保留既有冲突反例和失败关闭 | Fins 财期 owner → 取得具体异常来源后另开 work unit |
| TLS／沙箱／域名调查、调用方变更 | 非目标／assigned to later work unit；未调查、未修改 | 原报修方／调用方 owner → 各自后续范围 |

下一入口：**交付总控，进入最终 mimo-flash／ds-flash 双路完整 deepreview；没有 commit／push／PR／merge。**
