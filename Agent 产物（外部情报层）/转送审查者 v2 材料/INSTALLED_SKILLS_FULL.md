# Installed Skills Full Audit

> 自动扫描生成（只读，未安装/删除/修改任何 Skill；未修复符号链接、未改动安装结构）
> 更新时间：2026-09-22 13:55 (GMT+8)
> 数据基准：2026-09-22 13:55 扫描（约 14:23 检测到外部工具对中央仓库做过结构改动，未纳入本报告数据）
> 完整审计档案；来源映射见 SKILL_SOURCE_MAP.json；轻量日报背景见 INSTALLED_SKILLS_CONTEXT.md
> 概念边界：来源是谁 ≠ 针对什么平台 ≠ 上游是否存在 ≠ 上游是否活跃，四者严格分开

## 扫描范围与方法

实际存在的 Agent/Skill 环境（以文件系统为准）：
- `~/.skills-manager/skills/` — 中央仓库（用户级，41 个主副本，各 agent 的规范加载源）
- `~/.workbuddy/skills/` — WorkBuddy 用户级（多为指向 skills-manager 的符号链接 + dida-task-manager/place-journal-qa 实目录）
- `~/.claude/skills/` — Claude Code 用户级（符号链接）
- `~/.config/opencode/skills/` — OpenCode 用户级（符号链接 + browseros-neo/orca-codex-commands 实目录）
- `~/.agents/skills/` — Codex(.agents) 用户级（仅 browseros-neo 实目录）
- `/Users/zzymima0000/Downloads/大模型 HANDOFF/60 Skill 仓库/` — 项目级平行开发副本（13 个 skill 有副本；**非任何 agent 的加载路径**）

唯一 Skill 数：**45**；物理副本总数：**61**（冗余 16）。
去重方法：按 SKILL.md 真实路径(realpath)归并符号链接；多副本按 SKILL.md SHA256 实测判断内容是否一致。

## 一、来源映射（SKILL_SOURCE_MAP.json 摘要）

方法（第三轮修订）：只认**作者来源证据**——official=官方仓库/官方 LICENSE 版权/官方发布记录/与官方仓库历史 commit 逐字节一致；vendor=明确证据表明 Skill 由该厂商/团队提供（含文件内署名）；community=可确认第三方作者/社区来源；local=明确属于本机/用户项目自研；unknown=无法确认作者归属。
**『Skill 面向/调用某产品』一律记入 target_platform，不作为作者证据**（类比：本地写的 Vercel 部署 skill ≠ Vercel 官方 skill；本地写的 Orca CLI 操作 skill ≠ Orca 厂商发布）。绝不按名称猜作者。
第三轮交叉验证记录：orca-cli / orchestration / computer-use 与 stablyai/orca 历史 commit 逐字节一致（sha1 前12位：cddfd0a8c44e==f8b430f7、8dd31dae1235==1a9e819c、c79dedb3c7df==1a9e819c）；computer-use-2 内容（991f5dcdb2e5）与官方 skills/computer-use@b44ef1e5（2026-08-31）逐字节一致（本地仅目录改名）；browseros-neo 有官方管理清单 .browserclaw-managed.json 佐证（medium）；aihot 文件内署名 Virxact v1.2.0，官方渠道已 v1.7.1；orca-codex-commands 经官方全量 tree（29,540 路径）检索排除官方发布，维持 unknown。
第一/二轮修订记录：第一版曾因『面向 Orca/BrowserOS』判 vendor、『调用 aihot API』判 community，第二证据不足降回 unknown；第三轮以联网实证重新升级（见上）。

- 已确认来源（作者归属有证据）：**14**（official 8 ｜ vendor 1 ｜ community 2 ｜ local 3 ｜ fork 0 ｜ modified 0）
- 来源未知：**31**（orca-codex-commands 已排除官方发布；leader/neat-freak 有逐字节一致证据但待用户确认，见 pending_upgrade）

### official（8）
- **browseros-neo** ← github.com/browseros-ai/BrowserOS ｜ confidence=medium ｜ 证据：安装目录含 BrowserOS 官方管理清单 .browserclaw-managed.json（官方安装器管理标记）；内容与官方仓库 skill 高度同源，但与所查 3 个官方 commit 均非逐字节一致（官方持续演进）→ 判 official，confidence=medium。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 browseros-ai/BrowserOS 最近 push 2026-09-22）
- **computer-use** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：内容与官方仓库逐字节一致：本地 SKILL.md（c79dedb3c7df）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/computer-use/SKILL.md → 由 Orca 官方仓库发布。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **computer-use-2** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08-31）中 skills/computer-use/SKILL.md 逐字节一致 → 内容源自官方仓库（非本地修改；目录改名不改变来源归属）。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **frontend-design** ← github.com/anthropics/skills ｜ confidence=high ｜ 证据：LICENSE.txt (Apache)；SKILL.md 自述为 Anthropic 官方设计 skill（'Anthropic's own Claude-interaction accent'）。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10）
- **orca-cli** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：内容与官方仓库逐字节一致：本地 SKILL.md（sha1 前12位 cddfd0a8c44e）== stablyai/orca commit f8b430f7（2026-07-20）中 skills/orca-cli/SKILL.md，同算法实测 → 由 Orca 官方仓库发布（第二轮『仅面向产品』的保守判定据此撤销）。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **orchestration** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：内容与官方仓库逐字节一致：本地 SKILL.md（8dd31dae1235）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/orchestration/SKILL.md → 由 Orca 官方仓库发布。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **skill-creator** ← github.com/anthropics/skills ｜ confidence=high ｜ 证据：LICENSE.txt line 190: 'Copyright 2026 Anthropic, PBC.'（官方版权行）。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10）
- **theme-factory** ← github.com/anthropics/skills ｜ confidence=high ｜ 证据：LICENSE.txt line 190: 'Copyright 2026 Anthropic, PBC.'（官方版权行）。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10）

### vendor（1）
- **aihot** ← Virxact / AI HOT（aihot.virxact.com） ｜ confidence=high ｜ 证据：SKILL.md frontmatter 直接署名：metadata.author=Virxact、version=1.2.0（文件内作者证据，非『调用其 API』推断）；官方渠道当前版本 v1.7.1 同署名，版本谱系连续 → 由 AI HOT 服务方 Virxact 发布。
  - 活跃度：active（核验日 2026-09-22；官方渠道实测当前版本 v1.7.1（高于本地 1.2.0，持续更新中））

