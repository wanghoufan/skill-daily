# Skill 日报引擎 V1.4（skill-daily）

把已冻结的四类输入合成一份「每天只看 5～10 条，就知道今天有什么值得装 / 恢复 / 更新 / 替换 /
观察」的个性化 Skill 日报。**引擎不自动安装任何 Skill**：所有安装 / 删除 / 升级仍由人在
Skill Manager 里确认执行（`auto_install` 恒为 false，代码里无任何安装/删除调用）。

## 怎么复现（与代码完全一致，无需任何环境变量）

1. 解压 `skill-daily-v1.4.zip`（得到 `skill-daily/`）；
2. 解压 External v2.11 转送包（得到 `转送审查者 v5 材料（外部情报层）/`）；
3. 把这两个顶层目录放在同一个父目录里（同级）；
4. 直接运行：`python3 skill-daily/tests/test_daily.py`（需要 Python 3.12+）。

可选：`EXTERNAL_INTELLIGENCE_ROOT=/你的/外部包目录` 显式指定（放任意位置均可）。
定位逻辑 `resolve_external_root()` 按优先级尝试：环境变量 → 同级
`external-intelligence`（开发仓）→ 同级 `转送审查者 v5 材料（外部情报层）` →
旧版 `Agent 产物（外部情报层）/转送审查者 v5 材料（外部情报层）`；
每一级都验证 SKILL_CANDIDATES.json 与 build_context.py 真实存在才采用。
全部找不到时给出带修复指引的友好错误，不会再出现 `ModuleNotFoundError`。
实际采用的布局记录在 `DAILY_REPORT_CONTEXT.json.external_resolution`。

历史修复说明（V1.1~V1.3 各轮能力均保留，当前版本 = V1.4，见 engine.version）：

```text
NO_LONGER_RELEVANT  曾展示/用户碰过的候选从池中消失 → 暂不建议桶 + 「之前动作→现在」可读卡片，只通知一次
STATUS_DOWNGRADED   new_install/update/restore → reject 或 watch/ignore（此前展示过）→ 明确降级提醒；
                    原因如实（产品范围/需求变化/评分…），不谎称安全风险；risk_kind 在机器层分开
STATUS_UPGRADED     watch/reject/ignore → install/update/restore、reject → watch：写「状态提升/改善」
RETURNED            消失后又回来的候选：说「重新出现」，不冒充全新发现
replacement_candidate → 第 6 类用户动作「建议替换」（External 合同已有该 action，日报不丢）
```

- `candidate_tombstones`：消失候选的历史台账（last_seen / last_action_type /
  last_recommendation / last_snapshot / 最后可读信息 / notified 标记）。
  保留期 `tombstone_retention_days=30`（config）；未通知的重要消失项不提前清理，
  通知过且过保留期才删——不无限增长。
- `shown` 条目同时保留 skill_name/source/source_url/last_action/last_reason，
  消失当天还能生成可读卡片（不只剩 canonical_key）。
- 机器摘要新增 `lifecycle`（removed/returned/upgraded/downgraded/replacement 计数）、
  `suppressed.no_longer_relevant_unseen`、每条 item 的 `event_type` 与 risk 项的
  `risk_kind ∈ {security, source, no_longer_relevant, status_downgrade}`。
- 用户层保持简单：6 类动作文案；tombstone/STATUS_* 等工程词只进技术详情。

## 三种状态严格分开（V1.2 核心，V1.3 继续）

```text
initial_baseline  首份基线：从当前静态候选面挑最值得处理的 5~10 条（明示不是今天新发生）
daily_delta       次日起只允许：真 NEW/UPDATED/RISING、SECURITY/SOURCE/MATCH 变化、
                  action_type 迁移、新项目匹配、反馈变化、冷却到期的已展示提醒
baseline_backlog  首份基线没展示完的静态候选：只在 Day1 脚注报数量，永不自动轮播
```

- `candidate_baseline`（日报自有）：首跑即为**全池**建立签名基线
  （`bc.snap_key` + action_type/recommendation/项目匹配/安全签名），只存签名不复制候选。
- `shown`：用户真的在日报里见过的条目；**只有 shown 候选才进 repeat cooldown / 到期提醒**。
  alternatives 与 PRIMARY 共享 shown 状态（防换皮重现）。
- Delta 优先级链：① 日报自有 candidate_baseline → ② 外部 last_snapshot（若存在，仅首日辅助，
  辅助时缺键不判 NEW）→ ③ 都没有 → 无事件、initial_baseline、零 NEW 风暴。
  仍复用 v2.11 `classify_delta/snap_key` 语义，不重造 Delta。
