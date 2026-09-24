# Installed Skills Full Audit（Canonical 模型 v4）

> 更新时间：2026-09-22 17:0x (GMT+8)｜MACHINE_ID：Mac-mini｜数据基准：2026-09-22 15:12 (GMT+8) 双扫描稳定窗口；16:5x Skill Manager 注册表副本核验
> 完整审计档案。来源映射见 SKILL_SOURCE_MAP.json；轻量日报底座见 INSTALLED_SKILLS_CONTEXT.md。

## 〇、CANONICAL_SKILL 模型（本版核心变更）

真实架构：**Skill Manager 中央管理 → 双机 git 备份同步 → Claude / OpenCode / WorkBuddy / Codex 等 Agent 经软链接、映射或本地部署使用**。
因此：『存在多个文件系统目录』≠『存在多个不同 Skill』。一个逻辑 Skill 只有一个 canonical identity（CANONICAL_ID）；同步副本、镜像目录、导入别名一律记为副本，不再计入唯一 Skill。

| 概念 | 定义 | 本机数值 |
|---|---|---|
| CANONICAL_UNIQUE_SKILLS | 逻辑 Skill 全集（installed + known_missing） | **45** |
| CANONICAL_INSTALLED | 当前本机有 canonical 副本 | 42 |
| CANONICAL_KNOWN_MISSING | 来源档案确认存在、本机当前无 canonical 副本 | 3（orca 三件套） |
| LOADABLE_SKILL_ENTRIES | 目录扫描加载器视角的条目数（含别名） | 49 |
| SYNC_REPLICAS | 同步/部署副本（内容随 canonical） | 19 |
| DUPLICATE_ALIASES | 导入别名目录（(2)） | 7 |
| PHYSICAL_COPIES | 物理副本总数 | 65 |
| BROKEN_AGENT_LINKS | 悬空软链接 | 6 |

副本角色（role）与同步状态（SYNC_STATE）：

- `canonical`：规范主副本（中央仓库，或经注册表/管理器确认的原位主副本）｜ SYNC_STATE=canonical
- `agent_replica`：agent 目录物理部署副本｜ SYNC_STATE=synced_replica
- `dev_replica`：60 Skill 仓库项目级开发副本｜ SYNC_STATE=local_only
- `duplicate_alias`：`(2)` 导入别名目录｜ SYNC_STATE=conflict_copy（内容与原目录逐字节一致）
- 主副本缺失｜ SYNC_STATE=missing（orca 三件套）

## 一、扫描范围与方法

- `~/.skills-manager/skills/` — 中央仓库（Skill Manager 管理，39 个 canonical 主副本 + 7 个 `(2)` 别名）
- `~/.workbuddy/skills/`、`~/.claude/skills/`、`~/.config/opencode/skills/`、`~/.agents/skills/` — 各 Agent 加载路径（软链接/物理副本）
- 60 Skill 仓库 — 项目级平行开发副本（不参与 agent 加载）
- Skill Manager 注册表（skills-manager.db，46 条 skills、194 条 skill_targets、2 条 pending_conflicts）——只读副本核验
- 所有符号链接 realpath 解析；全部多副本 SKILL.md SHA256 + 换行符规范化比对

## 二、机制诊断：`(2)` 目录与 Orca 三件套消失（Skill Manager 自证）

### 2.1 七个 `(2)` 目录的机制（已确证）

- **诞生时间**：2026-09-22 12:39（birth time 实测），7 个同批。
- **注册表实锤**：skills 表存在 7 条**独立记录**，central_path 直接指向 `skills/xxx (2)`（各自 UUID、source_type=local、status=ok）。
- **导入源**：其中至少 3 条 source_ref 指向 60 Skill 仓库对应目录 → Skill Manager 的导入/收编（adopt）流程把仓库 skill 目录复制进中央时，中央已有同名目录 → 另存 `(2)` 并**注册为新 Skill**。
- **内容**：`diff -rq` 全目录递归比对，7 个全部与原目录**逐字节一致**（不只 SKILL.md）。
- **结论**：`(2)` 是 Skill Manager 导入命名行为产生的**同名别名副本**，不是新逻辑 Skill，不是另一台电脑的冲突文件；应并入对应 CANONICAL_SKILL（已完成建模），物理目录待用户确认后清理（本轮未动）。

### 2.2 Orca 三件套（orca-cli / orchestration / computer-use）消失的机制（已确证到应用层）

- 注册表 skills 表**无任何 orca 行**；skill_targets 表无 orca 行（外键 ON DELETE CASCADE 级联删除）→ 注册表行与部署目标是**应用内一起删掉的**，不是文件系统层面被单独 rm。
- audit_log 全历史（474 条，action ∈ install/update/remove/enable/disable/sync）**无 orca 的 remove 记录** → 删除未走常规审计操作，指向 re-index/停靠（park）内部路径。
- WAL 中大量 `sm-reindex-parked://<uuid>` 记录 → Skill Manager 存在「重新索引时把失配条目停靠」的机制。
- 时间线：12:39 导入收编批次（与 (2) 诞生、pending_conflicts 检测同批）→ ~14:23 中央 orca 目录消失 → 14:55:52 最后一条 audit（update github-readme-maintainer）→ 15:20 一次 frontmatter 瞬时改写后还原（应用后台写盘）。
- **排除项**：不是另一台电脑的文件级冲突覆盖（无 conflict 文件）；不是用户手动删除（无审计、无回收站迹象）。
- **`(2)` 与 Orca 消失是否同一机制**：同一应用（Skill Manager）同一时间窗内后台维护行为（re-index + git 备份 auto update），但具体动作不同——前者是导入收编，后者是停靠/移除。

### 2.3 双机同步确认为正式机制

- settings：`backup_device_name=zzymima0000deMacBook-Air`（本机 scutil ComputerName=**Mac mini** → skills-manager 状态从 MacBook Air 携带到本机）、`git_backup_remote_url`（加密 GitHub 远端）、`backup_auto_enabled=on`、`git_backup_engine=git2`、`merge_engine=object`、`auto_update_apply=on`、`auto_update_last_run_at=2026-09-22T07:48:45Z`（本地 15:48）。
- **本机 `~/.skills-manager` 整体就是双机同步的产物**。同步工具（Skill Manager 自身的备份引擎）把 canonical 当普通托管对象处理，是 Orca 事件的风险根因。

## 三、AGENT_AVAILABILITY（安装态与可用态分列）

- machine：Mac-mini｜link_status ∈ available / broken / missing / not_deployed
- **broken（悬空链接）6 条**：
  - computer-use × claude：broken（链接目标 `~/.skills-manager/skills/computer-use` 已被移除）
  - computer-use × opencode：broken（链接目标 `~/.skills-manager/skills/computer-use` 已被移除）
  - computer-use × workbuddy：broken（链接目标 `~/.skills-manager/skills/computer-use` 已被移除）
  - orca-cli × claude：broken（链接目标 `~/.skills-manager/skills/orca-cli` 已被移除）
  - orca-cli × opencode：broken（链接目标 `~/.skills-manager/skills/orca-cli` 已被移除）
  - orchestration × claude：broken（链接目标 `~/.skills-manager/skills/orchestration` 已被移除）