### community（2）
- **hv-analysis** ← 数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills ｜ confidence=high ｜ 证据：SKILL.md 明确标注方法由『数字生命卡兹克』提出；且内容与 github.com/KKKKhazix/khazix-skills 仓库中同名 skill 逐字节一致（本地 cb6227bf8ee4 == 上游实测）→ 作者归属与上游均确认，confidence 升为 high。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 KKKKhazix/khazix-skills 最近 push 2026-09-16）
- **khazix-writer** ← 数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills ｜ confidence=high ｜ 证据：SKILL.md 自述：『数字生命卡兹克（Khazix）的个人写作风格skill』——直接署名；且内容与 khazix-skills 仓库逐字节一致（本地 521606caa000 == 上游实测）。
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 KKKKhazix/khazix-skills 最近 push 2026-09-16）

### local（3）
- **manage-skills** ← 本地 skills-manager CLI ｜ confidence=high ｜ 证据：SKILL.md 自述管理『the user's shared agent-skill library via skills-manager-cli』——面向本机自建工具的运维 skill（对 anthropics/skills.git 的引用是它可安装的来源之一，非自身出处）。
- **place-journal-qa** ← place-journal 项目 ｜ confidence=high ｜ 证据：SKILL.md 自述为个人地点打卡手账 place-journal 项目的开发/测试 skill。
- **skill-manager-governance** ← 本地 Skill Manager / 60 Skill 仓库 ｜ confidence=high ｜ 证据：SKILL.md 自述『审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库』——本机 Skill Manager 体系配套 skill。

### unknown（部分示例，共 31）
- agent-central-mapping：无 source 字段、无作者/上游引用。
- ai-coding-homework-writeup：无 source 字段、无作者/上游引用。
- ai-quota-recovery-board：无 source 字段、无作者/上游引用。
- batch-organize：无 source 字段、无作者/上游引用。
- bilibili-download-check：面向 B 站投稿目录比对，无作者归属证据。
- browser-e2e-login-pitfalls：无 source 字段、无作者/上游引用。
- coding-workspace-organizer：无 source 字段、无作者/上游引用。
- course-md-organize：无 source 字段、无作者/上游引用。（NOTE: central 与 60 Skill 仓库副本内容不同，见 CONTENT_VARIANTS。）
- course-pdf-to-md：无 source 字段、无作者/上游引用。
- deploy-to-vercel：面向 Vercel 部署的 skill，无作者/发布方证据（类比：本地写的 Vercel 部署 skill ≠ Vercel 官方 skill）。
- dida-task-manager：封装 Dida365 API 的操作 skill，无法证明由滴答清单官方编写。
- find-skills：无 source 字段、无 anthropic/作者引用（仅提及 WorkBuddy/skills CLI 安装机制）。
- …（其余 19 个同口径：无作者来源证据）

### TARGET_PLATFORMS（面向产品登记，不作作者证据）
- AI HOT (aihot.virxact.com): aihot
- BrowserOS: browseros-neo
- Claude / Agent Skills: frontend-design, skill-creator, theme-factory
- Dida365（滴答清单）: dida-task-manager
- GitHub: github, github-portfolio-sync, github-readme-maintainer, make-repo-contribution
- Netlify: netlify-deploy
- Obsidian: obsidian
- Orca: computer-use, computer-use-2, orca-cli, orca-codex-commands, orchestration
- Vercel: deploy-to-vercel, vercel-blocked-deploy-triage
- place-journal（本机项目）: place-journal-qa
- skills-manager-cli（本机自建工具）: manage-skills
- 去哪儿/携程/飞猪（Expedia 中国版）: travel-cn
- 哔哩哔哩: bilibili-download-check
- 本地 Skill Manager: skill-manager-governance

## 总览统计

- 唯一 Skill：45
- 物理副本：61（冗余 16）
- 多平台/多目录副本：browseros-neo×3(agents/claude/opencode 同内容)；dida-task-manager 在 workbuddy 有平行副本
- 项目级平行副本：13 个 skill 在 60 Skill 仓库有副本（其中 1 个为内容变体；仓库副本不参与 agent 加载）
- 悬空符号链接：0（全部可正常解析）
- 内容变体（CONTENT_VARIANTS）：1（course-md-organize）
- 本地修改（LOCAL_MODIFIED，可证明基于上游的修改）：0（判定需上游基线；本轮已对 11 个联网验证项与官方上游逐字节比对，均一致、无可证明的本地修改）
- 安装冲突（INSTALLATION_CONFLICT）：0（各 agent 加载路径上的副本内容经 SHA256 实测一致；内容变体≠安装冲突）
- 已确认来源：14/45；来源未知：31/45

## 已有能力分类统计
- Other: 36
- Agent/Workflow: 11
- Documentation: 10
- Git/GitHub: 10
- Automation: 6
- Windows: 6
- Frontend/UI: 5
- Browser Automation: 5
- MCP: 5
- macOS: 5
- QA/Testing: 4
- Skill Development: 4
- Research: 3
- PDF/DOCX/PPTX/Spreadsheet: 3
- Deployment: 3
- Prompt Engineering: 3
- Python: 2
- Vercel: 2
- UX/Design Review: 2
- Education: 1

## 二、推荐抑制（CAPABILITY_SUPPRESSION 能力级 + INSTALLED_SKILL_OVERLAP 名称级）

两层分工：**日报推荐排序主要读取 CAPABILITY_SUPPRESSION（能力级）**；INSTALLED_SKILL_OVERLAP（名称级）仅用于解释本库内部具体关系。本节取代旧 DO_NOT_RECOMMEND_DUPLICATES / EXISTING_CAPABILITY_SUPPRESSION。

### CAPABILITY_SUPPRESSION（能力级，主去重依据）
strong = 新 Skill 若只是重复该能力，应明显降权；仅当带来明确新增能力时才推荐
medium = 已有较强覆盖，但允许明显更好的专项 Skill
weak   = 已有零散能力，欢迎完整方案
none   = 当前缺失，优先搜索

- **strong（重复即明显降权）**：github_ops, deployment_vercel, deployment_netlify, frontend_design, ui_theme, skill_creation, skill_management, course_pipeline, browser_automation, computer_use, orca_integration, research, writing
- **medium（允许明显更好的专项）**：productivity_personal, obsidian
- **weak（欢迎完整方案）**：security_audit, supabase_db, testing_qa, docx_xlsx, mcp_dev, windows, macos
- **none（缺失，优先搜索）**：mobile_qa, image_creative, data_analytics

