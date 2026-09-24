# External Skills Context（外部 Skill 情报 · 日报底座）

> 生成日期：2026-09-24｜来源注册表 v2：T0 2 / T1 9 / T2 3 / T3 3
> 本层只做「发现 → 标准化 → 去重 → 匹配 → 安全审查 → 个性化排序」。**不安装、不删除、不升级任何 Skill**；安装一律在 Skill Manager 人工执行。
> 排名/安装量只是 adoption signal，绝不等于质量或推荐依据。完整数据：`data/SKILL_CANDIDATES.json`

```
SOURCE_HEALTH:
  - T0 agentskills.io: reachable (trust=spec_only)
  - T0 agentskills/agentskills: reachable (trust=spec_only)
  - T1 anthropics/skills: verified (trust=high)
  - T1 github/awesome-copilot: verified (trust=medium)
  - T1 vercel-labs/agent-skills: verified (trust=high)
  - T1 vercel-labs/skills: verified (trust=high)
  - T1 microsoft/skills: verified (trust=high)
  - T1 huggingface/skills: verified (trust=high)
  - T1 stablyai/orca: verified (trust=high)
  - T1 google/skills: verified (trust=high)
  - T1 browseros-ai/BrowserOS: verified (trust=high)
  - T2 KKKKhazix/khazix-skills: verified (trust=medium)
  - T2 obra/superpowers: verified (trust=medium)
  - T2 wshobson/agents: verified (trust=medium)
  - T3 skills.sh: reachable (trust=discovery_only)
  - T3 clawhub.ai: reachable (trust=discovery_only)
  - T3 skillsmp.com: reachable (trust=discovery_only)
  - skills.sh entries_today: 50 (healthy=True)
  - clawhub entries_today: 2 (healthy=True)

CANDIDATE_POOL_SUMMARY:
  raw: 1170
  canonical: 1106
  invalid_artifacts_removed: 67   # 构建产物/静态资源（§一.1）
  invalid_names_removed: 1   # 非法 skill slug
  bottom_up_total: 41
  bottom_up_verified: 17   # 过 SKILL.md 硬门
  bottom_up_quarantined: 23   # 已隔离，不入正式池
  already_installed: 8
  same_name_unverified: 4
  same_name_different_source: 2
  near_duplicate: 0
  overlap: 9
  complement: 2
  new_capability: 1078
  replacement_candidate: 3
  gap_none: 28
  gap_weak: 97
  gap_medium: 0
  gap_strong: 981

NEW_DISCOVERIES: 0
HIGH_MATCH_CANDIDATES: 9
CAPABILITY_GAP_CANDIDATES: 125   # gap_level ∈ {none, weak}
TRENDING_RELEVANT: 9
UPDATE_CANDIDATES: 1   # delta 变化 + 已装但版本落后（update_available）
SECURITY_REJECTED: 9
WATCHLIST: 238

ACTION_TYPES:
  new_install: 9
  watch: 1084
  restore_candidate: 3
  update_candidate: 1
  replacement_candidate: 0
  reject: 9
  known_missing_misreported_as_new_install: 0   # v2.11 §十二/§十六：必须为 0（缺失能力不得伪装成新装推荐）

UPDATE_LINEAGE: 3   # 更新项来源=Installed Source Map，不绑同名外部仓
  - installed_canonical_id: aihot
    installed_upstream: Virxact / AI HOT（aihot.virxact.com）
    update_upstream: Virxact / AI HOT（aihot.virxact.com）
    lineage_evidence: SKILL.md frontmatter 直接署名：metadata.author=Virxact、version=1.2.0（文件内作者证据，非『调用其 API』推断）；官方渠道当前版本 v1.7.1 同署名，版本谱系
    lineage_verified: true
  - installed_canonical_id: browseros-neo
    installed_upstream: github.com/browseros-ai/BrowserOS
    update_upstream: browseros-ai/BrowserOS
    lineage_evidence: upstream_repo:browseros-ai/browseros
    lineage_verified: true
  - installed_canonical_id: computer-use-2
    installed_upstream: github.com/stablyai/orca
    update_upstream: github.com/stablyai/orca
    lineage_evidence: 本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08-31）中 skills/computer-use/SKILL
    lineage_verified: true

PROJECT_MATCH_QUALITY:
  matched_candidates: 73   # 至少有一个 matched_project 的候选数
  matched_project_entries: 144   # matched_project 总条数（候选×项目）
  strong_tech_evidence: 121   # 专用技术栈直接命中（Expo/RN/Android/Supabase/Next.js/PWA/Vercel/.NET…）
  positioning_evidence: 15   # 项目定位/功能语义命中
  shared_need_evidence: 13   # 项目自身需求与候选能力命中
  lexical_evidence: 4   # 词面证据（v2.5：独立成立仅限领域短语；词级重叠只作次要加分）
  secondary_tech_only_rejected: 158   # 只靠泛用技术栈（TS/React/Python/Docker…）硬凑、已被拒的候选数
  negated_evidence_rejected: 46   # 被否定窗口/排除语境压制掉的命中次数
  lexical_single_rejected: 1436   # 词面重叠只因单个低区分度词（manager/service…）而不足以成立的次数
  lexical_alone_rejected: 4   # v2.5 §三：词面 boost（≥2 词）想**独立**造匹配、被拒的次数（词面只作次要加分）
  lexical_phrase_direct_evidence: 4   # v2.5 §五：靠人工整理的领域短语独立成立的词面证据条数
  bare_prompt_direct_evidence: 0   # v2.5 §四：裸 prompt 被当直接证据的次数（**必须为 0**）
  tech_words_used_as_lexical_direct_evidence: 0   # v2.5 §四：泛用技术词充当词面直接证据的次数（**必须为 0**）
  unresolved_mismatch_candidates: 414   # 存在未解除平台错配的候选数（只作观察）
  redirect_evidence_rejected: 689   # v2.6 §五：跨 Skill 重定向小句被剪掉的次数
  required_tech_blocked_shared_need: 5   # v2.10 §八：required_tech 与项目不兼容 → shared_need 单独不造项目匹配的次数
  same_name_only_already_installed: 0   # v2.6 §二：只凭同名判已安装的条数（**必须为 0**）
  wrong_update_lineage: 0   # v2.6 §三：血缘未验证的 update_available（**必须为 0**）
  same_name_unverified_candidates: 6   # 同名但血缘未确认（最高 watch，等人工确认）
  gcp_alias_missed: 0   # v2.6 §四：描述含 GCP 产品别名却未标 gcp 域的条数（**必须为 0**）
  product_internal_unresolved_candidates: 2   # v2.6 §十：未解除的产品自研 Skill 数
  product_specific_scope_unresolved: 69   # v2.7 §七：未解除的产品专项 platform_operation 数（GA Admin / SecOps / anthropic-brand…）
  determinism: hashseed_matrix（0/1/2/3/42/123）已由 tests/test_pipeline.py::test_v27_determinism_hashseed 作为硬门   # v2.7 §二
  note: 四个 *_evidence 是「候选×项目」条数，同一条可同时具备多种证据；
        所有 projected 条目都必须至少带 1 类直接证据（direct_evidence 非空率 100%，仅作完整性自检，不作 KPI）

PROJECT_CONTEXT_HEALTH:
  conflict_count: 1   # v2.11 §四：描述 ↔ 技术栈互相矛盾的项目数（外部层不修改输入 A，只标记）
  - project: yejian-buguangdeng
    reason: description-tech mismatch
    description_tech: expo/react-native
    missing_tech: expo/react-native
    declared_tech: nextjs/pwa
    suppressed_strong_tech: PWA/Next.js   # 冲突解决前不得凭这些造 strong_tech 匹配
  conflict_strong_tech_suppressed: 8   # 候选×项目 被抑制的冲突 strong_tech 证据次数

PERSONALIZED_TOP30:
  target_limit: 30
  actual_count: 16   # 不足 target 时输出实际数量，不塞 ignore/reject 补数量
  min_score: 50
  functional_duplicates: 1   # 跨仓同功能族被折叠进 alternatives 的条目数（§三）
  t3_uncorroborated: 23   # T3/discovery_only 无 T1·T2·官方交叉佐证，挡在 Top 外（只留 WATCHLIST）
  alternative_families: 1
  contains_ignore: no
  contains_reject: no
  generated: yes
  high_match_count: 9
  matched_projects_coverage: 16/90   # 高匹配候选中答出具体项目名的比例（准确率优先，不再要求 90%+）
  top_candidates_with_unresolved_mismatch: 0   # §九：必须为 0
  mismatch_blocked_from_top: 6   # 因未解除平台错配被挡在 Top 外（仍留 WATCHLIST）
  top_candidates_with_unresolved_product_scope: 0   # v2.6 §十：必须为 0（第五道门）
  scope_blocked_from_top: 19   # 因未解除 product_internal 被挡在 Top 外（可解除，非黑名单）
  top_candidates_supporting_only: 0   # v2.8 §十四：Top 内仅有 supporting/mention 级核心证据的条数（**必须为 0**）
  core_evidence_blocked_from_top: 109   # 因缺核心需求证据被挡在 Top 外（仍留 WATCHLIST）
  top_candidates_strong_saturation: 2   # v2.10 §五：Top 内 strong 饱和族候选数（每条都必须带增量价值）
  top_strong_without_incremental_reason: 0   # v2.10 §十二：strong 饱和但 incremental_over_installed 为空（**必须为 0**）
  saturation_blocked_from_top: 31   # v2.10 §五：strong/medium 饱和且无明确增量 → 挡在 Top 外（可解除，非黑名单）
  frontend_design_strong_top_count: 1   # v2.10 §十一：frontend_design（已装 strong）族在 Top 的条数
  capability_family_quota: strong=1 / medium=2 / weak|none=3   # v2.10 §七
  security_scanned: 1075
  security_unscanned: 31
  security_verdict_pass: 701
  security_verdict_review_required: 365
  security_verdict_block: 9
  deep_scan_complete: 1021   # 真正做了深度静态审查的（= install 候选）
  deep_scan_failed: 0
  deep_scan_pending: 0   # 超预算未扫，fail-closed
  deep_scan_not_required: 55   # 未进安装候选，未触发
  deep_scan_skipped: 30   # 无目录/未扫描
  full_scan_eligible: 1021   # 入队候选（硬 Gate 命中者不入队）
  full_scan_complete: 1021
  full_scan_remaining: 0   # **必须为 0**
  full_scan_gated_out: 54   # 被硬 Gate 挡在队列外
  top10:
    - stablyai/orca/orca-emulator-android | score=79.4 | gap=none | rel=new_capability | risk=low | verdict=pass | rec=install_candidate
    - microsoft/skills/frontend-design-review | score=78.8 | gap=strong | rel=new_capability | risk=low | verdict=pass | rec=watch
    - vercel-labs/agent-skills/react-native-skills | score=58.8 | gap=strong | rel=new_capability | risk=low | verdict=pass | rec=watch
    - github/awesome-copilot/ai-prompt-engineering-safety-review | score=79.6 | gap=weak | rel=new_capability | risk=low | verdict=pass | rec=install_candidate
    - github/awesome-copilot/webapp-testing | score=72.3 | gap=weak | rel=new_capability | risk=low | verdict=pass | rec=install_candidate
    - wshobson/agents/e2e-testing-patterns | score=66.3 | gap=weak | rel=new_capability | risk=low | verdict=pass | rec=install_candidate
    - github/awesome-copilot/dependabot | score=64.6 | gap=weak | rel=new_capability | risk=low | verdict=pass | rec=install_candidate
    - github/awesome-copilot/scoutqa-test | score=64.3 | gap=weak | rel=new_capability | risk=medium | verdict=review_required | rec=install_candidate
    - anthropics/skills/claude-api | score=67 | gap=strong | rel=new_capability | risk=medium | verdict=review_required | rec=watch
    - wshobson/agents/team-composition-patterns | score=60.6 | gap=strong | rel=new_capability | risk=low | verdict=pass | rec=watch

SECURITY_REVIEW_GATE:
  full_scan_complete: 1021   # 本轮真正完成深度静态审查的候选数
  full_scan_eligible: 1021   # 入队候选（硬 Gate 命中者不入队）
  full_scan_queue: 1021   # 队列长度（明细见 data/state/full_scan_queue.json）
  full_scan_remaining: 0   # **必须为 0**（不得只报计划）
  product_internal_unresolved: 0
  product_internal_blocked: 54   # 被硬 Gate 挡在队列外
  product_internal_block_breakdown:
    project_scope_section_not_required: 30   # §四.11 即使为 0 也必须输出
    developer_tool_gate_unresolved: 24   # scope unresolved / mcp-only / 主目标未解决
    competitor_block: 1   # 未解决竞品关系
  resolved_remaining_count: 0   # 被挡但已具备解除证据（可复核后放行）的条数
  completed_at: 2026-09-24
V29_FINAL_AUDIT:
  competitor_unresolved_in_top: 0   # **必须为 0**（§四.11）
  competitor_unresolved_full_scan: 0   # **必须为 0**
  product_name_false_positive_remaining: 0   # 名字含品牌词却被 Gate 挡的残留（**必须为 0**）
  product_internal_unresolved_pool_count: 30   # v2.11 §八：全池未解除计数（**允许 >0**，可合法留池等待解除）
  product_internal_in_full_scan_count: 0   # 深度审查队列内残留（**必须为 0**）
  product_internal_in_top_count: 0   # Top 内残留（**必须为 0**，build_context 现算）
  internal_capability_in_full_scan_count: 0   # 队列内残留的产品内部能力（**必须为 0**）
  scope_unresolved_in_top: 0   # **必须为 0**
  top_candidates_with_unresolved_mismatch: 0   # §九/§三.5：必须为 0（只算产品/平台领域）

DAILY_DELTA:   # 与昨日快照相比；Top30 无变化时不要重复输出同样内容
  first_run: no
  changed_total: 0
  snapshot_schema_version: 2
  analysis_engine_version: 11
  system_rebaseline: no   # v2.11 §十：schema/引擎换代本轮重建基线，不冒充上游更新
  NEW: 0
  RISING: 0
  FALLING: 0
  UPDATED: 0
  SECURITY_CHANGED: 0
  SOURCE_CHANGED: 0
  MATCH_CHANGED: 0
  ALREADY_INSTALLED: 0
  NO_LONGER_RELEVANT: 0
  METADATA_ENRICHED: 0
  RECALCULATED: 0
  SYSTEM_REBASELINE: 0
```