- **missing（canonical 缺失）3 个**：computer-use, orca-cli, orchestration（KNOWN_SKILL=yes，INSTALLED_CANONICAL=no，来源档案完整保留在 SKILL_SOURCE_MAP.json）
- available 109 ｜ not_deployed 104

### 逐 skill × agent 可用性矩阵（仅列非 not_deployed 项）

| Canonical Skill | central | workbuddy | claude | opencode | agents |
|---|---|---|---|---|---|
| agent-central-mapping | ✅ available | — | — | — | — |
| ai-coding-homework-writeup | ✅ available | ✅ available | ✅ available | ✅ available | — |
| ai-quota-recovery-board | ✅ available | ✅ available | — | — | — |
| aihot | ✅ available | — | — | — | — |
| batch-organize | ✅ available | ✅ available | ✅ available | ✅ available | — |
| bilibili-download-check | ✅ available | — | — | — | — |
| browser-e2e-login-pitfalls | ✅ available | ✅ available | — | — | — |
| browseros-neo | ❌ missing | — | ✅ available | ✅ available | ✅ available |
| coding-workspace-organizer | ✅ available | ✅ available | ✅ available | ✅ available | — |
| computer-use | ❌ missing | 🔴 broken | 🔴 broken | 🔴 broken | — |
| computer-use-2 | ✅ available | — | — | — | — |
| course-md-organize | ✅ available | ✅ available | ✅ available | ✅ available | — |
| course-pdf-to-md | ✅ available | ✅ available | ✅ available | ✅ available | — |
| deploy-to-vercel | ✅ available | ✅ available | ✅ available | ✅ available | — |
| dida-task-manager | ✅ available | ✅ available | — | — | — |
| find-skills | ✅ available | ✅ available | ✅ available | ✅ available | — |
| frontend-design | ✅ available | ✅ available | ✅ available | ✅ available | — |
| github | ✅ available | ✅ available | ✅ available | ✅ available | — |
| github-portfolio-sync | ✅ available | ✅ available | ✅ available | ✅ available | — |
| github-readme-maintainer | ✅ available | ✅ available | ✅ available | ✅ available | — |
| grill-me | ✅ available | ✅ available | ✅ available | ✅ available | — |
| guizang-ppt-skill | ✅ available | — | — | — | — |
| hv-analysis | ✅ available | ✅ available | — | — | — |
| khazix-writer | ✅ available | — | — | — | — |
| leader | ✅ available | ✅ available | ✅ available | ✅ available | — |
| local-service-change-acceptance | ✅ available | — | — | — | — |
| make-repo-contribution | ✅ available | — | — | — | — |
| manage-skills | ✅ available | — | — | ✅ available | — |
| mcp-one-command-setup | ✅ available | ✅ available | — | — | — |
| neat-freak | ✅ available | — | ✅ available | ✅ available | — |
| netlify-deploy | ✅ available | ✅ available | ✅ available | ✅ available | — |
| obsidian | ✅ available | — | — | — | — |
| orca-cli | ❌ missing | — | 🔴 broken | 🔴 broken | — |
| orca-codex-commands | ❌ missing | — | — | ✅ available | — |
| orchestration | ❌ missing | — | 🔴 broken | — | — |
| place-journal-qa | ❌ missing | ✅ available | — | — | — |
| ponytail | ✅ available | ✅ available | ✅ available | ✅ available | — |
| skill-creator | ✅ available | — | ✅ available | ✅ available | — |
| skill-manager-governance | ✅ available | ✅ available | ✅ available | ✅ available | — |
| storage-analyzer | ✅ available | ✅ available | — | — | — |
| theme-factory | ✅ available | — | ✅ available | ✅ available | — |
| travel-cn | ✅ available | — | — | — | — |
| vercel-blocked-deploy-triage | ✅ available | ✅ available | ✅ available | ✅ available | — |
| weekly-review-standard | ✅ available | ✅ available | — | — | — |
| win-reveal-and-gui-selftest | ✅ available | — | — | — | — |

## 四、能力层

### CURRENT_CAPABILITIES + CAPABILITY_SUPPRESSION（结构沿用已验收版本，未改动）

strong = 新 Skill 若只是重复该能力，应明显降权；仅当带来明确新增能力时才推荐
medium = 已有较强覆盖，但允许明显更好的专项 Skill
weak   = 已有零散能力，欢迎完整方案
none   = 当前缺失，优先搜索

- **strong**：browser_automation, computer_use, course_pipeline, deployment_netlify, deployment_vercel, frontend_design, github_ops, orca_integration, research, skill_creation, skill_management, ui_theme, writing
- **medium**：obsidian, productivity_personal
- **weak**：docx_xlsx, macos, mcp_dev, security_audit, supabase_db, testing_qa, windows
- **none**：data_analytics, image_creative, mobile_qa

### CAPABILITY_AVAILABILITY（新增维度：coverage 与 availability 分列）

规则：CAPABILITY_SUPPRESSION 不能只看历史上『曾安装过』。coverage=历史覆盖度（原 suppression 级别）；availability=当前载体在位情况（ok / degraded / unavailable）。

- **orca_integration**：coverage=strong ｜ availability=**degraded** ｜ 载体在位 computer-use-2｜ 缺失 orca-cli, orchestration, computer-use
- **computer_use**：coverage=strong ｜ availability=**degraded** ｜ 载体在位 computer-use-2, browseros-neo｜ 缺失 computer-use
- **browser_automation**：coverage=strong ｜ availability=**ok** ｜ 载体在位 browseros-neo, computer-use-2, bilibili-download-check, browser-e2e-login-pitfalls｜ 缺失 —

> 日报注意：orca_integration 不得因 coverage=strong 而视为完全正常——availability=degraded，关键载体 orca-cli/orchestration/computer-use 当前加载不到。

### INSTALLED_SKILL_OVERLAP（名称级，仅解释库内关系；canonical 口径）

- near_duplicate：computer-use ≈ computer-use-2（computer-use 当前缺失，仅 computer-use-2 在位）；find-skills ≈ manage-skills（~70% 重叠）；skill-creator ≈ skill-manager-governance（~60% 重叠）
- complementary：orca-cli ↔ computer-use ↔ orchestration（ORCA 三件套，互补，当前全部缺失/仅 computer-use-2 在位）；course-pdf-to-md → course-md-organize；frontend-design ↔ theme-factory；deploy-to-vercel ↔ vercel-blocked-deploy-triage；github ↔ 各专项；khazix-writer ↔ hv-analysis；orca-codex-commands 与 orca-cli 同属 ORCA 平台集成

## 五、来源层（按 CANONICAL 统计）

- **SOURCE_SUMMARY（全集 45）**：official 8 ｜ vendor 1 ｜ community 2 ｜ local 3 ｜ fork 0 ｜ modified 0 ｜ unknown 31
- 规则不变：面向某产品 ≠ 由该厂商发布；origin_type 只认作者来源证据；同步副本/别名不重复计数（skill-manager-governance 只算一次 local，其 `(2)` 别名不参与统计）。

