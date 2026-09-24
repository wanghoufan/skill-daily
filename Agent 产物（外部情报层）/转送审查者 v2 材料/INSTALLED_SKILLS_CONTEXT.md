# Installed Skills Context

> 自动扫描生成（只读，未安装/删除/修改任何 Skill；未修复符号链接、未改动安装结构）
> 更新时间：2026-09-22 13:55 (GMT+8)
> 数据基准：2026-09-22 13:55 扫描（约 14:23 检测到外部工具对中央仓库做过结构改动——3 个 Orca 主副本被移除、新增 7 个『(2)』重复目录；本轮整改范围不含安装结构，该变动未纳入本报告数据）
> 用途：供 Skill 情报日报进行能力级去重推荐、来源判断与健康检查（机器可读、轻量）
> 配套：SKILL_SOURCE_MAP.json（来源映射层）｜ INSTALLED_SKILLS_FULL.md（完整审计）
> 概念边界：来源是谁 ≠ 针对什么平台 ≠ 上游是否存在 ≠ 上游是否活跃，四者严格分开

## 1. 总览

- 唯一 Skill 数：**45**
- 物理副本总数：61（含 16 个冗余副本）
- 用户级（skills-manager 中央仓库）：41 个主副本
- 项目级（60 Skill 仓库平行开发副本）：13 个（其中 1 个为内容变体，均不参与 agent 加载）
- **已确认来源（作者归属有证据）：14**（official 8 ｜ vendor 1 ｜ community 2 ｜ local 3 ｜ fork 0 ｜ modified 0）
- **来源未知：31**（只能确认操作对象、无法证明作者归属；orca-codex-commands 已经官方全量 tree 检索排除官方发布）

### 健康与状态
- CONTENT_HEALTH（内容）：healthy 18 ｜ warning 27 ｜ broken 0
- INSTALLATION_HEALTH（安装/加载路径）：healthy 45 ｜ broken_link 0（安装冲突单列 INSTALLATION_CONFLICT）
- UPSTREAM_STATUS（来源确认态）：identified 14 ｜ unknown 31（identified≠活跃，活跃度见 UPSTREAM_ACTIVITY）
- UPSTREAM_ACTIVITY（联网核验活跃度）：active 11 ｜ stale 0 ｜ deprecated 0 ｜ not_applicable 3（本地自建） ｜ unknown 31（未核验/无上游可查）｜ 核验日 2026-09-22
- 内容变体 CONTENT_VARIANTS：1 ｜ 本地修改 LOCAL_MODIFIED（可证明）：0 ｜ 安装冲突 INSTALLATION_CONFLICT：0

## 2. 当前能力覆盖

### 已充分覆盖（strong）
- GitHub / Git 操作：github, github-readme-maintainer, github-portfolio-sync, make-repo-contribution
- 部署：deploy-to-vercel, netlify-deploy, vercel-blocked-deploy-triage
- 前端/UI 设计：frontend-design, theme-factory, guizang-ppt-skill
- Skill 开发/管理：skill-creator, skill-manager-governance, manage-skills, find-skills（内部有重叠）
- 课程/内容流水线：course-pdf-to-md, course-md-organize, batch-organize
- 浏览器自动化/桌面操作：computer-use, computer-use-2, orca-cli, orchestration, browseros-neo, browser-e2e-login-pitfalls
- 研究/写作：hv-analysis, khazix-writer, leader, grill-me, ponytail
- ORCA 平台集成：orca-cli, computer-use, orchestration, orca-codex-commands
- 个人效率：dida-task-manager(MCP), weekly-review-standard, ai-quota-recovery-board, obsidian

### 有覆盖但可增强（medium / weak）
- 安全审计：无专项（仅部署类顺带处理 secret）— weak
- Supabase / 数据库：无专项（browser-e2e-login-pitfalls 仅提 OAuth 坑）— weak
- 移动端 QA（Android/iOS/Expo/RN）：无专项 — none
- 通用测试/QA 框架：仅 browser-e2e-login-pitfalls 踩坑手册 — weak
- DOCX/XLSX/PPTX 本地处理：仅 hv-analysis(PDF)/guizang-ppt-skill(网页PPT) — weak
- 图像/创意生成：无本地 skill — none
- 数据分析/可视化：无专项 — none
- MCP 开发（非安装）：仅 mcp-one-command-setup 一键安装 — weak
- Windows 专项：win-reveal-and-gui-selftest（窄）— weak
- macOS 专项：computer-use 覆盖桌面，无独立系统 skill — weak

