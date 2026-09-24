# HANDOFF｜Skill 日报体系（2026-09-24 大交接）

> 恢复开发三件套（新智能体按此顺序读）：根 `AGENTS.md`（一页规矩+运行命令）→ 本文件 → `skill-daily/README.md`（V1.4 完整设计合同）。
> 项目状态快照时间：2026-09-24。数字均为当时代实测，接手后如需引用请先重测。

## 一、当前工作进展（全部已实测通过）

1. **External Skill Intelligence v2.11 = 冻结态**（`external-intelligence/`）
   - 数据合同+语义一致性收口全过：90 测试通过；Top 16/30；UPDATED 849→0。
   - 已通过审查者冻结审查。**任何轮次都不得再修改。**
2. **Skill 日报引擎 V1→V1.4 五轮整改全部交付**（`skill-daily/`）
   - V1 建成 → V1.1 重复抑制/展示去重 → V1.2 基线状态/真实 Delta → V1.3 候选消失与状态降级生命周期 → V1.4 归档自定位/版本一致性收口。
   - 终态：`pass=74 skip=1 fail=0`（唯一 SKIP 为合成测试 t37，真跳过）；Day1 initial_baseline=10 条、Day2 无变化=0 条；用户级「两个 ZIP 同级解压直跑」亲验；包内产物与 package-e2e-audit 同口径；正式产物绝对路径=0；auto_install 恒 false。
   - 最新送审件：`Agent 产物（外部情报层）/转送包（2026-09-24 日报引擎V1.4 送审）/skill-daily-v1.4.zip`（96,696 B，SHA256 前缀 `6446c269c66bd3c9`，含回执）。历史 V1~V1.3、v2.3~v2.11 送审包同目录可查。
   - **状态：等审查者对 V1.4 的结论 → 可能宣布「Skill 日报引擎冻结」。冻结前不升版、不改算法。**
3. **工作区迁移完成**
   - 2026-09-24 由 `~/Downloads/大模型 HANDOFF/60 Skill 仓库` 以 ditto **复制**（非移动）至此，三目录同级（开发仓布局）；`diff -r` 逐字节一致后清理了验证产生的状态漂移。
   - **旧位置三份原件仍在**（skill-daily / external-intelligence / Agent 产物），等用户确认新位置稳定后由用户决定是否清理。智能体不得代删。
4. **launchd 本地自动化已部署并端到端验证**
   - `~/Library/LaunchAgents/com.alw.skill-daily.plist`，每天 07:00 直跑 Python，无大模型、无网络。
   - 产物目录：`/Users/zzymima0000/Developer/coding/1.Active/000-alw-自动化任务/skill 日报-py/`（`YYYY-MM-DD.md` + `DAILY_REPORT_CONTEXT.json` + `state/` + `logs/`）。
   - 验证：plutil OK / bootstrap 成功 / kickstart 真触发 runs=1 exit=0 / stderr 空 / 项目区零写入（diff 亲验）。
   - 关键部署事实：本机 `command -v python3` 是 3.9.6（跑 V1.4 必 SyntaxError），launchd 与一切脚本必须用 `~/.workbuddy/binaries/python/versions/3.13.12/bin/python3` 绝对路径。
5. **收尾（neat-freak）**：本工作区 `__pycache__`/`.pyc`/`.DS_Store` 已清零；根 `AGENTS.md` 与 README、launchd 实况已对齐。

## 二、下一步的任务

| # | 任务 | 触发条件 | 说明 |
|---|---|---|---|
| 1 | 接收审查者对 V1.4 的结论 | 用户粘贴新整改提示词 | 按老规矩执行：只修列出的问题、不重做已通过架构、不中途询问、最后只交文档规定格式的验收摘要+重新打包送审 |
| 2 | 若审查通过 → 宣布冻结 | 用户口令 | 冻结后在 AGENTS.md/README 标冻结日期；引擎与 v2.11 双双封存 |
| 3 | 外部候选池数据刷新轮（未来） | 用户主动发起 | 引擎只吃快照；要真实「今日变化」必须先刷 external-intelligence 数据（独立整改轮，需重过审查）|
| 4 | 旧位置清理决定 | 用户确认 | 用户说清理才动；给方案等确认，不代删 |
| 5 | （可选，未排期）反馈 CLI 化 | 用户提出 | 反馈机制（deferred/好用/不好用）目前靠直接编辑 `skill-daily/data/SKILL_FEEDBACK.json` + 历史 jsonl；V1.4 合同不含 CLI 写反馈，做之前先问审查者口径 |

## 三、注意事项及相关规矩（红线）

1. **冻结层不许碰**：`external-intelligence/` 全目录只读；验证有无被改用 `find external-intelligence -type f -newer <上一交付物>`。
2. **算法冻结**：V1.4 的推荐/Delta/冷却/生命周期语义不得顺手改（口径详见 AGENTS.md 与 README）。业务逻辑改动只能通过「审查文档驱动的新版本整改轮」发生。
3. **禁止**：自动安装/删除/升级 Skill；给引擎接大模型或网络；创建新 Web 服务/Docker；把日报产物写回项目源码目录。
4. **执行环境**：一律 workbuddy python 3.13.12 绝对路径；测试期望 `74/1/0`；跑完清理 `__pycache__`。
5. **交付/转送**：产物只进 `Agent 产物（外部情报层）/转送包（YYYY-MM-DD …送审）/`（zip+回执）；SHA/大小等一切数字落笔前重新实测，不沿用记忆；交付后 `open` 对应 Finder 并点名该送/不该送。
6. **操作规矩**：任何删除/合并/重命名先给方案等用户确认；本目录 2026-09-24 起已是 git 仓库，公开在 `github.com/wanghoufan/skill-daily`（main；范围=代码+文档，`Agent 产物` 送审包经 .gitignore 排除仅本地），常规改动可 commit+push，结构性改动先问用户；发现与本文件不符的现场，以现场为准并更新本文件。
7. **沟通**：用户是编程小白——大白话；每轮末三行心跳（目标/剩 P0/下一步）；整改提示词轮次内不中途询问、一次性交付。