## 0. 今日 Delta（0 项变化 · 按变化数排序）

- 今日无变化：候选池与昨日一致 —— **日报不要重复输出同样内容**。

## 1. 今日重点：**无**（Top30 与昨日一致，不重复输出）

> 日报请只报告下方 `DAILY_DELTA` 的变化；候选池无变化时不要重复罗列同样的 Skill。

> 需要完整清单时看第 2 节 Top30 表或 `data/SKILL_CANDIDATES.json`。

## 1B. 恢复 / 修复（1 条 · 已有能力的恢复路线，不是外部新发现的 Skill）

- `stablyai/orca/computer-use` action_type=**restore_candidate**（recommendation=watch；中分 52.0：值得关注，需人工判断（未命中项目需求；仅作观察））

> 日报引擎必须把本节单独渲染为「恢复 / 修复」，不得表述成「推荐安装一个全新的 Skill」（v2.11 §十二）。

## 2. Personalized Top（target_limit 30 · 实际 16）

> 定义 = **值得用户看的候选**：只含 `install_candidate` / `watch`，**不含 ignore / reject**；且必须按 v2.10 §十四 的固定顺序同时过十道门（1 Security → 2 validity/lineage → 3 产品/领域 scope → 4 primary 核心需求证据 → 5 required-tech 兼容 → 6 能力饱和 → 7 已装重复/增量价值 → 8 分数阈值 → 9 功能族折叠 → 10 能力族配额）：① score ≥ 50（配置化最低阈值）② 有真实个性化证据（命中需求 / 能力缺口 / 更新 / 恢复）③ T3·discovery_only 来源需有 T1·T2·官方交叉佐证④ **无未解除的平台错配**（Azure / AWS / GCP / .NET / Microsoft Store 等：项目档案里没有项目用该平台 → 只留 WATCHLIST，不占个人 Top）⑤ **无未解除的 product_internal**（v2.6 §十：产品自研/维护 Skill —— 如 BrowserOS test-ui —— 只有用户项目真的在做这个产品才进 Top)⑥ **v2.9 §二/§三/§四**：无未解决竞品关系、非产品自身内部能力、领域三态不为「信息不足 / 不适用」——**名字含 Claude/Codex/Copilot/Gemini 本身不构成这道门**。⑦ **v2.10 §五/§六/§七**：能力族 saturated=strong 默认 watchlist，除非有 CLEAR_INCREMENTAL_VALUE（update / availability degraded / 明确新子能力 / 未覆盖的项目专用技术路线）；strong 族 Top 最多 1 条代表项。符合标准的不足 30 个时就输出实际数量，**不为凑数塞低质量 watch**。

