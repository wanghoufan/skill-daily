# External Skill Intelligence（外部 Skill 情报层）

Skill 日报的**第三个正式输入**。回答一个问题：

> 外面出现了哪些值得关注的新 Skill / 更新 Skill，其中哪些真正适合我当前项目，而且**不会与已有能力重复**？

三层输入的分工：

| 输入 | 文件 | 回答 |
|---|---|---|
| A 项目需求 | `SKILL_CONTEXT.md`（项目档案自动生成，只读） | 我现在在做什么、真正需要什么能力 |
| B 已装能力 | `Agent 产物（外部情报层）/转送审查者 v4 材料（Canonical 模型）/INSTALLED_SKILLS_CONTEXT.md` + `SKILL_SOURCE_MAP.json`（**已冻结，本层只读**；v2.6 起转送材料统一收进 `Agent 产物（外部情报层）/` 子目录，路径自动定位，也可用环境变量指路） | 我已经有什么、哪些 strong/weak/none、哪些当前 degraded |
| C 外部候选 | **本层**：`EXTERNAL_SKILLS_CONTEXT.md` + `data/SKILL_CANDIDATES.json` | 外面有什么值得看的新候选 |

> **本层只做发现与分析，绝不安装。** 安装一律由用户在 Skill Manager 中人工执行。

---

## 一、快速开始

```bash
cd "external-intelligence"
PY=${PY:-python3}                 # 用你自己的 python3（**需 3.12+**，仅标准库，无第三方依赖）

$PY scripts/run_daily.py          # 一键全链路：注册表 → 发现 → 分析 → Context + delta
$PY tests/test_pipeline.py        # 离线测试（90 项，含 hashseed 矩阵硬门；摘要分 PASS / SKIP / FAIL 三栏）
$PY scripts/make_digest.py        # 生成精简对照件（总览 + Top + ALTERNATIVES + 安全清单 + 整改记录）
```

> 交换目录：`SKILL_REPO_ROOT` / `SKILL_CONTEXT_PATH` / `SKILL_DATA_DIR` /
> `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH` 可覆盖默认路径（见 `scripts/common.py` 顶部注释）。
> 代码内不写死任何用户名与绝对目录，换机器或换账号只需设环境变量。
>
> **GitHub API 配额（v2.2 重要）**：本层会调 GitHub API。匿名额度只有 **60 次/小时**，
> 一轮全量跑需要几百次调用，很容易半途耗尽并把整批候选打成 `deep_scan=failed`
> （fail-closed → 安装候选归零，v2.2 实测踩过）。解决办法按优先级：
> ① 设 `GITHUB_TOKEN` / `GH_TOKEN` 环境变量（5000 次/小时）；
> ② 什么都不设也行——脚本会自动读本机 `gh auth token`（已 `gh auth login` 即可）。
> API 响应**只在成功时落盘缓存**（24h），失败绝不写缓存，因此配额耗尽后隔一会儿重跑即可恢复。

单步：

| 脚本 | 作用 | 输出 |
|---|---|---|
| `scripts/build_registry.py` | 联网验证 TIER 0-3 来源并采集证据 | `data/SKILL_SOURCE_REGISTRY.json` |
| `scripts/discover.py` | 双向发现：Top-down（官方/社区仓库 + 聚合榜）+ Bottom-up（能力缺口查询族）；顺带采集每个 Skill 目录下的脚本清单，供 PASS 2 零额外 API 调用使用 | `data/raw/discovery_*.json`、`data/raw/gap_focus.json` |
| `scripts/analyze.py` | canonical 去重 → **数据质量 Gate** → 安装关系 → MATCH_RULE 语义匹配 → Security Gate → 评分 → PASS 2 深度审查 | `data/SKILL_CANDIDATES.json` |
| `scripts/build_context.py` | 轻量日报底座 + 每日 delta | `EXTERNAL_SKILLS_CONTEXT.md`、`data/state/last_snapshot.json` |
| `scripts/make_digest.py` | 给审查者看的切片视图（**排序与 Top 规则复用 `build_context`，不另写一套**） | `CANDIDATES_DIGEST.md` |

模块（被上面脚本 import）：

| 模块 | 职责 |
|---|---|
| `scripts/match_rules.py` | **MATCH_RULE 语义引擎**：`all_groups`(组间 AND/组内 OR) / `any_of` / `any_groups` / `none_of` / `context_terms` / `custom`；整词与短语匹配（含 CJK 子串）；**两段式否定窗口**（v2.4 §五 + v2.5 §二：逗号只在段内传播否定、对比词恢复正向）；`TECH_MATCH`（带 `tier: strong/secondary`）/ `CAP_TYPE` / `NEED_TYPE`；**`match_projects`（v2.4 直接证据分级 + v2.5 词面证据仅限领域短语/次要加分）**；**`capability_evidence_context` 四态分类器（v2.5 §九）**；**v2.6：跨 Skill 重定向窗口 `strip_redirects`（§五）/ MCP 工件级分类 `mcp_usage`（§六）/ frontend_design 设计语义与 image_creative 扩充（§七）/ deploy 纯操作语义（§八）/ GCP 产品别名 + `microsoft-store` 域（§四）/ `product_scope` 三态 + 解除判定（§十）** |
| `scripts/security_gate.py` | Security Gate **v2.3**（finding 带 `confidence` + `behavior_context`，含 `warning` 语境；`always_block` 受语境约束）+ PASS 2 深度静态审查 + 带认证的 API 层 |
| `scripts/data_gate.py` | 数据质量 Gate：构建产物识别、skill slug 合法性、最小 frontmatter 校验 |

### 换机器 / 归档副本怎么跑

本层**不是自包含的**：它读「已装侧底座」（v4 转送文件夹）和「项目需求」（本机另一处
`SKILL_CONTEXT.md`）。两者路径都可用环境变量覆盖，**不用改代码**：

```bash
SKILL_REPO_ROOT="/path/to/60 Skill 仓库" \
SKILL_CONTEXT_PATH="/path/to/SKILL_CONTEXT.md" \
$PY scripts/run_daily.py
```

| 环境变量 | 作用 | 默认 |
|---|---|---|
| `SKILL_REPO_ROOT` | 中央仓库根目录（v4 底座所在） | 按脚本位置向上推断 |
| `SKILL_CONTEXT_PATH` | 输入 A：项目需求 `SKILL_CONTEXT.md` | 见下方三级优先序 |
| `SKILL_DATA_DIR` | 候选池/注册表目录 | `scripts/` 上一级的 `data/` |
| `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH` | 直接指定已装侧单个文件 | 由 `SKILL_REPO_ROOT` 推出 |

**（v2.3 §九）输入解析优先序**——归档包解压后能自定位，不再依赖本机路径：

| 输入 | ① 环境变量 | ② 自动定位 | ③ 兜底 |
|---|---|---|---|
| A 项目需求 | `SKILL_CONTEXT_PATH` | **包内 `支撑/输入/SKILL_CONTEXT.md`**（兼容 `BASE/输入/` 与 `dirname(BASE)/支撑/输入/`） | 本机默认路径 |
| B 已装侧底座 | `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH` | 同级 **v4 文件夹**自动发现（向上 3 级） | **SKIP 并明确提示** |

命中的来源会记录在 `common.PATH_RESOLUTION`，可直接核对本次到底读了哪个文件（对照件 §六 会打印它）。

> **测试摘要不再混淆**：runner 把结果拆成 `pass / skip / fail` 三栏。`ALL TESTS PASSED`
> 只有在 `fail=0` 时成立，且**SKIP 不计入 PASS**——归档副本若缺输入 B，会如实显示
> `pass=25 skip=1 fail=0`，而不是含糊的「26/26 PASS」。
>
> 归档副本（`转送审查者 v5 材料（外部情报层）/支撑/`）**解压后能自定位输入 A**（命中包内
> `支撑/输入/SKILL_CONTEXT.md`）；若环境里没有同级 v4 底座，输入 B 相关测试会如实记为
> `SKIP` 并打印原因，**不会伪装成 PASS**。
> 注意 `run_daily.py` 会写文件；不想污染送审副本就先整包复制一份。

---

## 二、来源注册表（TIER 0-3）

`data/SKILL_SOURCE_REGISTRY.json`，每条来源含规定字段：

`source_id` / `name` / `tier` / `type` / `url` / `repo` / `owner` / `trust_level` /
`discovery_only` / `supports_versions` / `supports_install_signal` /
`supports_activity` / `last_checked` / `status`

| TIER | 定位 | 当前来源 | trust_level |
|---|---|---|---|
| **0** | 标准/规范——只做结构合规验证，**不参与热门排名** | agentskills.io、agentskills/agentskills | `spec_only` |
| **1** | 官方/厂商仓库（org 归属已核验） | anthropics/skills、github/awesome-copilot、vercel-labs/agent-skills、vercel-labs/skills、microsoft/skills、huggingface/skills、stablyai/orca、google/skills、browseros-ai/BrowserOS | `high`（awesome-copilot 为 `medium`） |
| **2** | 高质量社区作者（逐项验证，**不按 star 收录**） | KKKKhazix/khazix-skills、obra/superpowers、wshobson/agents | `medium` |
| **3** | 聚合发现源——只用于发现与趋势 | skills.sh、ClawHub、SkillsMP | `discovery_only` |

**TIER 2 收录硬门**：必须①真有 `SKILL.md`（tree API 计数）②作者身份可核验（GitHub API `repo.owner`）③维护活跃度可核验（`pushed_at`）④记录 license 与版本元数据。**star 只记录、不排序。**

> 实测口径：按 `topic:agent-skills` 动态搜索到的 24 个仓库里，绝大多数是 0-2 star 的垃圾/SEO 仓——这正是「不按 star 盲目收录」的现场证据，因此首版 TIER 2 只收 3 个能拿出硬证据的仓库。

`discovery_only` 的含义：**不得据其排名或安装量直接推荐**。TIER 0 与 TIER 3 恒为 `true`。

---

## 三、候选数据模型

`data/SKILL_CANDIDATES.json`，每条候选含：

- **身份**：`canonical_key`（= `owner/repo/skill`，小写）/ `skill_name` / `owner` / `repo` / `source` / `sources[]` / `source_tier` / `origin_type` / **`lineage_evidence`（v2.6 §二：already_installed 的血缘证据，必须非空）** / **`update_lineage`（v2.6 §三：installed_canonical_id / installed_upstream / update_upstream / lineage_evidence / lineage_verified）**
  - `source_tier` 取值：`0/1/2/3` 或 **`null`（= unverified，bottom-up 直出但已过 SKILL.md 硬门）**。unverified 恒为最低信任（`tier_trust_ceiling.unverified = 3`），**永不得升为安装候选**。
- **内容**：`description` / `capability_tags` / `content_fingerprint` / `skillmd_url`
- **时间**：`discovered_at` / `last_seen_at` / `latest_commit`（+`latest_commit_source`）/ `latest_version` / `latest_release`
- **信号**：`adoption_signal`（install_count / weekly_installs / stars / signal_source / note）/ `trend_signal` / `upstream_activity`
- **匹配**：`project_match`（`matched_needs` / `matched_need_weights` / `matched_need_evidence` / **`matched_need_evidence_levels`（v2.5 §九）** / `need_evidence` / `domain_mismatch` / **`domain_mismatch_domains` + `domain_mismatch_unresolved`（v2.4 §九）** / **`matched_projects[]`（每条含 `direct_evidence` + `direct_evidence_kinds` + `project_domains`，v2.4）** / `priority`）/ `capability_gap_match`（gap_level ∈ none/weak/medium/strong + **`capability_evidence_context` ∈ primary/supporting/mention/negated（v2.5 §九）** + **`scope_type` ∈ generic/platform_operation/product_internal 与 `target_product`、`product_internal_unresolved`（v2.6 §四/§十）**）
- **关系**：`installed_relationship` ∈ `already_installed` / `near_duplicate` / `overlap` / `complement` / `new_capability` / `replacement_candidate` / **`same_name_unverified` / `same_name_different_source` / `possible_fork`（v2.6 §二：同名但血缘未确认——不标已装、不建 update/replacement 关联、最高 watch）**
- **安全**：`security`（`status` ∈ scanned/unscanned + `verdict` + `risk_level` + 7 个行为布尔标志 + `findings` + `deep_scan_status`）
- **评分**：`scores`（8 维 + `total`）
- **结论**：`recommendation` ∈ `install_candidate` / `watch` / `ignore` / `reject` + `recommendation_reason`

顶层还有 `counts`（含 `invalid_artifacts_removed` / `invalid_names_removed` / `bottom_up_*`）与
`quarantine`（四类隔离区：`invalid_artifacts` / `invalid_names` / `invalid_bottom_up` /
`unverified_bottom_up`）——**被挡掉的条目留痕可追溯，不是悄悄丢掉**。

**去重只认 canonical source（owner/repo/skill），绝不只按名称。** 同一 Skill 出现在多个来源时会合并，`source_tier` 取最小（最可信）的那个。

`security` 的 7 个行为标志：`shell_exec` / `network_access` / `filesystem_write` /
`destructive_commands` / `secret_access` / `remote_instruction_fetch` / `external_dependencies`（未扫描时为 `null`）。

### 3.1 `matched_projects`：把「对哪个项目有用」答出来（v2.4 STRONG/SECONDARY 分级 + v2.5 词面证据收口）

`project_match.matched_projects[]` 从输入 A `SKILL_CONTEXT.md` 的 §2「进行中的项目」解析出
（name / positioning / tech / date），逐条打分，**最多 5 条**、低于阈值不硬凑。
每条含 `project` / `evidence[]` / `match_score` / **`direct_evidence` + `direct_evidence_kinds`
+ `project_domains`**。

**v2.3 §一/§六——DIRECT_PROJECT_EVIDENCE（建立直接证据门）。**
v2.2 的 `TYPE_W=30` 在最后 ×2，于是「同属 Web/PWA / Android / macOS」这种**类型适用**就能
单独拿到 60 分，制造出大量假匹配：

| 假匹配（v2.2 实测） | 分数 |
|---|---|
| `orca-emulator-android` → `DeepSeekBalanceWidget-Mac` | 90 |
| Bats testing → 多个普通 PWA 项目 | 60 |
| GitHub issue creator → Expo/Android 项目 | 60 |

**v2.4 §一/§二——把「直接证据」本身再分级（本轮核心）。**
v2.3 之后仍有「**规则形式上有 direct evidence，但真实语义是假相关**」的问题：
`azure-microsoft-playwright-testing-ts` 只因描述里有 `TypeScript`，就匹配了 5 个普通 TS 项目。
技术栈命中**不能天然等于**直接项目证据，所以拆成两级：

| 级别 | 技术栈 | 行为 |
|---|---|---|
| **STRONG** | Expo / React Native / Android / Kotlin / Supabase / Postgres / Next.js / PWA / 离线本地存储 / macOS 桌面 / 原生 / LLM API / Playwright / Vercel / Netlify / Cloudflare / CF Pages / .NET / C# | **可独立形成** matched_project |
| **SECONDARY** | TypeScript / React / Python / Docker / 自托管 / Tailwind / shadcn / 单文件 HTML / Shell | 只加 `SECONDARY_BOOST = 3.0`，**绝不单独成立** |

> 不变式守卫：`STRONG_TIER_MIN_W = 10`，且回归测试断言「每个 strong 技术栈的权重都够独立过
> `min_score`」——否则分级只是文档承诺（Next.js 原为 9 分，归一化 18 < 20，**永远无法独立成立**）。

四类直接证据（`direct_evidence_kinds`）：

| 证据类型 | 含义 | 判定 |
|---|---|---|
| `strong_tech` | 候选核心能力**明确针对**项目用的技术栈 | `TECH_MATCH` 命中且 `tier == strong` |
| `positioning` | 候选任务与项目**定位/功能语义**命中 | 能力类型 ∩ 项目定位语义 |
| `shared_need` | 项目**自己的高优需求**与候选能力命中 | `NEED_RULE` 命中 |
| `lexical` | 词面证据 | **v2.5 §三/§四/§五**：可独立成立的只有人工整理的**项目域短语**（`_PROJECT_DOMAIN_PHRASES`：prompt management / prompt library / 提示词管理…）；普通词级重叠（≥2 个非 stop、非技术泛词的词）**只作次要加分**，须与其余三类主证据同现；泛用技术词（react / native / typescript / api…）与裸 `prompt` **全禁**，单独成立计 `lexical_alone_rejected` |

- 无任何直接证据 → `matched_projects = []`（**宁可空，不准硬凑**）。
- 覆盖类指标**不再是 KPI**（v2.2 曾要求 90%+），改为准确率优先、只作参考。

**v2.4 §十——精度指标换成 `PROJECT_MATCH_QUALITY`。**
`351/351 direct evidence` 只能证明「字段不为空」，证明不了证据有效。现在改为分项计数：