### 明显缺失（基于现有库本身，不推荐具体新 Skill）
- Security 审计/密钥扫描
- Supabase / 数据库专项
- 移动端真机 QA
- 通用测试/QA 框架
- DOCX/XLSX 处理（非网页 PPT）
- 图像/创意生成
- 数据分析/可视化专项

## 3. 库名内部重叠关系（INSTALLED_SKILL_OVERLAP，名称级，仅解释用）

### 近重复 / 候选重复
- computer-use ≈ computer-use-2（同名近重复，computer-use-2 为细化版）
- find-skills ≈ manage-skills（技能安装/管理，~70% 重叠）
- skill-creator ≈ skill-manager-governance（修改现有 skill 编辑路径，~60% 重叠）

### 互补组合
- course-pdf-to-md → course-md-organize（PDF提取→Markdown精校，流水线上下游，互补）
- frontend-design ↔ theme-factory（生成阶段设计方向 vs 主题样式应用，互补）
- guizang-ppt-skill ↔ theme-factory（网页PPT生成 vs 通用 artifact 主题，部分重叠）
- orca-cli ↔ computer-use ↔ orchestration（ORCA 三件套：工作树/终端、桌面GUI、多agent协调，互补）
- deploy-to-vercel ↔ vercel-blocked-deploy-triage（部署 vs 故障排查，互补）
- github ↔ github-readme-maintainer ↔ github-portfolio-sync ↔ make-repo-contribution（基础CLI vs 各专项，互补）
- khazix-writer ↔ hv-analysis（写作 vs 深度研究，互补）
- batch-organize 与 course-* 同属批量整理范式（互补）

## 4. 风险与维护关注（概念分列，不混用）

### 🔗 安装层异常（INSTALLATION broken_link）
- （无，全部符号链接可正常解析）

### ⚠️ 安装冲突（INSTALLATION_CONFLICT，可能导致加载错版本/优先级不确定）
- （无：60 Skill 仓库副本不参与任何 agent 加载；各 agent 加载路径上的副本内容经 SHA256 实测一致）

### 📄 内容变体（CONTENT_VARIANTS，同一 Skill 多位置内容版本不同）
- course-md-organize：central 与 60 Skill 仓库副本内容不同（repo 副本非加载路径 → 属内容变体，非安装冲突；需人工对齐）

### ✏️ 本地修改（LOCAL_MODIFIED，可证明基于上游/原版本的本地修改）
- （无可证明项：判定需先有上游基线可比对；本轮已对 11 个联网验证项与官方上游逐字节比对，全部一致、无本地改动，computer-use-2 目录改名但内容与官方一致不构成修改；内容变体不自动等于本地修改）

### 🟡 内容层关注（CONTENT warning，需审阅）
- 含 secret/token 引用（经 .env/MCP 注入，未见硬编码）：github-readme-maintainer, netlify-deploy, neat-freak, mcp-one-command-setup, vercel-blocked-deploy-triage, storage-analyzer, skill-creator, ai-coding-homework-writeup, course-md-organize, course-pdf-to-md, github-portfolio-sync
- 含 rm -rf 引用（部署临时清理）：aihot, deploy-to-vercel
- 依赖网络/外部 CLI：aihot, bilibili-download-check, travel-cn, hv-analysis, find-skills, manage-skills, guizang-ppt-skill, skill-creator 等

### ⚪ 来源层（UPSTREAM_STATUS + UPSTREAM_ACTIVITY，两态分列）
- identified（来源已确认）：14（official 8 / vendor 1 / community 2 / local 3）
- unknown（未确认）：31（不代表失效；orca-codex-commands 已排除官方发布，leader/neat-freak 待用户确认后可升级）
- UPSTREAM_ACTIVITY：active 11（均经 2026-09-22 联网核验：anthropics/skills push 2026-09-10、stablyai/orca 与 browseros-ai/BrowserOS push 2026-09-22、KKKKhazix/khazix-skills push 2026-09-16、aihot 官方渠道 v1.7.1 持续更新）｜ not_applicable 3（local 自建，无外部上游）｜ unknown 31（来源未知项不做活跃推断）