### official（8）
- **browseros-neo** ← github.com/browseros-ai/BrowserOS ｜ confidence=medium ｜ 证据：安装目录含 BrowserOS 官方管理清单 .browserclaw-managed.json（官方安装器管理标记）；内容与官方仓库 skill 高度同源，但与所查 3 个官方 commit 均非逐字节一致（官方持续演进）→ 判 official，confidence=medium。 
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 browseros-ai/BrowserOS 最近 push 2026-09-22）
- **computer-use** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：内容与官方仓库逐字节一致：本地 SKILL.md（c79dedb3c7df）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/computer-use/SKILL.md → 由 Orca 官方仓库发布。 ｜ **当前 canonical 副本缺失（known_missing）**
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **computer-use-2** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08-31）中 skills/computer-use/SKILL.md 逐字节一致 → 内容源自官方仓库（非本地修改；目录改名不改变来源归属）。 
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **frontend-design** ← github.com/anthropics/skills ｜ confidence=high ｜ 证据：LICENSE.txt (Apache)；SKILL.md 自述为 Anthropic 官方设计 skill（'Anthropic's own Claude-interaction accent'）。 
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 anthropics/skills 最近 push 2026-09-10）
- **orca-cli** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：内容与官方仓库逐字节一致：本地 SKILL.md（sha1 前12位 cddfd0a8c44e）== stablyai/orca commit f8b430f7（2026-07-20）中 skills/orca-cli/SKILL.md，同算法实测 → 由 Orca 官方仓库发布（第二轮『仅面向产品』的保守判定据此撤销）。 ｜ **当前 canonical 副本缺失（known_missing）**
  - 活跃度：active（核验日 2026-09-22；GitHub API 实测 stablyai/orca 最近 push 2026-09-22）
- **orchestration** ← github.com/stablyai/orca ｜ confidence=high ｜ 证据：内容与官方仓库逐字节一致：本地 SKILL.md（8dd31dae1235）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/orchestration/SKILL.md → 由 Orca 官方仓库发布。 ｜ **当前 canonical 副本缺失（known_missing）**
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

### unknown（31）
- agent-central-mapping, ai-coding-homework-writeup, ai-quota-recovery-board, batch-organize, bilibili-download-check, browser-e2e-login-pitfalls, coding-workspace-organizer, course-md-organize, course-pdf-to-md, deploy-to-vercel, dida-task-manager, find-skills, github, github-portfolio-sync, github-readme-maintainer, grill-me, guizang-ppt-skill, leader, local-service-change-acceptance, make-repo-contribution, mcp-one-command-setup, neat-freak, netlify-deploy, obsidian, orca-codex-commands, ponytail, storage-analyzer, travel-cn, vercel-blocked-deploy-triage, weekly-review-standard, win-reveal-and-gui-selftest
- orca-codex-commands 已经官方全量 tree（29,540 路径）检索排除官方发布；leader / neat-freak 与 khazix-skills 逐字节一致（pending_upgrade，待用户确认后升 community）。

## 六、上游状态 / 活跃度 / 版本关系

- **UPSTREAM_STATUS**：identified 14（official 8 / vendor 1 / community 2 / local 3）｜ unknown 31（identified 仅指作者归属确认，≠活跃）
- **UPSTREAM_ACTIVITY**（2026-09-22 联网核验）：active 11 ｜ stale 0 ｜ deprecated 0 ｜ not_applicable 3（local 自建）｜ unknown 31。active 判定依据均为实测 recent push/release：anthropics/skills push 2026-09-10、stablyai/orca 与 browseros-ai/BrowserOS push 2026-09-22、KKKKhazix/khazix-skills push 2026-09-16、aihot 官方渠道 v1.7.1 持续更新。
- **VERSION_STATUS**（版本关系；版本旧/与当前上游不一致 ≠ LOCAL_MODIFIED，需证明基于官方基线人工修改才记 LOCAL_MODIFIED）：
  - historical_official_version 4：computer-use-2（与官方 skills/computer-use@b44ef1e5 2026-08-31 逐字节一致）、orca-cli / orchestration / computer-use（与官方历史 commit 逐字节一致，官方此后有更新）
  - upstream_in_sync 4：hv-analysis、khazix-writer、leader、neat-freak（与 khazix-skills 当前内容逐字节一致）
  - outdated_version 2：browseros-neo（官方持续演进、本地由官方安装器管理未跟进）、aihot（本地 1.2.0 落后官方 1.7.1，版本谱系连续、署名一致）——来源确认不依赖逐字节一致
  - local_modified 0 ｜ unresolved_variant 0 ｜ not_compared 35（无上游内容基线可比对）

## 七、内容 / 安装 / 变体（保持已验收结构，canonical 口径）

- **CONTENT_VARIANTS：1** — course-md-organize：仅换行符差异（repo 副本 CRLF vs central LF，规范化后内容一致，非实质内容变体）；repo 副本非加载路径，不构成安装冲突；可统一换行符后消除。
- **LOCAL_MODIFIED：0** — 无任何一项能证明『基于上游/原版本的本地修改』。browseros-neo/aihot 版本旧不触发本判定。
- **INSTALLATION_CONFLICT：0** — 各加载路径同名副本内容实测一致；`(2)` 别名按 duplicate_alias 建模，不属于路径冲突。
- **INSTALLATION_HEALTH**：broken_link 6（claude×3 / opencode×2 / workbuddy×1，目标为被移除的 Orca 主副本）；其余加载路径 healthy。
- **CONTENT_HEALTH**：全部 healthy/审阅级 warning（secret/token 引用经 .env/MCP 注入、rm -rf 为部署临时清理、网络依赖类），无损坏。

## 八、双机同步正式模型（为第二台电脑预留）

每个 CANONICAL_SKILL 携带：`MACHINE_ID` + `CANONICAL_ID` + `SYNC_STATE`。SYNC_STATE ∈ canonical / synced_replica / local_only / conflict_copy / stale_replica / missing。

- 本轮已在 SKILL_SOURCE_MAP.json 每个条目写入 `canonical` 块（canonical_id / installed_canonical / machine_id / sync_state / registry）。
- 目标不是两台电脑路径完全相同，而是：**同一个 Skill 永远拥有同一个 CANONICAL_ID**——即使两台机器路径不同，也能识别为同一逻辑 Skill。
- 另一台电脑接入时的判定规则：中央存在同名同内容 → synced_replica；同名不同内容 → conflict_copy（进入 pending_conflicts 人工裁决）；仅单机存在 → local_only；注册表有档案但无副本 → missing。

## 九、恢复方案（仅方案，未执行，待用户确认）

前提结论：中央 Skill Manager 应继续作为唯一规范源（Canonical Central Repository），双机经其 git 备份远端同步。