| 指标 | 含义 |
|---|---|
| `matched_candidates` | 至少有一个 `matched_project` 的候选数 |
| `strong_tech_evidence` / `positioning_evidence` / `shared_need_evidence` / `lexical_evidence` | 四类直接证据的「候选 × 项目」条数 |
| `secondary_tech_only_rejected` | **只**靠泛用技术栈硬凑、已被拒的候选数 |
| `negated_evidence_rejected` | 被否定窗口 / 排除语境压掉的命中次数（看得见门在工作） |
| `lexical_single_rejected` | 词面重叠只因单个低区分度词而不足以成立的次数 |
| `lexical_alone_rejected`（v2.5） | 词级重叠想**独立**造匹配、被拒的次数（词面只作次要加分） |
| `lexical_phrase_direct_evidence`（v2.5） | 靠领域短语独立成立的词面直接证据条数 |
| `bare_prompt_direct_evidence`（v2.5） | 裸 prompt 被当直接证据的次数 —— **恒为 0 哨兵** |
| `tech_words_used_as_lexical_direct_evidence`（v2.5） | 泛用技术词充当词面直接证据的次数 —— **恒为 0 哨兵** |
| `redirect_evidence_rejected`（v2.6） | 跨 Skill 重定向小句（For X, use other-skill）被剪掉的次数（§五） |
| `same_name_only_already_installed`（v2.6） | 只凭同名判已安装的条数 —— **恒为 0 哨兵**（§二） |
| `wrong_update_lineage`（v2.6） | 血缘未验证的 update_available —— **恒为 0 哨兵**（§三） |
| `gcp_alias_missed`（v2.6） | 描述含 GCP 产品别名却未标 gcp 域 —— **恒为 0 哨兵**（§四） |
| `same_name_unverified_candidates` / `product_internal_unresolved_candidates`（v2.6） | 等同名未确认 / 未解除产品自研的候选数（观察项） |
| `product_specific_scope_unresolved`（v2.7） | 未解除的产品专项 platform_operation 数（GA Admin / SecOps / anthropic-brand…，观察项） |

四项写在 `SKILL_CANDIDATES.json` 顶层与 `EXTERNAL_SKILLS_CONTEXT.md` 的
`PROJECT_MATCH_QUALITY:` 机器块里。**准确率优先于 coverage：`matched_projects`
下降完全可以接受。**

### 3.2 数据质量 Gate（v2.2 新增）

进正式候选池**之前**先过一道 Gate，避免「不是 Skill 的东西」污染池子——这是 v2.1
被审查指出的「普通仓库/静态资源混进候选池」问题的修法（模块：`scripts/data_gate.py`）。

| 判定 | 挡什么 | 例子 |
|---|---|---|
| `is_artifact_entry` | 构建产物：扩展名（`.css/.js/.map/图片/字体/.min.js`）+ 路径（`assets/` `static/` `build/` `dist/`）+ 哈希文件名 | `assets/design-system-xxxx.css`、`index-xxxx.js`、`fonts/inter.woff2` |
| `is_valid_skill_name` | 必须像 slug（字母数字起头，允许 `-_.`）；含文件扩展名或路径分隔符的一律挡 | `logo.png`、`chunk-9f8e7d.js` |
| `has_min_fm` | 连 `name`/`description` 都没有的「伪 SKILL.md」 | 空文件、纯 README |

**Bottom-up 搜索 ≠ TIER 2**（v2.2 修正）：

- bottom-up 只是 `discovery_channel`，它找到的仓库**必须过与 TIER 2 同一道硬门**
  ——用 tree API 校验目录内真有 `SKILL.md`。
- 过了门也只进 `source_tier = null`（**unverified**，最低信任，`tier_trust_ceiling.unverified = 3`），
  **永不自动升 T2**；没过门的进 `quarantine.invalid_bottom_up` / `unverified_bottom_up` 留痕。

本期实测：`bottom_up_total 41 → verified 17 / quarantined 23`；
聚合源解析层挡掉构建产物 **67** 条；入池前挡掉非法名 1 条。

---

## 四、能力缺口如何驱动发现（读取已装侧，不写死）

Bottom-up 搜索的焦点能力**动态派生**自已装侧冻结真相源：

| 已装侧状态 | 发现优先级 |
|---|---|
| `CAPABILITY_SUPPRESSION = none` | **高优先**搜索 |
| `weak` | 优先寻找完整方案 |
| `medium` | 只有明显增强才推荐 |
| `strong` | 默认大幅降权 |
| `strong` **但** `CAPABILITY_AVAILABILITY = degraded` | **不按正常 strong 压制** → 记为 `priority=recovery`，允许「恢复现有官方 Skill」或「补足缺失能力」的候选进入高优先关注 |

当前该规则的实际生效对象：`orca_integration`（coverage=strong / availability=degraded）。

---

## 五、安全 Gate v2（优先于分数）

对候选的 `SKILL.md`（PASS 1）与 Skill 目录下的脚本（PASS 2）做**静态**审查
（只读文本匹配，**任何情况下都不执行被抓取的代码**）。

### 5.1 核心原则：「提到危险行为」≠「真的要求执行危险行为」

v2.1 的缺陷：只要文本里出现 `.env` / `GITHUB_TOKEN` / `eval` / `sudo`，就判 `risk_level=high`
→ `reject`。结果是**误伤**：正常部署 Skill 合法引用 token、安全审计 Skill 讲解 `eval` 的危害、
文档里讨论 `.env` 规范——统统被判高危。

v2.2 给每条 finding 增加两个维度：

| 字段 | 取值 | 含义 |
|---|---|---|
| `confidence` | `high` / `medium` / `low` | 证据强度 |
| `behavior_context` | `mention` / `instruction` / `executable` / `remote_execution` / **`warning`**（v2.3） | 这段文字是**在讲**、在**让人做**、**真的会被执行**，还是**在警告别人别做** |

`verdict` 取值：`pass` / `review_required` / `block` / `unscanned`。

- **`block`** 只留给高置信、会真被执行的危险行为：`curl|bash` 管道执行、`rm -rf ~/`、
  凭据外泄（`cat ~/.ssh/id_rsa | curl …`）、混淆 payload 执行（`base64 -d | bash`）等。
- 文档讨论 `sudo` / 示例读取 `GITHUB_TOKEN` / 解释 `eval` → `review_required`，交人工判断。
- **只有 `block` 才 `reject`**；`review_required` 不再等于 reject。
  但**真在指令/可执行语境里的高敏感项**（`severity=high` 且 `behavior_context != mention`）
  会挡在安装候选之外 → 最高 `watch`。

**（v2.3 §四）`always_block` 不再「命中即 block」。**
v2.2 里 `destructive_rm_root` / `pipe_to_shell` 这类 `always_block` 规则绕过了语境判断，
后果是：**安全审查类 Skill 在文档里举 `rm -rf /` 反例，自己反而被 reject** ——
「讲安全的被安全门杀了」。现在改为：

```python
_should_block(rule, ctx) = rule in BLOCK_ELIGIBLE_RULES and ctx != "warning"
```

- `warning` 语境优先判定：`never ...` / `do not ...` / `禁止 ...` / `不要 ...` / 举反例 /
  安全审计文档 → **一律 `review_required`，绝不 block**（`_NEGATION_RE`）。
- 其余高敏命令语境未限定时 **fail-closed**：真 `rm -rf ~/`、真 `curl … | bash` 仍必须 block。
- 同时收窄了 `destructive_rm_root` 的正则，`rm -rf /tmp/build-cache` 这类正常清理不再误伤
  （原正则把任意以 `/` 开头的路径都当根目录）。

### 5.2 两阶段：PASS 1 扫文档，PASS 2 深读脚本

有 `scripts/` 的候选不能只打一个「bundled_scripts=low」就放行。

- **PASS 1**：并发抓取 `SKILL.md`（预算 `scan_budget`，默认 600），套用规则表。
- **PASS 2**：对本轮 `install_candidate`（预算 `deep_scan_budget`，默认 80）逐个列出
  `.py/.sh/.js/.ts/.mjs/.cjs/.ps1` 与 `package.json` 的 `postinstall`/`preinstall`，静态读取并套用同一套规则。
  - **零额外 API 调用**：脚本清单在 discover 阶段随仓库文件树一次取回。
  - **硬门**：`install_candidate` 必须 `deep_scan_status = complete` 且无 block 级 finding。
  - `deep_scan_status` 枚举：`complete`（真扫过）/ `failed`（文件树不可读）/ `pending`（超预算，fail-closed）/
    `not_required`（未进安装候选，未触发）/ `skipped`（无目录信息）。
    **`complete` 只出现在真正做过深度审查的候选上**，不把「没扫」写成「已扫」。

### 5.3 fail-closed，但不制造不可恢复的假阴性

- 未扫描（`unscanned`）→ **不得成为 `install_candidate`**，最高只能 `watch`。
- **官方来源不豁免**（source_trust 可以高，不能跳过 Gate）。
- 抓取失败**不长期缓存**：命中缓存的失败只保留 1 小时（成功结果缓存 24 小时），
  API 失败**完全不落盘**。避免「一次配额耗尽锁死一整天」。

### 5.4 规则表中的「无条件 block」（高置信危险行为）

`pipe_to_shell` / `pipe_to_interpreter` / `destructive_rm_root` / `credential_exfil` /
`obfuscated_payload_exec` / `remote_fetch_exec` 属于 `BLOCK_ELIGIBLE_RULES`；
其余规则（`sudo`、`dynamic_code`、`ssh_keys`、`credential_files`、`git_push_auto`、
`auto_deploy`、`telemetry_exfil`、`postinstall_hook`、`obfuscation`、`broad_fs`、
`network_generic`）**永远只产生 `review_required`**，`severity` 由 `behavior_context`
决定（`mention` / `warning` 降一档，`instruction`/`executable`/`remote_execution` 保持原档）。

> **注意措辞的变化（v2.3）**：v2.2 管它们叫「无条件 block」，但 v2.3 起它们**也是有条件**的
> —— `behavior_context == "warning"` 时不 block。这个表名改成
> `BLOCK_ELIGIBLE_RULES`（有资格 block）而不是「必然 block」。

---

## 六、个性化评分（总分 100，权重可配置）

配置在 `config/scoring.json`，改权重无需改代码。同文件还有 `scan_budget`（单轮静态审查的抓取上限，默认 600；按「焦点能力相关性 → 层级 → adoption」优先扫描，超出预算的候选记 `unscanned`，**不得成为 install_candidate**）。

`top_candidates` 段（v2.3 扩充，v2.4 §九 加第四道门）同时承载 Top 的质量门：

```json
"top_candidates": {
  "target_limit": 30,
  "allowed_recommendations": ["install_candidate", "watch"],
  "min_score": 55,                    // §五 质量门①
  "require_personalized_evidence": true,   // §五 质量门②
  "t3_requires_corroboration": true,       // §五 质量门③
  "fold_cross_repo_family": true           // §三 跨仓功能族折叠
}
```

> 质量门④（**无未解除的平台错配**，v2.4 §九）由 `build_context.select_top()` 的
> `require_no_mismatch=True` 默认生效，判定依据是 `analyze.py` 写进
> `capability_gap_match.domain_mismatch_unresolved` 的结果——不需要额外配置项，
> 因为它表达的是「用户项目里没有该平台就不该占 Top」这条不变式。

| 维度 | 权重 | 说明 |
|---|---|---|
| PROJECT_MATCH | 25 | 命中 `SKILL_CONTEXT.md` 的真实需求权重后归一化（`wsum/2.6`：单个最热需求约 18~20 分，两个高权重需求封顶 25）。**无需求证据 = 0 分**；平台错配再 ×0.35；**v2.5 §九：supporting 级需求证据权重 ×0.5** |
| CAPABILITY_GAP | 20 | 读已装侧 none/weak/medium/strong；overlap/near_duplicate 封顶 5；**无需求证据时封顶 5**（缺口必须先是项目需要的能力）；**v2.5 §九：`capability_evidence_context` 非 primary 封顶（supporting ≤8，mention/negated ≤2）** |
| SOURCE_TRUST | 15 | TIER 只决定信任**上限** |
| SECURITY | 15 | low 15 / medium 7 / unknown 4 / high 0 |
| MAINTENANCE | 10 | 最近提交/推送时间 |
| ADOPTION_TREND | 5 | **上限只有 5 分**——排行榜/安装量绝不能等于推荐 |
| DETOUR_REDUCTION | 5 | 是否减少反复踩坑 |
| NOVELTY_VS_INSTALLED | 5 | 只是重复已有 strong 能力则降分 |

> **v2.4 §九 的总分乘数**：若 `domain_mismatch_unresolved` 非空，上面八项相加得到的
> `total` 会再乘 `DOMAIN_MISMATCH_PENALTY = 0.7`。因此 `total` **刻意不等于各分项之和**，
> 系数以 `domain_mismatch_penalty` 单独记录，可审计；平台一旦被真实项目解除，惩罚自动消失。

### 6.1 相关性否决（Gate 之后、install_candidate 之前）

分数再高，只要满足下列任一条件，最高只能是 `watch`：

1. **未命中任何真实项目需求**——说明这个 Skill 与用户在跑的项目无关；
2. **平台错配（v2.4 §九 起真正生效）**——技能面向用户技术栈里不存在的云/企业平台
   （`azure` / `google cloud` / `bigquery` / `aws` / `java` / `.net` / `dynamics 365` …，
   见 `match_rules.py:MISMATCH_DOMAIN`）。现在不只是降权：**不得 `install_candidate`、
   不得进 Personalized Top、总分 ×0.7**，默认进 watchlist。
   但**不做永久 blacklist**——用户项目档案里一旦明确出现该平台（name / desc / tech 任一），
   该域即标为 `domain_mismatch_resolved`，惩罚自动解除、正常参与排序。
   错配平台仍可能含通用方法，故不从池中删除，只降权 + 挡住 Top。

理由是「个性化」三个字的底线：日报应当回答「有什么适合**我**的」，而不是「世界上有什么」。

### 6.2 关键词必须整词/短语匹配（2026-09-22 修复）

> **这是个真实事故，值得记住。** 早期版本用 `kw in text` 做子串匹配，而 `frontend_design` 的关键词里有一个 `"ui"`：
> - `"ui" in "build"` → True
> - `"ui" in "require"` → True
> - `"ui" in "guidance"` / `"guide"` / `"built-in"` → 全是 True
>
> 结果**几乎所有 Skill 都被打上 `frontend_design`**，而 `frontend-design` 恰好是权重最高的项目需求（`w=48`）→ `PROJECT_MATCH` 恒等于满分 25，该维度彻底失去区分度；与此同时 `"image"` 命中 `imageanalysis`、`"data"` 命中 `database`、`"migration"` 命中 Airflow migrations。最终 Top30 被 `azure-ai-vision-imageanalysis-java`、`bigquery-ai-ml`、`managed-airflow-migrations` 这类与用户毫无关系的云厂商技能占满。
>
> 现在 `match_rules.py` 强制：单个词元 → **整词**匹配；含空格/点/井号的词元 → 在归一化文本上做**短语**匹配。回归测试 `test_keyword_matching_no_substring` 盯着（连 `ui` / `image` / `data` / `migration` 四个历史误命中都写进了断言）。

### 6.3 MATCH_RULE 语义引擎（v2.2 新增）

v2.1 用扁平关键词表，导致「出现平台词 = 能力已满足」的假阳性。v2.2 换成结构化规则：

```python
CAP_RULE["mobile_qa"] = dict(
    all_groups=[["mobile", "android", "ios", "appium", "device farm"],   # 组间 AND
                ["qa", "test", "verification", "build", "emulator"]],    # 组内 OR
    any_of=[...], none_of=[...], context_terms=[...])
```

- `all_groups`：**组间 AND、组内 OR** —— 必须同时具备「移动平台证据」与「QA/设备/构建验证证据」才算。
- `any_of` / `none_of` / `context_terms`：白名单、否决项、语境限定。
- 配套拆出 `mobile_dev` / `expo_rn_dev` 等**独立能力**，让「React Native 开发」不再冒充「移动 QA」。

同轮收紧的还有 `supabase_db`（必须真出现 Supabase/RLS 语境，普通 PostgreSQL → `postgres_db`）、
`android`、`desktop_app`、`deploy`、`python_auto`、`llm_api`、`photo_mgmt`、`voice_input`。

**（v2.3 §二/§七）又一轮收紧——四条规则的真实误判**。v2.2 上线后实际抽查发现仍有假阳性：

| 规则 | 误判实例 | 根因 | v2.3 处置 |
|---|---|---|---|
| `llm-api` | `google-ads-api-mcp-setup`、`google-mobile-ads-validate` 命中 llm-api | 「API + Gemini」被当成大模型接入；Google Mobile Ads SDK ≠ LLM API | 改为「LLM/model/provider 语境 **AND** api/sdk/tool calling/structured output/streaming 等动作」+ `none_of`（google ads / mobile ads / admob / advertising / ad rank / prompt injection） |
| `deploy` | `react-best-practices`（仅因来自 Vercel）、`bats-testing-patterns`（仅因 CI/CD）命中 deploy | 工具品牌与流水线词被当成部署能力 | `any_of` 只留**真部署动词**（deploy / deployment / release pipeline / 部署上线…）；vercel / netlify / ci-cd 全部降为 `context_terms`（v2.4 又把裸 `hosting` 移入 `any_groups`，见 §6.3.2）|
| `voice-input` | `github-issue-creator` 命中 voice-input | 「可接受 voice dictation 作为输入材料」≠ 提供语音输入能力 | `any_of` 去掉裸 `dictation` / `transcription`；新增 `none_of`（voice dictation as input / accepts voice dictation / as input material / as raw material / tts only） |
| `supabase-db` | `powerbi-modeling` 命中 supabase-db | 裸 `RLS` 不足——**Power BI 也有 row-level security** | `all_groups` 收紧为**必须出现 `supabase`**，RLS 不再单独成立 |