## 5. 给 Skill 日报智能体的机器可读摘要

```
CURRENT_CAPABILITIES:
  github_ops: strong
  deployment_vercel: strong
  deployment_netlify: strong
  frontend_design: strong
  ui_theme: strong
  skill_creation: strong   # 内部重叠见 INSTALLED_SKILL_OVERLAP
  skill_management: strong
  course_pipeline: strong
  browser_automation: strong
  computer_use: strong
  orca_integration: strong
  research: strong
  writing: strong
  productivity_personal: medium
  obsidian: medium
  security_audit: weak
  supabase_db: weak
  testing_qa: weak
  docx_xlsx: weak
  mcp_dev: weak
  windows: weak
  macos: weak
  mobile_qa: none
  image_creative: none
  data_analytics: none

CAPABILITY_SUPPRESSION:   # 日报推荐主去重依据（能力级，替代旧 DO_NOT_RECOMMEND_DUPLICATES / EXISTING_CAPABILITY_SUPPRESSION）
  strong = 新 Skill 若只是重复该能力，应明显降权；仅当带来明确新增能力时才推荐
  medium = 已有较强覆盖，但允许明显更好的专项 Skill
  weak   = 已有零散能力，欢迎完整方案
  none   = 当前缺失，优先搜索
  strong: github_ops, deployment_vercel, deployment_netlify, frontend_design, ui_theme, skill_creation, skill_management, course_pipeline, browser_automation, computer_use, orca_integration, research, writing
  medium: productivity_personal, obsidian
  weak: security_audit, supabase_db, testing_qa, docx_xlsx, mcp_dev, windows, macos
  none: mobile_qa, image_creative, data_analytics

INSTALLED_SKILL_OVERLAP:   # 名称级，仅解释库内具体关系；排序去重以 CAPABILITY_SUPPRESSION 为准
  near_duplicate:
    - computer-use ≈ computer-use-2（同名近重复，computer-use-2 为细化版）
    - find-skills ≈ manage-skills（技能安装/管理，~70% 重叠）
    - skill-creator ≈ skill-manager-governance（修改现有 skill 编辑路径，~60% 重叠）
  complementary:
    - course-pdf-to-md → course-md-organize（PDF提取→Markdown精校，流水线上下游，互补）
    - frontend-design ↔ theme-factory（生成阶段设计方向 vs 主题样式应用，互补）
    - guizang-ppt-skill ↔ theme-factory（网页PPT生成 vs 通用 artifact 主题，部分重叠）
    - orca-cli ↔ computer-use ↔ orchestration（ORCA 三件套：工作树/终端、桌面GUI、多agent协调，互补）
    - deploy-to-vercel ↔ vercel-blocked-deploy-triage（部署 vs 故障排查，互补）
    - github ↔ github-readme-maintainer ↔ github-portfolio-sync ↔ make-repo-contribution（基础CLI vs 各专项，互补）
    - khazix-writer ↔ hv-analysis（写作 vs 深度研究，互补）
    - batch-organize 与 course-* 同属批量整理范式（互补）

SOURCE_SUMMARY:   # 来源 ≠ 目标平台 ≠ 上游存在 ≠ 上游活跃
  official: 8
  vendor: 1
  community: 2
  local: 3
  fork: 0
  modified: 0
  unknown: 31
  rule: 面向某产品≠由该厂商发布；origin_type 只认作者来源证据（详见 SKILL_SOURCE_MAP.json）

TARGET_PLATFORMS:   # Skill 操作/面向的产品（仅记录，不作作者证据）
  AI HOT (aihot.virxact.com): aihot
  BrowserOS: browseros-neo
  Claude / Agent Skills: frontend-design, skill-creator, theme-factory
  Dida365（滴答清单）: dida-task-manager
  GitHub: github, github-portfolio-sync, github-readme-maintainer, make-repo-contribution
  Netlify: netlify-deploy
  Obsidian: obsidian
  Orca: computer-use, computer-use-2, orca-cli, orca-codex-commands, orchestration
  Vercel: deploy-to-vercel, vercel-blocked-deploy-triage
  place-journal（本机项目）: place-journal-qa
  skills-manager-cli（本机自建工具）: manage-skills
  去哪儿/携程/飞猪（Expedia 中国版）: travel-cn
  哔哩哔哩: bilibili-download-check
  本地 Skill Manager: skill-manager-governance

CONTENT_VARIANTS:   # 同一 Skill 多位置内容版本不同（动态实测 SHA256）
  - course-md-organize   # repo 副本非加载路径 → 非安装冲突

LOCAL_MODIFIED:   # 仅登记可证明『基于上游本地修改』的项；内容变体≠本地修改
  (none)   # 无上游基线可比对，本轮无可证明项

CONTENT_HEALTH:
  healthy: 18
  warning: 27
  broken: 0

INSTALLATION_HEALTH:   # 仅看加载路径；内容变体单列 CONTENT_VARIANTS，不在此计冲突
  healthy: 45
  broken_link: 0
  path_error: 0
  conflict: 0

UPSTREAM_STATUS:   # identified=作者归属已确认（≠活跃）；活跃度核验见 UPSTREAM_ACTIVITY
  identified: 14
  unknown: 31

UPSTREAM_ACTIVITY:   # active 仅在联网核验后填写；not_applicable=本地自建无上游；unknown=来源未知项不做推断
  active: 11
  stale: 0
  deprecated: 0
  not_applicable: 3
  unknown: 31
  activity_verified_at: 2026-09-22
  evidence: anthropics/skills push 2026-09-10；stablyai/orca、browseros-ai/BrowserOS push 2026-09-22；KKKKhazix/khazix-skills push 2026-09-16；aihot 官方渠道 v1.7.1 持续更新
  active_items: aihot, browseros-neo, computer-use, computer-use-2, frontend-design, hv-analysis, khazix-writer, orca-cli, orchestration, skill-creator, theme-factory

NEEDS_ATTENTION:
  - 内容变体待对齐(CONTENT_VARIANTS): course-md-organize
  - 来源未知 31 个(UPSTREAM_STATUS unknown)：建议补登 source 字段（勿按名称猜）
  - 来源待升级(pending_upgrade): leader, neat-freak — 与 khazix-skills 逐字节一致，待用户确认后升级 community
  - 含 rm -rf / secret 引用的 Skill 需审阅(CONTENT warning)
```