> 跨仓库**同功能族**只展示一条 PRIMARY（§三）：如 `github/awesome-copilot/webapp-testing` 与 `anthropics/skills/webapp-testing` 只出一条，其余进下方 ALTERNATIVES。

| # | Skill | owner/repo | 分 | 缺口 | 饱和 | 关系 | verdict | 最匹配项目 | 产品关系与领域状态 | 推荐 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | orca-emulator-android | stablyai/orca | 79.4 | none | none | new_capability | pass | landedazi-android（50） | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | install_candidate |
| 2 | frontend-design-review | microsoft/skills | 78.8 | strong | strong | new_capability | pass | a-share-index-valuation-report（32） | 产品关系=无 | watch |
| 3 | react-native-skills | vercel-labs/agent-skills | 58.8 | strong | none | new_capability | pass | protein-calculator（52） | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | watch |
| 4 | ai-prompt-engineering-safety-review | github/awesome-copilot | 79.6 | weak | weak | new_capability | pass | — | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | install_candidate |
| 5 | webapp-testing | github/awesome-copilot | 72.3 | weak | weak | new_capability | pass | — | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | install_candidate |
| 6 | e2e-testing-patterns | wshobson/agents | 66.3 | weak | weak | new_capability | pass | — | 产品关系=无 | install_candidate |
| 7 | dependabot | github/awesome-copilot | 64.6 | weak | weak | new_capability | pass | — | 产品关系=github/developer_tool；项目分区=项目核心业务能力；置信度=high；领域状态=applicable；适用证据=ai-coding-agent/github-devops；解除=github-copilot | install_candidate |
| 8 | scoutqa-test | github/awesome-copilot | 64.3 | weak | weak | new_capability | review_required | — | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | install_candidate |
| 9 | claude-api | anthropics/skills | 67 | strong | none | new_capability | review_required | — | 产品关系=anthropic-api/developer_tool；项目分区=—；置信度=low；领域状态=applicable；适用证据=anthropic-assistants | watch |
| 10 | team-composition-patterns | wshobson/agents | 60.6 | strong | none | new_capability | pass | — | 产品关系=无 | watch |
| 11 | prompt-engineering-patterns | wshobson/agents | 56.6 | strong | none | new_capability | pass | — | 产品关系=无 | watch |
| 12 | parallel-feature-development | wshobson/agents | 56.6 | strong | none | new_capability | pass | — | 产品关系=无 | watch |
| 13 | react-best-practices | vercel-labs/agent-skills | 53.0 | strong | strong | new_capability | pass | party-night-v1-2（30） | 产品关系=vercel/developer_tool；项目分区=项目核心业务能力；置信度=high；领域状态=applicable；适用证据=vercel-hosting | watch |
| 14 | react-view-transitions | vercel-labs/agent-skills | 53.0 | strong | none | new_capability | pass | party-night-v1-2（30） | 产品关系=无 | watch |
| 15 | computer-use | stablyai/orca | 52.0 | weak | weak | replacement_candidate | pass | DeepSeekBalanceWidget-Mac（20） | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | watch |
| 16 | canvas-design | anthropics/skills | 53 | none | none | new_capability | pass | — | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate | watch |