1. **防再发（P0，建议先做）**：在 Skill Manager 设置中把 `auto_update_apply` 改为 off（或确认 re-index 不再停靠官方源条目）；同步前确认 git 备份远端快照里 orca 三件套仍在（可用远端仓库历史恢复 canonical 目录）。
2. **恢复 Orca 三件套（P1）**：从 stablyai/orca 官方对应 commit 重新导入中央（内容已知：sha1 cddfd0a8c44e / 8dd31dae1235 / c79dedb3c7df），再由 Skill Manager 重新 deploy 生成各 agent 链接；6 条悬空链接随之自愈。
3. **清理 `(2)` 别名（P2）**：确认后删除 7 个 `(2)` 目录并同步删除 Skill Manager 注册表中对应 7 条记录（避免再次收编/同步回来）；`(2)` 在注册表内是独立条目，只删目录会被 re-index 再次拉起。
4. **pending_conflicts×2（P2）**：bilibili-download-check / github-portfolio-sync 的 git 远端更新冲突，在 Skill Manager 界面裁决 theirs/ours。
5. 全部完成后重扫，重出三件套并复跑验收。

## 十、NEEDS_ATTENTION

1. Orca 3 件 canonical 缺失 + 悬空链接×6（根因=Skill Manager re-index/停靠；恢复方案 §九-2，待确认）
2. `(2)` 别名×7：建模已并入 canonical；物理清理需连同注册表 7 条记录一起处理（§九-3，待确认）
3. Skill Manager pending_conflicts×2（§九-4）
4. 双机同步防再发（§九-1，建议用户在 Skill Manager 设置界面操作）
5. 来源待升级(pending_upgrade)：leader, neat-freak（与 khazix-skills 逐字节一致，待确认升 community）
6. course-md-organize 换行符差异（低危，统一后消除）

## 十一、逐 Canonical Skill 明细