## 6. 唯一 Skill 简表

| Skill | 用途(简述) | 级别 | 来源 | 标签 | 内容 | 安装 | 来源态 | 活跃 |
|---|---|---|---|---|---|---|---|---|
| agent-central-mapping | 当用户希望让 Claude Code、Codex、opencode、CodeArts Doer、Cursor、Gemini CLI、Zed、Windsurf 等编码 agent 从… | 用户级 | unknown | Agent/Workflow,Other | ✅ | ✅ | ⚪ | ⚪ |
| ai-coding-homework-writeup | "本 skill 适用于「把 AI 辅助开发的编程作业写成一份能交的提交材料」这类任务。当用户拿出作业要求（例如『用 Expo/React Native 开发一个 App，提交一句… | 用户级 | unknown | Documentation,Education,Other | ✅ | ✅ | ⚪ | ⚪ |
| ai-quota-recovery-board | 当用户想跟踪多个 AI 工具 / 服务的「额度 / 频率限制 / 信用点」恢复时间并做成可视化看板时使用。生成单文件 HTML 看板（时间轴甘特 + 实时倒计时表 + 本地追加表单… | 用户级 | unknown | Automation,Frontend/UI,Other | ✅ | ✅ | ⚪ | ⚪ |
| aihot | 查询 AI HOT 的中文 AI 资讯、精选、当前热点和日报。用户询问今天或最近的 AI 新闻、AI 圈动态、大模型或产品发布、OpenAI／Anthropic／Google 最新… | 用户级 | vendor | Research,Other | 🟡 | ✅ | 🔵 | 🟢 |
| batch-organize | "本 skill 适用于「一批杂乱原始素材 → 统一规范成品」且需可重跑、可中断、可多智能体协作的批量整理任务（课程/播客/视频转写稿清洗、PDF 抽取稿整理、文档/知识库迁移、素… | 用户级 | unknown | Agent/Workflow,Documentation,Other | ✅ | ✅ | ⚪ | ⚪ |
| bilibili-download-check | 当需要对比哔哩哔哩 UP 主投稿目录与本地已下载视频、生成未下载清单，或按红利/打新等关键词筛选时使用。 | 用户级 | unknown | Browser Automation,Other | 🟡 | ✅ | ⚪ | ⚪ |
| browser-e2e-login-pitfalls | "浏览器端 E2E / 验收测试的踩坑与避坑手册：Vite 环境变量未注入、Google OAuth 拦截自动化浏览器（Chrome for Testing）、多 Chrome 窗… | 用户级 | unknown | Browser Automation,QA/Testing,Other | 🟡 | ✅ | ⚪ | ⚪ |
| browseros-neo | The user's dedicated browser for agents — a real browser signed into their accounts, with … | 用户级 | official | Browser Automation,MCP,Other | ✅ | ✅ | 🔵 | 🟢 |
| coding-workspace-organizer | 整理编码工作区：拍平嵌套归档目录，按 `NNN-状态-项目名` 规则重命名项目，并生成按序号查找的索引表。用户要求整理工作区、给项目文件夹编号、按序号排序、拍平暂停或归档目录，或在… | 用户级 | unknown | macOS,Windows,Automation,Other | ✅ | ✅ | ⚪ | ⚪ |
| computer-use | - Use Orca's computer-use CLI to inspect and operate local desktop app windows through acc… | 用户级 | official | Agent/Workflow,macOS,Windows,Browser Automation | ✅ | ✅ | 🔵 | 🟢 |
| computer-use-2 | - Use Orca's computer-use CLI for OS/window-level inspection and input in visible local ap… | 用户级 | official | Agent/Workflow,macOS,Windows,Browser Automation | ✅ | ✅ | 🔵 | 🟢 |
| course-md-organize | "把已提取的课程 Markdown 整理成「得到·刘澜式」舒服可读的文稿：顶部本课总结、错别字/OCR 校对、三级子标题逻辑分段、段落自然流动。用于 OCR/语音转写稿存在文字墙、… | 用户级 | unknown | Documentation,Python,Other | 🟡 | ✅ | ⚪ | ⚪ |
| course-pdf-to-md | "将课程类 PDF（得到/知识星球/小报童等导出，常配 MP3）批量整理为每章一个 Markdown 的流水线 skill。当用户需要：把一批课程 PDF 按章节提取文字稿、清洗平… | 用户级 | unknown | PDF/DOCX/PPTX/Spreadsheet,Python,Documentation | 🟡 | ✅ | ⚪ | ⚪ |
| deploy-to-vercel | Deploy applications and websites to Vercel. Use when the user requests deployment actions … | 用户级 | unknown | Deployment,Vercel,Git/GitHub | 🟡 | ✅ | ⚪ | ⚪ |
| dida-task-manager | "Dida365 / 滴答清单 习惯与任务操作的统一入口。覆盖新建/修改习惯（尤其『每天 N 次打卡才算完成』的量化习惯正确模板）、任务自动归类路由、习惯图标规则、倒数日只读边界。… | 用户级 | unknown | Automation,MCP,Other | ✅ | ✅ | ⚪ | ⚪ |
| find-skills | "帮助用户发现和安装智能体技能。当用户提出「如何做 X」、「查找某个技能」、「有没有能做……的技能」等问题，或表示希望扩展功能时使用。当用户正在寻找可能作为可安装技能存在的功能时，… | 用户级 | unknown | Skill Development,MCP,Other | 🟡 | ✅ | ⚪ | ⚪ |
| frontend-design | Guidance for distinctive, intentional visual design when building new UI or reshaping an e… | 用户级 | official | Frontend/UI,UX/Design Review | 🟡 | ✅ | 🔵 | 🟢 |
| github | "Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` … | 用户级 | unknown | Git/GitHub,Other | 🟡 | ✅ | ⚪ | ⚪ |
| github-portfolio-sync | 当需要采集当前 GitHub 账号的公开和私有仓库，整理功能、技术栈与最新进度，并生成项目全景 Markdown 背景档案时使用。 | 用户级 | unknown | Git/GitHub,Documentation,MCP | 🟡 | ✅ | ⚪ | ⚪ |
| github-readme-maintainer | 当需要编写、重写、审查或维护 GitHub README、项目介绍、docs 结构、仓库说明，或补全仓库 About 简介（Description / Website / Topi… | 用户级 | unknown | Git/GitHub,Documentation | 🟡 | ✅ | ⚪ | ⚪ |
| grill-me | Interview the user relentlessly about a plan or design until reaching shared understanding… | 用户级 | unknown | Agent/Workflow,Prompt Engineering,Other | 🟡 | ✅ | ⚪ | ⚪ |
| guizang-ppt-skill | 生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。提供两种风格：① "电子杂志 × 电子墨水"（衬线 + 流体背景 + 暖… | 用户级 | unknown | Frontend/UI,PDF/DOCX/PPTX/Spreadsheet,Other | 🟡 | ✅ | ⚪ | ⚪ |
| hv-analysis | 横纵分析法（Horizontal-Vertical Analysis）深度研究Skill。由数字生命卡兹克提出，融合了索绪尔的历时-共时分析、社会科学的纵向-横截面研究设计、商学院… | 用户级 | community | Research,PDF/DOCX/PPTX/Spreadsheet,Other | 🟡 | ✅ | 🔵 | 🟢 |
| khazix-writer | 数字生命卡兹克（Khazix）的公众号长文写作skill。当用户需要撰写公众号文章、写稿子、续写文章、根据素材产出长文时使用。触发词包括但不限于：写文章、写稿子、帮我写、续写、扩写… | 用户级 | community | Documentation,Prompt Engineering,Other | ✅ | ✅ | 🔵 | 🟢 |
| leader | 把一句话的想法拆成 AI agent 能独立跑完的目标任务书。用户说「帮我给 agent 写个目标」「帮我详细拆一下这个目标」「写个任务书/brief 给 agent」「写个 go… | 用户级 | unknown | Agent/Workflow,Prompt Engineering,Other | 🟡 | ✅ | ⚪ | ⚪ |
| local-service-change-acceptance | 改完本地长驻服务（单文件 Python HTTP 服务、本地控制台后端、桌面应用的内嵌服务）后，如何在真机上做「可信验收」——把用户真实数据撇开、用隔离目录跑端到端、以及识破「乐观… | 用户级 | unknown | QA/Testing,Other | ✅ | ✅ | ⚪ | ⚪ |
| make-repo-contribution | 'All changes to code must follow the guidance documented in the repository. Before any iss… | 用户级 | unknown | Git/GitHub,Other | 🟡 | ✅ | ⚪ | ⚪ |
| manage-skills | Manage the user's shared agent-skill library via skills-manager-cli — install, update, rem… | 用户级 | local | Skill Development,Git/GitHub,Other | 🟡 | ✅ | 🔵 | ➖ |
| mcp-one-command-setup | Write a zero-dependency one-command installer for a local MCP (Model Context Protocol) ser… | 用户级 | unknown | MCP,Automation,Other | 🟡 | ✅ | ⚪ | ⚪ |
| neat-freak | - Knowledge and governance closeout: reconcile project docs, rule files (CLAUDE.md/AGENTS.… | 用户级 | unknown | Documentation,Agent/Workflow,Other | 🟡 | ✅ | ⚪ | ⚪ |
| netlify-deploy | Create, configure, and manage Netlify deploys from code — reach for this when setting up G… | 用户级 | unknown | Deployment,Git/GitHub,Other | 🟡 | ✅ | ⚪ | ⚪ |
| obsidian | "Work with Obsidian vaults (plain Markdown notes) and automate via obsidian-cli." | 用户级 | unknown | Documentation,Other | 🟡 | ✅ | ⚪ | ⚪ |
| orca-cli | - Use the public `orca` CLI to operate Orca-managed worktrees, folder contexts, terminals,… | 用户级 | official | Agent/Workflow,macOS,Windows,Git/GitHub | ✅ | ✅ | 🔵 | 🟢 |
| orca-codex-commands | - Use when Stage Manager needs to call Codex via Orca terminal. Provides the exact command… | 用户级 | unknown | Agent/Workflow,Git/GitHub,Other | ✅ | ✅ | ⚪ | ⚪ |
| orchestration | - Use Orca orchestration for structured multi-agent coordination: threaded messages, block… | 用户级 | official | Agent/Workflow,Other | ✅ | ✅ | 🔵 | 🟢 |
| place-journal-qa | 个人地点打卡手账（place-journal）项目的开发、测试与已知坑。适用于该工作区内 PWA 的迭代、QA 与部署准备。 | 用户级 | local | QA/Testing,Frontend/UI,Other | ✅ | ✅ | 🔵 | ➖ |
| ponytail | Forces the laziest solution that actually works, simplest, shortest, most minimal. Channel… | 用户级 | unknown | Agent/Workflow,Other | ✅ | ✅ | ⚪ | ⚪ |
| skill-creator | Create new skills, modify and improve existing skills, and measure skill performance. Use … | 用户级 | official | Skill Development,Other | 🟡 | ✅ | 🔵 | 🟢 |
| skill-manager-governance | 审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库。用户要求把中转站 skill 纳入中央库、解释为什么软件看不到、或迁移到 Windows、macOS 或其… | 用户级 | local | Skill Development,Other | 🟡 | ✅ | 🔵 | ➖ |
| storage-analyzer | macOS / Windows 只读存储分析助手（自动识别系统）。扫描整机磁盘占用，找出 占空间大户，把每一项分成 🟢可自动清理 / 🟡需人工判断 / 🔴谨慎清理 三级并给出 可执… | 用户级 | unknown | macOS,Windows,Automation,Other | 🟡 | ✅ | ⚪ | ⚪ |
| theme-factory | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reporting… | 用户级 | official | Frontend/UI,UX/Design Review,Other | ✅ | ✅ | 🔵 | 🟢 |
| travel-cn | 旅行信息查询 - 去哪儿/携程/飞猪数据查询（Expedia 中国版） | 用户级 | unknown | Research,Other | 🟡 | ✅ | ⚪ | ⚪ |
| vercel-blocked-deploy-triage | "当 Vercel 部署显示 UNKNOWN/BLOCKED、构建被跳过、提交作者校验失败，或部署成功但线上仍是旧版本时使用；先诊断原因，再按授权执行解除措施。" | 用户级 | unknown | Deployment,Vercel,Git/GitHub | 🟡 | ✅ | ⚪ | ⚪ |
| weekly-review-standard | "周复盘 / 月复盘的标准格式、详细度、颗粒度与踩坑库。当用户要求「做周复盘 / 周报 / 拉取一周数据复盘 / 生成复盘看板 / 月度复盘」时触发，确保一次到位、不返工。覆盖 9… | 用户级 | unknown | Documentation,Automation,Other | ✅ | ✅ | ⚪ | ⚪ |
| win-reveal-and-gui-selftest | 在 Windows 上实现「打开文件所在位置／在资源管理器中定位文件」，以及用窗口标题差分自测任何 GUI 动作是否真的发生（含沙箱里跑 Bash/PowerShell 的进程与窗… | 用户级 | unknown | Windows,QA/Testing,Other | 🟡 | ✅ | ⚪ | ⚪ |

> 图例：内容=CONTENT_HEALTH(✅正常/🟡需审阅/🔴损坏)；安装=INSTALLATION_HEALTH(✅正常/🔴悬空链接)；来源态=UPSTREAM_STATUS(🔵来源已确认 identified/⚪未确认 unknown)；活跃=UPSTREAM_ACTIVITY(🟢active 联网核验/➖本地自建/⚪未核验)。各态互不推断。
> 详细审计与来源证据见 INSTALLED_SKILLS_FULL.md。