> 安装候选 ≠ 自动安装；任何 Skill 的安装都需用户在 Skill Manager 中人工执行，并另行安全复核。

### 2.1 ALTERNATIVES（同功能族的其他上游 · 不重复推荐）

> 候选池按 `owner/repo/skill` 各自独立记账；这里只做**展示层折叠**（§八）：同一功能族选一条 PRIMARY，其余列在此处备查。

| PRIMARY | 同功能来源 | 折叠依据 |
|---|---|---|
| `github/awesome-copilot/webapp-testing` | `anthropics/skills/webapp-testing`（anthropics/skills，score=71.3） | 同名同功能 |

- Top 内跨仓同功能族折叠：**1** 条；T3 无交叉佐证被挡在 Top 外：**23** 条（仍留在 WATCHLIST）。

## 3. 安全拒绝清单（SECURITY_REJECTED，Gate 优先于分数）

> v2.2 起只有 **block 级**（真要求执行的高危行为）才 reject；文档讨论 `.env`/`sudo`、示例引用 token 等属 `review_required`，不再误伤。

| Skill | owner/repo | verdict | 阻断规则 |
|---|---|---|---|
| aspire | github/awesome-copilot | block | pipe_to_shell |
| azure-container-registry-cli | github/awesome-copilot | block | pipe_to_shell |
| azure-devops-cli | github/awesome-copilot | block | pipe_to_shell |
| developing-genkit-dart | google/skills | block | pipe_to_shell |
| developing-genkit-go | google/skills | block | pipe_to_shell |
| hf-cli | huggingface/skills | block | pipe_to_shell |
| linkerd-patterns | wshobson/agents | block | pipe_to_shell |
| gitops-workflow | wshobson/agents | block | pipe_to_shell |
| uv-package-manager | wshobson/agents | block | pipe_to_shell |