反向保护同样进了回归测试：真 OpenAI/DashScope 接入仍命中 `llm-api`、真 Supabase 迁移仍命中
`supabase-db`、真语音输入仍命中 `voice-input`——**不能靠把规则收死来通过测试**。

### 6.3.1 项目匹配的技术栈词表同步收紧

`TECH_MATCH["macOS 桌面"]` 原先含裸词 `macos`，导致「在 Windows / Linux / macOS 上都支持」
这类**平台支持声明**被当成 macOS 技术栈命中。现在只认真技术栈词
（`appkit` / `cocoa` / `swiftui` / `swift` / `menubar` / `menu bar app` / `macos app` /
`macos application` / `菜单栏应用`）。

### 6.3.2 v2.4：否定窗口、deploy 二次收紧、testing_qa 主能力证据

v2.3 之后仍有一类问题：**规则形式上有证据，但真实语义是假相关**。

**(a) 通用否定窗口（§五）** —— `azure-resource-manager-playwright-dotnet` 明写
`NOT for running Playwright tests`，却因出现 Playwright 被判 `browser-qa`。现在：

- 按小句切分（句点**后必须跟空白/行尾**才算分句，否则会切碎 `next.js` / `.net` / `node.js`；
  逗号的语义在 v2.5 §二 被重新定义：不再直接分句，而是**段内传播否定**，见 6.3.3），
  丢弃含否定标记的小句
  （`not` / `never` / `don't` / `does not` / `avoid` / `without` / `not intended` /
  `非用于` / `不用于` / `不支持` / `不适用` / `禁止` / `不要` / `不可`…）；
- 判定只在**正向视图**里做（`hit_pos`）；**Skill 名不受描述里的否定影响**；
- 被压制且原本会命中的关键词计入 `negated_evidence_rejected`（可审计）；
- 这是**通用函数**，不是给 Playwright 打的补丁——对任何关键词、任何管理面 SDK 都成立。

**(b) `deploy` 继续收紧（§六）** —— `azure-microsoft-playwright-testing-ts` 写的是
`cloud-hosted browsers` 与 CI/CD 集成，也被判 deploy（这不是「部署用户项目」）：

- 删掉正向 `any_of` 里的裸 `hosted`；
- `hosting / hosted / publish / publishing` 必须与**部署对象**
  （app / application / site / service / pages / build / artifact / production / environment…）
  同现才成立（`any_groups`）；
- CI/CD 只作 context，不是正向动作。

**(c) `Docker` 词典删掉裸 `container`（§三）** —— `container queries` 被当成 Docker，
导致 `responsive-design` 匹配 3 个 Docker 项目。现在只认容器化语境词
（docker / dockerfile / docker compose / containerization / container image /
container runtime / docker container / 容器化）。

**(d) 词面 stop list 大幅扩展（§四）** —— Azure Resource Manager Skill 与 `prompt-manager`
只共有 `manager` 就成立。现在 `manager` / `management` / `resource` / `service(s)` /
`application(s)` / `system(s)` / `development` / `developer` / `testing` / `test(s)` / `data` /
`model(s)` / `client` / `server` / `api(s)`… 全部进 `_LEXICAL_STOP`，并要求「≥2 个高区分度词」
或「1 个项目域高信号词」才成立。

**(e) `testing_qa` 改「主能力证据」（§七/§八）** —— `ai-prompt-engineering-safety-review`
只是提到 `testing methodologies`、`ai-team-orchestration` 只是 `optional QA`，却都拿到
testing_qa 与 weak gap 的 15 分加成。现在二选一：**A.** Skill 名含
`test/tests/testing/qa/e2e/playwright/pytest/vitest/jest/cypress/spec/selenium`；
**B.** 描述把测试当核心任务（`run tests` / `write tests` / `test application` / `QA workflow` /
`acceptance testing` / `regression testing` / `validate behavior` / `test suite` / `e2e tests` /
`browser testing`…）。`testing methodologies` / `optional QA` / `may be tested` /
`QA is optional` / `examples include testing` 只算**提及**。

**(f) 两个「规则看起来对、实际不生效」的缺陷（排查中一并修掉）**

| 缺陷 | 后果 | 处置 |
|---|---|---|
| 中文关键词命中率恒为 0 | `_WORD_RE` 是纯 ASCII，中文没有词边界 → 规则表里 **48 个 NEED_RULE + 27 个 CAP_RULE 中文关键词**、加上 `TECH_MATCH` 的 `容器化` / `菜单栏应用`，**全是永不命中的死词** | 含 CJK 的关键词改走子串匹配；回归测试对规则表做**全量自检**，同时保留英文整词匹配（`ui` 命中 build 的老事故不许回归）|
| 分句不含逗号 → 否定窗口过度压制 | 「非用于 A，可用于 B」整句被丢弃，把逗号后的**正向证据**一起误杀 | 逗号纳入分句边界，否定只作用于本小句；修掉后 `negated_evidence_rejected` 由 **94 降到 30** |

### 6.3.3 v2.5：冻结前最后语义收口

同一类问题（「形式上有证据、真实语义仍是假相关」）的最后一层：

**(a) `android` 需求要真 QA 证据（§一）** —— 平台证据 AND（A 表：qa/e2e/adb/emulator/
real device/appium/detox/maestro/espresso/xctest/真机… **或** B 表：signing/keystore/
apk/aab/build verification/签名/构建验收…）；裸 device / build / install / launch 禁作
正向证据；`test ads`（广告测试位）由 `_AD_TEST_RE` 压制。

**(b) 否定窗口两段式（§二）** —— 大句只按 句号/分号/换行/句读 切；**逗号在段内传播
否定状态**（`Don't use for A, B, or C.` 的 B/C 保持否定），遇
`but / however / instead / whereas / use for / 但是 / 但 / 可用于 / 适用于`… 才恢复正向。

**(c) 词面证据重构（§三/§四/§五）** —— 泛用技术词全禁（`_LEXICAL_TECH_BAN`）、
裸 `prompt` 出局；词级重叠只作**次要加分**（须与主证据同现）；独立成立只认人工整理的
`_PROJECT_DOMAIN_PHRASES` 领域短语；两个**恒 0 哨兵**计数（`bare_prompt_direct_evidence` /
`tech_words_used_as_lexical_direct_evidence`）+ `lexical_alone_rejected` 可审计。

**(d) 能力核心化（§六/§七/§八）** —— `mcp_dev` 要开发动词或名称身份；PPTX 单列
`pptx_processing` 不冒充 `docx_xlsx`；`github-auto` = GitHub 平台词 AND 运维语义词。

**(e) 统一证据语境（§九）** —— `capability_evidence_context` 四态
（primary / supporting / mention / negated）：只有 primary 拿满缺口分，supporting ≤8，
mention/negated ≤2；需求侧 supporting 权重 ×0.5。以后新增误报按四态归类修，
**不再手写候选黑名单**。

### 6.3.4 v2.6：身份血缘 + 产品 scope + 五处语义收口（冻结前完整性修正）

**(a) 身份按血缘不按同名（§二/§三/§十一）** —— `installed_relationship` 的同名分支
不再直接返回 `already_installed`：必须过 `lineage_confirmed` 五条件之一
（① normalized upstream 一致；② 候选 owner/repo 与已装 `upstream` 字段明确一致；
③ 内容 fingerprint 可证（两侧有记录时）；④ Source Map 已把该 external repo 记为上游/内容同源；
⑤ 显式 `LINEAGE_ALIASES` 表且带证据摘录）。证明不了 → `same_name_unverified`
（已装侧 upstream=unknown）或 `same_name_different_source`（上游记录明确不同）：
不标已装、不建立 update/replacement 关联、`recommend_of` 最高 watch、NOVELTY=0、
CAPABILITY_GAP 封顶 5——**等待人工确认，不是拉黑**。
`update_available` 只对血缘成立的 already_installed 生效，并输出
`update_lineage`（installed_canonical_id / installed_upstream / update_upstream /
lineage_evidence / lineage_verified）；`EXTERNAL_SKILLS_CONTEXT.md` 的 `UPDATE_LINEAGE`
块由 Installed Source Map 驱动（`build_update_lineage`，日报与对照件共用），
候选池无同血缘候选时更新来源直接取 Source Map 的 upstream 证据。
`replacement_candidate` 的 known_missing 同名查找同样必须过血缘门（§十一 清扫）。

**(b) GCP 产品别名与产品 scope（§四/§十）** —— `MISMATCH_KW/MISMATCH_DOMAIN` 补
cloud run / agent platform / model garden / vertex ai / vertex / cloud build /
cloud functions / firestore / gke / google kubernetes engine / cloud sql / alloydb /
cloud monitoring / cloud logging → 全部 `gcp`；**裸 `Gemini` 不算 GCP**。
新增 `microsoft store` / `msstore` → `microsoft-store` 域（Windows 设备 ≠ Store 发布需求）。
`product_scope()` 三态：`generic / platform_operation / product_internal` +
`target_product`；product_internal 以「候选来源仓库即产品仓 + 自研动词句式」判定
（BrowserOS test-ui 事故；「在 Supabase 上做应用」不误伤）；解除 = 项目档案真的在用/开发该产品。

**(c) 跨 Skill 重定向窗口（§五）** —— `For X, use/see Y` · `use Y instead` ·
`handled/covered by Y` · `如果是X请改用Y` 等句子里的 X 是**排除当前 Skill** 的 scope，
不得作正向证据；目标 Y 必须是「另一个 Skill」形态（连字符 slug 或 `the X skill`，
`use this skill` / `Use when …` 自身指引不受影响）。与否定窗口并列：
`_ctx` 先剪重定向（原始句界还在）再剪否定；计数 `redirect_evidence_rejected` 可审计。
连带修两处：`fm_description` 300→600（截断会把重定向句切一半，规则形同虚设）；
`match_projects` ①② 两路从原始文本改到**正向视图**判定；TECH Android 去掉裸 `emulator`
（iOS 的 "emulator pane" 不是 Android 证据），`_QA_OR_DEVICE` 补 `simulator`。

**(d) mcp_usage 与 mcp_dev 分离（§六）** —— 开发动词的**宾语必须真的是 MCP 工件**
（server/client/tool/integration/protocol/sdk，`_MCP_ARTIFACT_RE` + 60 字符窗口内
`_MCP_DEV_VERB_RE`，且工件紧贴 `using/via/through` 视为使用）。
「using MCP tools」→ 独立标签 `mcp_usage`（记录不算开发）；`_rule_mcp_dev` **只认 primary**。

**(e) frontend_design / image_creative / deploy / testing_qa 收口（§七/§八/§九）** ——
frontend_design（CAP+NEED 同步）删裸 frontend/front-end/ux/css/tailwind/shadcn/visual design，
只认明确设计语义；image_creative 扩充（generate images / artwork / poster / sprite /
texture / visual asset / 海报 / 插画 / 图标生成 / 视觉素材…）；
DEPLOY_RULE 的 any_of 移除裸 `deployment`，primary = 动词+对象 / *pipeline / rollout /
deploy to X / provision deployment / 部署应用·发布站点·上线服务，裸名词只能 mention；
`_TESTING_NAME_TOKENS` 删裸 spec/specs（补 rspec；phrase 表加 test spec / test
specification / executable specification）。**§五 已知副作用**：描述窗口 300→600 让
`react-view-transitions → yejian-buguangdeng` 以 `strong_tech: Next.js` 重新成立
（项目技术栈确含 Next.js，属 §十四 保留的合法强证据）；v2.5 禁的 **lexical 依据**
仍由恒 0 哨兵与按依据类型断言把关。

### 6.3.5 v2.7：一致性与 Top 精度修复（冻结前最后一轮）

**(a) 确定性硬门（§二/§十一）** —— `_ctx` 同时保存 `raw_name` / `name_norm`（有序）/
`name_words_set`；一切名称短语判定（MCP 名称断言、pnorm 追加名、Skill 名词面）读
`name_norm`，**禁止 `" ".join(set)`**。根因实测：set 词序随 PYTHONHASHSEED 变化 →
`php-mcp-server-generator` 的 `mcp server` 短语在部分 seed 下被打散，mcp_dev/mcp_usage
分类翻转（审查环境 50/1/1 vs 本机 52/52 的真凶）。硬门
`test_v27_determinism_hashseed` 用子进程跑 seed 0/1/2/3/42/123 矩阵，
输出必须逐字节一致，漂移即 FAIL。

**(b) Question Answering ≠ Quality Assurance（§三）** —— 名称证据只有裸 `qa` 时必须
描述带真实质保语义（`_QA_REAL_TERMS`）；`_QA_NEG_PHRASES`（answers questions / q&a /
knowledge qa / 问答…）在无其他测试身份时一票否决；新增独立记录位 `question_answering`
（不吃 testing_qa 缺口分）。反向保护 place-journal-qa（真验收描述）/ webapp-testing。

**(c) deploy 邻近语义（§四）** —— `_DEPLOY_PROX_RE`：部署动词（deploy/publish/host/roll out）
与**通用部署对象**（app/site/service/function/container/workload/artifact/pages/production…）
必须同句 ≤50 字符邻近；rules/policies/prompts/detections/configs/dashboards/alerts/
games/content/documentation 不是通用对象。`publishing games`、`deploy YARA-L rules to SecOps`
出局；`deploy-to-vercel`、`python-appservice-deploy`、「Deploy the app to production」保住。
`_cls_deploy`：命中=primary；裸 `deployment` 名词=mention；否定作用域=negated；
被压制命中仍计入 `negated_evidence_rejected`（审计口径不回退）。

**(d) 跨域歧义守卫（§五）** —— `_AMBIGUOUS_DOMAIN_TERMS`（breakout/native/model/agent/
manager/dashboard/channel/store/platform/stream/shell/library/network）：**单词形态不得
独立成为 lexical 项目证据**；`_PROJECT_DOMAIN_PHRASES` 的 breakout 改为 trading/price/
market breakout、breakout radar/signal、backtest、量化交易等。game-engine（打砖块）
不再匹配行情项目；交易语境的合成候选仍可匹配（反向保护）。

**(e) React Native ≠ 原生（§六）** —— `_rn_masked()`：TECH_MATCH ① 判定前先把
`react native / react-native / nativewind` 从正向视图**占位遮蔽**，
`React Native apps` 不再拆出 `native app` 去匹配 macOS 原生项目；
Swift/AppKit/menubar 真原生描述照旧成立。

**(f) 产品专项门 + secret 收紧（§七/§八）** —— `_PRODUCT_OPERATION_TERMS`
（google-analytics / google-secops / anthropic-brand / microsoft-store / shopify /
salesforce / servicenow / databricks / snowflake）→ `platform_operation + target_product`；
`scope_unresolved()` 统一解除判定（项目档案提到该产品即解除，非 blacklist），
未解除 → 最高 watch + 第五道 Top 门。`secret-safety` = 安全对象 AND 安全动作
（rotate/scan/redact/vault/keychain/密钥管理/防泄露…）——「Measurement Protocol secrets」
这类产品资源字眼出局；secret-scanning / secrets-management 保住。

**(g) 扫描预算诚实化（§一「50/1/1 不一致」的第二个根因）** —— `scan_budget` 600 → **1200
覆盖全池**（实测 1,075 次抓取）：旧预算按 preliminary 排序分配，语义一变，落选候选的
description 为空 → 分类失真且不可复现。代价如实记录：verdict unscanned 506 → 31，
block 5 → 9（新抓出的真 `curl | bash` 安装脚本，fail-closed 方向）。

### 6.3.6 v2.8：产品范围与核心需求证据最终收口（冻结前）

**(a) 五个需求全面四态化（§二/§五/§六/§七/§八）** —— `EVIDENCE_CLASSIFIERS` 扩到 10 键：
`expo-rn`（核心 RN/Expo 开发才 primary；「SDK supports React Native / plugin / works with
Expo」= supporting，`expo_rn_dev` 标签同步只认 primary）、`python-auto`（本地/工作流/批处理/
文件/数据自动化才 primary；产品自带 CLI/SDK 的 automation 字眼 = supporting）、
`llm-api`（调用/集成动作或名称即 `<provider> api/sdk` 才 primary；
「serving container / model deployment / image URI」→ supporting 并改挂信息标签
`model_serving`；ML 实验看板类改挂 `ml_experiment_tracking`）、`browser-qa`
（测试动作 AND 浏览器对象才 primary；单独提到 Playwright/CDP = mention；管理面排除保持）、
`dashboard-viz`（generic 看板/可视化才 primary；`_dashboard_domain_only` 判定所有 dashboard
出现点都被 ML/训练/监控/安全等领域词限定 → supporting）。信息标签不在
CAPABILITY_SUPPRESSION 表内 → 天然不吃缺口分。

