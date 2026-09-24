# Installed Skills Context（Canonical 模型 v4）

> 更新时间：2026-09-22 17:0x (GMT+8)｜MACHINE_ID：Mac-mini｜数据基准：2026-09-22 15:12 (GMT+8) 双扫描稳定窗口；16:5x 注册表副本核验
> 本版引入 CANONICAL_SKILL：『存在多个目录』≠『存在多个不同 Skill』。同步副本 / 冲突副本 / 别名目录不再计入唯一 Skill。
> 模型：Skill Manager 中央管理 → 双机 git 备份同步 → 各 Agent 经软链接/副本加载。

## 1. 四数拆分（一个 unique 数字不再表达所有概念）

- **CANONICAL_UNIQUE_SKILLS：45**（逻辑 Skill 全集 = 当前有 canonical 副本 42 + 已知但本机缺失 3〔orca 三件套〕）
- **LOADABLE_SKILL_ENTRIES：49**（目录扫描加载器视角：42 canonical + 7 个 `(2)` 别名目录，加载器会把别名当独立 Skill——这是加载器命名识别问题，不是 7 个新逻辑 Skill）
- **SYNC_REPLICAS：19**（repo 平行开发副本 + agent 目录物理副本；内容与 canonical 一致或仅换行符差异）
- **DUPLICATE_ALIASES：7**（`(2)` 目录：Skill Manager 导入收编时中央已存在同名目录 → 另存 `(2)` 并注册为独立条目；全目录 diff -rq 实测与原目录逐字节一致）
- 物理副本：65 ｜ 悬空软链接：6

## 2. 机制诊断（Skill Manager 自证，2026-09-22 16:5x 注册表副本核验）

- **`(2)` 目录 = Skill Manager 的导入收编行为**：注册表 7 条独立记录 central_path 直接指向 `skills/xxx (2)`（source_type=local，status=ok，各有 UUID），source_ref 指向 60 Skill 仓库对应目录 → 用户/流程把仓库 skill 目录导入中央时中央已有同名 → 另存 `(2)`。诞生时间 12:39，与 pending_conflicts 检测时间（bilibili-download-check、github-portfolio-sync 的 git 远端更新冲突）同批。
- **Orca 三件套消失 = Skill Manager 应用内删除**：注册表无 orca 行、skill_targets 无 orca 行（FK ON DELETE CASCADE 级联删除）、audit_log 全历史无 remove 记录、WAL 含大量 `sm-reindex-parked://` 停靠记录 → re-index/停靠机制所为，非用户手动 rm，也非另一台电脑文件级冲突覆盖。
- **双机同步确认为正式机制**：settings 内 `backup_device_name=zzymima0000deMacBook-Air`（本机 scutil=Mac-mini，说明 skills-manager 状态跨机携带）、`git_backup_remote_url`（加密 GitHub 远端）、`backup_auto_enabled=on`、`merge_engine=object`、`auto_update_apply=on`（最近一次 auto_update 15:48）。**这台 Mac-mini 上的 ~/.skills-manager 整体就是双机同步的产物。**

## 3. AGENT_AVAILABILITY（安装态与可用态分列）

- broken（链接悬空）：**6 条** — computer-use×workbuddy；computer-use×claude；computer-use×opencode；orca-cli×claude；orca-cli×opencode；orchestration×claude
- missing（canonical 缺失）：3 个 — computer-use, orca-cli, orchestration（KNOWN_SKILL=yes，INSTALLED_CANONICAL=no）
- available：109 ｜ not_deployed：104（未部署到该 agent，属正常状态）
- 详细逐 skill × agent 矩阵见 INSTALLED_SKILLS_FULL.md。

## 4. 能力层（覆盖度 coverage 与可用性 availability 分列）

- CAPABILITY_SUPPRESSION 结构沿用已验收版本，未改动；新增 CAPABILITY_AVAILABILITY 维度：
  - **orca_integration：coverage=strong，availability=degraded**（载体 1/4 在位，缺失：orca-cli, orchestration, computer-use）→ 日报不得视为完全正常
  - **computer_use：coverage=strong，availability=degraded**（载体 2/3 在位，缺失：computer-use）→ 日报不得视为完全正常