### agent-central-mapping（安装｜unknown｜unknown）
- 用途：当用户希望让 Claude Code、Codex、opencode、CodeArts Doer、Cursor、Gemini CLI、Zed、Windsurf 等编码 agent 从同一个中央仓库读取全局规则和 skill 时使用。必须先询问中央 AGENTS.md 和中央 skill 仓库的绝对路径…
- CANONICAL_ID：agent-central-mapping ｜ canonical_path：~/.skills-manager/skills/agent-central-mapping ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（8368109d-436c-49f3-861f-2cc4b2540cdb，central_path=~/.skills-manager/skills/agent-central-mapping）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/agent-central-mapping
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/agent-central-mapping
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### ai-coding-homework-writeup（安装｜unknown｜unknown）
- 用途："本 skill 适用于「把 AI 辅助开发的编程作业写成一份能交的提交材料」这类任务。当用户拿出作业要求（例如『用 Expo/React Native 开发一个 App，提交一句话介绍、运行截图、页面结构、核心功能、数据库说明』），要求你根据项目实际情况代写、帮交作业、填提交材料时触发；用户抱怨材…
- CANONICAL_ID：ai-coding-homework-writeup ｜ canonical_path：~/.skills-manager/skills/ai-coding-homework-writeup ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（3c833d12-397a-46dc-b618-7f2280c523df，central_path=~/.skills-manager/skills/ai-coding-homework-writeup）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/ai-coding-homework-writeup
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/ai-coding-homework-writeup
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/ai-coding-homework-writeup (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### ai-quota-recovery-board（安装｜unknown｜unknown）
- 用途：当用户想跟踪多个 AI 工具 / 服务的「额度 / 频率限制 / 信用点」恢复时间并做成可视化看板时使用。生成单文件 HTML 看板（时间轴甘特 + 实时倒计时表 + 本地追加表单），数据存浏览器 localStorage 不上云。This skill should be used when the…
- CANONICAL_ID：ai-quota-recovery-board ｜ canonical_path：~/.skills-manager/skills/ai-quota-recovery-board ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（b5eb016d-ff22-4d7d-a577-5b437a31264a，central_path=~/.skills-manager/skills/ai-quota-recovery-board）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/ai-quota-recovery-board
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### aihot（安装｜vendor｜active）
- 用途：查询 AI HOT 的中文 AI 资讯、精选、当前热点和日报。用户询问今天或最近的 AI 新闻、AI 圈动态、大模型或产品发布、OpenAI／Anthropic／Google 最新消息、AI 论文、AI 日报、AI HOT 精选、当前最热事件，或需要同步当前全部精选时使用。必须通过 aihot.vi…
- CANONICAL_ID：aihot ｜ canonical_path：~/.skills-manager/skills/aihot ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（b49f6fb0-a74f-4ff6-82fe-d8dd374de0ca，central_path=~/.skills-manager/skills/aihot）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/aihot
- 可用性：central(skills-manager)=available
- 来源：vendor ← Virxact / AI HOT（aihot.virxact.com）（confidence=high）｜ SKILL.md frontmatter 直接署名：metadata.author=Virxact、version=1.2.0（文件内作者证据，非『调用其 API』推断）；官方渠道当前版本 v1.7.1 同署名，版本谱系连续 → 由 AI HOT 服务方 Virxact 发布。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：outdated_version

### batch-organize（安装｜unknown｜unknown）
- 用途："本 skill 适用于「一批杂乱原始素材 → 统一规范成品」且需可重跑、可中断、可多智能体协作的批量整理任务（课程/播客/视频转写稿清洗、PDF 抽取稿整理、文档/知识库迁移、素材库去重归类等）。它提供通用分阶段流程、状态位(幂等)机制，以及「大模型管语义判断、脚本管确定性装配」的分工契约；具体提…
- CANONICAL_ID：batch-organize ｜ canonical_path：~/.skills-manager/skills/batch-organize ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（2a468daf-3f49-4997-a14e-e0a3b5647a3e，central_path=~/.skills-manager/skills/batch-organize）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/batch-organize
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/batch-organize
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/batch-organize (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### bilibili-download-check（安装｜unknown｜unknown）
- 用途：当需要对比哔哩哔哩 UP 主投稿目录与本地已下载视频、生成未下载清单，或按红利/打新等关键词筛选时使用。
- CANONICAL_ID：bilibili-download-check ｜ canonical_path：~/.skills-manager/skills/bilibili-download-check ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（27a7e1b3-d24e-4417-840f-437f1ca8ce25，central_path=~/.skills-manager/skills/bilibili-download-check）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/bilibili-download-check
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/bilibili-download-check
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 B 站投稿目录比对，无作者归属证据。
- 版本关系：not_compared

### browser-e2e-login-pitfalls（安装｜unknown｜unknown）
- 用途："浏览器端 E2E / 验收测试的踩坑与避坑手册：Vite 环境变量未注入、Google OAuth 拦截自动化浏览器（Chrome for Testing）、多 Chrome 窗口 activate 认错、Supabase OAuth 回调回落到错误 origin、supabase-js 默认 r…
- CANONICAL_ID：browser-e2e-login-pitfalls ｜ canonical_path：~/.skills-manager/skills/browser-e2e-login-pitfalls ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（7a8393b6-553c-499e-8c29-486a2a9bbb0a，central_path=~/.skills-manager/skills/browser-e2e-login-pitfalls）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/browser-e2e-login-pitfalls
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### browseros-neo（安装｜official｜active）
- 用途：The user's dedicated browser for agents — a real browser signed into their accounts, with live logins and a persistent profile. Use it for any task th…
- CANONICAL_ID：browseros-neo ｜ canonical_path：~/.agents/skills/browseros-neo ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：未注册（canonical 主副本不在中央仓库，属 agent 目录原位主副本）
  - 副本 [agent_replica/synced_replica]：~/.claude/skills/browseros-neo
  - 副本 [agent_replica/synced_replica]：~/.config/opencode/skills/browseros-neo
  - 副本 [canonical/canonical]：~/.agents/skills/browseros-neo
- 可用性：central(skills-manager)=missing，claude=available，opencode=available，agents=available
- 来源：official ← github.com/browseros-ai/BrowserOS（confidence=medium）｜ 安装目录含 BrowserOS 官方管理清单 .browserclaw-managed.json（官方安装器管理标记）；内容与官方仓库 skill 高度同源，但与所查 3 个官方 commit 均非逐字节一致（官方持续演进）→ 判 official，confidence=medium。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：outdated_version

### coding-workspace-organizer（安装｜unknown｜unknown）
- 用途：整理编码工作区：拍平嵌套归档目录，按 `NNN-状态-项目名` 规则重命名项目，并生成按序号查找的索引表。用户要求整理工作区、给项目文件夹编号、按序号排序、拍平暂停或归档目录，或在 Windows / macOS 上复用同一命名方案时使用。
- CANONICAL_ID：coding-workspace-organizer ｜ canonical_path：~/.skills-manager/skills/coding-workspace-organizer ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（17801f91-0451-4366-9450-a54c42d9a25f，central_path=~/.skills-manager/skills/coding-workspace-organizer）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/coding-workspace-organizer
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/coding-workspace-organizer
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/coding-workspace-organizer (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### computer-use（缺失（known_missing）｜official｜active）
- CANONICAL_ID：computer-use ｜ canonical_path：（无） ｜ SYNC_STATE：missing ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：未注册
- 可用性：central(skills-manager)=missing，workbuddy=broken，claude=broken，opencode=broken
- 来源：official ← github.com/stablyai/orca（confidence=high）｜ 内容与官方仓库逐字节一致：本地 SKILL.md（c79dedb3c7df）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/computer-use/SKILL.md → 由 Orca 官方仓库发布。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：historical_official_version

### computer-use-2（安装｜official｜active）
- 用途：Use Orca's computer-use CLI for OS/window-level inspection and input in visible local app windows. Use when a task must read or operate a native app o…
- CANONICAL_ID：computer-use-2 ｜ canonical_path：~/.skills-manager/skills/computer-use-2 ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（096b604d-6692-45ea-99e5-1486628b5fbb，central_path=~/.skills-manager/skills/computer-use-2）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/computer-use-2
- 可用性：central(skills-manager)=available
- 来源：official ← github.com/stablyai/orca（confidence=high）｜ 本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08-31）中 skills/computer-use/SKILL.md 逐字节一致 → 内容源自官方仓库（非本地修改；目录改名不改变来源归属）。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：historical_official_version

### course-md-organize（安装｜unknown｜unknown）
- 用途："把已提取的课程 Markdown 整理成「得到·刘澜式」舒服可读的文稿：顶部本课总结、错别字/OCR 校对、三级子标题逻辑分段、段落自然流动。用于 OCR/语音转写稿存在文字墙、错字、无结构的一批课程 .md，做批量、一致的重排版与精校。脚本阶段用 Python 标准库（无需依赖）；语义阶段由 L…
- CANONICAL_ID：course-md-organize ｜ canonical_path：~/.skills-manager/skills/course-md-organize ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（124de865-f8f2-45b6-b8d7-c76e19615e4a，central_path=~/.skills-manager/skills/course-md-organize）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/course-md-organize
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/course-md-organize
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/course-md-organize (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。（NOTE: central 与 60 Skill 仓库副本内容不同，见 CONTENT_VARIANTS。）
- 版本关系：not_compared

### course-pdf-to-md（安装｜unknown｜unknown）
- 用途："将课程类 PDF（得到/知识星球/小报童等导出，常配 MP3）批量整理为每章一个 Markdown 的流水线 skill。当用户需要：把一批课程 PDF 按章节提取文字稿、清洗平台声明/水印/评论区、原素材与文稿物理分离、文件名数字有序规整、顶部生成「本课总结」、或跨电脑/换智能体迁移复用该流水线…
- CANONICAL_ID：course-pdf-to-md ｜ canonical_path：~/.skills-manager/skills/course-pdf-to-md ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（3aee0d95-b9d5-42d0-9df3-2565c61b3d76，central_path=~/.skills-manager/skills/course-pdf-to-md）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/course-pdf-to-md
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/course-pdf-to-md
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### deploy-to-vercel（安装｜unknown｜unknown）
- 用途：Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push t…
- CANONICAL_ID：deploy-to-vercel ｜ canonical_path：~/.skills-manager/skills/deploy-to-vercel ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（23ad5e6e-14e2-4b69-99e3-9c25f1655783，central_path=~/.skills-manager/skills/deploy-to-vercel）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/deploy-to-vercel
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 Vercel 部署的 skill，无作者/发布方证据（类比：本地写的 Vercel 部署 skill ≠ Vercel 官方 skill）。
- 版本关系：not_compared

### dida-task-manager（安装｜unknown｜unknown）
- 用途："Dida365 / 滴答清单 习惯与任务操作的统一入口。覆盖新建/修改习惯（尤其『每天 N 次打卡才算完成』的量化习惯正确模板）、任务自动归类路由、习惯图标规则、倒数日只读边界。当用户说『新建习惯/打卡 N 次/建待办/提醒/排日程/复盘』时触发。"
- CANONICAL_ID：dida-task-manager ｜ canonical_path：~/.skills-manager/skills/dida-task-manager ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（f7ce8226-bdbd-43fe-9198-67f554cb0028，central_path=~/.skills-manager/skills/dida-task-manager）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/dida-task-manager
  - 副本 [agent_replica/synced_replica]：~/.workbuddy/skills/dida-task-manager
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：unknown ← unknown（confidence=n/a）｜ 封装 Dida365 API 的操作 skill，无法证明由滴答清单官方编写。
- 版本关系：not_compared

### find-skills（安装｜unknown｜unknown）
- 用途："帮助用户发现和安装智能体技能。当用户提出「如何做 X」、「查找某个技能」、「有没有能做……的技能」等问题，或表示希望扩展功能时使用。当用户正在寻找可能作为可安装技能存在的功能时，应使用此技能。"
- CANONICAL_ID：find-skills ｜ canonical_path：~/.skills-manager/skills/find-skills ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（5caa78c7-8a65-40ad-84ac-c86a8e5c05cf，central_path=~/.skills-manager/skills/find-skills）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/find-skills
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无 anthropic/作者引用（仅提及 WorkBuddy/skills CLI 安装机制）。
- 版本关系：not_compared

### frontend-design（安装｜official｜active）
- 用途：Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and…
- CANONICAL_ID：frontend-design ｜ canonical_path：~/.skills-manager/skills/frontend-design ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（f763a551-c35b-44db-9b29-c6d6b4e8a0aa，central_path=~/.skills-manager/skills/frontend-design）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/frontend-design
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：official ← github.com/anthropics/skills（confidence=high）｜ LICENSE.txt (Apache)；SKILL.md 自述为 Anthropic 官方设计 skill（'Anthropic's own Claude-interaction accent'）。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：not_compared

### github（安装｜unknown｜unknown）
- 用途："Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` for issues, PRs, CI runs, and advanced queries."
- CANONICAL_ID：github ｜ canonical_path：~/.skills-manager/skills/github ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（55b1f2d6-987e-4720-8ea7-ebeea7bf359d，central_path=~/.skills-manager/skills/github）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/github
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 封装 gh CLI 操作 GitHub，无作者归属证据（≠ GitHub 官方发布）。
- 版本关系：not_compared

### github-portfolio-sync（安装｜unknown｜unknown）
- 用途：当需要采集当前 GitHub 账号的公开和私有仓库，整理功能、技术栈与最新进度，并生成项目全景 Markdown 背景档案时使用。
- CANONICAL_ID：github-portfolio-sync ｜ canonical_path：~/.skills-manager/skills/github-portfolio-sync ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（eaa9b89c-e526-480e-8ee8-aaec20965ace，central_path=~/.skills-manager/skills/github-portfolio-sync）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/github-portfolio-sync
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/github-portfolio-sync
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 GitHub 仓库数据采集，无作者归属证据。
- 版本关系：not_compared

### github-readme-maintainer（安装｜unknown｜unknown）
- 用途：当需要编写、重写、审查或维护 GitHub README、项目介绍、docs 结构、仓库说明，或补全仓库 About 简介（Description / Website / Topics）时使用。默认基于真实仓库内容生成简体中文 README.md，并维护 README.en.md；禁止凭空编造功能。
- CANONICAL_ID：github-readme-maintainer ｜ canonical_path：~/.skills-manager/skills/github-readme-maintainer ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（f1e048df-4755-4642-b9e4-c7c2724ab47f，central_path=~/.skills-manager/skills/github-readme-maintainer）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/github-readme-maintainer
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/github-readme-maintainer
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 GitHub README 维护，无作者归属证据。
- 版本关系：not_compared

### grill-me（安装｜unknown｜unknown）
- 用途：Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user …
- CANONICAL_ID：grill-me ｜ canonical_path：~/.skills-manager/skills/grill-me ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（8062033d-0b31-4e90-bf9e-03d15e83b47b，central_path=~/.skills-manager/skills/grill-me）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/grill-me
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### guizang-ppt-skill（安装｜unknown｜unknown）
- 用途：生成横向翻页网页 PPT（单 HTML 文件），含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。提供两种风格：① "电子杂志 × 电子墨水"（衬线 + 流体背景 + 暖色） ② "瑞士国际主义"（无衬线 + 网格点阵 + IKB/柠檬黄/柠檬绿/安全橙高亮）。当用户需要制作分享 / 演讲…
- CANONICAL_ID：guizang-ppt-skill ｜ canonical_path：~/.skills-manager/skills/guizang-ppt-skill ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（9d71312b-5f9a-4ec9-a137-39991a42c203，central_path=~/.skills-manager/skills/guizang-ppt-skill）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/guizang-ppt-skill
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### hv-analysis（安装｜community｜active）
- 用途：横纵分析法（Horizontal-Vertical Analysis）深度研究Skill。由数字生命卡兹克提出，融合了索绪尔的历时-共时分析、社会科学的纵向-横截面研究设计、商学院案例研究法与竞争战略分析的核心思想。 当用户想要系统性研究一个产品、公司、概念、技术或人物时使用。核心是双轴分析：纵轴追…
- CANONICAL_ID：hv-analysis ｜ canonical_path：~/.skills-manager/skills/hv-analysis ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（16f95447-f6f2-4509-a156-b7bf2733bbad，central_path=~/.skills-manager/skills/hv-analysis）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/hv-analysis
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：community ← 数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills（confidence=high）｜ SKILL.md 明确标注方法由『数字生命卡兹克』提出；且内容与 github.com/KKKKhazix/khazix-skills 仓库中同名 skill 逐字节一致（本地 cb6227bf8ee4 == 上游实测）→ 作者归属与上游均确认，confidence 升为 high。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：upstream_in_sync

### khazix-writer（安装｜community｜active）
- 用途：数字生命卡兹克（Khazix）的公众号长文写作skill。当用户需要撰写公众号文章、写稿子、续写文章、根据素材产出长文时使用。触发词包括但不限于：写文章、写稿子、帮我写、续写、扩写、公众号文章、长文、出稿、按我的风格写。即使用户只是说"帮我把这个写成文章"或"用我的风格写一下"，只要上下文涉及内容创…
- CANONICAL_ID：khazix-writer ｜ canonical_path：~/.skills-manager/skills/khazix-writer ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（f2b9337f-7e38-4db6-9a03-3b1ed6c61103，central_path=~/.skills-manager/skills/khazix-writer）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/khazix-writer
- 可用性：central(skills-manager)=available
- 来源：community ← 数字生命卡兹克 (Khazix) — github.com/KKKKhazix/khazix-skills（confidence=high）｜ SKILL.md 自述：『数字生命卡兹克（Khazix）的个人写作风格skill』——直接署名；且内容与 khazix-skills 仓库逐字节一致（本地 521606caa000 == 上游实测）。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：upstream_in_sync

### leader（安装｜unknown｜unknown）
- 用途：把一句话的想法拆成 AI agent 能独立跑完的目标任务书。用户说「帮我给 agent 写个目标」「帮我详细拆一下这个目标」「写个任务书/brief 给 agent」「写个 goal 提示词」「让 agent 自己跑这个项目」「把活分给几个 agent 并行」时使用。先进代码库实测、必要时联网调研…
- CANONICAL_ID：leader ｜ canonical_path：~/.skills-manager/skills/leader ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（91d95755-0235-4b17-a9e3-58128ae36a65，central_path=~/.skills-manager/skills/leader）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/leader
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无文件内署名；但内容与 github.com/KKKKhazix/khazix-skills 中同名 skill 逐字节一致（本地 018fe973901c == 上游实测）——作者归属证据已具备，待用户确认后可升级 community（pending_upgrade）。
- 版本关系：upstream_in_sync

### local-service-change-acceptance（安装｜unknown｜unknown）
- 用途：改完本地长驻服务（单文件 Python HTTP 服务、本地控制台后端、桌面应用的内嵌服务）后，如何在真机上做「可信验收」——把用户真实数据撇开、用隔离目录跑端到端、以及识破「乐观状态位」「去重计数翻倍」「新字段没清零」这三类假通过/假失败。当用户说「改完了帮我验一下」「重启服务」「为什么状态显示不…
- CANONICAL_ID：local-service-change-acceptance ｜ canonical_path：~/.skills-manager/skills/local-service-change-acceptance ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（8852763a-48ff-43f5-85e6-13db1a091b89，central_path=~/.skills-manager/skills/local-service-change-acceptance）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/local-service-change-acceptance
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/local-service-change-acceptance
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/local-service-change-acceptance (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### make-repo-contribution（安装｜unknown｜unknown）
- 用途：'All changes to code must follow the guidance documented in the repository. Before any issue is filed, branch is made, commits generated, or pull requ…
- CANONICAL_ID：make-repo-contribution ｜ canonical_path：~/.skills-manager/skills/make-repo-contribution ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（e75ec231-27fa-4074-8b0a-184243138ea0，central_path=~/.skills-manager/skills/make-repo-contribution）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/make-repo-contribution
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 GitHub 仓库贡献流程，无作者归属证据。
- 版本关系：not_compared

### manage-skills（安装｜local｜not_applicable）
- 用途：Manage the user's shared agent-skill library via skills-manager-cli — install, update, remove, deploy or undeploy skills per agent, manage presets, or…
- CANONICAL_ID：manage-skills ｜ canonical_path：~/.skills-manager/skills/manage-skills ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（1bef6aec-76a4-4e70-a9e3-e2cf469e2b61，central_path=~/.skills-manager/skills/manage-skills）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/manage-skills
- 可用性：central(skills-manager)=available，opencode=available
- 来源：local ← 本地 skills-manager CLI（confidence=high）｜ SKILL.md 自述管理『the user's shared agent-skill library via skills-manager-cli』——面向本机自建工具的运维 skill（对 anthropics/skills.git 的引用是它可安装的来源之一，非自身出处）。
- 版本关系：not_compared

### mcp-one-command-setup（安装｜unknown｜unknown）
- 用途：Write a zero-dependency one-command installer for a local MCP (Model Context Protocol) server: auto-build, detect which AI clients are installed on th…
- CANONICAL_ID：mcp-one-command-setup ｜ canonical_path：~/.skills-manager/skills/mcp-one-command-setup ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（d8d37749-9a8d-475f-8a33-00e8bf2a62b3，central_path=~/.skills-manager/skills/mcp-one-command-setup）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/mcp-one-command-setup
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### neat-freak（安装｜unknown｜unknown）
- 用途：Knowledge and governance closeout: reconcile project docs, rule files (CLAUDE.md/AGENTS.md), authorized agent memory, and workspace residue with what …
- CANONICAL_ID：neat-freak ｜ canonical_path：~/.skills-manager/skills/neat-freak ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（357be922-3ec0-4cd4-adc6-b07459b04d56，central_path=~/.skills-manager/skills/neat-freak）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/neat-freak
- 可用性：central(skills-manager)=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无文件内署名（v3.0.0，仅泛引 Agent Skills 标准）；但内容与 github.com/KKKKhazix/khazix-skills 中同名 skill 逐字节一致（本地 c4dbe94169ed == 上游实测）——待用户确认后可升级 community（pending_upgrade）。
- 版本关系：upstream_in_sync

### netlify-deploy（安装｜unknown｜unknown）
- 用途：Create, configure, and manage Netlify deploys from code — reach for this when setting up Git continuous deployment, running netlify deploy or netlify …
- CANONICAL_ID：netlify-deploy ｜ canonical_path：~/.skills-manager/skills/netlify-deploy ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（36d5cbf1-f77b-4970-9b6b-53af42b80a33，central_path=~/.skills-manager/skills/netlify-deploy）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/netlify-deploy
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 Netlify 部署的 skill，无作者归属证据。
- 版本关系：not_compared

### obsidian（安装｜unknown｜unknown）
- 用途："Work with Obsidian vaults (plain Markdown notes) and automate via obsidian-cli."
- CANONICAL_ID：obsidian ｜ canonical_path：~/.skills-manager/skills/obsidian ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（6ba83375-4520-42bb-ad80-bed59d1a9e20，central_path=~/.skills-manager/skills/obsidian）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/obsidian
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 Obsidian vault 操作，无作者归属证据（≠ Obsidian 官方发布）。
- 版本关系：not_compared

### orca-cli（缺失（known_missing）｜official｜active）
- CANONICAL_ID：orca-cli ｜ canonical_path：（无） ｜ SYNC_STATE：missing ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：未注册
- 可用性：central(skills-manager)=missing，claude=broken，opencode=broken
- 来源：official ← github.com/stablyai/orca（confidence=high）｜ 内容与官方仓库逐字节一致：本地 SKILL.md（sha1 前12位 cddfd0a8c44e）== stablyai/orca commit f8b430f7（2026-07-20）中 skills/orca-cli/SKILL.md，同算法实测 → 由 Orca 官方仓库发布（第二轮『仅面向产品』的保守判定据此撤销）。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：historical_official_version

### orca-codex-commands（安装｜unknown｜unknown）
- 用途：Use when Stage Manager needs to call Codex via Orca terminal. Provides the exact commands for creating terminals, sending commands, monitoring progres…
- CANONICAL_ID：orca-codex-commands ｜ canonical_path：~/.config/opencode/skills/orca-codex-commands ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：未注册（canonical 主副本不在中央仓库，属 agent 目录原位主副本）
  - 副本 [canonical/canonical]：~/.config/opencode/skills/orca-codex-commands
- 可用性：central(skills-manager)=missing，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 排除法证据：对官方仓库 stablyai/orca 全量 tree（29,540 个路径，无截断）检索，不存在 skills/orca-codex-commands → 可排除官方发布；又无其他作者归属证据 → 维持 unknown。
- 版本关系：not_compared

### orchestration（缺失（known_missing）｜official｜active）
- CANONICAL_ID：orchestration ｜ canonical_path：（无） ｜ SYNC_STATE：missing ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：未注册
- 可用性：central(skills-manager)=missing，claude=broken
- 来源：official ← github.com/stablyai/orca（confidence=high）｜ 内容与官方仓库逐字节一致：本地 SKILL.md（8dd31dae1235）== stablyai/orca commit 1a9e819c（2026-07-22）中 skills/orchestration/SKILL.md → 由 Orca 官方仓库发布。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：historical_official_version

### place-journal-qa（安装｜local｜not_applicable）
- 用途：个人地点打卡手账（place-journal）项目的开发、测试与已知坑。适用于该工作区内 PWA 的迭代、QA 与部署准备。
- CANONICAL_ID：place-journal-qa ｜ canonical_path：~/.workbuddy/skills/place-journal-qa ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：未注册（canonical 主副本不在中央仓库，属 agent 目录原位主副本）
  - 副本 [canonical/canonical]：~/.workbuddy/skills/place-journal-qa
- 可用性：central(skills-manager)=missing，workbuddy=available
- 来源：local ← place-journal 项目（confidence=high）｜ SKILL.md 自述为个人地点打卡手账 place-journal 项目的开发/测试 skill。
- 版本关系：not_compared

### ponytail（安装｜unknown｜unknown）
- 用途：Forces the laziest solution that actually works, simplest, shortest, most minimal. Channels a senior dev who has seen everything: question whether the…
- CANONICAL_ID：ponytail ｜ canonical_path：~/.skills-manager/skills/ponytail ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（8d4419c6-bb56-48bf-83c9-6193be5b679d，central_path=~/.skills-manager/skills/ponytail）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/ponytail
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### skill-creator（安装｜official｜active）
- 用途：Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or opt…
- CANONICAL_ID：skill-creator ｜ canonical_path：~/.skills-manager/skills/skill-creator ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（ffb8b289-2b94-46ff-a2ea-c85b4b851eda，central_path=~/.skills-manager/skills/skill-creator）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/skill-creator
- 可用性：central(skills-manager)=available，claude=available，opencode=available
- 来源：official ← github.com/anthropics/skills（confidence=high）｜ LICENSE.txt line 190: 'Copyright 2026 Anthropic, PBC.'（官方版权行）。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：not_compared

### skill-manager-governance（安装｜local｜not_applicable）
- 用途：审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库。用户要求把中转站 skill 纳入中央库、解释为什么软件看不到、或迁移到 Windows、macOS 或其他智能体时使用。
- CANONICAL_ID：skill-manager-governance ｜ canonical_path：~/.skills-manager/skills/skill-manager-governance ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（2cb54f1d-1205-4448-9193-18ad230e4412，central_path=~/.skills-manager/skills/skill-manager-governance）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/skill-manager-governance
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/skill-manager-governance
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/skill-manager-governance (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：local ← 本地 Skill Manager / 60 Skill 仓库（confidence=high）｜ SKILL.md 自述『审查、修正、跨平台打包并正式导入本地 Skill Manager 技能库』——本机 Skill Manager 体系配套 skill。
- 版本关系：not_compared

### storage-analyzer（安装｜unknown｜unknown）
- 用途：macOS / Windows 只读存储分析助手（自动识别系统）。扫描整机磁盘占用，找出 占空间大户，把每一项分成 🟢可自动清理 / 🟡需人工判断 / 🔴谨慎清理 三级并给出 可执行处置方案，生成排版精美、可折叠、命令可一键复制的交互式 HTML 报告，并可 起本地服务在网页上一键删除（移废纸篓/直…
- CANONICAL_ID：storage-analyzer ｜ canonical_path：~/.skills-manager/skills/storage-analyzer ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（9cf9bc58-fbe3-432b-ba97-299aca2bdbab，central_path=~/.skills-manager/skills/storage-analyzer）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/storage-analyzer
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### theme-factory（安装｜official｜active）
- 用途：Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with…
- CANONICAL_ID：theme-factory ｜ canonical_path：~/.skills-manager/skills/theme-factory ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（ce21694b-4d08-44cf-ad22-56cdea7f27f5，central_path=~/.skills-manager/skills/theme-factory）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/theme-factory
- 可用性：central(skills-manager)=available，claude=available，opencode=available
- 来源：official ← github.com/anthropics/skills（confidence=high）｜ LICENSE.txt line 190: 'Copyright 2026 Anthropic, PBC.'（官方版权行）。
- 活跃度：active（核验日 2026-09-22）
- 版本关系：not_compared

### travel-cn（安装｜unknown｜unknown）
- 用途：旅行信息查询 - 去哪儿/携程/飞猪数据查询（Expedia 中国版）
- CANONICAL_ID：travel-cn ｜ canonical_path：~/.skills-manager/skills/travel-cn ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（76fc7ea5-9d1b-4be6-a005-1b514d186bbd，central_path=~/.skills-manager/skills/travel-cn）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/travel-cn
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向旅行服务数据查询，无作者归属证据。
- 版本关系：not_compared

### vercel-blocked-deploy-triage（安装｜unknown｜unknown）
- 用途："当 Vercel 部署显示 UNKNOWN/BLOCKED、构建被跳过、提交作者校验失败，或部署成功但线上仍是旧版本时使用；先诊断原因，再按授权执行解除措施。"
- CANONICAL_ID：vercel-blocked-deploy-triage ｜ canonical_path：~/.skills-manager/skills/vercel-blocked-deploy-triage ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（2ada1d17-e821-4b67-bb40-6b833ff2982e，central_path=~/.skills-manager/skills/vercel-blocked-deploy-triage）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/vercel-blocked-deploy-triage
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/vercel-blocked-deploy-triage
- 可用性：central(skills-manager)=available，workbuddy=available，claude=available，opencode=available
- 来源：unknown ← unknown（confidence=n/a）｜ 面向 Vercel 部署故障排查的 skill，无作者归属证据。
- 版本关系：not_compared

### weekly-review-standard（安装｜unknown｜unknown）
- 用途："周复盘 / 月复盘的标准格式、详细度、颗粒度与踩坑库。当用户要求「做周复盘 / 周报 / 拉取一周数据复盘 / 生成复盘看板 / 月度复盘」时触发，确保一次到位、不返工。覆盖 9 板块结构、各段详细度要求、B 快乐四象限按象限聚合、睡眠 SVG 折线图、习惯真实打卡率、长文分段、确认落盘门槛。与 …
- CANONICAL_ID：weekly-review-standard ｜ canonical_path：~/.skills-manager/skills/weekly-review-standard ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（b93de7e8-c2a4-48f1-8474-84e10bbe7176，central_path=~/.skills-manager/skills/weekly-review-standard）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/weekly-review-standard
- 可用性：central(skills-manager)=available，workbuddy=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

### win-reveal-and-gui-selftest（安装｜unknown｜unknown）
- 用途：在 Windows 上实现「打开文件所在位置／在资源管理器中定位文件」，以及用窗口标题差分自测任何 GUI 动作是否真的发生（含沙箱里跑 Bash/PowerShell 的进程与窗口可见性坑）。当用户说「点击后打开访达失效了」「改成打开文件所在位置」「explorer /select 定位错了」「怎…
- CANONICAL_ID：win-reveal-and-gui-selftest ｜ canonical_path：~/.skills-manager/skills/win-reveal-and-gui-selftest ｜ SYNC_STATE：canonical ｜ MACHINE_ID：Mac-mini
- Skill Manager 注册表：已注册（17d6651f-b9d7-44a0-a974-f44ca7a20997，central_path=~/.skills-manager/skills/win-reveal-and-gui-selftest）
  - 副本 [canonical/canonical]：~/.skills-manager/skills/win-reveal-and-gui-selftest
  - 副本 [dev_replica/local_only]：~/Downloads/大模型 HANDOFF/60 Skill 仓库/win-reveal-and-gui-selftest
  - 别名 [duplicate_alias/conflict_copy]：`~/.skills-manager/skills/win-reveal-and-gui-selftest (2)`（全目录逐字节一致）
- 可用性：central(skills-manager)=available
- 来源：unknown ← unknown（confidence=n/a）｜ 无 source 字段、无作者/上游引用。
- 版本关系：not_compared