### INSTALLED_SKILL_OVERLAP（名称级，解释用）
近重复：
- computer-use ≈ computer-use-2（同名近重复，computer-use-2 为细化版）
- find-skills ≈ manage-skills（技能安装/管理，~70% 重叠）
- skill-creator ≈ skill-manager-governance（修改现有 skill 编辑路径，~60% 重叠）
互补：
- course-pdf-to-md → course-md-organize（PDF提取→Markdown精校，流水线上下游，互补）
- frontend-design ↔ theme-factory（生成阶段设计方向 vs 主题样式应用，互补）
- guizang-ppt-skill ↔ theme-factory（网页PPT生成 vs 通用 artifact 主题，部分重叠）
- orca-cli ↔ computer-use ↔ orchestration（ORCA 三件套：工作树/终端、桌面GUI、多agent协调，互补）
- deploy-to-vercel ↔ vercel-blocked-deploy-triage（部署 vs 故障排查，互补）
- github ↔ github-readme-maintainer ↔ github-portfolio-sync ↔ make-repo-contribution（基础CLI vs 各专项，互补）
- khazix-writer ↔ hv-analysis（写作 vs 深度研究，互补）
- batch-organize 与 course-* 同属批量整理范式（互补）

## 三、健康与状态明细

### 🔗 INSTALLATION broken_link（悬空符号链接，内容正常）
- （无，全部符号链接可正常解析）

### ⚠️ INSTALLATION_CONFLICT（安装冲突：可能加载错版本/优先级不确定）
- （无。加载路径 = skills-manager / workbuddy / claude / opencode / agents 五处；60 Skill 仓库副本不在加载路径上；各加载路径多副本内容经 SHA256 实测一致。）

### 📄 CONTENT_VARIANTS（内容变体：同一 Skill 多位置内容版本不同）
- course-md-organize：central 与 60 Skill 仓库副本的 SKILL.md/assets/references/scripts/summaries.json 存在差异；repo 副本非加载路径 → 属内容变体，不构成安装冲突；需人工对齐。

### ✏️ LOCAL_MODIFIED（可证明基于上游/原版本的本地修改）
- （无可证明项：判定需先确认上游基线并比对；本轮已对 11 个联网验证项与官方上游逐字节比对，全部一致、无本地改动。『两份本地副本内容不同』只记 CONTENT_VARIANTS，不自动记 LOCAL_MODIFIED；computer-use-2 目录改名但内容与官方一致，不记修改。）

### 🟡 CONTENT warning（逐条，需审阅）
- secret/token 引用（经 .env/MCP 注入，未见硬编码）：github-readme-maintainer, netlify-deploy, neat-freak, mcp-one-command-setup, vercel-blocked-deploy-triage, storage-analyzer, skill-creator, ai-coding-homework-writeup, course-md-organize, course-pdf-to-md, github-portfolio-sync。
- rm -rf 引用：aihot, deploy-to-vercel（部署临时清理，需审阅脚本）。
- 网络/外部 CLI 依赖：aihot(curl), bilibili-download-check(curl/browser), travel-cn(curl), hv-analysis(curl+weasyprint), find-skills(npx), manage-skills(npx), guizang-ppt-skill(npx), skill-creator, storage-analyzer 等。

### ⚪ UPSTREAM_STATUS + UPSTREAM_ACTIVITY（两态分列，互不推断）
- identified（来源已确认）：14 个 — official 8（anthropics/skills×3 版权行；stablyai/orca×4 与官方 commit 逐字节一致；browseros-ai/BrowserOS×1 官方管理清单）、vendor 1（aihot，文件内署名 Virxact）、community 2（hv-analysis/khazix-writer，具名作者 + khazix-skills 逐字节一致）、local 3（manage-skills/skill-manager-governance/place-journal-qa，本机项目自建）。
- unknown（未确认）：31 个。其中 orca-codex-commands 已排除官方发布；leader/neat-freak 与 khazix-skills 逐字节一致，待用户确认后升级（pending_upgrade）。
- UPSTREAM_ACTIVITY（活跃度，2026-09-22 联网核验）：active 11 ｜ stale 0 ｜ deprecated 0 ｜ not_applicable 3（local，无外部上游） ｜ unknown 31（来源未知项不做活跃推断）。active 判定依据均为实测 recent push/release，非『URL 能打开』。

## 已安装 Skill 详情（按名称）

### agent-central-mapping
- 用途：当用户希望让 Claude Code、Codex、opencode、CodeArts Doer、Cursor、Gemini CLI、Zed、Windsurf 等编码 agent 从同一个中央仓库读取全局规则和 skill 时使用。必须先询问中央 AGENTS.md 和中央 skill 仓库的绝对路径，再识别目标工具、建立链接并验证工具实际加载了这些内容。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：是（2 份；内容一致）
- 能力标签：Agent/Workflow, Other
- 脚本/代码：py=0 js=0 ts=0 sh=1；scripts_dir=是
- 风险面引用：readlink×8, openai×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/agent-central-mapping

### ai-coding-homework-writeup
- 用途："本 skill 适用于「把 AI 辅助开发的编程作业写成一份能交的提交材料」这类任务。当用户拿出作业要求（例如『用 Expo/React Native 开发一个 App，提交一句话介绍、运行截图、页面结构、核心功能、数据库说明』），要求你根据项目实际情况代写、帮交作业、填提交材料时触发；用户抱怨材料『写太长了』『像 GitHub 说明』『复制会乱码』『图片不要放中间』时同样触发。它提供事实核实流程、长度红线、富文本（非 Markdown）输出规范，以及两个跨平台脚本：扫描项目事实、把内容清单渲染成富文本 HTML。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：Documentation, Education, Other
- 脚本/代码：py=2 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：git ×5, pip ×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/ai-coding-homework-writeup

### ai-quota-recovery-board
- 用途：当用户想跟踪多个 AI 工具 / 服务的「额度 / 频率限制 / 信用点」恢复时间并做成可视化看板时使用。生成单文件 HTML 看板（时间轴甘特 + 实时倒计时表 + 本地追加表单），数据存浏览器 localStorage 不上云。This skill should be used when the user wants to organize quota/credit/rate-limit reset reminders (from Dida365/TickTick "提醒日子" or from screenshots) into a visual timeline, or asks "哪个账号限额了、什么时候恢复、再过多久"。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Automation, Frontend/UI, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：mcp×4
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/ai-quota-recovery-board