- 其余能力 availability 均为 ok（carrier 全部在位）。

## 5. 给 Skill 日报智能体的机器可读摘要（仅暴露 9 键）

```
CANONICAL_UNIQUE_SKILLS:   # 逻辑 Skill 全集（含已知未安装）；同步副本/别名不在此列
  total: 45
  installed_canonical: 42
  known_missing: 3   # orca-cli, orchestration, computer-use（来源档案在案，本机暂缺）
  loadable_skill_entries: 49   # 目录视角，含 7 个 (2) 别名，勿当独立 Skill
  sync_replicas: 19
  duplicate_aliases: 7
  machine_id: Mac-mini

CURRENT_CAPABILITIES:   # 按逻辑 Skill 统计；availability 见 CAPABILITY_AVAILABILITY
  browser_automation: strong
  computer_use: strong
  course_pipeline: strong
  deployment_netlify: strong
  deployment_vercel: strong
  frontend_design: strong
  github_ops: strong
  orca_integration: strong
  research: strong
  skill_creation: strong
  skill_management: strong
  ui_theme: strong
  writing: strong
  obsidian: medium
  productivity_personal: medium

CAPABILITY_SUPPRESSION:   # 结构沿用已验收版本；主键=canonical skill，(2) 别名不参与
  strong = 新 Skill 若只是重复该能力，应明显降权；仅当带来明确新增能力时才推荐
  medium = 已有较强覆盖，但允许明显更好的专项 Skill
  weak   = 已有零散能力，欢迎完整方案
  none   = 当前缺失，优先搜索
  strong: browser_automation, computer_use, course_pipeline, deployment_netlify, deployment_vercel, frontend_design, github_ops, orca_integration, research, skill_creation, skill_management, ui_theme, writing
  medium: obsidian, productivity_personal
  weak: docx_xlsx, macos, mcp_dev, security_audit, supabase_db, testing_qa, windows
  none: data_analytics, image_creative, mobile_qa

CAPABILITY_AVAILABILITY:   # coverage=历史覆盖度；availability=当前载体在位情况
  orca_integration:
    coverage: strong
    availability: degraded
    carriers_missing: orca-cli, orchestration, computer-use
  computer_use:
    coverage: strong
    availability: degraded
    carriers_missing: computer-use
  browser_automation:
    coverage: strong
    availability: ok

AGENT_AVAILABILITY:   # link_status: available/broken/missing/not_deployed（逐项矩阵见 FULL）
  machine_id: Mac-mini
  broken: 6
    - computer-use/claude: broken
    - computer-use/opencode: broken
    - computer-use/workbuddy: broken
    - orca-cli/claude: broken
    - orca-cli/opencode: broken
    - orchestration/claude: broken
  missing: 3
    - computer-use: KNOWN_SKILL=yes, INSTALLED_CANONICAL=no, central=missing
    - orca-cli: KNOWN_SKILL=yes, INSTALLED_CANONICAL=no, central=missing
    - orchestration: KNOWN_SKILL=yes, INSTALLED_CANONICAL=no, central=missing

SOURCE_SUMMARY:   # 按 CANONICAL 统计（同步副本/别名不重复计数）；括号内为当前安装集口径
  official: 8（installed 5）
  vendor: 1（installed 1）
  community: 2（installed 2）
  local: 3（installed 3）
  fork: 0
  modified: 0
  unknown: 31（installed 31）
  rule: 面向某产品≠由该厂商发布；origin_type 只认作者来源证据（详见 SKILL_SOURCE_MAP.json）

UPSTREAM_STATUS:
  identified: 14（installed 11）
  unknown: 31（installed 31）

UPSTREAM_ACTIVITY:   # active 仅联网核验后填写
  active: 11（installed 8）
  stale: 0
  deprecated: 0
  not_applicable: 3（local 自建）
  unknown: 31
  activity_verified_at: 2026-09-22
  evidence: anthropics/skills push 2026-09-10；stablyai/orca、browseros-ai/BrowserOS push 2026-09-22；KKKKhazix/khazix-skills push 2026-09-16；aihot 官方渠道 v1.7.1

VERSION_STATUS:   # 版本旧/与当前上游不一致 ≠ LOCAL_MODIFIED
  historical_official_version: 4
  upstream_in_sync: 4
  outdated_version: 2
  local_modified: 0
  unresolved_variant: 0
  not_compared: 35

NEEDS_ATTENTION:
  - 悬空链接×6 + Orca 3 件 canonical 缺失：根因=Skill Manager re-index/停靠（机制诊断见 §2）；恢复方案待用户确认，本轮未动
  - 『(2)』别名×7：已并入 canonical，不计入统计；物理目录待用户确认后清理（本轮未动）
  - Skill Manager pending_conflicts×2：bilibili-download-check, github-portfolio-sync（git 远端更新冲突，待处理）
  - 双机同步风险：auto_update_apply=on + merge_engine=object 曾致 canonical 被停靠/删除；建议先关闭 auto_update 或将中央目录纳入排除名单（待用户在 Skill Manager 界面操作）
  - 内容差异(CONTENT_VARIANTS): course-md-organize   # 仅换行符差异（CRLF vs LF，规范化后内容一致，非实质变体）
  - 来源待升级(pending_upgrade): leader, neat-freak
```