**(b) Top 核心证据门（§十四）** —— `build_context.core_evidence_ok()`：无 primary 级需求、
无 matched_project、无 primary 证据的 gap、无 update/replacement → 不进 Top。
`shared_need` 与「看板」定位证据同步只认 primary 级。审计行：
`top_candidates_supporting_only`（必须为 0）+ `core_evidence_blocked_from_top`（被挡数，仍可查 WATCHLIST）。

**(c) 平台 scope 证据层（§三/§四/§十）** —— `_PRODUCT_OPERATION_TERMS` 补
azure-application-insights / microsoft-365-copilot / huggingface-spaces；AWS 服务别名入
mismatch 词典（sagemaker / amazon sagemaker / cloudwatch / aws lambda / s3 / amazon s3 /
ecs / eks / fargate / bedrock / amazon bedrock → aws；**裸 lambda 不收录**）；
识别只按 skill_name / description / repo（owner 一刀切被明令禁止——
Microsoft 仓的 frontend-design-review 照旧正常）。每条候选输出
`platform_scope_evidence{scope_type, target_product, evidence[], confidence}`，
名称/仓库可独立指认产品 = high，仅描述命中 = medium。§十 的「可解除」全部进测试
（Application Insights / M365 Copilot / HF Spaces / SageMaker 四种喂法）。

**(d) deploy 的 host 名词修正（§九）** —— 「cloud sandbox, VM, **SSH host**, or local
container」里的 host 是**主机**；host 系动词从通用邻近表拆出，只认
`host(s|ing) + an/the/your + app|site|service|model` 严格式，且同文本出现
ssh/remote/local/docker/… host 名词搭配时不再参与。orca-per-workspace-env 的假 deploy 消失；
「We host an app and a static site」照常命中。

### 6.3.7 v2.10：冻结前 Top 语义与能力饱和收口（审查文档《v2.9 …Top 语义与能力饱和收口》）

> 树内编号说明：v2.9 已被「产品关系与领域三态」轮占用（其口径完整记录在
> `CANDIDATES_DIGEST.md` §5.0.1–5.0.5），本审查文档轮在库内编号 **v2.10**，两轮规则同时生效。

**(a) browser-qa 测试目标门 + 页面捕获独立标签（§二/§十）** —— primary 必须同时满足
「浏览器/Web 测试对象 + 测试动作 + **测试目标**（behavior / functionality / interaction /
acceptance / e2e / regression / DOM/UI state / navigation / forms / user flow，或登记测试工件
短语）」；`QA workflow / screenshot for QA / theme testing / design review / accessibility
audit` 最多 supporting。新增信息标签 `browser_capture`（screenshot / full-page capture /
webpage PDF / website thumbnail）与 `accessibility_audit`；`image_creative` 改为 custom：
纯页面捕获（website thumbnail / screenshot）不再冒充「创作图像」。latchshot-page-capture
browser-qa=supporting、image_creative 消失、按 browser_automation 族记 strong 饱和 → 离开 Top；
webapp-testing（verify functionality + UI behavior）与 e2e-testing-patterns 反向保护保持。

**(b) spec-driven 改为开发过程语义（§三）** —— `_cls_spec_driven` 四态：primary 只认
「产出/维护开发规格」（write/create+spec、feature/product/requirements specification、
requirements document、PRD、design doc、RFC、implementation plan、task breakdown、
acceptance criteria、constitution、SPEC/PLAN/TASK、SDD/Spec Kit、需求规格/任务拆解/验收标准…）
与真 SDD 流程；`following / compliant with the X specification`（llms.txt / protocol /
file format / API / CSS）= supporting。新增信息标签 `llm_documentation`。
wiki-llms-txt spec-driven=false；gen-specs-as-issues（create detailed specifications）保住。

**(c) capability_saturation + 增量价值 + 家族配额（§四~§七）** —— 每条候选输出
`capability_saturation ∈ {none, weak, medium, strong, strong_degraded}`（saturation 族按
matched_gap；只有信息标签时经 `TAG_FAMILY` 归族——名字不同不等于 new_capability）。
strong 默认 watchlist，进 Top 必须有 CLEAR_INCREMENTAL_VALUE：update_available /
replacement_candidate / availability degraded / `incremental_subcapability`（数据驱动：
子能力词形在候选正向文本、且在该族任何已装 Skill 文本中不出现）/ 未覆盖的项目专用技术
强命中。**不是硬黑名单**，条件满足即恢复。`capability_family_quota`：strong 族 Top 最多
1 条代表项（超额必须各带未用过的增量子能力），medium=2、weak/none=3。结果：
frontend_design（已装 strong）族 Top 从 7 条降到 **1** 条（frontend-design-review，
依据 accessibility_audit 已装侧未覆盖）。

**(d) required_tech / compatible_tech 项目兼容门（§八/§九）** —— 候选级提取**硬依赖**
技术栈（`Build … React applications`、`using Tailwind CSS`、React Native、Expo Router、
Next.js、Jetpack Compose、SwiftUI、AppKit…；「SDK supports X」只算 optional，走四态）。
项目兼容按映射而非机械相等：CSS/HTML/响应式标准 ↔ 单文件 HTML/PWA 项目**兼容**；
Tailwind 需 Tailwind、React 需 React/Next.js、Expo/RN 需 Expo/RN。不兼容时
`shared_need` 单独不得生成 matched_project（general_need_match 保留，project_match=[]）。
frontend-ui-dark-ts（react/tailwind/framer-motion）不再匹配 family-insurance-dashboard；
responsive CSS ↔ 单文件 HTML、React Native ↔ Expo 项目匹配保持；
`required_tech_blocked_shared_need=5`。

**(e) personalized_reason + Top Gate 十步顺序（§十二/§十四）** —— 每条 Top 写回
`personalized_reason{fills_gap, matched_project, incremental_over_installed, why_now}`，
strong 饱和候选 `incremental_over_installed` 必须非空
（`top_strong_without_incremental_reason=0`）。`select_top` 固定按
「1 Security → 2 validity/lineage → 3 产品/领域 scope → 4 primary 证据 →
5 required-tech 兼容（match_projects 层）→ 6 能力饱和 → 7 已装重复/增量 →
8 分数阈值 → 9 功能族折叠 → 10 能力族配额」判定，不再先按分数再解释不相关。
本轮基线：数据 version 9 → **10**（scoring.json 维持 v2.9 轮的 version 5，**权重仍未动**）；测试 79 → **85**；
池 1,106；**Top 19/30**；install 9 / watch 239 / ignore 849 / reject 9；
`saturation_blocked_from_top=31`、`core_evidence_blocked_from_top=108`、
`top_candidates_supporting_only=0`、known_fp（四案）=0。

### 6.3.8 v2.11：冻结前数据合同与语义一致性收口

**(a) security_audit 四态（§二）** —— 新 `_cls_security_audit`：primary=核心任务执行安全审计
（security audit / vulnerability assessment·scanning / threat modeling / OWASP / SAST·DAST /
penetration testing / secure code review / secret·security·dependency scanning / supply chain
security / 漏洞扫描 / 安全审计 / 威胁建模）；出现在「such as / for example / optional /
preset / workflow」示例槽位里的安全词（team-composition 事故："custom team composition for a
non-standard workflow such as a migration or **security audit**"）= supporting；
只提 security/audit = mention。CAP_RULE 同步只认 primary，登记进 `EVIDENCE_CLASSIFIERS`。
secret-scanning / dependabot（核心任务即安全更新与供应链安全）保持 primary 反向保护进测试。

**(b) spec-driven 语境门（§三）** —— `task breakdown / implementation plan / 任务拆解 / 开发计划 /
实施计划` 降级为**弱规划词**：只有同文存在开发规格语境（spec / requirements / PRD / product /
feature / constitution / 需求…或任一强短语）才计入 primary；
「test task breakdown / QA task breakdown / migration task breakdown」（breakdown-test 事故）
= supporting。breakdown-test 改为纯 testing_qa 证据；`feature specification + task breakdown`、
`requirements → implementation plan` 保持 primary。

**(c) PROJECT_CONTEXT_CONFLICT（§四/§五）** —— `detect_project_conflict()`：描述声明技术 A、
tech 列**缺 A** 却出现互斥组对侧 B（Expo/RN ↔ Next.js/PWA）→ conflict +
`suppressed_strong_tech`；match_projects 里冲突侧 strong_tech **本来会命中才计抑制量**，
命中即跳过；非冲突证据（一致的 strong_tech、shared_need、positioning、lexical）全部保留。
输入 A 一字不改，结果落 `project_context_health{conflict_count, conflicts[]}` +
日报 `PROJECT_CONTEXT_HEALTH` 机器块，供上游 Project Profile 修数据。
yejian-buguangdeng（描述 Expo+RN、列表 Next.js/PWA）冲突检出；
stretch-side-timer（描述与列表都含 Expo/RN）**不判**——没有真相源就不猜。

**(d) NEED_PROJECT_COMPATIBILITY（§六）** —— 每个 primary matched_need 记
`{evidence_level, compatible_projects, incompatible_projects, need_project_compatibility}`；
承载该需求的项目**全部**与候选 required_tech 不兼容 → level=none →
`core_evidence_ok()` 不再认它为主证据（§六：「需求名匹配」不能脱离「需求对应项目能不能用」）。
frontend-ui-dark-ts（React+Tailwind+Framer Motion）的 dashboard-viz 唯一承载项目
family-insurance-dashboard 不兼容 → 退出 Top；测试合成一个 React/Tailwind dashboard 项目，
兼容恢复、need 重新可用（§十 回归 10）。

**(e) 机器合同拆分（§七/§八）** —— `product_internal_remaining_count`（值取全池、注释写
「Top 与队列必须为 0」）这类名/值/注释互相矛盾的字段**废弃**，拆成四字段：
`product_internal_unresolved_pool_count`（允许 >0，留池等待解除）/
`product_internal_in_full_scan_count`（=0 硬门；未解除 product_internal 从此不入深度审查队列）/
`product_internal_in_top_count`（=0，由 build_context 这个 Top 唯一出口现算回写）/
`internal_capability_in_full_scan_count`（=0）。哨兵 `CONTRADICTORY_AUDIT_FIELDS=0`。

**(f) Delta 反冒充（§九/§十）** —— UPDATED 严格化：version 两侧非空且不同、或 commit 两侧非空
且 new>old 才算上游更新；null→值、unknown→active 一律 METADATA_ENRICHED；回退 commit 不配
UPDATED。快照改带信封 `{snapshot_schema_version:2, analysis_engine_version:数据版本,
generated, candidates}`，任一变化 → **SYSTEM_REBASELINE**（本轮重建基线、changed_total 记 0，
绝不产出数百条假 UPDATED——上一版 `UPDATED: 849` 就是引擎换代被误读成上游风暴）。
score/recommendation/gap 变化只产生 MATCH_CHANGED / RISING / FALLING。

**(g) action_type 与恢复分栏（§十二）** —— 每候选 `action_type ∈ {new_install, watch,
restore_candidate, update_candidate, replacement_candidate, reject}`：known_missing
（来源档案在案、本机 canonical 缺失）+ 血缘确认 → restore_candidate（computer-use 实证），
血缘未确认也**绝不允许**伪装 new_install（`overlap_known_missing` 落档，
`known_missing_misreported_as_new_install=0` 哨兵）；outdated+血缘 → update_candidate。
日报新增机器块 `ACTION_TYPES` 与正文 `## 1B. 恢复 / 修复` 独立小节。

**(h) 增量证据分级（§十三）** —— `incremental_subcapability` 返回 `[(sub, level)]`，
`incremental_evidence_level ∈ {confirmed_absent, summary_not_found, unknown}`：
只有**实际读取**该族全部已装成员完整 SKILL.md（只读）且均未提及才 confirmed_absent
（frontend-design-review 的 accessibility_audit 实证）；仅摘要未发现 = summary_not_found
（可 watch、可撑 Top 名额，但**不得仅此成为安装候选**——recommend 层显式拒绝）；
缺输入 B = unknown（不作解除依据）。措辞从「已装 Skill 明确没有」改为诚实的
「底座摘要未发现 / 全文已核验」。

本轮基线：数据 version 10 → **11**（scoring.json 仍 5，权重未动）；测试 85 → **90**；
池 1,106；**Top 16/30**；install 9 / watch 238 / ignore 850 / reject 9；
`DAILY_DELTA.UPDATED=0`（原 849 假风暴消失）；`product_internal: pool 30 / queue 0 / top 0`；
`conflict_strong_tech_suppressed=8`（yejian 等）；known_fp（v2.11 组）=0。

### 6.4 Top 候选：宁少不凑（v2.4 第四道门 + v2.6 第五道门 + v2.8 核心证据门 + v2.10 饱和/配额门 + v2.11 需求-项目兼容门）

`PERSONALIZED_TOP30` 的定义是「值得用户看的 Personalized Top candidates」：

- **只允许 `install_candidate` / `watch`**，禁止 `ignore` / `reject`；
- 十道门（v2.3 三道 + v2.4 `require_no_mismatch` + v2.6 `require_no_unresolved_scope` +
  v2.8 `require_core_evidence` + **v2.10 §十四：固定顺序 = Security → validity/lineage →
  产品/领域 scope → primary 核心需求证据 → required-tech 兼容（match_projects 层）→
  能力饱和 → 已装重复/增量价值 → 分数阈值 → 功能族折叠 → 能力族配额**
  （`capability_family_quota`：strong=1 / medium=2 / weak·none=3；可解除、非黑名单））；
- 排序键：`需要证据 → 有具体项目 → 无平台错配 → install_candidate → 分数`（字典序）；
- 多样性：同仓库最多 3 条 + 同仓库内**同族折叠**
  （词元最长公共前缀 ≥3，或短词元是长词元的完整前缀且短者 ≥2 词。
  例：`google-mobile-ads-get-started` / `-interstitial` 折叠；`orca-emulator` vs `orca-emulator-android` 折叠）；
- **符合标准的不足 30 个就输出实际数量**（`target_limit` / `actual_count` 两个字段如实记录），
  不为凑数字塞垃圾。否则 `google/skills` 一家就能用 6 个 Mobile Ads 变体占掉 1/5 个 Top。

**（v2.3 §五）新增三道质量门**——v2.2 的 Top 里混进过
`SkillsMP business-and-financial-operations-occupations`（score 约 31），只因为它是个 watch：

| # | 质量门 | 判定 |
|---|---|---|
| ① | `score ≥ min_score` | 配置化阈值（`config/scoring.json` → `top_candidates.min_score = 55`） |
| ② | **有真实个性化证据** | `matched need` / `capability gap` / `update` / `replacement` **至少一项成立**（`has_personalized_evidence`） |
| ③ | T3 需交叉佐证 | `discovery_only` / T3 来源若无 T1·T2·官方来源佐证 → **不进 Top，只留 WATCHLIST**（`is_t3_uncorroborated`） |
| ④ | **无未解除的平台错配**（v2.4 §九） | `domain_mismatch` 且**项目档案里没有任何项目使用该平台** → 不进 Personalized Top，只留 WATCHLIST（`unresolved_mismatch`） |

**（v2.4 §九）第四道门 + 总分 penalty。** v2.3 把 `domain_mismatch = azure / dotnet / aws`
**只记录**了下来，却仍让 Azure Playwright Testing、Azure Resource Manager Playwright .NET、
SageMaker deployment planner 占高位 Top。现在：

- 未解除错配 → **不得 `install_candidate`**、**不得进 Personalized Top**、总分再乘
  `DOMAIN_MISMATCH_PENALTY = 0.7`（系数记在 `domain_mismatch_penalty`，可审计）；
- **解除条件 = 用户真实项目明确使用该平台**（项目档案 name / desc / tech 里出现
  Azure / AWS / GCP / .NET / Java / Dynamics…）→ `domain_mismatch_resolved` 非空，
  penalty 自动消失、正常参与排序；
- 看的是**整个项目档案的技术面**，不是「该候选恰好匹配到的项目」——否则一个 Azure 候选
  只要没有别的直接证据匹配不上项目，就永远无法解除，变成事实上的永久 blacklist，
  而 §九 明确要求「**不要永久 blacklist**，只是『当前没有证据使用该技术栈 → 不该占个人 Top』」。

> `gap_level` 语义提醒：它是**已装侧对该能力的压制强度**（`none`/`weak` = **真有缺口** →
> 合法证据；`medium`/`strong` = 已覆盖或无缺口证据）。写测试断言时别搞反。

**（v2.3 §三/§八）跨仓 FUNCTIONAL_CLUSTER 折叠**。v2.2 只在**同仓库内**折叠，于是
`github/awesome-copilot/webapp-testing` 与 `anthropics/skills/webapp-testing`
同时占了 Top1 / Top2 —— 对用户来说这就是两个几乎一样的 Skill 连着推荐两次。

现在：

- 候选池仍按 `owner/repo/skill` **各自独立记账**（不合并、不丢数据）；
- 但 **Top 展示层**做跨仓折叠：同一个功能族只出 **PRIMARY**，其余进 **ALTERNATIVES**；
- 同族判定（满足其一）：`normalized skill name` 相同且 ≥5 字符 / `description` jaccard ≥ 0.62
  且名称同前缀 / `content_fingerprint` 相同；