### aihot
- 用途：查询 AI HOT 的中文 AI 资讯、精选、当前热点和日报。用户询问今天或最近的 AI 新闻、AI 圈动态、大模型或产品发布、OpenAI／Anthropic／Google 最新消息、AI 论文、AI 日报、AI HOT 精选、当前最热事件，或需要同步当前全部精选时使用。必须通过 aihot.virxact.com 的匿名只读 API 获取当前数据，不凭训练记忆回答新闻；不需要 API Key 或 MCP server。
- 来源：vendor ｜ 上游：Virxact / AI HOT（aihot.virxact.com） ｜ confidence=high ｜ 目标平台：AI HOT (aihot.virxact.com)
  - 证据：SKILL.md frontmatter 直接署名：metadata.author=Virxact、version=1.2.0（文件内作者证据，非『调用其 API』推断）；官方渠道当前版本 v1.7.1 同署名，版本谱系连续 → 由 AI HOT 服务方 Virxact 发布。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Research, Other
- 脚本/代码：py=0 js=0 ts=0 sh=1；scripts_dir=否
- 风险面引用：https://×28, curl×10, openai×7, rm -rf×2, mcp×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 脚本含 rm -rf（部署临时清理，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：vendor / Virxact / AI HOT（aihot.virxact.com）（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；官方渠道实测当前版本 v1.7.1（高于本地 1.2.0，持续更新中）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/aihot

### batch-organize
- 用途："本 skill 适用于「一批杂乱原始素材 → 统一规范成品」且需可重跑、可中断、可多智能体协作的批量整理任务（课程/播客/视频转写稿清洗、PDF 抽取稿整理、文档/知识库迁移、素材库去重归类等）。它提供通用分阶段流程、状态位(幂等)机制，以及「大模型管语义判断、脚本管确定性装配」的分工契约；具体提示词与脚本需按任务填充占位符。本身不认识具体素材，套用请复制骨架并替换占位符。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：Agent/Workflow, Documentation, Other
- 脚本/代码：py=2 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：无
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 course-* 流水线同属批量整理范式（互补）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/batch-organize

### bilibili-download-check
- 用途：当需要对比哔哩哔哩 UP 主投稿目录与本地已下载视频、生成未下载清单，或按红利/打新等关键词筛选时使用。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：哔哩哔哩
  - 证据：面向 B 站投稿目录比对，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：是（2 份；内容一致）
- 能力标签：Browser Automation, Other
- 脚本/代码：py=1 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：https://×4, browser×3, fetch(×3, curl×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/bilibili-download-check

### browser-e2e-login-pitfalls
- 用途："浏览器端 E2E / 验收测试的踩坑与避坑手册：Vite 环境变量未注入、Google OAuth 拦截自动化浏览器（Chrome for Testing）、多 Chrome 窗口 activate 认错、Supabase OAuth 回调回落到错误 origin、supabase-js 默认 return=minimal 导致响应体无字段。当需要「浏览器验收 / E2E 测试 / 点登录 / 抓 Network 回执 / 测云同步」时使用。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Browser Automation, QA/Testing, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×36, .env×9, curl×6, http://×6, token×5, requests×3, playwright×2, Authorization×1, bearer×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/browser-e2e-login-pitfalls

### browseros-neo
- 用途：The user's dedicated browser for agents — a real browser signed into their accounts, with live logins and a persistent profile. Use it for any task that touches a website or browser (open, read, act, fill, sign in, download, verify). The user installed it precisely so agents default here unprompted — over in-app browser tools, devtools/playwright automation, or headless fetching. When the user say…
- 来源：official ｜ 上游：github.com/browseros-ai/BrowserOS ｜ confidence=medium ｜ 目标平台：BrowserOS
  - 证据：安装目录含 BrowserOS 官方管理清单 .browserclaw-managed.json（官方安装器管理标记）；内容与官方仓库 skill 高度同源，但与所查 3 个官方 commit 均非逐字节一致（官方持续演进）→ 判 official，confidence=medium。
- 安装位置：用户级（agent 目录）
- 可用 Agent：claude
- 多副本：是（3 份；内容一致）
- 能力标签：Browser Automation, MCP, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×20, mcp×1, playwright×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/browseros-ai/BrowserOS（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 browseros-ai/BrowserOS 最近 push 2026-09-22
- 规范路径：/Users/zzymima0000/.claude/skills/browseros-neo

### coding-workspace-organizer
- 用途：整理编码工作区：拍平嵌套归档目录，按 `NNN-状态-项目名` 规则重命名项目，并生成按序号查找的索引表。用户要求整理工作区、给项目文件夹编号、按序号排序、拍平暂停或归档目录，或在 Windows / macOS 上复用同一命名方案时使用。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：macOS, Windows, Automation, Other
- 脚本/代码：py=1 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：git ×4, shutil×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/coding-workspace-organizer

### computer-use
- 用途：- Use Orca's computer-use CLI to inspect and operate local desktop app windows through accessibility trees, screenshots, and safe UI actions. Use for desktop app interaction: list apps/windows, get app state, read visible UI, click controls, type, press keys, scroll, drag, set values, or perform accessibility actions. Also use for browser windows, webviews, Orca app UI, or other desktop UI. Trigge…
- 来源：official ｜ 上游：github.com/stablyai/orca ｜ confidence=high ｜ 目标平台：Orca
  - 证据：内容与官方仓库逐字节一致：本地 SKILL.md（c79dedb3c7df）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/computer-use/SKILL.md → 由 Orca 官方仓库发布。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, macOS, Windows, Browser Automation
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/stablyai/orca（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22
- 与其他 Skill：
  - 与 computer-use-2 同名近重复（后者为细化版，建议合并/保留其一）
  - 与 orca-cli、orchestration 互补（ORCA 三件套）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/computer-use

### computer-use-2
- 用途：- Use Orca's computer-use CLI for OS/window-level inspection and input in visible local app windows. Use when a task must read or operate a native app or an external browser window (for example, Chrome, Edge, or Safari) or an app webview. Do not use for Orca's embedded browser or page-only browser automation. Use `orca-cli` for Orca's embedded pages and a page-automation tool such as Playwright or…
- 来源：official ｜ 上游：github.com/stablyai/orca ｜ confidence=high ｜ 目标平台：Orca
  - 证据：本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08-31）中 skills/computer-use/SKILL.md 逐字节一致 → 内容源自官方仓库（非本地修改；目录改名不改变来源归属）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, macOS, Windows, Browser Automation
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×6, playwright×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/stablyai/orca（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22
- 与其他 Skill：
  - 与 computer-use 同名近重复（本品为细化版）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/computer-use-2