## 6. Canonical Skill 简表（45 行；`(2)` 别名不再单列）

| Canonical Skill | 状态 | 用途(简述) | 来源 | 活跃 | 版本关系 | 标签 |
|---|---|---|---|---|---|---|
| agent-central-mapping | ✅ 安装 | 当用户希望让 Claude Code、Codex、opencode、CodeArts Doer、Cursor、Gemin… | unknown | ⚪unknown | not_compared | Agent/Workflow,Other |
| ai-coding-homework-writeup | ✅ 安装 | "本 skill 适用于「把 AI 辅助开发的编程作业写成一份能交的提交材料」这类任务。当用户拿出作业要求（例如『用 E… | unknown | ⚪unknown | not_compared | Documentation,Education,Other |
| ai-quota-recovery-board | ✅ 安装 | 当用户想跟踪多个 AI 工具 / 服务的「额度 / 频率限制 / 信用点」恢复时间并做成可视化看板时使用。生成单文件 H… | unknown | ⚪unknown | not_compared | Automation,Frontend/UI,Other |
| aihot | ✅ 安装 | 查询 AI HOT 的中文 AI 资讯、精选、当前热点和日报。用户询问今天或最近的 AI 新闻、AI 圈动态、大模型或产… | vendor | 🟢active | outdated_version | Research,Other |
| batch-organize | ✅ 安装 | "本 skill 适用于「一批杂乱原始素材 → 统一规范成品」且需可重跑、可中断、可多智能体协作的批量整理任务（课程/播… | unknown | ⚪unknown | not_compared | Agent/Workflow,Documentation,Other |
| bilibili-download-check | ✅ 安装 | 当需要对比哔哩哔哩 UP 主投稿目录与本地已下载视频、生成未下载清单，或按红利/打新等关键词筛选时使用。 | unknown | ⚪unknown | not_compared | Browser Automation,Other |
| browser-e2e-login-pitfalls | ✅ 安装 | "浏览器端 E2E / 验收测试的踩坑与避坑手册：Vite 环境变量未注入、Google OAuth 拦截自动化浏览器（… | unknown | ⚪unknown | not_compared | Browser Automation,QA/Testing,Other |
| browseros-neo | ✅ 安装 | The user's dedicated browser for agents — a real browser sig… | official | 🟢active | outdated_version | Browser Automation,MCP,Other |
| coding-workspace-organizer | ✅ 安装 | 整理编码工作区：拍平嵌套归档目录，按 `NNN-状态-项目名` 规则重命名项目，并生成按序号查找的索引表。用户要求整理工… | unknown | ⚪unknown | not_compared | macOS,Windows,Automation,Other |
| computer-use | ⚠️ 缺失 | — | official | 🟢active | historical_official_version | Agent/Workflow,macOS,Windows,Browser Automation |
| computer-use-2 | ✅ 安装 | Use Orca's computer-use CLI for OS/window-level inspection a… | official | 🟢active | historical_official_version | Agent/Workflow,macOS,Windows,Browser Automation |
| course-md-organize | ✅ 安装 | "把已提取的课程 Markdown 整理成「得到·刘澜式」舒服可读的文稿：顶部本课总结、错别字/OCR 校对、三级子标题… | unknown | ⚪unknown | not_compared | Documentation,Python,Other |
| course-pdf-to-md | ✅ 安装 | "将课程类 PDF（得到/知识星球/小报童等导出，常配 MP3）批量整理为每章一个 Markdown 的流水线 skil… | unknown | ⚪unknown | not_compared | PDF/DOCX/PPTX/Spreadsheet,Python,Documentation |
| deploy-to-vercel | ✅ 安装 | Deploy applications and websites to Vercel. Use when the use… | unknown | ⚪unknown | not_compared | Deployment,Vercel,Git/GitHub |
| dida-task-manager | ✅ 安装 | "Dida365 / 滴答清单 习惯与任务操作的统一入口。覆盖新建/修改习惯（尤其『每天 N 次打卡才算完成』的量化习惯… | unknown | ⚪unknown | not_compared | Automation,MCP,Other |
| find-skills | ✅ 安装 | "帮助用户发现和安装智能体技能。当用户提出「如何做 X」、「查找某个技能」、「有没有能做……的技能」等问题，或表示希望扩… | unknown | ⚪unknown | not_compared | Skill Development,MCP,Other |
| frontend-design | ✅ 安装 | Guidance for distinctive, intentional visual design when bui… | official | 🟢active | not_compared | Frontend/UI,UX/Design Review |
| github | ✅ 安装 | "Interact with GitHub using the `gh` CLI. Use `gh issue`, `g… | unknown | ⚪unknown | not_compared | Git/GitHub,Other |
| github-portfolio-sync | ✅ 安装 | 当需要采集当前 GitHub 账号的公开和私有仓库，整理功能、技术栈与最新进度，并生成项目全景 Markdown 背景档… | unknown | ⚪unknown | not_compared | Git/GitHub,Documentation,MCP |
| github-readme-maintainer | ✅ 安装 | 当需要编写、重写、审查或维护 GitHub README、项目介绍、docs 结构、仓库说明，或补全仓库 About 简… | unknown | ⚪unknown | not_compared | Git/GitHub,Documentation |
| grill-me | ✅ 安装 | Interview the user relentlessly about a plan or design until… | unknown | ⚪unknown | not_compared | Agent/Workflow,Prompt Engineering,Other |
| guizang-ppt-skill | ✅ 安装 | 生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。提供两种风格… | unknown | ⚪unknown | not_compared | Frontend/UI,PDF/DOCX/PPTX/Spreadsheet,Other |
| hv-analysis | ✅ 安装 | 横纵分析法（Horizontal-Vertical Analysis）深度研究Skill。由数字生命卡兹克提出，融合了索… | community | 🟢active | upstream_in_sync | Research,PDF/DOCX/PPTX/Spreadsheet,Other |
| khazix-writer | ✅ 安装 | 数字生命卡兹克（Khazix）的公众号长文写作skill。当用户需要撰写公众号文章、写稿子、续写文章、根据素材产出长文时… | community | 🟢active | upstream_in_sync | Documentation,Prompt Engineering,Other |
| leader | ✅ 安装 | 把一句话的想法拆成 AI agent 能独立跑完的目标任务书。用户说「帮我给 agent 写个目标」「帮我详细拆一下这个… | unknown | ⚪unknown | upstream_in_sync | Agent/Workflow,Prompt Engineering,Other |
| local-service-change-acceptance | ✅ 安装 | 改完本地长驻服务（单文件 Python HTTP 服务、本地控制台后端、桌面应用的内嵌服务）后，如何在真机上做「可信验收… | unknown | ⚪unknown | not_compared | QA/Testing,Other |
| make-repo-contribution | ✅ 安装 | 'All changes to code must follow the guidance documented in … | unknown | ⚪unknown | not_compared | Git/GitHub,Other |
| manage-skills | ✅ 安装 | Manage the user's shared agent-skill library via skills-mana… | local | ➖not_applicable | not_compared | Skill Development,Git/GitHub,Other |
| mcp-one-command-setup | ✅ 安装 | Write a zero-dependency one-command installer for a local MC… | unknown | ⚪unknown | not_compared | MCP,Automation,Other |
| neat-freak | ✅ 安装 | Knowledge and governance closeout: reconcile project docs, r… | unknown | ⚪unknown | upstream_in_sync | Documentation,Agent/Workflow,Other |
| netlify-deploy | ✅ 安装 | Create, configure, and manage Netlify deploys from code — re… | unknown | ⚪unknown | not_compared | Deployment,Git/GitHub,Other |
| obsidian | ✅ 安装 | "Work with Obsidian vaults (plain Markdown notes) and automa… | unknown | ⚪unknown | not_compared | Documentation,Other |
| orca-cli | ⚠️ 缺失 | — | official | 🟢active | historical_official_version | Agent/Workflow,macOS,Windows,Git/GitHub |
| orca-codex-commands | ✅ 安装 | Use when Stage Manager needs to call Codex via Orca terminal… | unknown | ⚪unknown | not_compared | Agent/Workflow,Git/GitHub,Other |
| orchestration | ⚠️ 缺失 | — | official | 🟢active | historical_official_version | Agent/Workflow,Other |
| place-journal-qa | ✅ 安装 | 个人地点打卡手账（place-journal）项目的开发、测试与已知坑。适用于该工作区内 PWA 的迭代、QA 与部署准… | local | ➖not_applicable | not_compared | QA/Testing,Frontend/UI,Other |
| ponytail | ✅ 安装 | Forces the laziest solution that actually works, simplest, s… | unknown | ⚪unknown | not_compared | Agent/Workflow,Other |
| skill-creator | ✅ 安装 | Create new skills, modify and improve existing skills, and m… | official | 🟢active | not_compared | Skill Development,Other |
| skill-manager-governance | ✅ 安装 | 审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库。用户要求把中转站 skill 纳入中央库、解释… | local | ➖not_applicable | not_compared | Skill Development,Other |
| storage-analyzer | ✅ 安装 | macOS / Windows 只读存储分析助手（自动识别系统）。扫描整机磁盘占用，找出 占空间大户，把每一项分成 🟢可… | unknown | ⚪unknown | not_compared | macOS,Windows,Automation,Other |
| theme-factory | ✅ 安装 | Toolkit for styling artifacts with a theme. These artifacts … | official | 🟢active | not_compared | Frontend/UI,UX/Design Review,Other |
| travel-cn | ✅ 安装 | 旅行信息查询 - 去哪儿/携程/飞猪数据查询（Expedia 中国版） | unknown | ⚪unknown | not_compared | Research,Other |
| vercel-blocked-deploy-triage | ✅ 安装 | "当 Vercel 部署显示 UNKNOWN/BLOCKED、构建被跳过、提交作者校验失败，或部署成功但线上仍是旧版本时… | unknown | ⚪unknown | not_compared | Deployment,Vercel,Git/GitHub |
| weekly-review-standard | ✅ 安装 | "周复盘 / 月复盘的标准格式、详细度、颗粒度与踩坑库。当用户要求「做周复盘 / 周报 / 拉取一周数据复盘 / 生成复… | unknown | ⚪unknown | not_compared | Documentation,Automation,Other |
| win-reveal-and-gui-selftest | ✅ 安装 | 在 Windows 上实现「打开文件所在位置／在资源管理器中定位文件」，以及用窗口标题差分自测任何 GUI 动作是否真的… | unknown | ⚪unknown | not_compared | Windows,QA/Testing,Other |

> 同步副本 / `(2)` 别名明细：见 INSTALLED_SKILLS_FULL.md §副本与别名。本表 45 行 = CANONICAL_UNIQUE_SKILLS，与机器块一致。