- PRIMARY 的选取综合考虑 source trust / security / maintenance / 项目匹配 /
  upstream lineage / 内容完整度（**不是只看分数**）；
- 兄弟条目**即使是被同仓库上限先拦下的，也会登记进 ALTERNATIVES**——不得无声消失。

实测本轮：`functional_duplicates = 1`，PRIMARY = `anthropics/skills/webapp-testing`，
ALTERNATIVES = `github/awesome-copilot/webapp-testing`（score 85，因 awesome-copilot 已有 3 席被挡）。

---

## 七、Context 文件（日报读取）

`EXTERNAL_SKILLS_CONTEXT.md` 机器可读区固定 **12 节**（v2.6 新增 `UPDATE_LINEAGE`）：

`SOURCE_HEALTH` / `CANDIDATE_POOL_SUMMARY` / `NEW_DISCOVERIES` / `HIGH_MATCH_CANDIDATES` /
`CAPABILITY_GAP_CANDIDATES` / `TRENDING_RELEVANT` / `UPDATE_CANDIDATES` / **`UPDATE_LINEAGE`（v2.6 §三）** /
`SECURITY_REJECTED` / `WATCHLIST` / `PERSONALIZED_TOP30` / `DAILY_DELTA`

正文遵守两条纪律：

1. **每日重点只展示 5-10 个**真正发生变化或值得看的候选，每个回答七问（是什么 / **对哪个具体项目有用（`matched_projects`）** / 我现在有没有类似能力 / 为什么今天值得看 / 来源是谁 / 安全状态（`verdict` + `deep_scan_status`） / 推荐）。
2. **Top 无变化时不重复输出**——日报的职责是回答「今天与昨天相比有什么值得我知道」。

`PERSONALIZED_TOP30` 块自带自证字段：`target_limit` / `actual_count` / **`min_score`** /
`contains_ignore` / `contains_reject` / `high_match_count` / `matched_projects_coverage` /
**`top_candidates_with_unresolved_mismatch`（v2.4 §九，必须为 0）** /
**`mismatch_blocked_from_top`** / **`top_candidates_with_unresolved_product_scope`（v2.6 §十，必须为 0）** /
**`scope_blocked_from_top`** / **`functional_duplicates`** / **`alternative_families`** /
**`t3_uncorroborated`** / `security_verdict_pass|review_required|block` / `deep_scan_*`
——审查者不用翻全量数据就能核验「Top 里没有垃圾、门槛是多少、折叠了几条、覆盖率与安全状态是多少」。

另有独立的 **`PROJECT_MATCH_QUALITY`** 机器块（v2.4 §十），把四类直接证据的条数与
三个「被拒」计数写清楚，取代原先只能证明「字段不为空」的「直接证据率」。

正文 §2 之后另有 **`### 2.1 ALTERNATIVES`** 子表，列出被折叠的同功能族备选
（PRIMARY / 同功能来源 / 折叠依据），对应 §八 的「PRIMARY + ALTERNATIVES」展示模型。

另外两节辅助语义：

- `replacement_candidate`：① 对应 canonical 已知但当前不在安装集（`known_missing`，如 orca 三件套）→ 可用于恢复；② 与已装重叠但已装侧版本落后/上游不活跃，而候选上游活跃 → 具备替换/升级价值。
- `update_available`：已装且 `VERSION_STATUS` 落后但上游仍活跃 → **不重复推荐安装**，只在 `UPDATE_CANDIDATES` 提示更新。
  **v2.6 §三**：更新项由 `UPDATE_LINEAGE`（Installed Source Map 驱动）逐条给
  `installed_canonical_id / installed_upstream / update_upstream / lineage_evidence / lineage_verified`；
  血缘不成立就不建关联，候选池无同血缘候选时更新来源直接取 Source Map 的 upstream 证据。

Delta 支持 9 类：`NEW` / `RISING` / `FALLING` / `UPDATED` / `SECURITY_CHANGED` /
`SOURCE_CHANGED` / `MATCH_CHANGED` / `ALREADY_INSTALLED` / `NO_LONGER_RELEVANT`。
（`SECURITY_CHANGED` 会同时盯 `verdict` 与 `deep_scan_status` 的变化。）

---

## 八、参考实现研究：github/awesome-copilot 的 `agent-skill-stack`

实际读取了它的 `SKILL.md` + `references/discovery-ranking.md`、`local-index-and-profiles.md`、
`security-installation.md`、`workflow-model.md`。**未安装、未替换我们的 Skill Manager、未让它控制双机同步。**

### ✅ ABSORB（已吸收）

| 设计 | 我们怎么落地 |
|---|---|
| canonical identity（owner/repo:path@revision）+ 内容指纹 | 去重主键 `owner/repo/skill`；`content_fingerprint` 记录内容是否变过 |
| 查询族动态生成（direct / operation / supporting / integration + 中英双语） | `GAP_QUERY_FAMILIES` + 缺口派生的 12 个查询族 |
| 硬门先于评分（hard gates → 再打分） | Security Gate 优先于分数：high→reject、unscanned→不得推荐 |
| 置信标签 Confirmed / Promising / Unconfirmed / Blocked | 用 `security.status`(scanned/unscanned) + `risk_level` 表达等价信息，不额外造词 |
| adoption 归一化（避免 monorepo 的 star 被每个小 Skill 重复计入） | ADOPTION_TREND 上限 5 分；star 只记录不排序；TIER 2 不以 star 收录 |
| 「内部技术记录」与「面向用户的大白话」分离 | 机器可读块 vs 正文七问，两层分开 |
| 冲突模型（identity / recall / permission 等） | 用于 `INSTALLED_SKILL_OVERLAP` 的解释与 `replacement_candidate` 判定 |

### 🔁 OVERLAP（与我们已有体系重复，不重复造）

| 它的能力 | 已由我们覆盖 |
|---|---|
| local Skill index / inventory（`scripts/skill_index.py build`） | 已装侧 v4 `INSTALLED_SKILLS_CONTEXT.md` + `SKILL_SOURCE_MAP.json` + CANONICAL_SKILL 模型 |
| project profile | `SKILL_CONTEXT.md`（项目需求真相源，由项目档案自动生成） |
| overlap / 冲突检测 | 已冻结的 `CAPABILITY_SUPPRESSION` + `INSTALLED_SKILL_OVERLAP` |
| 来源与版本记录 | 已冻结的 `SOURCE_SUMMARY` / `UPSTREAM_STATUS` / `UPSTREAM_ACTIVITY` / `VERSION_STATUS` |
| license / 权限边界记录 | SOURCE 分类体系 + 安全 Gate 行为标志 |

### ⛔ REJECT（不适合我们「Skill Manager + 双机同步」架构）

| 它的做法 | 为什么不能引入 |
|---|---|
| staged install / `stage_install.py --apply` 写盘 | **我们只发现不安装。**第三方脚本自行写 `~/.skills-manager/skills/` 会与 Skill Manager 的 re-index「收编」机制打架（`(2)` 别名目录就是这么来的） |
| `skill-stack-lock.json` / manifest / rollback 作为真相源 | 与 Skill Manager 的 SQLite 注册表 + git 备份引擎（双机同步）职责冲突，会形成**双套真相源** |
| `project_profile.py --apply` 写 `.codex/skill-stack.json` | 引入第二套 profile 真相源，与 CANONICAL_SKILL / `SKILL_CONTEXT.md` 冲突 |
| recall check（召回测试） | 需要真实的安装/变更动作，本层没有安装权，不适用 |
| 「一键批量安装」策略 | 与本阶段禁令直接冲突 |
| 依赖 OpenCLI / 浏览器登录态做发现 | 不引入需登录态的抓取通道 |
| 索引根目录按 `~/.codex/*` 组织 | 本机 Agent 根目录是 `~/.skills-manager`、`~/.claude`、`~/.config/opencode`、`~/.workbuddy`，路径模型不同 |

---

## 九、本阶段的禁止事项（硬约束）

- ❌ 自动安装 Skill ❌ 删除 Skill ❌ 升级 Skill
- ❌ 修复 Orca 链接 ❌ 清理 `(2)` alias ❌ 改 Skill Manager 安装结构
- ❌ 修改已冻结的 Installed Skills 三份文件（本层对它们**只读**）
- ❌ 因排行榜高直接推荐 ❌ 把 marketplace 当安全认证 ❌ 因官方来源跳过安全检查

---

## 十、已知限制与待人工决定

1. **skills.sh 用首页 HTML 解析**（官方 API 需 Vercel OIDC 认证）。够用，但页面结构若变更需修解析器；ClawHub / SkillsMP 同理（容错解析，已在输出里标注）。
2. **安全审查是静态启发式**：规则表给出的是「指标」而非判决。v2.2 已大幅降低误伤（区分「提及」与「要求执行」），但 `reject` 名单仍建议人工扫一眼。
3. **TIER 2 白名单目前 3 个**：动态 topic 搜索返回的候选质量太差（多为 0-2 star 垃圾仓），后续发现到可验证的高质量作者再回填。
4. **GitHub API 配额**：匿名 60 次/小时、认证 5000 次/小时。脚本会自动读 `gh auth token`，并把 API 响应在**成功时**落盘缓存 24h，因此同日重跑基本不再消耗配额；**但首次冷跑仍需认证或分时段**。配额耗尽不会静默造假——候选会记为 `deep_scan_status=failed` 并**降级为 watch**（fail-closed），隔时段重跑即恢复。
4b. **扫描预算（v2.7 起）**：`scan_budget` 已从 600 提到 **1200 覆盖全池**——旧值按
   preliminary 排序分配，任何语义改动都会让落选候选**没有 description**，分类与审查随之失真
   （这正是「本机 52/52、审查环境 50/1/1」的两个根因之一）。raw.githubusercontent 不占 API 配额；
   抓取失败仍 fail-closed 记 unscanned，不静默造假。
5. **`matched_projects` 覆盖率 18%（16/90）**：v2.3 §一.4 起**这一项不再是 KPI**。
   剩下的条目属于「需求侧命中、但技术栈/定位与任何在跑项目都对不上」，按设计**不硬凑项目名**。
   完整性仍是硬要求：**每条 `matched_project` 都必须带 `direct_evidence`**（146/146 = 100%，
   但这只是完整性自检，**不再当作精度 KPI** —— v2.4 §十 已换成 `PROJECT_MATCH_QUALITY` 分项计数；
   v2.5 §四 加了 `bare_prompt_direct_evidence` / `tech_words_used_as_lexical_direct_evidence`，
   v2.6 §二/§三/§四 又加 `same_name_only_already_installed` / `wrong_update_lineage` /
   `gcp_alias_missed` —— 共**五个恒为 0 的哨兵计数**）。
   v2.6 条目数回升（122→146）是**描述窗口 300→600** 带来的真实文本证据（含合法的
   strong_tech Next.js 命中），不是放松：词面依据仍由哨兵把住。
6. **Top 可能不足 30 条**：符合「值得看」标准的候选不足时输出实际数量（`actual_count`，
   本期 **16/30**），这是设计而非故障。v2.3 三道质量门、v2.4 第四道（无未解除平台错配，
   本期 mismatch_blocked_from_top 6）、
   v2.6/v2.7 第五道（无未解除产品 scope；本期 scope_blocked_from_top 19）、
   **v2.8 核心证据门（`core_evidence_blocked_from_top` 本期 109 —— supporting/mention-only
   不得撑起个人 Top 位）**、**v2.10 饱和/配额门（`saturation_blocked_from_top` 本期 31，
   strong 无增量不进 Top；可解除、非黑名单）**。Top 更短是正常结果。**宁可少，不要伪个性化。**
8. **`same_name_unverified` / `same_name_different_source` 是「待人工确认」状态**（v2.6 §二）：
   本期 6 条（4 + 2）。它们的最终归属（确为同一 Skill / 确为不同 Skill / fork）
   需要人在 Skill Manager 侧核对来源；体系只保证它们**不会被当成已装、更新源或替换件**。

### 已修（v2.7 关闭的 v2.6 遗留问题）

| v2.6 问题 | v2.7 修法 |
|---|---|
| 分类随 PYTHONHASHSEED 漂移（php-mcp-server-generator 在审查环境翻转为 mcp_usage，50/1/1 ≠ 51+1SKIP） | `_ctx` 存有序 `name_norm`，一切名称短语判定禁止 `" ".join(set)`；hashseed 矩阵（0/1/2/3/42/123）子进程硬门 `test_v27_determinism_hashseed`，漂移即 FAIL |
| wiki-qa（Question Answering）凭名字里的 `qa` 吃 testing_qa 缺口分进 Top | 裸 `qa` 名需真实质保语义；问答语境一票否决；独立记录位 `question_answering`；真 QA 反向保护 |
| game-engine 凭 `publishing + build` **全文任意共现**命中 deploy（Top #2） | deploy 改**动词+通用对象邻近**（≤50 字符同句）；games/content/documentation/rules 不是通用对象；deploy-to-vercel / python-appservice-deploy 保住 |
| detection-engineering「deploy YARA-L rules to SecOps」被当通用部署 | 同上 + §七 产品专项门（google-secops）双保险 |
| game-engine 凭领域短语 `breakout` 匹配行情突破项目 | `_AMBIGUOUS_DOMAIN_TERMS`：跨域高歧义单词不得独立成词面证据；pepe 词条改 trading/price/market breakout、backtest 等 |
| react-native-design 凭「React Native apps ⊃ native app」匹配 macOS 原生项目 | `_rn_masked()` 最长短语优先遮蔽 React Native 再判原生；Swift/AppKit 真原生保住 |
| GA Admin 凭「Measurement Protocol secrets」命中 secret-safety | secret-safety = 安全对象 AND 安全动作；secret-scanning / secrets-management 保住 |
| GA Admin / SecOps / Anthropic brand 等产品专项无 scope 门 | `_PRODUCT_OPERATION_TERMS` → platform_operation + `scope_unresolved()` 统一解除判定；未解除最高 watch、不进 Top（可解除非 blacklist） |
| scan_budget=600 按 preliminary 排序分配 → 语义一变，落选候选 description 为空、分类失真且不可复现 | 预算 600 → 1200 覆盖全池（实测抓 1,075）；副作用如实记录：unscanned 506→31、block 5→9（新抓出的真 `curl \| bash`，fail-closed） |

### 已修（v2.6 关闭的 v2.5 遗留问题）

| v2.5 问题 | v2.6 修法 |
|---|---|
| 同名即已装：`KKKKhazix/khazix-skills/aihot` 被判 Virxact `aihot` 的 already_installed + update_available，更新源绑错仓库 | §二/§三/§十一：`lineage_confirmed` 五条件 + `LINEAGE_ALIASES` 证据表；不成立 → `same_name_unverified/same_name_different_source`（不装不更新不替换，最高 watch）；`UPDATE_LINEAGE` 由 Source Map 驱动、四件套字段 + `lineage_verified`；replacement 同名查找同过血缘门；哨兵 `same_name_only_already_installed` / `wrong_update_lineage` 恒 0 |
| GCP 专项漏进 Top（`cloud-run-basics` / `agent-platform-deploy` / `agent-platform-endpoint-management` 的 `domain_mismatch=[]`） | §四：14 个 GCP 产品别名 → `gcp` 域（裸 Gemini 豁免）；`microsoft store` → 独立域；哨兵 `gcp_alias_missed` 恒 0 |
| BrowserOS `test-ui` 凭 `testing_qa=weak` 成通用 install_candidate；Microsoft Store CLI 凭 Windows 设备成高优候选 | §四/§十：`scope_type` 三态 + `target_product` + 解除判定；第五道 Top 门；未解除 product_internal 最高 watch |
| `orca-emulator`（iOS）把重定向句「For an Android device…use the Android emulator skill」当自己的 android 能力，误上 install≈79.4 | §五：`strip_redirects` 重定向窗口（slug / the X skill 形态；`Use when`/`this skill` 不误伤）+ `fm_description` 600 窗口 + `match_projects` 正向视图 + Android tech 去裸 `emulator`；`redirect_evidence_rejected` 可审计 |
| `penpot-uiux-design`「using MCP tools」被判 mcp_dev primary（宽窗正则把 creating…MCP 连起来） | §六：开发动词必须管辖 MCP 工件；using/via 紧贴 → `mcp_usage` 独立标签；`_rule_mcp_dev` 只认 primary |
| `webapp-testing` 凭「frontend functionality」白拿最高权重 frontend-design；`canvas-design`/`generate-image` 漏 image_creative（已装 image_creative=none 的真缺口看不见） | §七：frontend_design 只认设计语义；image_creative 扩充（含中文词）；真设计三件（web-design-reviewer / frontend-design-review / tailwind-design-system）反向保护 |
| 「enable fast deployment / before production deployment / deployment categories / Ease of Deployment」被当部署能力 | §八：deploy primary 纯操作语义；裸 `deployment` 只能 mention；真部署动作反向保护 |
| `gen-specs-as-issues`（产品规格）凭名字含 specs 被打 testing_qa 白拿 15 分 | §九：名称词表删裸 spec/specs，测试语境的 spec（test spec / RSpec / executable specification）才成立；`test-spec-generator` / `rspec-*` 反向保护 |