### course-md-organize
- 用途："把已提取的课程 Markdown 整理成「得到·刘澜式」舒服可读的文稿：顶部本课总结、错别字/OCR 校对、三级子标题逻辑分段、段落自然流动。用于 OCR/语音转写稿存在文字墙、错字、无结构的一批课程 .md，做批量、一致的重排版与精校。脚本阶段用 Python 标准库（无需依赖）；语义阶段由 LLM 执行。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。（NOTE: central 与 60 Skill 仓库副本内容不同，见 CONTENT_VARIANTS。）
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容存在变体）
- 能力标签：Documentation, Python, Other
- 脚本/代码：py=5 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：token×13, .env×7, openai×5, pip ×3, git ×2, shutil×1
- 内容变体：是（CONTENT_VARIANT：central 与 repo 副本内容不同；repo 非加载路径，非安装冲突）
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 course-pdf-to-md 互补（上游提取结果精校）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/course-md-organize

### course-pdf-to-md
- 用途："将课程类 PDF（得到/知识星球/小报童等导出，常配 MP3）批量整理为每章一个 Markdown 的流水线 skill。当用户需要：把一批课程 PDF 按章节提取文字稿、清洗平台声明/水印/评论区、原素材与文稿物理分离、文件名数字有序规整、顶部生成「本课总结」、或跨电脑/换智能体迁移复用该流水线时，使用此 skill。覆盖双通道提取（文本直取/图片切片OCR）、后处理三阶段与集合级批量三件套（process_collection / cleanup_collection / fill_summaries）。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：PDF/DOCX/PPTX/Spreadsheet, Python, Documentation
- 脚本/代码：py=11 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：pip ×21, token×11, .env×8, subprocess×7, shutil×5, git ×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 course-md-organize 互补（PDF提取→MD精校，流水线上下游）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/course-pdf-to-md

### deploy-to-vercel
- 用途：Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push this live", or "create a preview deployment".
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：Vercel
  - 证据：面向 Vercel 部署的 skill，无作者/发布方证据（类比：本地写的 Vercel 部署 skill ≠ Vercel 官方 skill）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Deployment, Vercel, Git/GitHub
- 脚本/代码：py=0 js=0 ts=0 sh=2；scripts_dir=否
- 风险面引用：git ×24, curl×5, https://×5, .env×5, rm -rf×2, browser×1, requests×1, npm ×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 脚本含 rm -rf（部署临时清理，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 vercel-blocked-deploy-triage 互补（部署 vs 故障排查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/deploy-to-vercel

### dida-task-manager
- 用途："Dida365 / 滴答清单 习惯与任务操作的统一入口。覆盖新建/修改习惯（尤其『每天 N 次打卡才算完成』的量化习惯正确模板）、任务自动归类路由、习惯图标规则、倒数日只读边界。当用户说『新建习惯/打卡 N 次/建待办/提醒/排日程/复盘』时触发。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：Dida365（滴答清单）
  - 证据：封装 Dida365 API 的操作 skill，无法证明由滴答清单官方编写。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：是（2 份；内容一致）
- 能力标签：Automation, MCP, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：mcp×4
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/dida-task-manager

### find-skills
- 用途："帮助用户发现和安装智能体技能。当用户提出「如何做 X」、「查找某个技能」、「有没有能做……的技能」等问题，或表示希望扩展功能时使用。当用户正在寻找可能作为可安装技能存在的功能时，应使用此技能。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无 anthropic/作者引用（仅提及 WorkBuddy/skills CLI 安装机制）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Skill Development, MCP, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：npx ×18, https://×4, git ×1, playwright×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 manage-skills 高度重叠（均做技能安装/管理，~70%）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/find-skills

### frontend-design
- 用途：Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults.
- 来源：official ｜ 上游：github.com/anthropics/skills ｜ confidence=high ｜ 目标平台：Claude / Agent Skills
  - 证据：LICENSE.txt (Apache)；SKILL.md 自述为 Anthropic 官方设计 skill（'Anthropic's own Claude-interaction accent'）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Frontend/UI, UX/Design Review
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：token×2, http://×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/anthropics/skills（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10
- 与其他 Skill：
  - 与 theme-factory 互补（设计方向 vs 主题样式应用）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/frontend-design

### github
- 用途："Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` for issues, PRs, CI runs, and advanced queries."
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：GitHub
  - 证据：封装 gh CLI 操作 GitHub，无作者归属证据（≠ GitHub 官方发布）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Git/GitHub, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：https://×2, git ×1, requests×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 github-readme-maintainer/github-portfolio-sync/make-repo-contribution 互补（基础CLI vs 专项）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/github

### github-portfolio-sync
- 用途：当需要采集当前 GitHub 账号的公开和私有仓库，整理功能、技术栈与最新进度，并生成项目全景 Markdown 背景档案时使用。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：GitHub
  - 证据：面向 GitHub 仓库数据采集，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：Git/GitHub, Documentation, MCP
- 脚本/代码：py=1 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：token×8, npm ×4, subprocess×3, git ×2, .env×2, https://×1, mcp×1, pip3×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 github 互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/github-portfolio-sync

### github-readme-maintainer
- 用途：当需要编写、重写、审查或维护 GitHub README、项目介绍、docs 结构、仓库说明，或补全仓库 About 简介（Description / Website / Topics）时使用。默认基于真实仓库内容生成简体中文 README.md，并维护 README.en.md；禁止凭空编造功能。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：GitHub
  - 证据：面向 GitHub README 维护，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：Git/GitHub, Documentation
- 脚本/代码：py=1 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：git ×6, secret×4, token×4, api_key×2, http://×1, https://×1, urllib×1, openai×1, .env×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 github 互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/github-readme-maintainer

### grill-me
- 用途：Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, Prompt Engineering, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：https://×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/grill-me

### guizang-ppt-skill
- 用途：生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。提供两种风格：① "电子杂志 × 电子墨水"（衬线 + 流体背景 + 暖色） ② "瑞士国际主义"（无衬线 + 网格点阵 + IKB/柠檬黄/柠檬绿/安全橙高亮）。当用户需要制作分享 / 演讲 / 发布会风格的网页 PPT，或提到"杂志风 PPT"、"瑞士风 PPT"、"Swiss Style"、"horizontal swipe deck"时使用。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Frontend/UI, PDF/DOCX/PPTX/Spreadsheet, Other
- 脚本/代码：py=0 js=1 ts=0 sh=0；scripts_dir=是
- 风险面引用：https://×71, token×12, git ×12, browser×6, npx ×4, exec(×1, requests×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 theme-factory 部分重叠（网页PPT样式）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/guizang-ppt-skill