## 4. 能力缺口候选（按缺口优先级）

当前焦点能力（读取已装侧 CAPABILITY_SUPPRESSION + CAPABILITY_AVAILABILITY 动态派生）：

| 能力 | 覆盖 | 可用性 | 优先级 |
|---|---|---|---|
| computer_use | strong | degraded | recovery |
| orca_integration | strong | degraded | recovery |
| docx_xlsx | weak | ok | medium |
| macos | weak | ok | medium |
| mcp_dev | weak | ok | medium |
| security_audit | weak | ok | medium |
| supabase_db | weak | ok | medium |
| testing_qa | weak | ok | medium |
| windows | weak | ok | medium |
| data_analytics | none | ok | high |
| image_creative | none | ok | high |
| mobile_qa | none | ok | high |

- 命中 none/weak 缺口的候选：**125** 个（完整清单见 SKILL_CANDIDATES.json）

## 5. 更新候选与恢复候选

**已装但版本落后（v2.6 §三：更新项由 Installed Source Map 的血缘驱动，不再从候选池找同名对象冒充上游）**

| installed_canonical_id | installed_upstream | update_upstream | 血缘已验证 | 依据 |
|---|---|---|---|---|
| `aihot` | Virxact / AI HOT（aihot.virxact.com） | Virxact / AI HOT（aihot.virxact.com） | 是 | SKILL.md frontmatter 直接署名：metadata.author=Virxact、version=1.2.0（文件内作者证据，非『调用其 AP |
| `browseros-neo` | github.com/browseros-ai/BrowserOS | browseros-ai/BrowserOS | 是 | upstream_repo:browseros-ai/browseros |
| `computer-use-2` | github.com/stablyai/orca | github.com/stablyai/orca | 是 | 本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08- |

**恢复/替换候选（replacement_candidate）**

| Skill | owner/repo | 对应已装/已知 | 分数 | 上游 | 依据 |
|---|---|---|---|---|---|
| computer-use | stablyai/orca | computer-use | 52.0 | active | 对应 canonical `computer-use` 当前不在本机安装集（known_missing）且血缘确认（upstream_repo:stablyai/orca，来源档案在案：github.com/stably |
| orca-cli | stablyai/orca | orca-cli | 48 | active | 对应 canonical `orca-cli` 当前不在本机安装集（known_missing）且血缘确认（upstream_repo:stablyai/orca，来源档案在案：github.com/stablyai/o |
| orchestration | stablyai/orca | orchestration | 48 | active | 对应 canonical `orchestration` 当前不在本机安装集（known_missing）且血缘确认（upstream_repo:stablyai/orca，来源档案在案：github.com/stabl |

