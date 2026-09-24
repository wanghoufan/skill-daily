# AGENTS.md｜Skill 日报体系（任何智能体进入本目录先读这一页）

## 这个项目是什么

两层独立程序，已全部建成并送审：

1. **External Skill Intelligence v2.11**（`external-intelligence/`）：外部 Skill 情报层。
   产出冻结的候选池 `data/SKILL_CANDIDATES.json`（1106 条，快照日期 2026-09-24）与
   Delta 语义（`scripts/build_context.py` 的 `classify_delta/snap_key`）。**已通过审查者冻结审查，不许再改。**
2. **Skill 日报引擎 V1.4**（`skill-daily/`）：每天把候选池合成一份人话日报（5~10 条）+
   机器摘要 `DAILY_REPORT_CONTEXT.json`。**不安装、不删除、不升级任何 Skill**（`auto_install` 恒 false，
   代码无任何网络/大模型调用）。V1.4 已交付，等审查者宣布冻结。

## 怎么运行（照抄即可，两条命令）

必须用这个 Python（系统 `/usr/bin/python3` 是 3.9，跑 V1.4 会直接 SyntaxError）：

```bash
PY=/Users/zzymima0000/.workbuddy/binaries/python/versions/3.13.12/bin/python3

# 全量回归测试（期望：pass=74 skip=1 fail=0；唯一 SKIP 是合成测试 t37，真跳过）
"$PY" skill-daily/tests/test_daily.py

# 生成某天的日报（默认今天；--out-dir 时报告+机器摘要+state 全落到指定目录，不污染项目区）
"$PY" skill-daily/scripts/build_daily.py --date 2026-09-24 \
  --out-dir "/Users/zzymima0000/Developer/coding/1.Active/000-alw-自动化任务/skill 日报-py"
```

External 定位是自动的（`skill-daily/scripts/common.py` 的 `resolve_external_root()`）：
优先环境变量 `EXTERNAL_INTELLIGENCE_ROOT` → 同级 `external-intelligence/`（本工作区就是这种）→
同级转送包目录 → 旧版嵌套布局；每级都校验文件真实存在，找不到给友好报错。
实际用了哪种布局记在机器摘要 `external_resolution` 里。

## 每天产物去哪看

launchd 已配好（`~/Library/LaunchAgents/com.alw.skill-daily.plist`，Label `com.alw.skill-daily`）：
**每天早上 07:00 自动跑，不经任何智能体/大模型。** 产物目录：

```text
/Users/zzymima0000/Developer/coding/1.Active/000-alw-自动化任务/skill 日报-py/
├── YYYY-MM-DD.md                  ← 当天日报
├── DAILY_REPORT_CONTEXT.json      ← 机器摘要
├── state/daily_snapshot.json      ← 自动化专用状态（与项目区 state 互不干扰）
└── logs/stdout.log / stderr.log   ← 出事先看 stderr
```

改时间：编辑 plist 的 Hour/Minute，然后
`launchctl bootout gui/$(id -u)/com.alw.skill-daily && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.alw.skill-daily.plist`。

## 红线（违者打回）

- **不修改 `external-intelligence/`**（冻结 v2.11）。验证是否被动过：`find external-intelligence -type f -newer <上次交付物>` 应为空。
- **不修改 `skill-daily/` 的推荐/Delta/冷却/生命周期算法**（V1~V1.4 每轮都过审查，改前先问用户）；路径/部署问题按部署解决，不许借机升版本。
- 禁止自动安装/删除/升级 Skill；禁止给引擎接大模型或网络调用。
- 每日自动化产物只落上面那个自动化目录，**不要写回项目源码目录**。
- 业务逻辑口径（改前必须知道）：Day1=initial_baseline（全池建基线，不算 NEW 风暴）；Day2 无变化=0 条；
  未展示的 baseline_backlog 永不轮播；只有 shown 候选才进冷却提醒；候选消失/降级/回归走
  NO_LONGER_RELEVANT / STATUS_DOWNGRADED / STATUS_UPGRADED / RETURNED，各只通知一次；tombstone 保留 30 天。

## 数据新鲜度（重要认知）

引擎是确定性的、只吃快照。**外部候选池不刷新，日报长期是「今天没有需要你处理的 Skill 变化」——这是设计，不是故障。**
要真实变化，需先人工发起一轮外部情报层数据更新（那是独立整改轮，用户口令驱动），再跑日报。

## 转送/送审规矩

- 一切要交给审查者的东西只放 `Agent 产物（外部情报层）/转送包（YYYY-MM-DD …送审）/`（zip + 回执），禁止污染仓库根。
- 最新送审件：`转送包（2026-09-24 日报引擎V1.4 送审）/skill-daily-v1.4.zip`（96,696 B，
  SHA256 前缀 `6446c269c66bd3c9`）。历史轮 V1~V1.3、外部层 v2.3~v2.11 同目录可查。
- 凡要转送的文件，写完 `open <文件夹>` 打开 Finder 并点名该送哪个。
- 任何删除/合并/重命名操作前先给用户方案、等确认；不 commit 不 push（本目录非 git）。

## 当前状态（2026-09-24）

- 引擎 V1.4：74 pass / 1 真 SKIP / 0 fail；用户级「两个 ZIP 同级解压直跑」已亲验；launchd 端到端已触发验证（exit 0）。
- 外部层 v2.11：冻结，90 测试全过。
- 待办：等审查者对 V1.4 的结论 → 可能宣布「Skill 日报引擎冻结」；冻结前本目录不升版。
- 工作区沿革：2026-09-24 由 `~/Downloads/大模型 HANDOFF/60 Skill 仓库` 整体复制至此（旧位置原件暂留，待用户决定清理）。