### hv-analysis
- 用途：横纵分析法（Horizontal-Vertical Analysis）深度研究Skill。由数字生命卡兹克提出，融合了索绪尔的历时-共时分析、社会科学的纵向-横截面研究设计、商学院案例研究法与竞争战略分析的核心思想。 当用户想要系统性研究一个产品、公司、概念、技术或人物时使用。核心是双轴分析：纵轴追踪从诞生到当下的完整生命历程（以叙事故事呈现），横轴在当下时间截面上与竞品/同类进行系统性横向对比，最后交叉两条轴产出独到洞察。最终产出一份排版精美的PDF研究报告。 触发词包括但不限于：横纵分析、研究一下、帮我分析、深度研究、做个研究、调研一下、竞品分析、帮我看看这个东西怎么样、这个产品/公司/概念是怎么回事、帮我摸清楚、帮我搞懂、帮我做个deep research。 即使用户只是说"帮我了解一下XX"或"XX是什么来头"，只要上下文暗示需要系统性的深度研究（而非简单的概念解释），都应该触发。…
- 来源：community ｜ 上游：数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills ｜ confidence=high
  - 证据：SKILL.md 明确标注方法由『数字生命卡兹克』提出；且内容与 github.com/KKKKhazix/khazix-skills 仓库中同名 skill 逐字节一致（本地 cb6227bf8ee4 == 上游实测）→ 作者归属与上游均确认，confidence 升为 high。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Research, PDF/DOCX/PPTX/Spreadsheet, Other
- 脚本/代码：py=1 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：pip ×3, https://×2, curl×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：community / 数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 KKKKhazix/khazix-skills 最近 push 2026-09-16
- 与其他 Skill：
  - 与 khazix-writer 互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/hv-analysis

### khazix-writer
- 用途：数字生命卡兹克（Khazix）的公众号长文写作skill。当用户需要撰写公众号文章、写稿子、续写文章、根据素材产出长文时使用。触发词包括但不限于：写文章、写稿子、帮我写、续写、扩写、公众号文章、长文、出稿、按我的风格写。即使用户只是说"帮我把这个写成文章"或"用我的风格写一下"，只要上下文涉及内容创作和公众号输出，都应该触发。也适用于用户丢过来一个PDF、brief、新闻链接、语音转文字或任何素材说"帮我写篇文章"的场景。不要用于短内容（小红书帖子、推特、朋友圈）或纯标题摘要生成（那个用wechat-title skill）。
- 来源：community ｜ 上游：数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills ｜ confidence=high
  - 证据：SKILL.md 自述：『数字生命卡兹克（Khazix）的个人写作风格skill』——直接署名；且内容与 khazix-skills 仓库逐字节一致（本地 521606caa000 == 上游实测）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Documentation, Prompt Engineering, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：无
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：community / 数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 KKKKhazix/khazix-skills 最近 push 2026-09-16
- 与其他 Skill：
  - 与 hv-analysis 互补（写作 vs 研究；hv-analysis 明确把写作交给本 skill）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/khazix-writer

### leader
- 用途：把一句话的想法拆成 AI agent 能独立跑完的目标任务书。用户说「帮我给 agent 写个目标」「帮我详细拆一下这个目标」「写个任务书/brief 给 agent」「写个 goal 提示词」「让 agent 自己跑这个项目」「把活分给几个 agent 并行」时使用。先进代码库实测、必要时联网调研，再一次性提问（≤5 个），产出一份 ≤4000 字符、直接粘进 /goal 就能跑的任务书，含实测数字、白名单地界、防作弊验收和断点续跑。执行型与探索型（调研/选型/找方案）自动分流。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无文件内署名；但内容与 github.com/KKKKhazix/khazix-skills 中同名 skill 逐字节一致（本地 018fe973901c == 上游实测）——作者归属证据已具备，待用户确认后可升级 community（pending_upgrade）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, Prompt Engineering, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：git ×4, token×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/leader

### local-service-change-acceptance
- 用途：改完本地长驻服务（单文件 Python HTTP 服务、本地控制台后端、桌面应用的内嵌服务）后，如何在真机上做「可信验收」——把用户真实数据撇开、用隔离目录跑端到端、以及识破「乐观状态位」「去重计数翻倍」「新字段没清零」这三类假通过/假失败。当用户说「改完了帮我验一下」「重启服务」「为什么状态显示不对」「验收不通过但看不出原因」时使用。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：是（2 份；内容一致）
- 能力标签：QA/Testing, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：无
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/local-service-change-acceptance

### make-repo-contribution
- 用途：'All changes to code must follow the guidance documented in the repository. Before any issue is filed, branch is made, commits generated, or pull request (or PR) created, a search must be done to ensure the right steps are followed. Whenever asked to create an issue, commit messages, to push code, or create a PR, use this skill so everything is done correctly.'
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：GitHub
  - 证据：面向 GitHub 仓库贡献流程，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Git/GitHub, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：requests×3, npm ×2, secret×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 github 互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/make-repo-contribution

### manage-skills
- 用途：Manage the user's shared agent-skill library via skills-manager-cli — install, update, remove, deploy or undeploy skills per agent, manage presets, organize tags, search, and adopt existing skills. Use this whenever the user wants Claude Code, Codex, Cursor, or another agent to gain or lose a skill, wants to organize the central library, or asks what is installed or deployed. Prefer this over dire…
- 来源：local ｜ 上游：本地 skills-manager CLI ｜ confidence=high ｜ 目标平台：skills-manager-cli（本机自建工具）
  - 证据：SKILL.md 自述管理『the user's shared agent-skill library via skills-manager-cli』——面向本机自建工具的运维 skill（对 anthropics/skills.git 的引用是它可安装的来源之一，非自身出处）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：opencode, skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Skill Development, Git/GitHub, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：git ×8, https://×6, npx ×2, requests×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：local / 本地 skills-manager CLI（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: ➖ not_applicable（本地自建，无外部上游） — 核验日 ；本地自建，无外部上游
- 与其他 Skill：
  - 与 find-skills 高度重叠（均做技能安装/管理）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/manage-skills

### mcp-one-command-setup
- 用途：Write a zero-dependency one-command installer for a local MCP (Model Context Protocol) server: auto-build, detect which AI clients are installed on this machine, safely patch each client's config (JSON and TOML) while preserving every other entry, then verify by driving a real stdio JSON-RPC handshake instead of trusting that "the config got written". Use when the user wants end users to onboard a…
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：MCP, Automation, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：mcp×23, token×2, http://×1, npm ×1, bearer×1, .env×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/mcp-one-command-setup