- 每条 item 带 `report_reason_type`
  （initial_baseline / material_delta / cooldown_reminder / feedback_reentry /
  project_match_change / risk_change）与 `material_today_evidence`；
  `why_today` 由 reason_type 生成——daily_delta 里没有今日理由的候选不得进日报。
- 审计硬门（全部按上一日快照/基线复算，不手工声明）：
  `unchanged_repeated_items = 0`、`stale_backlog_items = 0`、`non_material_daily_items = 0`。

## 目录

```
skill-daily/
├── README.md                     ← 本文件
├── config/daily.json             上限 / 全动作冷却周期 / 族配额 / 开关（全部配置化）
├── data/
│   ├── SKILL_FEEDBACK.json       每技能最新反馈状态（机器读取）
│   ├── SKILL_FEEDBACK_HISTORY.jsonl  一行一事件的历史
│   └── state/daily_snapshot.json shown（含三签名+delta_cats+reason） + candidate_baseline（全池）
├── scripts/
│   ├── common.py                 输入定位（冻结层只读；自动适配开发仓/转送包布局）
│   ├── build_daily.py            引擎主体（确定性，无 LLM）
│   └── feedback.py               反馈录入 CLI
├── reports/YYYY-MM-DD.md         用户日报（第一层只有中文小白文案）
├── reports/package-e2e-audit.txt 包内统一口径 E2E 审计（Day1/Day2/Day8）
├── reports/repeat-audit-*.txt    真实两日重复审计
├── reports/lifecycle-e2e-audit.txt 真实池合成 mutation 审计（消失/降级/重现，§三十二）
├── DAILY_REPORT_CONTEXT.json     机器摘要（logical_path；pool_counts 四分法；lifecycle 统计）
└── tests/test_daily.py           81 项测试（V1.2 44~62、V1.3 63~77、V1.4 78~83）
```

## 用法

```bash
P=python3   # 需要 3.12+
$P scripts/build_daily.py                 # 生成今天：reports/ + DAILY_REPORT_CONTEXT.json
$P scripts/build_daily.py --date 2026-09-24 --out-dir /tmp/x   # 隔离运行（状态也重定向）
$P scripts/feedback.py <canonical_key> <status> ["备注"]        # status: installed|tried|useful|poor|ignored|removed|deferred
$P scripts/feedback.py --list
$P tests/test_daily.py                    # 测试合同：SKIP 只允许 unittest.SkipTest，真计数
```

## 展示去重与多样性（V1.1 保留）

- `display_family_key = 规范化 skill_name + matched_gap`：完全重复只展示一个 PRIMARY，
  其余进 `alternatives[]`；PRIMARY 判定：动作优先级 → verdict → tier → 分数 → canonical_key。
- 能力族配额：install ≤2 / watch ≤1 每族（restore/update/risk 豁免）；被挡只计数不删候选。
- 处理顺序固定：安全硬门 → 反馈 → 实质变化 → 冷却 → 功能去重 → 族配额 → 优先级 → 上限 10；
  先去重再截断，绝不为凑满 10 条回填。

## 机器合同（DAILY_REPORT_CONTEXT.json）

- `one_line_explanation` 中文且与 Markdown 同源；原文英文在 `source_description_excerpt`。
- `suppressed` 九字段：repeat_cooldown / functional_duplicate / capability_family_quota /
  unchanged_watch / metadata_only / feedback / baseline_backlog / non_material_today /
  no_longer_relevant_unseen。
- `lifecycle`：removed_from_pool / returned_to_pool / status_upgraded /
  status_downgraded / replacement_candidates（V1.3 §二十四）。
- `pool_counts` 四分：current_static_actionables（现在总体值得装）≠ material_today_items
  （今天为什么要提醒）≠ baseline_backlog ≠ shown_items。
- `input_provenance` 只写 `logical_path`（如 `external-intelligence/SKILL_CANDIDATES.json`）；
  真实路径仅当环境变量 `SKILL_DAILY_DEBUG_PATHS=1` 时写入 `runtime_debug_path`，默认不进交付物。
- `delta_source`：daily_candidate_baseline / external_snapshot_aux / none_first_run_zero_new。

## 扩展位（明确不做）

自动安装 / Web Dashboard / 移动 App / Slack / 邮件推送 / AI 聊天界面 / 云数据库 /
多用户 / 企业权限 / 自动删除 / backlog 周报轮播 —— 先闭环「输入 → 自有基线 → 真 Delta →
动作 → 冷却/去重/配额 → 5~10 条日报 → 反馈」。

## 与中央 Skill 仓库规则的关系

本目录是脚本引擎，不是 Skill 工件（不新增 SKILL.md，故不涉及 `SKILL-REGISTRY.md` 登记；
若以后把「跑日报」封装成 Skill，按 `SKILL-CONTRIBUTION.md` 入库并登记）。