### 已修（v2.5 关闭的 v2.4 遗留问题）

| v2.4 问题 | v2.5 修法 |
|---|---|
| `android` 需求被裸 device / build / install / launch 命中（`google-mobile-ads-get-started` / `-validate` 只是接入广告 SDK 就命中 w=27） | `android = custom _rule_android`：平台证据 AND **真实 QA 证据**（A 表 adb/emulator/real device/e2e/真机… 或 B 表 signing/keystore/apk/aab/构建验收…）；`test ads` 广告语境不算；反向回归 `orca-emulator-android` 照常命中 |
| 否定窗口把 `Don't use for A, B, or C.` 的 B / C 洗回正向（逗号也是分句边界，`agent-platform-prompt-management` 明写不用于部署仍误命中 deploy） | 两段式：大句只按 句号（跟空白/行尾，保护 `next.js` / `.net` / `node.js`）/ 分号 / 换行 / 句读 切分；**逗号仅在段内传播否定状态**；遇 `but / however / instead / 但 / 可用于 / 适用于` 等对比词才恢复正向 |
| 词面证据凭泛用技术词或裸 `prompt` 独立成立（`react-view-transitions`→yejian-buguangdeng via react/native；`claude-api`、`breakdown-test`→prompt-manager via prompt） | 泛用技术词（`_LEXICAL_TECH_BAN`，含 §三 19 词 ∪ TECH_MATCH 全部词）从词面证据**全禁**；`prompt` 移出高信号词并入 stop list；词级重叠降级为**次要加分**（须与 strong_tech/positioning/shared_need 同现，单独成立计 `lexical_alone_rejected`）；独立成立只认人工整理的 `_PROJECT_DOMAIN_PHRASES` 领域短语；新增恒 0 哨兵 `bare_prompt_direct_evidence` / `tech_words_used_as_lexical_direct_evidence` |
| 提到 MCP 就打 `mcp_dev`（`claude-api`「可与 MCP 配合」白拿缺口分） | `_cls_mcp` 四态：build/create/develop/implement… + MCP（同一句内）或名含 mcp-server/mcp-builder = primary；集成/连接类 = supporting；单纯提及 = mention 不打标签。`claude-api` 失去 mcp_dev；真实 builder 不受影响 |
| PPTX 冒充 `docx_xlsx`（`publish-to-pages` 生成 PPTX/PDF/HTML 却拿文档缺口分） | `_cls_docx`：只认 docx/xlsx/Word/Excel/spreadsheet/office document；PPTX/PowerPoint 单列 `pptx_processing` 标签 |
| 裸 `github` 命中 `github-auto`（`breakdown-test` 只因 GitHub 语境） | `GITHUB_AUTO_RULE = all_groups[GitHub 平台词, 运维语义词]`（Actions / gh CLI / issue creation / PR review / repository sync / 自动建 issue…） |
| 「顺带提及」与「核心能力」在评分层无统一口径 | §九 统一字段 `capability_evidence_context` ∈ {primary, supporting, mention, negated}（android / github-auto / deploy / mcp_dev / docx_xlsx 共用分类器）；只有 primary 拿满缺口分，supporting ≤8，mention/negated ≤2；matched_needs 带 `evidence_level`，supporting 权重 ×0.5 |
| 事故候选靠假证据占位 | §十一 数据重审：三处禁选项目匹配 = 0；两个事故候选不再因错误规则进 Top；Top 收缩至 19/30（**宁可少，不要假相关**） |

### 已修（v2.4 关闭的 v2.3 遗留问题）

| v2.3 问题 | v2.4 修法 |
|---|---|
| 技术栈命中天然等于直接项目证据（`azure-microsoft-playwright-testing-ts` 仅因 TypeScript 匹配 5 个普通 TS 项目） | 技术栈证据拆 **STRONG / SECONDARY**；泛用技术栈只加 `SECONDARY_BOOST`，绝不单独成立；首项证据改名 `strong_tech`；加「strong 必须能独立过 `min_score`」不变式 |
| Docker 词典含裸 `container`（`container queries` 误判为 Docker） | Docker 只认容器化语境词，删掉裸 `container` |
| 词面重叠凭单个泛词成立（`manager` → `prompt-manager`） | 泛词 stop list 大幅扩展；要求「≥2 个高区分度词」或「1 个项目域高信号词」 |
| 否定语境里的关键词仍算正向证据（`NOT for running Playwright tests` → browser-qa） | 新增**通用否定窗口**（按小句切分 + 否定标记 + 正向视图判定）；`negated_evidence_rejected` 可审计 |
| `deploy` 仍被 `cloud-hosted browsers` / CI-CD 命中 | 删裸 `hosted`；`hosting/hosted/publish` 必须与部署对象同现；CI/CD 只作 context |
| `testing_qa` 被 `testing methodologies` / `optional QA` 污染 | 改为「主能力证据」：Skill 名含测试身份词 **或** 描述把测试当核心任务 |
| `domain_mismatch` 只记录、不影响排序 | 未解除错配 → 不得 install_candidate / 不得进 Top / 总分 ×0.7；项目真实用上该平台即解除（非永久黑名单）；`select_top` 加第四道门 |
| 精度指标只能证明「字段不为空」（351/351） | 换成 `PROJECT_MATCH_QUALITY` 四类证据条数 + 三个「被拒」计数 |
| 中文关键词命中率恒为 0（75 个死词） | 含 CJK 的关键词改走子串匹配；回归测试对规则表做全量自检 |
| 分句不含逗号 → 否定窗口过度压制 | 逗号纳入分句边界；`negated_evidence_rejected` 由 94 → 30 |

### 已修（v2.3 关闭的 v2.2 遗留问题）

| v2.2 问题 | v2.3 修法 |
|---|---|
| 「项目类型适用」单独制造项目匹配（`orca-emulator-android` → macOS Widget 90 分） | 建立 `DIRECT_PROJECT_EVIDENCE`（`tech_stack` / `positioning` / `shared_need` / `lexical` 四选一），`TYPE_W` 30→10 降为 secondary boost；无证据 → `matched_projects=[]`。直接证据率 351/351 |
| `llm-api` 把 Google Ads / Mobile Ads API 当大模型接入 | `all_groups` 要求 LLM 语境 **AND** api/sdk/tool calling 等动作；新增 `none_of` 广告词表 |
| `deploy` 被 Vercel / CI-CD 语境误命中 | `any_of` 只留真部署动词；`vercel`/`netlify`/`ci-cd` 降为 `context_terms` |
| `voice-input` 把「可用语音口述当输入材料」当能力 | 去掉裸 `dictation`/`transcription`；新增 `none_of`（as input material 等） |
| `supabase-db` 被裸 RLS 误命中（Power BI 也有 RLS） | `all_groups` 收紧为必须出现 `supabase` |
| Top 内跨仓同功能族重复占位（两个 `webapp-testing` 同占 Top1/Top2） | 新增跨仓 `FUNCTIONAL_CLUSTER` 折叠 → PRIMARY + ALTERNATIVES；被同仓库上限拦下的兄弟也会登记，不再无声消失 |
| `always_block` 忽略语境，安全文档举反例被 reject | `_should_block(rule, ctx) = rule in BLOCK_ELIGIBLE_RULES and ctx != "warning"`；新增 `warning` 语境；收窄 `destructive_rm_root` 正则避免误伤 `/tmp/...` |
| Top 用 31 分的低质量 watch 凑数 | 三道质量门：`min_score=55` / 必须有个性化证据 / T3 需交叉佐证 |
| 归档包不自定位；SKIP 被算成 PASS | 输入 A 三级优先序（env → 包内 `支撑/输入/` → 本机默认）；测试摘要拆 PASS/SKIP/FAIL，SKIP 不计入 PASS |

### 已修（v2.2 关闭的 v2.1 遗留问题）

| v2.1 问题 | v2.2 修法 |
|---|---|
| 聚合源解析器误收构建产物（`.css/.js` 当成 Skill） | `data_gate.is_artifact_entry` + discover 解析层过滤，本期挡掉 **67** 条；并在 `counts.invalid_artifacts_removed*` 与 `quarantine` 留痕 |
| bottom-up 结果未过 TIER 2 硬门（`orca-codenewbies/backend` 这类后端仓混入） | bottom-up 进池前用 tree API 校验目录内确有 `SKILL.md`；过门也只给 `source_tier=null`（unverified），不高攀 T2；本期 41 → verified 17 / quarantined 23 |
| 关键词扁平表导致「平台词=能力已满足」假阳性 | `match_rules.py` MATCH_RULE 引擎（`all_groups` 组间 AND / 组内 OR）；`mobile_qa` / `supabase_db` / `android` / `desktop_app` / `deploy` / `python_auto` / `llm_api` / `photo_mgmt` / `voice_input` 逐一收紧 |
| 「提到凭据/`sudo`/`eval`」被判高危 → 误 reject | Security Gate v2：`confidence` + `behavior_context`，只有 block 级才 reject |
| 32 个安装候选全 `deep_scan=failed`（配额耗尽 + 失败缓存 24h） | API 层带认证 + **只在成功时落盘**；失败缓存 TTL 缩到 1 小时；脚本清单在 discover 阶段一次取回供 PASS 2 复用（零额外调用） |
| 高匹配候选答不出具体项目名 | 新增 `matched_projects`（解析 `SKILL_CONTEXT.md` §2，最多 5 条，覆盖率 92%） |
| Top30 可能混入 `ignore` / `reject` | Top 池只允许 `install_candidate` / `watch`；`contains_ignore` / `contains_reject` 作为自证字段输出 |
| orca / browseros 来源口径与已装侧不一致 | 注册表把 `stablyai/orca`、`browseros-ai/BrowserOS` 统一为 `official_repo` |

---

## 十一、变更日志

- **v2.11（2026-09-24）· 冻结前数据合同与语义一致性收口**（v2.10 / v2.9 全部机制保持；§十四 26 项回归；测试 85 → **90** 项）：
  - **§二/§三**：security_audit 四态（示例槽位降 supporting；team-composition 退出 install、breakdown-test 的 test task breakdown 不再撑 spec-driven；secret-scanning / dependabot / OWASP 保持 primary）。
  - **§四~§六**：PROJECT_CONTEXT_CONFLICT（yejian 检出、冲突侧 strong_tech 抑制、非冲突证据保留、输入 A 不改）；NEED_PROJECT_COMPATIBILITY（frontend-ui-dark-ts 的 global dashboard-viz 不再独自撑 Top；兼容项目出现即恢复——进测试）。
  - **§七~§十三**：机器合同四字段拆分（pool 允许 >0 / queue、top 必须 0，歧义字段废弃 + 哨兵）；未解除 product_internal 不入深度审查队列；Delta UPDATED 严格化 + 快照 schema/engine 信封 + SYSTEM_REBASELINE；action_type（computer-use=restore_candidate、known_missing 永不伪装新装）+ 日报 1B 恢复分栏；incremental_evidence_level（confirmed_absent 需读全 SKILL.md；summary_not_found 不得单独支撑安装推荐）。
  - **§十五~§十七 基线重生成**：数据 version 10 → **11**（scoring.json 仍 5，**评分权重自 v2.4 起未动**）；池 1,106；**Top 16/30**；install 9 / watch 238 / ignore 850 / reject 9；verdict pass 701 / review_required 365 / block 9 / unscanned 31；deep_scan eligible=complete=1,021；`DAILY_DELTA.UPDATED=0`（上轮 849 假风暴消失）；`product_internal pool=30 / queue=0 / top=0`；`internal_capability_in_full_scan=0`；`conflict_strong_tech_suppressed=8`；matched_projects 覆盖 16/90、完整性 144/144；known_fp（v2.11 组）=0、supporting_only=0、五个旧恒 0 哨兵 + v2.10 六案 + v2.11 组断言全 0。
- **v2.10（2026-09-24）· 冻结前 Top 语义与能力饱和收口**（对应审查文档《v2.9 …Top 语义与能力饱和收口》；树内 v2.9 已被产品关系轮占用，故编号顺延。§二~§十三 全部落地；测试 79 → **85** 项，原 v2.4–v2.9 全部 79 项 + hashseed 矩阵保持）：
  - **§二/§十 browser-qa 测试目标门**：primary = 对象+动作+**测试目标**；`browser_capture` / `accessibility_audit` / `llm_documentation` 信息标签；latchshot（screenshot/QA 一个词）与 frontend-design-review（theme testing）假 primary 清零，webapp-testing / e2e / 真行为测试保持。
  - **§三 spec-driven 重写**：「following/compliant with the X specification」= supporting；开发规格/SDD 词形才 primary；wiki-llms-txt 出局、gen-specs 保住。
  - **§四~§七 能力饱和**：`capability_saturation` 五档 + CLEAR_INCREMENTAL_VALUE Gate + `capability_family_quota`（strong=1/medium=2/weak·none=3）；frontend_design（已装 strong）Top 条数 7 → **1**（accessibility_audit 增量），`saturation_blocked_from_top=31`（可解除，非黑名单）。
  - **§八/§九 required_tech/compatible_tech**：frontend-ui-dark-ts 不再强配 family-insurance-dashboard（`required_tech_blocked_shared_need=5`）；CSS↔单文件 HTML、RN↔Expo 兼容保持。
  - **§十二/§十四**：`personalized_reason` 四字段进 Top 每条（strong 候选 `incremental_over_installed` 必非空，`top_strong_without_incremental_reason=0`）；`select_top` 按十步固定顺序执行。
  - **§十五 基线重生成**：数据 version 9 → **10**（scoring.json 为 v2.9 轮的 version 5，**评分权重自 v2.4 起未动**）；池 1,106；**Top 19/30**；install 9 / watch 239 / ignore 849 / reject 9；verdict pass 701 / review_required 365 / block 9 / unscanned 31；matched_projects 覆盖 16/92、完整性 144/144；PROJECT_MATCH_QUALITY：matched_candidates 73 / strong_tech 121 / positioning 15 / shared_need 13 / lexical 4 / negated 48 / redirect 689；known_fp（四案）=0、supporting_only=0、五个旧恒 0 哨兵保持 0。
  - 注：**v2.9（产品关系与领域三态轮）**当时未回写本 README，其完整记录在 `CANDIDATES_DIGEST.md` §5.0.1–5.0.5（六条数据完整性校验、21 case、全池安全队列、`product_scope` 三态与解除测试），规则与 v2.10 同时生效。
- **v2.8（2026-09-23）· 冻结前产品范围与核心需求证据最终收口**（v2.7 确定性矩阵 / 血缘 / UPDATE_LINEAGE / GCP 域 / 五道门 / 安全 Gate **全部保持**；§十三 16 项回归进套件；测试 58 → **63** 项）：
  - **§二/§五/§六/§七/§八 五个需求四态化**：expo-rn / python-auto / llm-api / browser-qa / dashboard-viz 全入 `EVIDENCE_CLASSIFIERS`（含管理面排除保持）；信息标签 `ml_experiment_tracking` / `model_serving` 独立记录、不吃缺口分。applicationinsights-web-ts（expo support ≠ RN 开发）、huggingface-trackio（实验看板 ≠ 通用看板）、hf-cloud-serving-image-selection（serving ≠ API 接入）、browserclaw（提到 Playwright ≠ 测试）的假需求全部消失；claude-api / react-native 双件 / webapp-testing / e2e / generic dashboard+python 自动化全部保住。
  - **§三/§四/§十 平台 scope 证据层**：azure-application-insights / microsoft-365-copilot / huggingface-spaces 补录 + AWS 服务别名（裸 lambda 不收）；`platform_scope_evidence{...evidence[],confidence}` 落进每条候选；解除矩阵（四种产品喂法）进测试；ui-widget-developer 保留 mcp_dev primary、被 scope 挡 Top（§三.2 原话执行）。
  - **§九 host 名词修正**：`_HOST_DEPLOY_RE` 严格式 + `_NOUNY_HOST_RE`；orca-per-workspace-env 假 deploy 消失，「host an app」保住。
  - **§十四 核心证据门**：`core_evidence_ok()` 进 `select_top`（require_core_evidence）；shared_need / 「看板」定位证据只认 primary。审计：`top_candidates_supporting_only: 0`、`core_evidence_blocked_from_top: 111`。
  - **§十一 终审计与基线**：七案（appinsights / trackio / ui-widget / hf-spaces / hf-cloud-serving / browserclaw / orca-env）全部退出或降 watch，`KNOWN_FALSE_POSITIVE_COUNT=0`、`SUPPORTING_ONLY_IN_TOP=0`、五个旧恒 0 哨兵保持 0；`AWS_ALIAS` 断言含「裸 lambda 不误伤」。基线：数据 version 6 → **8**（scoring.json 仍 4，权重未动）；池 1,106；**Top 15/30**；install_candidate 12 / watch 253 / ignore 832 / reject 9（block 名单与 v2.7 相同，本轮未动安全层）；matched_projects 覆盖 **22/103（21%）**、完整性 147/147；PROJECT_MATCH_QUALITY：matched_candidates 76 / strong_tech 121 / positioning 16 / shared_need 18 / lexical 4 / negated 48 / redirect 357 / product_specific_scope_unresolved 47。
  - **§十三 测试**：新增 5 个函数 16 断言点（`test_v28_expo_rn_support_vs_primary` / `test_v28_platform_scope_evidence_layer` / `test_v28_core_need_evidence` / `test_v28_browser_qa_and_host_noun` / `test_v28_top_final_audit`）；原 58 项 + hashseed 矩阵全保持：pass=63 skip=0 fail=0。