### neat-freak
- 用途：- Knowledge and governance closeout: reconcile project docs, rule files (CLAUDE.md/AGENTS.md), authorized agent memory, and workspace residue with what the code and runtime actually do, so the next session or the next person starts from one current answer. Trigger when the user names "neat-freak", "洁癖", or "/neat" — and also on clear knowledge-closeout intent without the name: syncing or tidying p…
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无文件内署名（v3.0.0，仅泛引 Agent Skills 标准）；但内容与 github.com/KKKKhazix/khazix-skills 中同名 skill 逐字节一致（本地 c4dbe94169ed == 上游实测）——待用户确认后可升级 community（pending_upgrade）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Documentation, Agent/Workflow, Other
- 脚本/代码：py=3 js=4 ts=5 sh=2；scripts_dir=是
- 风险面引用：token×26, git ×15, .env×13, npm ×11, Authorization×7, https://×6, secret×5, curl×4, http://×4, openai×4, readlink×3, pip ×2, bearer×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 知识治理收尾，与 skill-manager-governance 不同域（后者管 skill 库）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/neat-freak

### netlify-deploy
- 用途：Create, configure, and manage Netlify deploys from code — reach for this when setting up Git continuous deployment, running netlify deploy or netlify deploy --prod from the CLI, writing netlify.toml deploy contexts, adding a Deploy to Netlify button, wiring build hooks, configuring Deploy Previews or branch deploys, locking or skipping deploys, fixing a failed or secrets-scanning deploy, or when s…
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：Netlify
  - 证据：面向 Netlify 部署的 skill，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Deployment, Git/GitHub, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：secret×22, git ×15, https://×14, .env×9, token×7, npm ×6, browser×4, password×2, npx ×1, openai×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 deploy-to-vercel 同属部署类，互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/netlify-deploy

### obsidian
- 用途："Work with Obsidian vaults (plain Markdown notes) and automate via obsidian-cli."
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：Obsidian
  - 证据：面向 Obsidian vault 操作，无作者归属证据（≠ Obsidian 官方发布）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Documentation, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：https://×4
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/obsidian

### orca-cli
- 用途：- Use the public `orca` CLI to operate Orca-managed worktrees, folder contexts, terminals, repos, automations, worktree comments, and the browser embedded inside the Orca app. Use when the user says "$orca-cli", "use orca cli", "Orca worktree", "child worktree", "cardStatus", "spawn codex/claude in a worktree", "read/wait/send Orca terminal", "terminal send", "full handoff", "handover", "give this…
- 来源：official ｜ 上游：github.com/stablyai/orca ｜ confidence=high ｜ 目标平台：Orca
  - 证据：内容与官方仓库逐字节一致：本地 SKILL.md（sha1 前12位 cddfd0a8c44e）== stablyai/orca commit f8b430f7（2026-07-20）中 skills/orca-cli/SKILL.md，同算法实测 → 由 Orca 官方仓库发布（第二轮『仅面向产品』的保守判定据此撤销）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, macOS, Windows, Git/GitHub
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×8, git ×1, playwright×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/stablyai/orca（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22
- 与其他 Skill：
  - 与 computer-use、orchestration 互补（ORCA 三件套：工作树/终端 vs 桌面GUI vs 多agent协调）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/orca-cli

### orca-codex-commands
- 用途：- Use when Stage Manager needs to call Codex via Orca terminal. Provides the exact commands for creating terminals, sending commands, monitoring progress, and handling common errors. Use when the user says "call codex", "dispatch to codex", "send task to codex", "codex terminal", "orca terminal codex", or similar.
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：Orca
  - 证据：排除法证据：对官方仓库 stablyai/orca 全量 tree（29,540 个路径，无截断）检索，不存在 skills/orca-codex-commands → 可排除官方发布；又无其他作者归属证据 → 维持 unknown。
- 安装位置：用户级（agent 目录）
- 可用 Agent：opencode
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, Git/GitHub, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：无
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 orca-cli 同属 ORCA 平台集成，部分重叠
- 规范路径：/Users/zzymima0000/.config/opencode/skills/orca-codex-commands

### orchestration
- 用途：- Use Orca orchestration for structured multi-agent coordination: threaded messages, blocking ask/reply flows, task dispatch, worker_done/escalation waits, task DAGs, decision gates, coordinator loops, or decomposing work across agents. Use `orca-cli` instead for full ownership handoffs, including requests phrased as "hand off", "handoff", "handover", "give this to another agent", or "another work…
- 来源：official ｜ 上游：github.com/stablyai/orca ｜ confidence=high ｜ 目标平台：Orca
  - 证据：内容与官方仓库逐字节一致：本地 SKILL.md（8dd31dae1235）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/orchestration/SKILL.md → 由 Orca 官方仓库发布。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×4, requests×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/stablyai/orca（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22
- 与其他 Skill：
  - 与 orca-cli、computer-use 互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/orchestration

### place-journal-qa
- 用途：个人地点打卡手账（place-journal）项目的开发、测试与已知坑。适用于该工作区内 PWA 的迭代、QA 与部署准备。
- 来源：local ｜ 上游：place-journal 项目 ｜ confidence=high ｜ 目标平台：place-journal（本机项目）
  - 证据：SKILL.md 自述为个人地点打卡手账 place-journal 项目的开发/测试 skill。
- 安装位置：用户级（agent 目录）
- 可用 Agent：workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：QA/Testing, Frontend/UI, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：browser×6, npm ×3, npx ×1, .env×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：local / place-journal 项目（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: ➖ not_applicable（本地自建，无外部上游） — 核验日 ；本地自建，无外部上游
- 规范路径：/Users/zzymima0000/.workbuddy/skills/place-journal-qa

### ponytail
- 用途：Forces the laziest solution that actually works, simplest, shortest, most minimal. Channels a senior dev who has seen everything: question whether the task needs to exist at all (YAGNI), reach for the standard library before custom code, native platform features before dependencies, one line before fifty. Supports intensity levels: lite, full (default), ultra. Use on ANY coding task: writing, addi…
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Agent/Workflow, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：requests×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/ponytail

### skill-creator
- 用途：Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
- 来源：official ｜ 上游：github.com/anthropics/skills ｜ confidence=high ｜ 目标平台：Claude / Agent Skills
  - 证据：LICENSE.txt line 190: 'Copyright 2026 Anthropic, PBC.'（官方版权行）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Skill Development, Other
- 脚本/代码：py=10 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：token×44, browser×14, subprocess×13, http://×3, https://×3, requests×3, .env×2, api_key×1, mcp×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/anthropics/skills（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10
- 与其他 Skill：
  - 与 skill-manager-governance 编辑路径高度重叠（~60%）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/skill-creator