- **v2.7（2026-09-23）· 冻结前一致性与 Top 精度修复**（v2.6 身份血缘 / UPDATE_LINEAGE / GCP 别名 / 产品 scope / 安全 Gate / Deep Scan / 功能族 / Canonical **全部保持**；只修实测的一致性问题与 Top 剩余假相关；测试 52 → **58** 项）：
  - **§二/§十一 确定性硬门**：`_ctx` 保存 `raw_name` / `name_norm`（有序）/ `name_words_set`；名称短语判定禁止 `" ".join(set)`（实测 set 词序随 PYTHONHASHSEED 翻转 mcp_dev/mcp_usage——v2.6 回执「52/52」与审查环境「50/1/1」不一致的真凶）。新增 `test_v27_determinism_hashseed`：seed 0/1/2/3/42/123 子进程矩阵，输出逐字节一致才算过，`classification_drift` 必须为 0。
  - **§三 qa 歧义**：名称仅裸 `qa` 时需 `_QA_REAL_TERMS` 真实质保语义；`_QA_NEG_PHRASES`（answers questions / q&a / 问答…）一票否决；新增记录位 `question_answering`。wiki-qa 离开 Top；place-journal-qa（真验收描述）/ webapp-testing 反向保住。
  - **§四 deploy 邻近语义**：`_DEPLOY_PROX_RE` 动词+通用对象 ≤50 字符同句；`_DEPLOY_INTERNAL_OBJS`（rules/policies/games/content/documentation…）不算通用部署。game-engine（Top #2, 76.6）与 SecOps「deploy YARA rules」出局；deploy-to-vercel / python-appservice-deploy / 「Deploy the app to production」保住（§四 回归清单逐条进测试）。
  - **§五/§六 词面与技术遮蔽**：`_AMBIGUOUS_DOMAIN_TERMS` 守卫（breakout/native/model/agent/manager/dashboard… 单词不得独立成 lexical 证据；pepe 词条改 trading/price/market breakout、backtest…）；`_rn_masked()` 先遮蔽 React Native 跨度再判原生（React Native apps ≠ native macOS App，Swift/AppKit 保住）。
  - **§七/§八 产品专项 + secret**：`_PRODUCT_OPERATION_TERMS` → platform_operation + `scope_unresolved()` 统一解除判定（GA Admin / Google SecOps / anthropic-brand / Microsoft Store / SaaS 后台；未解除最高 watch + 第五道 Top 门；可解除非 blacklist）；secret-safety = 安全对象 AND 安全动作（rotate/scan/redact/vault/密钥管理…），「Measurement Protocol secrets」出局、secret-scanning 保住。
  - **§七 附：扫描预算诚实化**：`scan_budget` 600 → 1200 覆盖全池（实测 1,075 抓取）——旧预算按 preliminary 排序分配，语义一改就有候选饿成空描述、分类失真且不可复现。副作用如实入账：verdict unscanned 506 → 31、block 5 → 9（新抓出的真 `curl | bash`，安全规则层零改动）。
  - **§九~§十三 测试与基线**：新增 6 个 v2.7 测试函数（`test_v27_determinism_hashseed` / `test_v27_qa_ambiguity` / `test_v27_deploy_proximity` / `test_v27_lexical_domain_and_native_mask` / `test_v27_product_specific_scope` / `test_v27_top_final_audit`）；§九 六条 + `known_false_positive_count = 0` 对最终数据现算全过；`config/scoring.json` version 保持 4（**权重未动**，仅 scan_budget 600→1200），候选数据 version 6 → **7**。基线：raw 1170 → 池 1106；Top **20/30**；install_candidate **13** / watch 258 / ignore 826 / reject **9**；PROJECT_MATCH_QUALITY：matched_candidates 85 / strong_tech 121 / positioning 20 / shared_need 36 / lexical 4 / negated 54 / lexical_single 1437 / redirect 357 / phrase 4；五个恒 0 哨兵全 0；matched_projects 覆盖 29/121、完整性 158/158。
- **v2.6（2026-09-23）· 冻结前身份血缘与语义完整性整改**（v2.5 来源分层 / 安全 Gate / Deep Scan / 直接证据分级 / 否定窗口 / Top 质量门 / 功能族 / 归档自定位**全部保持**；只修复审发现的 7 类问题，未新增 blacklist；测试 43 → **52** 项）：
  - **§二/§三/§十一 身份血缘**：删除「同名即已装」——`installed_relationship` 同名分支必须过 `lineage_confirmed`（upstream 仓库一致 / Source Map 记载 / 内容指纹 / `LINEAGE_ALIASES` 证据表：leader、neat-freak 按『逐字节一致』证据入表）；不成立 → `same_name_unverified`（4 条）/`same_name_different_source`（2 条），不标已装、不建 update/replacement、最高 watch、NOVELTY 0、gap 封顶 5。更新检查读 Source Map：新增 `build_update_lineage()`（日报/对照件共用），每条更新项带 installed_canonical_id/installed_upstream/update_upstream/lineage_evidence/lineage_verified——**aihot 更新源回到 Virxact，不再绑 Khazix**；browseros-neo 同血缘仍可 update。实测：`SAME_NAME_ONLY_ALREADY_INSTALLED=0`、`WRONG_UPDATE_LINEAGE=0`。
  - **§四/§十 产品 scope**：`MISMATCH_KW` 补 14 个 GCP 产品别名（→gcp）+ `microsoft store`/`msstore`（→microsoft-store），裸 Gemini 豁免；新增 `product_scope()`（generic/platform_operation/product_internal + target_product）与 `product_internal_unresolved()`（项目档案真的在用该产品才解除）；`select_top` **第五道门** `require_no_unresolved_scope` + `recommend_of` 未解除 product_internal 最高 watch。效果：cloud-run-basics / agent-platform-deploy / -endpoint-management 标 gcp 并离开 Top（其中两条 deploy 需求同时被 §八 打成 mention 出局）；BrowserOS `test-ui`（product_internal，未解除）挡在 Top 外；`msstore-cli` 81 → 45.4 watch；`gcp_alias_missed=0`、`top_candidates_with_unresolved_product_scope=0`、`scope_blocked_from_top=1`。
  - **§五 重定向窗口**：`_REDIRECT_RE` + `strip_redirects()`（For X, use/see Y · instead · handled/covered by · 请使用/请改用；目标必须是 slug 或 `the X skill`，`Use when`/`this skill` 不误伤）；`_ctx` 先剪重定向再剪否定；`redirect_evidence_rejected=126` 可审计。连带修三处「规则看着对实际不生效」：`fm_description` 300→**600**（截断砍掉重定向句尾）、`match_projects` ①② 改**正向视图**判定、TECH Android 去裸 `emulator` + `_QA_OR_DEVICE` 补 `simulator`。效果：`orca-emulator` android 需求/matched_project/权重全部消失（→watch 50），`orca-emulator-android` 反向保护成功（79.4 install_candidate，Top #1）。
  - **§六 mcp_usage 分离**：`_MCP_ARTIFACT_RE`+`_MCP_DEV_VERB_RE`+`_MCP_PRE_USAGE_RE`——开发动词必须管辖 MCP 工件；新增 CAP `mcp_usage`；`_rule_mcp_dev` 只认 primary。penpot → mcp_usage ✓ mcp_dev ✗；mcp-builder / php / rust generator 三件套 primary 保住。
  - **§七/§八/§九**：frontend_design（CAP+NEED）只认设计语义（webapp-testing 出局，真设计三件保住）；image_creative 扩充（canvas-design / generate-image 命中 `image_creative=none` 真缺口，generate-image 84.5 → install_candidate 路径打开）；DEPLOY_RULE 删裸 `deployment`、primary 纯操作语义（e2e-testing-patterns / agent-owasp-compliance / cloud-design-patterns / impediment-prioritization 的「部署背景」全部出局，真 deploy 保住）；`_TESTING_NAME_TOKENS` 删裸 spec/specs（gen-specs-as-issues 出局；test-spec / rspec 保住）。
  - **§十二/§十三 测试与断言**：新增 9 个测试函数覆盖 §十二 20 个回归点（`test_v26_lineage_identity` / `test_v26_update_lineage_data` / `test_v26_gcp_aliases_and_scope` / `test_v26_product_internal_gate` / `test_v26_redirect_not_capability` / `test_v26_mcp_usage_vs_dev` / `test_v26_frontend_design_and_image_creative` / `test_v26_deploy_noun_and_spec_tokens` / `test_v26_final_data_assertions`）；§十三 十项数据断言全 0。原 43 项全部保持（其中 v2.5 的 react-view-transitions 禁选对改为**按依据类型断言**：600 窗口使 strong_tech Next.js 合法重新命中，lexical 依据仍被哨兵禁死）。
  - **§十三 基线重生成**：候选数据 version 5 → **6**（`config/scoring.json` version 保持 4，权重未动）。raw 1170 → 池 1106；Top **18/30**；install_candidate **12** / watch 454 / ignore 635 / reject **5**（block 3 → 5：`developing-genkit-dart` / `-go` 两条进入本轮 600 抓取扫描面后按既有规则判 block——真实 `curl … | bash` 远程安装命令；**安全规则层本轮零改动**，属 fail-closed 的正常轮换）；verdict pass 394 / review_required 201 / block 5 / unscanned 506；deep_scan complete 12；PROJECT_MATCH_QUALITY：matched_candidates 76 / strong_tech 119 / positioning 16 / shared_need 30 / lexical 2 / secondary_rejected 112 / negated 253 / lexical_single 1010 / lexical_alone 3 / phrase 2 / redirect 126；五个恒 0 哨兵全 0；matched_projects 覆盖 22/107、完整性 146/146。
- **v2.5（2026-09-23）· 冻结前最后语义收口**（v2.4 架构 / 来源层 / 安全 Gate / Top 质量门 / 直接证据分级 / 归档自定位**全部保持**，只修文档列出的剩余语义误判；测试 35 → **43** 项，Python 要求 **3.12+**）：
  - **§一 android 真 QA 证据**：`NEED_RULE["android"]` 改 `custom: _rule_android` —— 平台证据 AND（A 表 qa/e2e/adb/emulator/real device/appium/detox/maestro/espresso/xctest/instrumentation/真机… 或 B 表 signing/keystore/signed apk/apk/aab/build verification/签名/构建验收…）；裸 device/build/install/launch 禁作正向证据；`test ads` 语境由 `_AD_TEST_RE` 压制。`google-mobile-ads-get-started` / `-validate` 不再命中；`orca-emulator-android` 双向回归保持命中。
  - **§二 否定窗口两段式**：`_CLAUSE_SPLIT_RE` 去掉逗号（大句只按 句号+空白/行尾、分号、换行、句读 切），新增 `_COMMA_SPLIT_RE` 与 `_POS_RESTORE_RE`：逗号仅在段内**传播否定状态**，遇 but/however/instead/whereas/use for/但是/但/不过/而是/可用于/适用于… 才恢复正向。`Don't use for A, B, or C.` 的 B/C 不再复活（`agent-platform-prompt-management` / `-tuning` 的假 deploy 消失）；`next.js` / `.net` / `node.js` 照旧不被切碎。
  - **§三/§四/§五 词面证据重构**：`_LEXICAL_TECH_BAN`（§三 19 词 ∪ TECH_MATCH 全部词）从词面证据全禁；`prompt`/`prompts` 移出高信号、并入 stop list；词级重叠（≥2 高区分度词）**只作次要加分**、须与 strong_tech/positioning/shared_need 同现，单独成立计 `lexical_alone_rejected`；独立成立只认人工整理的 `_PROJECT_DOMAIN_PHRASES`（每项目 ≤14 分的领域短语表）；新增**恒 0 哨兵** `bare_prompt_direct_evidence` / `tech_words_used_as_lexical_direct_evidence`。三处事故匹配（react-view-transitions→yejian-buguangdeng、claude-api→prompt-manager、breakdown-test→prompt-manager）全部消失。
  - **§六 mcp_dev 核心化** / **§七 docx_xlsx 与 PPTX 分离** / **§八 github-auto 运维语义**：`_cls_mcp`（build/create/develop… + MCP = primary；集成/连接 = supporting；单纯提及 = mention 不打标签）、`_cls_docx`（docx/xlsx/Word/Excel 才成立；PPTX → 新标签 `pptx_processing`）、`GITHUB_AUTO_RULE = all_groups[GitHub 平台词, 运维语义词]`。
  - **§九 统一证据语境**：`EVIDENCE_CLASSIFIERS`（android / github-auto / deploy / mcp_dev / docx_xlsx）+ `evidence_context()` 四态字段 `capability_evidence_context` 写入 `capability_gap_match`；`matched_needs` 附 `evidence_level`，supporting 权重 ×0.5；`score_candidate`：CAPABILITY_GAP 只有 primary 满分、supporting ≤8、mention/negated ≤2。DEPLOY_RULE / GITHUB_AUTO_RULE 抽为常量供测试内省。
  - **§十 新增 8 个测试函数覆盖 18 个回归点**：`test_v25_android_real_qa_evidence` / `test_v25_negation_comma_enumeration` / `test_v25_lexical_evidence_tightened` / `test_v25_mcp_dev_core_capability` / `test_v25_docx_xlsx_vs_pptx` / `test_v25_github_auto_needs_ops_semantics` / `test_v25_capability_evidence_context` / `test_v25_top_reaudit_final_data`。原 35 项**全部保持通过**：pass=43 skip=0 fail=0。
  - **§十一 数据重审**：`google-mobile-ads-get-started` / `agent-platform-prompt-management` 不再因错误规则进 Top；日报「对我哪个项目有用」改为展示**直接证据原文**（不再回退「技术栈词面重叠」泛标签）。
  - **§十三 基线重生成**：`SKILL_SOURCE_REGISTRY.json` / `SKILL_CANDIDATES.json` / `EXTERNAL_SKILLS_CONTEXT.md` / `CANDIDATES_DIGEST.md` / 本 README 全部按 v2.5 口径重出。raw 1170 → 池 **1106**，Top **19/30**（宁可少，不塞假相关），install_candidate **15** / watch **492** / reject **3**；安全 pass 395 / review_required 202 / block 3 / unscanned 506；PROJECT_MATCH_QUALITY：matched_candidates **66** / strong_tech **103** / positioning **12** / shared_need **20** / lexical **1**（全部来自领域短语）/ secondary_tech_only_rejected 106 / negated_evidence_rejected 118 / lexical_single_rejected 943 / lexical_alone_rejected 1 / **两个哨兵 = 0**。`config/scoring.json` version 保持 4（权重未动），候选数据 version **5**。
- **v2.4（2026-09-23）· 项目相关性最终收口**（v2.3 架构 / 来源层 / 安全 Gate / Top 质量门 / Canonical 体系**全部保持**，只修「规则形式上有 direct evidence、真实语义仍是假相关」；测试 27 → **35** 项）：
  - **§一/§二 技术栈证据分 STRONG / SECONDARY**：`TECH_MATCH` 每条加 `tier`。strong（Expo / RN / Android / Kotlin / Supabase / Postgres / Next.js / PWA / 离线本地存储 / macOS 桌面 / 原生 / LLM API / Playwright / Vercel / Netlify / Cloudflare / CF Pages / .NET / C#）可**独立**形成匹配；secondary（TypeScript / React / Python / Docker / 自托管 / Tailwind / shadcn / 单文件 HTML / Shell）只加 `SECONDARY_BOOST = 3.0`，**绝不单独成立**。`DIRECT_EVIDENCE_KINDS` 首项 `tech_stack` → **`strong_tech`**。加不变式守卫 `STRONG_TIER_MIN_W = 10` + 回归断言：每个 strong 技术栈都够独立过 `min_score`（Next.js 原 9 分 → 归一化 18 < 20，**永远无法独立成立**，本轮修掉）。效果：`azure-microsoft-playwright-testing-ts` 的 matched_projects 5 → **0**。
  - **§三 Docker 词典**：删掉裸 `container`（`container queries` 被误当 Docker，`responsive-design` 曾匹配 3 个 Docker 项目）。只认 docker / dockerfile / docker compose / containerization / container image / container runtime / docker container / 容器化。
  - **§四 LEXICAL 收紧**：`_LEXICAL_STOP` 大幅扩展（manager / management / resource / service(s) / application(s) / system(s) / development / developer / testing / test(s) / data / model(s) / client / server / api(s) / code / library / framework / integration / automation / content / output / input / level / process + v2.3 平台泛词）；新增 `_LEXICAL_HIGH_SIGNAL`（prompt / insurance / rss / transcription / whisper / podcast / subtitle / obsidian / valuation / dividend / portfolio / backtest / playwright / supabase / expo / tauri / electron / journal / photography / invoice / ledger / checkin / exif）。判定：1 个高信号词 → `min(14, 10+2n)`（够单独过 `min_score`）；≥2 个 generic（≥5 字符）→ `min(10, 6+2n)`；单泛词 → `lexical_single_rejected` 计数、**不成立**。`manager` 单独不再匹配 `prompt-manager`。
  - **§五 通用否定窗口**：新增 `_CLAUSE_SPLIT_RE`（句点后必须跟空白/行尾才分句，保护 `next.js` / `.net` / `node.js`；逗号 `,` `，` 也是边界）/ `_NEG_MARK_RE`（not / never / don't / does not / avoid / without / not intended / 非用于 / 不用于 / 不支持 / 不适用 / 禁止 / 不要 / 不可…）/ `strip_negated()` / `hit_pos()` / `_note_suppressed()`。判定只在**正向视图**做，Skill 名不受描述否定影响。`MATCH_RULE` 新增 `any_groups`（组内 AND / 组间 OR）与 `custom`；优先级 custom → all_groups → (any_of OR any_groups) → none_of。`_MGMT_PLANE_TERMS` 进 `browser-qa` 的 `none_of`。效果：`azure-resource-manager-playwright-dotnet` 不再命中 browser-qa。
  - **§六 deploy 二次收紧**：删正向 `any_of` 里的裸 `hosted`；`hosting / hosted / publish / publishing` 必须与**部署对象**（app / application / site / service / pages / build / artifact / production / environment…）同现（`any_groups`）；CI/CD 只作 context。`azure-microsoft-playwright-testing-ts` 不再命中 deploy。
  - **§七/§八 testing_qa 改「主能力证据」**：`CAP_RULE["testing_qa"] = {"custom": _rule_testing_qa}`。**A.** Skill 名含 `test/tests/testing/qa/e2e/playwright/pytest/vitest/jest/cypress/spec/selenium`；**B.** 描述把测试当核心任务（`run/write/create tests` / `test application` / `QA workflow` / `acceptance testing` / `regression testing` / `validate behavior` / `test suite` / `e2e tests` / `unit tests` / `integration tests` / `browser testing` / `visual regression` / `testing standards` / 运行测试 / 编写测试 / 测试套件 / 自动化测试 / 端到端测试…）。`testing methodologies` / `optional QA` / `may be tested` / `QA is optional` / `examples include testing` 只算**提及**。效果：`ai-prompt-engineering-safety-review` / `ai-team-orchestration` / `orca-per-workspace-env` 不再误得；`webapp-testing` / `e2e-testing-patterns` 保持。
  - **§九 domain_mismatch 真正生效**：新增 `MISMATCH_DOMAIN`（azure→azure、google cloud/gcp/bigquery→gcp、aws→aws、java/spring boot→java、c#/.net/dotnet…→dotnet、dynamics 365→microsoft-business…）/ `mismatch_domains()` / `project_domains()`。`analyze.evaluate()` 计算 `domain_mismatch_resolved` / `domain_mismatch_unresolved` / `domain_mismatch_resolved_by`；`DOMAIN_MISMATCH_PENALTY = 0.7` 总分成乘数（系数记在 `domain_mismatch_penalty`）；`recommend_of` 对 unresolved **最高 watch**。解除看的是**整个项目档案的技术面**（不是「该候选匹配到的项目」，否则会变成事实上的永久 blacklist）。`build_context.select_top(..., require_no_mismatch=True)` 作为**第四道门**。效果：Top 内 `top_candidates_with_unresolved_mismatch = 0`，Azure / SageMaker 三条全部挡在 Top 外。
  - **§十 PROJECT_MATCH_QUALITY 取代「字段非空率」**：`match_rules.QUALITY` 计数器 + `reset_quality()`；`analyze.main()` 在最后一次 `evaluate()` 前清零，之后写进 `out["project_match_quality"]` 并打印 `PROJECT_MATCH_QUALITY | ...`；`build_context` 输出同名机器块。本期：matched_candidates **106** / strong_tech **100** / positioning **11** / shared_need **28** / lexical **49** / secondary_tech_only_rejected **102** / negated_evidence_rejected **30** / lexical_single_rejected **887**。
  - **§十一 新增 8 个测试函数覆盖 18 个回归点**：`test_v24_strong_tier_can_stand_alone`（§一/§二 不变式）、`test_v24_tech_evidence_tiers`（1-4/8-10）、`test_v24_negation_window_and_deploy`（5/6）、`test_v24_matching_primitives`（§五 + 命中原语）、`test_v24_lexical_stoplist`（7）、`test_v24_testing_qa_primary_capability`（11-15）、`test_v24_domain_mismatch_gate`（16-18）、`test_v24_project_match_quality`（§十）。全部通过：**pass=35 skip=0 fail=0**。
  - **附带修掉两个「规则看起来对、实际不生效」缺陷（排查中发现）**：① `_WORD_RE` 是纯 ASCII，中文没有词边界 → 规则表里 **48 个 NEED_RULE + 27 个 CAP_RULE 中文关键词**加 `容器化` / `菜单栏应用` **全是永不命中的死词**；改为含 CJK 的关键词走子串匹配，并加**全量自检**回归（同时保留英文整词匹配，`ui` 命中 build 的老事故不许回归）。② 分句不含逗号 → 「非用于 A，可用于 B」整句被丢弃、把正向证据一起误杀；逗号纳入分句边界后 `negated_evidence_rejected` 由 **94 → 30**。
  - **§十三 基线重生成**：`SKILL_SOURCE_REGISTRY.json` / `SKILL_CANDIDATES.json` / `EXTERNAL_SKILLS_CONTEXT.md` / `CANDIDATES_DIGEST.md` / 本 README 全部按 v2.4 口径重出。raw 1170 → 池 **1106**，Top **20/30**，安全 pass 396 / review_required 201 / block 3 / unscanned 506；`functional_duplicates = 1`，`t3_uncorroborated = 23`，`mismatch_blocked_from_top = 2`。`config/scoring.json` version 保持 4（评分权重未动），候选数据 version **4**。
- **v2.3（2026-09-23）· 语义精度最终整改**（v2.2 架构不变，按 §一–§九 逐条落实；测试 21 → **27** 项）：
  - **§一/§六 DIRECT_PROJECT_EVIDENCE**：`match_rules.match_projects` 重写。四类直接证据（`tech_stack` / `positioning` / `shared_need` / `lexical`）至少一项成立才产生匹配，否则 `matched_projects=[]`；`TYPE_W` 30 → **10**（`TYPE_BOOST`），**类型适用不得单独成立**；`_LEXICAL_STOP` 排除平台泛词（macos/windows/android/ios/platform/python…）；`TECH_MATCH["macOS 桌面"]` 去掉裸 `macos`。结果：`orca-emulator-android` 不再匹配 `DeepSeekBalanceWidget-Mac`，改为 `landedazi-android`（50，`tech_stack`）。覆盖率由 KPI 降为参考（**86/173**），直接证据率 **351/351**。
  - **§二 NEED_RULE 二轮收紧**：`llm-api`（LLM 语境 AND api/sdk/tool calling + `none_of` 广告词）、`deploy`（只留真部署动词，vercel/netlify/ci-cd → `context_terms`）、`voice-input`（去裸 dictation/transcription + `none_of` 输入材料语境）、`supabase-db`（`all_groups` 仅 `supabase`，RLS 不再单独成立）。
  - **§三/§八 FUNCTIONAL_CLUSTER**：`build_context.functional_family()`（normalized name ≥5 字符 / description jaccard ≥0.62 且同前缀 / content fingerprint）+ `select_top()` 跨仓折叠，Top 只出 PRIMARY，其余进 `alternatives`；新增 `### 2.1 ALTERNATIVES` 表。补漏：被同仓库上限先拦下的同族兄弟也登记进 alternatives，不再无声消失。
  - **§四 Security Gate always_block 修正**：新增 `_NEGATION_RE` / `BLOCK_ELIGIBLE_RULES` / `NON_BLOCKING_CONTEXTS` 与 `_should_block(rule, ctx)`；`behavior_context` 增加 **`warning`**；`always_block` **不再命中即 block**（`ctx == "warning"` → `review_required`）；收窄 `destructive_rm_root` 正则（`rm -rf /tmp/...` 不误伤）。双向验证：安全文档举反例不 block、真 `rm -rf ~/` 与真 `curl|bash` 必 block。
  - **§五 Top 三道质量门**：`select_top(min_score, require_evidence, corroborated_repos)` —— `score ≥ min_score`（配置 `55`）/ `has_personalized_evidence` / `is_t3_uncorroborated`。本期 Top **22/30**，`t3_uncorroborated` **23** 条挡在 Top 外只留 WATCHLIST。`build_corroborated_repos()` 抽成公共函数，日报与对照件共用同一口径。
  - **§九 归档包自定位 + 测试摘要三分**：`common._resolve_skill_context()` 三级优先序（`SKILL_CONTEXT_PATH` → 包内 `支撑/输入/SKILL_CONTEXT.md` → 本机默认）；v4 自动发现改为向上 **3** 级；新增 `PATH_RESOLUTION` 记录命中来源。`tests/test_pipeline.py` 新增 `_COUNTS` / `_classify_output()` / `_run()`，摘要打印 `TEST SUMMARY: pass=/skip=/fail=`，**SKIP 不计入 PASS**。
  - **§十 新增 6 个测试函数覆盖 15 个回归点**：`test_v23_need_rule_regressions`（§十 1-6）、`test_v23_project_match_direct_evidence`（7/8/14）、`test_v23_top_quality_gate_and_cluster`（9/13）、`test_v23_security_context_block`（10-12）、`test_v23_summary_counts`（15）、`test_v23_digest_generates`（对照件可生成）。`test_matched_projects_coverage` 放宽为「允许为空、机制仍需活着、非空必带直接证据」。`config/scoring.json` version 3→**4**。
  - **§十一 基线重生成**：`SKILL_SOURCE_REGISTRY.json` / `SKILL_CANDIDATES.json` / `EXTERNAL_SKILLS_CONTEXT.md` / `CANDIDATES_DIGEST.md` / 本 README 全部按 v2.3 口径重出。raw 1170 → 池 **1105**，Top **22/30**，安全 pass 395 / review_required 202 / block 3 / unscanned 505。
  - **§十二 验收摘要**：`false_positive_regression=PASS`、`false_block_regression=PASS`、测试 `pass=27 skip=0 fail=0`。
- **v2.2（2026-09-22 深夜）· 语义精度整改**（按外部审查意见逐条落实，12 节 / 17 项回归）：
  - **§一 数据质量 Gate**：新增 `scripts/data_gate.py`；聚合源在解析层挡掉构建产物（本期 **67** 条），入池前再挡非法名；`counts` 增 `invalid_artifacts_removed*` / `invalid_names_removed` / `bottom_up_*`，候选池增 `quarantine` 四类隔离区。**bottom-up 不再是 TIER 2**：过 `SKILL.md` 硬门后也只能是 `source_tier=null`（unverified），`tier_trust_ceiling.unverified=3`。
  - **§二 MATCH_RULE 语义引擎**：新增 `scripts/match_rules.py`，用 `all_groups`（组间 AND / 组内 OR）+ `any_of` / `none_of` / `context_terms` 取代扁平关键词表；收紧 `mobile_qa`（须同时有移动平台证据与 QA/设备/构建验证证据，并拆出 `mobile_dev` / `expo_rn_dev`）、`supabase_db`（须真 Supabase/RLS 语境，普通 PostgreSQL → `postgres_db`）、`android` / `desktop_app` / `deploy` / `python_auto` / `llm_api` / `photo_mgmt` / `voice_input`。
  - **§三 matched_projects**：解析 `SKILL_CONTEXT.md` §2 项目档案（name/positioning/tech/date），`TECH_MATCH` + `CAP_TYPE`∩`NEED_TYPE` + 描述信号 + 词元重合打分，最多 5 条、低于阈值不硬凑；覆盖率 **186/202 = 92%**。
  - **§四 Security Gate v2**：每条 finding 增 `confidence`（high/medium/low）与 `behavior_context`（mention/instruction/executable/remote_execution）；`verdict ∈ pass/review_required/block/unscanned`；**只有 block 才 reject**，「文档里提到 `sudo`/`.env`/`eval`」不再误伤。
  - **§五 两阶段深度静态审查**：PASS 1 扫 `SKILL.md`、PASS 2 深读 `.py/.sh/.js/.ts/.mjs/.cjs/.ps1` 与 `package.json` 的 `postinstall`/`preinstall`；`install_candidate` 必须 `deep_scan_status=complete` 且无 block finding；`deep_scan_status` 细分为 `complete/failed/pending/not_required/skipped`，**不把「没扫」写成「已扫」**；全程只读，绝不执行脚本。
  - **§六 来源口径统一**：`stablyai/orca`、`browseros-ai/BrowserOS` 由 `vendor_repo` 改为 `official_repo`，与已装侧一致。
  - **§七 Top 候选去垃圾**：只允许 `install_candidate` / `watch`，输出 `target_limit` / `actual_count` / `contains_ignore` / `contains_reject`；不足就输出实际数量。
  - **§八 基础设施修复（关键）**：修掉「32 个 install 候选全部 `deep_scan=failed`」的真实故障——根因是匿名配额 60/小时耗尽 + 失败被缓存 24h。改为：API 层支持 `GITHUB_TOKEN`/`GH_TOKEN`，**取不到时自动读本机 `gh auth token`**；**只在成功时落盘缓存**；失败缓存 TTL 缩到 1 小时；脚本清单在 discover 阶段随文件树一次取回供 PASS 2 复用。结果：`install_candidate` **0 → 32**，`deep_scan` 32/32 complete。
  - **§九 文档同步**：本 README 全面改写到 v2.2 口径。
  - **§十 测试**：14 → **21** 项，新增 8 项覆盖 17 个回归点（mobile_qa / supabase / 数据质量 / Security v2 误伤 / 深度审查硬门 / Top 无垃圾 / matched_projects 覆盖 / 来源统一），全部通过。
- **v2.1.1（2026-09-22 21:4x）· 归档与可复现性收尾**：
  - 新增 `scripts/make_digest.py` → `CANDIDATES_DIGEST.md`（给审查者的切片视图：总览 + Top + 安全清单 + 更新候选 + 已知缺陷）。**排序与 Top 规则直接复用 `build_context`**，避免「日报的 Top」与「对照件的 Top」不一致。
  - **修掉归档副本跑不起来的问题**：脚本原先按 `__file__` 推相对路径，整包单独交付时 `FileNotFoundError`（本机实测）。改为**环境变量可覆盖 + 自动向上定位**（`SKILL_REPO_ROOT` / `SKILL_CONTEXT_PATH` / `SKILL_DATA_DIR` / `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH`）。归档副本实测测试全过。
  - 归档出 `转送审查者 v5 材料（外部情报层）/`（正式件 + 对照件 + README + `支撑/` + 转送说明）。
  - 如实登记两条**已发现未修**的数据质量问题（见 §十「已修」表，v2.2 已关闭）。
- **v2.1（2026-09-22 晚）· 排序质量修复**：
  - **修掉一个真实事故**——关键词子串匹配（`"ui" in "build"` 等）导致 `PROJECT_MATCH` 恒为满分、Top 被云厂商无关技能占满。改为整词/短语匹配，并新增回归测试（见 §6.2）。
  - 新增**需求侧独立关键词表 `NEED_KW`**（覆盖 `SKILL_CONTEXT.md` 全部 24 项 needs），与已装侧 `CAP_KW` 分离——前者回答「用户需不需要」，后者回答「本机压不压制」。
  - 新增**相关性否决**与**平台错配降权**（见 §6.1）；`PROJECT_MATCH` 无证据不再送 8 分；`CAPABILITY_GAP` 无需求证据封顶 5。
  - 新增 **Top 多样性规则**（同仓库 ≤3、同族折叠，见 §6.4）。
  - 测试从 12 项扩到 14 项（新增 `test_keyword_matching_no_substring`、`test_top30_selection`），全部通过。
  - 效果：`install_candidate` 197 → 53，Top 从「Azure/BigQuery/Airflow 云厂商技能」变为「webapp-testing / uiux-design / responsive-design / react-native-skills / mcp-builder / deployment-pipeline-design」等真正对口的能力。
- **v2（2026-09-22 晚）**：注册表补齐 14 个规定字段（含 `trust_level` / `discovery_only` / `supports_*` / `status`）；新增 TIER 2 三个已证实社区源；发现层改用 tree API 精确定位 `SKILL.md` 并纳入 TIER 2；候选层补齐 `source` / `latest_version` / `adoption_signal` / `capability_gap_match` / `scores` / 7 个安全行为标志，`recommendation` 改用 `install_candidate`；新增 `replacement_candidate` 判定（读已装侧 `version_status`/`upstream_activity`）；Context 机器块补齐 11 节（含 `CANDIDATE_POOL_SUMMARY` / `PERSONALIZED_TOP30` / `DAILY_DELTA`）；修复 `description` 解析出 `>` 的 bug（YAML 块标量）。
- **v1（2026-09-22 18:xx）**：首版建成——注册表 T0/T1/T3（T2 空）、双向发现、canonical 去重、安全 Gate、8 维评分、Context 8 节、9 项离线测试。