### skill-manager-governance
- 用途：审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库。用户要求把中转站 skill 纳入中央库、解释为什么软件看不到、或迁移到 Windows、macOS 或其他智能体时使用。
- 来源：local ｜ 上游：本地 Skill Manager / 60 Skill 仓库 ｜ confidence=high ｜ 目标平台：本地 Skill Manager
  - 证据：SKILL.md 自述『审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库』——本机 Skill Manager 体系配套 skill。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：Skill Development, Other
- 脚本/代码：py=1 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：token×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：local / 本地 Skill Manager / 60 Skill 仓库（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: ➖ not_applicable（本地自建，无外部上游） — 核验日 ；本地自建，无外部上游
- 与其他 Skill：
  - 与 skill-creator 编辑路径高度重叠
- 规范路径：/Users/zzymima0000/.skills-manager/skills/skill-manager-governance

### storage-analyzer
- 用途：macOS / Windows 只读存储分析助手（自动识别系统）。扫描整机磁盘占用，找出 占空间大户，把每一项分成 🟢可自动清理 / 🟡需人工判断 / 🔴谨慎清理 三级并给出 可执行处置方案，生成排版精美、可折叠、命令可一键复制的交互式 HTML 报告，并可 起本地服务在网页上一键删除（移废纸篓/直接删）。扫描全程只读。务必在以下场景 使用：用户说"存储分析""磁盘满了""C盘/硬盘满了""空间不够""清理空间" "清理磁盘""占空间""哪些东西占地方""帮我看看存储""看一下电脑存储/空间" "存储空间""电脑空间不够""内存满了/不够/不足""看下内存/存储"（中文口语里 "内存"常指存储空间）"storage analysis""disk cleanup""清缓存""磁盘清理"； 或用户抱怨电脑没空间、想知道什么东西吃硬盘、想要清理建议时。注意：若用户明确 指运行内存/RAM（如"哪…
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：macOS, Windows, Automation, Other
- 脚本/代码：py=3 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：token×11, .env×11, subprocess×8, shutil×8, browser×3, secret×2, playwright×2, http://×1, pip ×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/storage-analyzer

### theme-factory
- 用途：Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly.
- 来源：official ｜ 上游：github.com/anthropics/skills ｜ confidence=high ｜ 目标平台：Claude / Agent Skills
  - 证据：LICENSE.txt line 190: 'Copyright 2026 Anthropic, PBC.'（官方版权行）。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Frontend/UI, UX/Design Review, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：http://×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: 🔵 已识别 — 来源已确认：official / github.com/anthropics/skills（identified 仅指作者归属确认）
  - UPSTREAM_ACTIVITY: 🟢 active（联网核验） — 核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10
- 与其他 Skill：
  - 与 frontend-design 互补；与 guizang-ppt-skill 部分重叠（artifact 样式）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/theme-factory

### travel-cn
- 用途：旅行信息查询 - 去哪儿/携程/飞猪数据查询（Expedia 中国版）
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：去哪儿/携程/飞猪（Expedia 中国版）
  - 证据：面向旅行服务数据查询，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：否（1 份；内容一致）
- 能力标签：Research, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：https://×3, curl×2, pip ×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/travel-cn

### vercel-blocked-deploy-triage
- 用途："当 Vercel 部署显示 UNKNOWN/BLOCKED、构建被跳过、提交作者校验失败，或部署成功但线上仍是旧版本时使用；先诊断原因，再按授权执行解除措施。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a ｜ 目标平台：Vercel
  - 证据：面向 Vercel 部署故障排查的 skill，无作者归属证据。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：claude, opencode, skills-manager, workbuddy
- 多副本：是（2 份；内容一致）
- 能力标签：Deployment, Vercel, Git/GitHub
- 脚本/代码：py=2 js=0 ts=0 sh=0；scripts_dir=是
- 风险面引用：git ×48, token×37, urllib×10, .env×6, https://×3, subprocess×2, fetch(×2, bearer×2, curl×1, Authorization×1
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 引用 secret/token（经 .env/MCP 注入，未见硬编码，需审阅）
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 与其他 Skill：
  - 与 deploy-to-vercel 互补
- 规范路径：/Users/zzymima0000/.skills-manager/skills/vercel-blocked-deploy-triage

### weekly-review-standard
- 用途："周复盘 / 月复盘的标准格式、详细度、颗粒度与踩坑库。当用户要求「做周复盘 / 周报 / 拉取一周数据复盘 / 生成复盘看板 / 月度复盘」时触发，确保一次到位、不返工。覆盖 9 板块结构、各段详细度要求、B 快乐四象限按象限聚合、睡眠 SVG 折线图、习惯真实打卡率、长文分段、确认落盘门槛。与 dida-task-manager 互补（本 skill 管格式标准，dida-task-manager 管滴答增删改查机制）。"
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager, workbuddy
- 多副本：否（1 份；内容一致）
- 能力标签：Documentation, Automation, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：无
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: ✅ 正常
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/weekly-review-standard

### win-reveal-and-gui-selftest
- 用途：在 Windows 上实现「打开文件所在位置／在资源管理器中定位文件」，以及用窗口标题差分自测任何 GUI 动作是否真的发生（含沙箱里跑 Bash/PowerShell 的进程与窗口可见性坑）。当用户说「点击后打开访达失效了」「改成打开文件所在位置」「explorer /select 定位错了」「怎么验证真的弹了窗口」「沙箱里怎么自测 GUI」时使用。
- 来源：unknown ｜ 上游：unknown ｜ confidence=n/a
  - 证据：无 source 字段、无作者/上游引用。
- 安装位置：用户级（skills-manager 中央仓库）
- 可用 Agent：skills-manager
- 多副本：是（2 份；内容一致）
- 能力标签：Windows, QA/Testing, Other
- 脚本/代码：py=0 js=0 ts=0 sh=0；scripts_dir=否
- 风险面引用：curl×3, git ×2, subprocess×2
- 本地修改（可证明）：未检出（无上游基线可比对）
- 健康与状态：
  - CONTENT_HEALTH: 🟡 需审阅 — 依赖网络/外部 CLI，离线环境可能受限
  - INSTALLATION_HEALTH: ✅ 正常
  - UPSTREAM_STATUS: ⚪ 未识别 — 来源未确认（只能确认操作对象，无法证明作者归属）
  - UPSTREAM_ACTIVITY: ⚪ unknown（未核验/无上游可查）
- 规范路径：/Users/zzymima0000/.skills-manager/skills/win-reveal-and-gui-selftest
