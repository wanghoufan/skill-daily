# 候选池精简对照件（External Skill Intelligence v2.11）

> 数据基线：2026-09-24｜源文件 `SKILL_CANDIDATES.json`（1106 条）
> 本件是**给审查者看得完的切片视图**，用于核对；完整数据与全部字段以 JSON 为准。
> 只做发现与评估：**不安装、不删除、不升级任何 Skill**；排名/安装量只是 adoption signal，不等于推荐。

## 一、总览

| 项目 | 数值 |
|---|---|
| 来源注册表 | 17 源（T0 2 / T1 9 / T2 3 / T3 3）|
| 候选（raw → 合法池） | 1170 → 1106 |
| 数据质量 Gate | 剔除构建产物 67 条 / 非法 skill 名 1 条 |
| bottom-up 硬门 | 共 41 条搜索结果 → 过 SKILL.md 硬门 17 / 隔离 23 |
| 推荐分布 | ignore 850 / install_candidate 9 / reject 9 / watch 238 |
| 与已装关系 | already_installed 8 / complement 2 / new_capability 1078 / overlap 9 / replacement_candidate 3 / same_name_different_source 2 / same_name_unverified 4 |
| 安全风险 | high 9 / low 701 / medium 365 / unknown 31（已静态审查 1075）|
| 安全 verdict | pass 701 / review_required 365 / block 9 / unscanned 31 |
| 深度静态审查 | complete 1021（= install 候选） / failed 0 / pending 0 / not_required 55 / skipped 30 |
| 能力缺口 | none 28 / strong 981 / weak 97 |
| 命中项目需求 / 平台错配 | 186 / 400 |
| matched_projects 覆盖（高匹配候选） | 16/90 (18%) —— **v2.3 起不再是 KPI**，只作参考 |
| matched_project 直接证据完整性 | 144/144 —— 每条匹配都必须带 1 类直接证据（完整性自检，**不是**质量 KPI）|
| update_available / replacement_candidate | 1 / 3 |

> **v2.4 §十：`direct evidence` 的「字段非空率」不再作为精度指标。**
> 字段非空只能证明写了；能不能证明「证据真的有效」，要看下面的分项计数：

| PROJECT_MATCH_QUALITY | 数值 | 含义 |
|---|---|---|
| matched_candidates | 73 | 至少有一个 matched_project 的候选数 |
| strong_tech_evidence | 121 | 专用技术栈直接命中（Expo / RN / Android / Supabase / Next.js / PWA / Vercel / .NET…）|
| positioning_evidence | 15 | 项目定位/功能语义命中 |
| shared_need_evidence | 13 | 项目自身需求与候选能力命中 |
| lexical_evidence | 4 | 词面证据（v2.5：独立成立仅限**领域短语**；词级重叠只作次要加分，泛词与裸 prompt 全禁）|
| **secondary_tech_only_rejected** | 158 | **只**靠泛用技术栈（TS / React / Python / Docker…）硬凑、已被拒的候选数 |
| **negated_evidence_rejected** | 46 | 被否定窗口 / 排除语境压掉的命中次数（看得见门在工作）|
| lexical_single_rejected | 1436 | 词面重叠只因单个低区分度词（manager / service…）而不足以成立的次数 |
| lexical_alone_rejected | 4 | v2.5 §三：词面 boost 想**独立**造匹配、被拒的次数（词面只作次要加分）|
| lexical_phrase_direct_evidence | 4 | v2.5 §五：靠人工整理的领域短语独立成立的词面直接证据条数 |
| **bare_prompt_direct_evidence** | 0 | v2.5 §四：裸 prompt 被当直接证据的次数 —— **必须为 0** |
| **tech_words_used_as_lexical_direct_evidence** | 0 | v2.5 §四：泛用技术词（react / native / typescript / api…）充当词面直接证据的次数 —— **必须为 0** |
| unresolved_mismatch_candidates | 414 | 存在未解除平台错配的候选数（只作观察）|
| redirect_evidence_rejected | 689 | v2.6 §五：跨 Skill 重定向小句（For X, use other-skill）被剪掉的次数 |
| **same_name_only_already_installed** | 0 | v2.6 §二：只凭同名判已安装的条数 —— **必须为 0** |
| **wrong_update_lineage** | 0 | v2.6 §三：血缘未验证的 update_available —— **必须为 0** |
| **gcp_alias_missed** | 0 | v2.6 §四：含 GCP 产品别名却未标 gcp 域 —— **必须为 0** |
| same_name_unverified_candidates | 6 | 同名但血缘未确认（最高 watch，等人工确认，不算已装/更新/替换）|
| product_internal_unresolved_candidates | 2 | v2.6 §十：未解除的产品自研 Skill 数（第五道门挡在 Top 外，可解除非黑名单）|
| product_specific_scope_unresolved | 69 | v2.7 §七：未解除的产品专项 platform_operation（GA Admin / SecOps / anthropic-brand…）|

> 四个 `*_evidence` 是**「候选 × 项目」条数**，同一条可同时具备多种证据；所有 matched_project 都必须至少带 1 类直接证据。**准确率优先于 coverage：matched_projects 下降完全可以接受。**

> **v2.3 的口径变化**：`candidate 数量` / `matched_projects 覆盖率` / `Top30 是否凑满` 这三项**不再是目标**；准确率优先。Top 里出现空位比塞垃圾好。

## 二、Personalized Top（target_limit 30 · 实际 16）

选取规则（与日报完全一致，复用同一函数 `select_top`）：① score ≥ **50**（配置化最低阈值）② 有真实个性化证据（matched need / capability gap / update / replacement 至少一个成立）③ T3/discovery_only 需有 T1·T2·官方交叉佐证 ④ **无未解除的平台错配**（v2.4 §九：项目档案里没有任何项目用该平台 → 不进 Top；v2.6 §四 GCP 产品别名补齐后，Cloud Run / Agent Platform / Microsoft Store 专项都走这道门）⑤ **无未解除的 product_internal**（v2.6 §十第五道门：产品自研 Skill —— 如 BrowserOS test-ui —— 只有项目真的在做该产品才进 Top）⑥ recommendation ≥ watch ⑦ 分数；多样性最后执行：同仓库上限 3 条 + **跨仓同功能族折叠**。

> **只含 `install_candidate` / `watch`，不含 `ignore` / `reject`**；符合标准的不足 30 个时就输出实际数量，**不为凑数塞垃圾**。

> 本轮被三道质量门挡下的：低分（< 50）若干 / 无个性化证据若干 / T3 无交叉佐证 **23** 条（仍留在 WATCHLIST）。跨仓同功能族折叠 **1** 条（见 2.1）。

「安全」列的口径：`pass` = 静态审查无发现；`review_required` = 有语境性提及，需人工看一眼；
`block` = 高风险行为，已 reject；`unscanned` = 超出抓取预算，**最高只能是 watch**。
`T—` 表示来源未经验证（bottom-up 搜索结果），不参与安装推荐。

| # | 分数 | 推荐 | canonical_key | 来源 | 命中需求 | 最匹配项目 | 缺口 | 饱和 | 安全 | 产品关系 / 项目分区 / 领域状态 / 解除证据 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 79.4 | install_candidate | `stablyai/orca/orca-emulator-android` | T1 stablyai/orca | android | landedazi-android(50) | none | none | pass | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |
| 2 | 78.8 | watch | `microsoft/skills/frontend-design-review` | T1 microsoft/skills | frontend-design, responsive | a-share-index-valuation-report(32) | strong | strong | pass | 产品关系=无 |
| 3 | 58.8 | watch | `vercel-labs/agent-skills/react-native-skills` | T1 vercel-labs/agent-skills | expo-rn | protein-calculator(52)；stretch-side-timer-project(52) | strong | none | pass | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |
| 4 | 79.6 | install_candidate | `github/awesome-copilot/ai-prompt-engineering-safety-review` | T1 github/awesome-copilot | agent-governance | — | weak | weak | pass | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |
| 5 | 72.3 | install_candidate | `github/awesome-copilot/webapp-testing` | T1 github/awesome-copilot | browser-qa | — | weak | weak | pass | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |
| 6 | 66.3 | install_candidate | `wshobson/agents/e2e-testing-patterns` | T2 wshobson/agents | browser-qa | — | weak | weak | pass | 产品关系=无 |
| 7 | 64.6 | install_candidate | `github/awesome-copilot/dependabot` | T1 github/awesome-copilot | github-auto | — | weak | weak | pass | 产品关系=github/developer_tool；项目分区=项目核心业务能力；置信度=high；领域状态=applicable；适用证据=ai-coding-agent/github-devops；解除=github-copilot |
| 8 | 64.3 | install_candidate | `github/awesome-copilot/scoutqa-test` | T1 github/awesome-copilot | browser-qa | — | weak | weak | review_required | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |
| 9 | 67.0 | watch | `anthropics/skills/claude-api` | T1 anthropics/skills | agent-governance, llm-api | — | strong | none | review_required | 产品关系=anthropic-api/developer_tool；项目分区=—；置信度=low；领域状态=applicable；适用证据=anthropic-assistants |
| 10 | 60.6 | watch | `wshobson/agents/team-composition-patterns` | T2 wshobson/agents | agent-governance | — | strong | none | pass | 产品关系=无 |
| 11 | 56.6 | watch | `wshobson/agents/prompt-engineering-patterns` | T2 wshobson/agents | agent-governance | — | strong | none | pass | 产品关系=无 |
| 12 | 56.6 | watch | `wshobson/agents/parallel-feature-development` | T2 wshobson/agents | agent-governance | — | strong | none | pass | 产品关系=无 |
| 13 | 53.0 | watch | `vercel-labs/agent-skills/react-best-practices` | T1 vercel-labs/agent-skills | — | party-night-v1-2(30)；prompt-manager(30) | strong | strong | pass | 产品关系=vercel/developer_tool；项目分区=项目核心业务能力；置信度=high；领域状态=applicable；适用证据=vercel-hosting |
| 14 | 53.0 | watch | `vercel-labs/agent-skills/react-view-transitions` | T1 vercel-labs/agent-skills | — | party-night-v1-2(30)；prompt-manager(30) | strong | none | pass | 产品关系=无 |
| 15 | 52.0 | watch | `stablyai/orca/computer-use` | T1 stablyai/orca | — | DeepSeekBalanceWidget-Mac(20) | weak | weak | pass | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |
| 16 | 53.0 | watch | `anthropics/skills/canvas-design` | T1 anthropics/skills | — | — | none | none | pass | 产品关系=仅名称/描述提及(mentioned)，不构成 Gate |

仓库分布：6 个仓库承载 16 条 → `github/awesome-copilot`×4、`wshobson/agents`×4、`vercel-labs/agent-skills`×3、`stablyai/orca`×2、`anthropics/skills`×2。

### 2.0 PERSONALIZED_REASON（v2.10 §十二：16 条逐条给强理由）

规则：每条 Top 至少一条非空强理由；已装能力 saturated=strong 的候选，`incremental_over_installed` **必须非空**（否则它根本进不了 Top）。

| canonical_key | 补什么缺口 | 匹配项目 | 比已装强在哪 | 为什么是现在 |
|---|---|---|---|---|
| `stablyai/orca/orca-emulator-android` | 能力族 mobile_qa 当前饱和=none，优先补齐 | landedazi-android（match=50，直接证据：strong_tech） | 项目专用技术路线直接命中：landedazi-android（现有已装强能力不覆盖该技术/平台组合） | 真实缺口（饱和=none），当前池内该族最优路线 |
| `microsoft/skills/frontend-design-review` | 命中需求（primary 证据）：frontend-design/responsive | a-share-index-valuation-report（match=32，直接证据：shared_need） | 新增子能力 accessibility_audit（该族已装成员完整 SKILL.md 均已读取且未提及= confirmed_absent） | 当前活跃项目直接命中 |
| `vercel-labs/agent-skills/react-native-skills` | 命中需求（primary 证据）：expo-rn | protein-calculator（match=52，直接证据：strong_tech） | 项目专用技术路线直接命中：protein-calculator（现有已装强能力不覆盖该技术/平台组合） | 真实缺口（饱和=none），当前池内该族最优路线 |
| `github/awesome-copilot/ai-prompt-engineering-safety-review` | 能力族 security_audit 当前饱和=weak，优先补齐 | — | — | 真实缺口（饱和=weak），当前池内该族最优路线 |
| `github/awesome-copilot/webapp-testing` | 能力族 testing_qa 当前饱和=weak，优先补齐 | — | — | 真实缺口（饱和=weak），当前池内该族最优路线 |
| `wshobson/agents/e2e-testing-patterns` | 能力族 testing_qa 当前饱和=weak，优先补齐 | — | — | 真实缺口（饱和=weak），当前池内该族最优路线 |
| `github/awesome-copilot/dependabot` | 能力族 security_audit 当前饱和=weak，优先补齐 | — | — | 真实缺口（饱和=weak），当前池内该族最优路线 |
| `github/awesome-copilot/scoutqa-test` | 能力族 testing_qa 当前饱和=weak，优先补齐 | — | — | 真实缺口（饱和=weak），当前池内该族最优路线 |
| `anthropics/skills/claude-api` | 命中需求（primary 证据）：agent-governance/llm-api | — | — | 真实缺口（饱和=none），当前池内该族最优路线 |
| `wshobson/agents/team-composition-patterns` | 命中需求（primary 证据）：agent-governance | — | — | 真实缺口（饱和=none），当前池内该族最优路线 |
| `wshobson/agents/prompt-engineering-patterns` | 命中需求（primary 证据）：agent-governance | — | — | 真实缺口（饱和=none），当前池内该族最优路线 |
| `wshobson/agents/parallel-feature-development` | 命中需求（primary 证据）：agent-governance | — | — | 真实缺口（饱和=none），当前池内该族最优路线 |
| `vercel-labs/agent-skills/react-best-practices` | — | party-night-v1-2（match=30，直接证据：strong_tech） | 项目专用技术路线直接命中：party-night-v1-2（现有已装强能力不覆盖该技术/平台组合） | 当前活跃项目直接命中 |
| `vercel-labs/agent-skills/react-view-transitions` | — | party-night-v1-2（match=30，直接证据：strong_tech） | 项目专用技术路线直接命中：party-night-v1-2（现有已装强能力不覆盖该技术/平台组合） | 真实缺口（饱和=none），当前池内该族最优路线 |
| `stablyai/orca/computer-use` | 能力族 windows 当前饱和=weak，优先补齐 | DeepSeekBalanceWidget-Mac（match=20，直接证据：strong_tech） | 可作为现有已装 Skill 的替代/升级；项目专用技术路线直接命中：DeepSeekBalanceWidget-Mac（现有已装强能力不覆盖该技术/平台组合） | 真实缺口（饱和=weak），当前池内该族最优路线 |
| `anthropics/skills/canvas-design` | 能力族 image_creative 当前饱和=none，优先补齐 | — | — | 真实缺口（饱和=none），当前池内该族最优路线 |

### 2.1 FUNCTIONAL_CLUSTER —— ALTERNATIVES（1 个功能族有备选）

候选池按 `owner/repo/skill` **保持独立记录**（不合并、不丢数据）；但 **Top 展示** 只出 PRIMARY —— 同一个功能族不连续推荐两个几乎一样的 Skill。
判定同族（满足其一即可）：normalized skill name 相同（≥5 字符）/ description jaccard ≥ 0.62 且名称同前缀 / content fingerprint 相同。
备选项**仍然完整保留在 `SKILL_CANDIDATES.json`**，此处只是不重复占版面。

| PRIMARY（Top 内） | 被折叠的同族备选 | 判同族依据 |
|---|---|---|
| `github/awesome-copilot/webapp-testing` | `anthropics/skills/webapp-testing`（71.3） | 同名同功能 |

## 三、安全清单（Security Gate v2.4 · 沿用 v2.2 语境判定）

核心区分：**「提到危险行为」≠「真的要求执行危险行为」**。每条 finding 带 `confidence` 与 `behavior_context`（mention / instruction / executable / remote_execution / **warning**），verdict 四值 `pass / review_required / block / unscanned`。

> **v2.3 §四 修正**：`always_block` 规则不再「命中即 block」。`destructive_rm_root` / `pipe_to_shell` 等只有在**非警示语境**下才 block；`warning` 语境（`never ...` / `do not ...` / `禁止 ...` / `不要 ...` / 安全审计文档举反例）一律降为 `review_required`。

总体：pass 701 / review_required 365 / block 9 / unscanned 31

### 3.1 block 级阻断（reject，9 条）

仅限高置信、**真会被执行**的高危行为：远程内容 pipe 进 shell/解释器、`rm -rf ~/` 或 `/`、凭据读取后外发、混淆 payload 执行等。官方来源**不豁免**。警示/反例语境不在此列。

| canonical_key | 来源 | 阻断规则 | 证据 |
|---|---|---|---|
| `github/awesome-copilot/aspire` | T1 | pipe_to_shell | `curl -sSL https://aspire.dev/install.sh | bash` |
| `github/awesome-copilot/azure-container-registry-cli` | T1 | pipe_to_shell | `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash` |
| `github/awesome-copilot/azure-devops-cli` | T1 | pipe_to_shell | `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash` |
| `google/skills/developing-genkit-dart` | T1 | pipe_to_shell | `curl -sL cli.genkit.dev | bash` |
| `google/skills/developing-genkit-go` | T1 | pipe_to_shell | `curl -sL cli.genkit.dev | bash` |
| `huggingface/skills/hf-cli` | T1 | pipe_to_shell | `curl -LsSf https://hf.co/cli/install.sh | bash` |
| `wshobson/agents/linkerd-patterns` | T2 | pipe_to_shell | `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install |` |
| `wshobson/agents/gitops-workflow` | T2 | pipe_to_shell | `curl -s https://fluxcd.io/install.sh | sudo bash` |
| `wshobson/agents/uv-package-manager` | T2 | pipe_to_shell | `curl -LsSf https://astral.sh/uv/install.sh | sh` |

### 3.2 review_required 需人工复核（365 条；其中 0 条被挡在安装候选之外）

口径：属于敏感行为但**语境上只是提及/解释/示例/警示**，或虽有指令语境但危险度不足 —— 一律不 reject，交人工判断。其中 `behavior_context` 为 instruction/executable 的高敏感项会被挡在 `install_candidate` 之外（最高 watch）；`warning` 语境（安全文档举反例）不挡安装、也不 block。

| canonical_key | 来源 | 是否挡安装 | 命中规则 |
|---|---|---|---|
| `anthropics/skills/claude-api` | T1 | 否（语境性提及） | credential_files,network_generic |
| `anthropics/skills/docx` | T1 | 否（语境性提及） | bundled_scripts |
| `anthropics/skills/mcp-builder` | T1 | 否（语境性提及） | credential_files,network_generic |
| `anthropics/skills/webapp-testing` | T1 | 否（语境性提及） | bundled_scripts |
| `anthropics/skills/xlsx` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/agent-governance` | T1 | 否（语境性提及） | network_generic,sudo |
| `github/awesome-copilot/agent-owasp-compliance` | T1 | 否（语境性提及） | dynamic_code |
| `github/awesome-copilot/containerize-aspnet-framework` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/containerize-aspnetcore` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/convert-excel-to-md` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/github-actions-hardening` | T1 | 否（语境性提及） | credential_files |
| `github/awesome-copilot/github-issues` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/mcp-implementation-security-review` | T1 | 否（语境性提及） | credential_files,dynamic_code,network_generic,postinstall_hook |
| `github/awesome-copilot/mcp-security-audit` | T1 | 否（语境性提及） | credential_files,network_generic |
| `github/awesome-copilot/md-to-docx` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/publish-to-pages` | T1 | 否（语境性提及） | bundled_scripts,git_push_auto,network_generic |
| `github/awesome-copilot/scoutqa-test` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/secret-scanning` | T1 | 否（语境性提及） | git_push_auto |
| `github/awesome-copilot/security-review` | T1 | 否（语境性提及） | credential_files |
| `github/awesome-copilot/test-gap-audit` | T1 | 否（语境性提及） | bundled_scripts |
| `vercel-labs/agent-skills/web-design-guidelines` | T1 | 否（语境性提及） | network_generic |
| `google/skills/google-ads-api-mcp-setup` | T1 | 否（语境性提及） | network_generic,sudo |
| `google/skills/cloud-monitoring-chart-generation` | T1 | 否（语境性提及） | bundled_scripts |
| `google/skills/gemini-agents-api` | T1 | 否（语境性提及） | network_generic |
| `google/skills/gemini-api` | T1 | 否（语境性提及） | credential_files |
| `google/skills/gemini-live-api` | T1 | 否（语境性提及） | sudo |
| `google/skills/google-cloud-solution-agentic-analytics-spark-knowledge-catalog` | T1 | 否（语境性提及） | network_generic |
| `google/skills/google-cloud-solution-multi-agent-security` | T1 | 否（语境性提及） | bundled_scripts,network_generic |
| `browseros-ai/browseros/test-ui` | T1 | 否（语境性提及） | bundled_scripts,network_generic |
| `microsoft/skills/azure-speech-to-text-rest-py` | T1 | 否（语境性提及） | credential_files |
| `microsoft/skills/mcp-builder` | T1 | 否（语境性提及） | credential_files,network_generic |
| `obra/superpowers/subagent-driven-development` | T2 | 否（语境性提及） | bundled_scripts |
| `wshobson/agents/web3-testing` | T2 | 否（语境性提及） | credential_files |
| `wshobson/agents/github-actions-templates` | T2 | 否（语境性提及） | credential_files |
| `wshobson/agents/secrets-management` | T2 | 否（语境性提及） | credential_files,network_generic |
| `wshobson/agents/react-native-architecture` | T2 | 否（语境性提及） | network_generic |
| `wshobson/agents/javascript-testing-patterns` | T2 | 否（语境性提及） | credential_files,network_generic |
| `wshobson/agents/python-testing-patterns` | T2 | 否（语境性提及） | network_generic |
| `wshobson/agents/sast-configuration` | T2 | 否（语境性提及） | bundled_scripts |
| `voidmatcha/e2e-skills/e2e-reviewer` | TNone | 否（语境性提及） | bundled_scripts |

### 3.3 install 候选的两阶段审查（PASS 2）

带 `scripts/` 的候选不能只打一个 `bundled_scripts=low` 就放行：进入 `install_candidate` 的候选会额外静态读取该 Skill 目录下的 `.py/.sh/.js/.ts/.mjs/.cjs/.ps1` 与 `package.json` 的 `postinstall`/`preinstall`。**只做静态读取，绝不执行脚本。**

深度审查状态分布：complete 1021 / failed 0 / pending 0 / not_required 55 / skipped 30；`install_candidate` 必须先满足 `deep_scan_status = complete` 且无 block 级 finding。

## 四、更新候选（update_available，1 条）

| canonical_key | 外部最新 | 上游活跃度 | 说明 |
|---|---|---|---|
| `browseros-ai/browseros/browseros-neo` | — | active | 已装但 version_status=outdated_version（上游 active）→ 属更新候选，不重复推荐安装，仅在 UPDAT |

### 4.0 UPDATE_LINEAGE（更新项血缘核对，3 条）

更新检查**不再从候选池找同名 Skill 冒充上游**：每条更新项绑定已装 Source Map 的 upstream；`installed_upstream` 与 `update_upstream` 不一致时必须有线缘证据，否则拒绝关联（Khazix aihot 事故）。候选池无同血缘候选时，更新来源直接取 Source Map 的 upstream 证据。

| installed_canonical_id | installed_upstream | update_upstream | 血缘已验证 | 依据 |
|---|---|---|---|---|
| `aihot` | Virxact / AI HOT（aihot.virxact.com） | Virxact / AI HOT（aihot.virxact.com） | 是 | SKILL.md frontmatter 直接署名：metadata.author=Virxact、version=1.2.0（文件内作者证据，非『调用其 AP |
| `browseros-neo` | github.com/browseros-ai/BrowserOS | browseros-ai/BrowserOS | 是 | upstream_repo:browseros-ai/browseros |
| `computer-use-2` | github.com/stablyai/orca | github.com/stablyai/orca | 是 | 本地目录名为改名副本，但内容未改动：SKILL.md（991f5dcdb2e5）与 stablyai/orca commit b44ef1e5（2026-08- |

### 4.1 恢复/替换候选（replacement_candidate，3 条）

判定口径：已装侧为 `known_missing`（如 Orca 三件套主副本缺失，coverage=strong / availability=degraded），或已装侧 `version_status=outdated_version` 且上游仍活跃。**仅登记候选，不自动安装。**

| canonical_key | 说明 |
|---|---|
| `stablyai/orca/computer-use` | 中分 52.0：值得关注，需人工判断（未命中项目需求；仅作观察） |
| `stablyai/orca/orca-cli` | 中分 48：值得关注，需人工判断（未命中项目需求；仅作观察） |
| `stablyai/orca/orchestration` | 分数 48，但这是产品自身内部能力 / 内部管线（ref:orca+internal_term:orchestration（同句共现）；候选服务于来源产品自身，不是用户通用能力）→ |

## 五、v2.11 修掉的问题（冻结前数据合同与语义一致性收口）

> 对应审查文档《v2.11 冻结前数据合同与语义一致性收口》。v2.10 / v2.9 轮整改全部保留生效（下文 5.0.0-A/B 系列）；本轮 5.0.0.x 为新增。

### 5.0.0 v2.11 本轮口径（§二~§十三 / §十六）

| 项 | 口径 |
|---|---|
| security_audit 四态（§二） | primary=核心任务执行安全审计（security audit / vulnerability assessment / threat modeling / OWASP / SAST / DAST / secret scanning / dependency vulnerability / penetration testing / secure code review…）；「team can be used for security audit」这类可选工作流/示例槽位 = supporting；只提 security/audit = mention |
| spec-driven 语境门（§三） | task breakdown / implementation plan（含中文任务拆解/开发计划/实施计划）只有在开发规格语境（同文出现 spec/requirements/PRD/feature/product/需求…或强短语）才 primary；test/QA/migration task breakdown → supporting（breakdown-test 事故） |
| PROJECT_CONTEXT_CONFLICT（§四/§五） | 描述声明技术 A、tech 列缺 A 却出现互斥 B → conflict=true；冲突侧 strong_tech 不得单独造项目匹配，shared_need / positioning / 一致技术仍允许；**不篡改输入 A**，输出 PROJECT_CONTEXT_HEALTH 供上游修数据 |
| NEED_PROJECT_COMPATIBILITY（§六） | 逐 primary 需求记录 compatible_projects / incompatible_projects；承载该需求的项目**全部**与 required_tech 不兼容 → 该 need 不能作为 Top 的 primary 个性化证据（可保留 watch/general_interest）；出现兼容项目后自动恢复 |
| 机器合同拆分（§七/§八） | product_internal 审计拆为 pool / in_full_scan / in_top 三个计数（pool 允许 >0；队列与 Top 残留 = 0 是硬门）；歧义字段 product_internal_remaining_count 与 internal_capability_remaining_count **废弃**，不得再输出 |
| Delta 反冒充（§九/§十） | UPDATED=两侧都有值且前进（commit 还需 new>old）；null→值、unknown→active 等 = METADATA_ENRICHED；快照带 snapshot_schema_version + analysis_engine_version，换代 → SYSTEM_REBASELINE 重建基线，不产出数百条假 UPDATED；score/recommendation/gap 变化只会 MATCH_CHANGED/RISING/FALLING |
| action_type（§十二） | new_install / watch / restore_candidate / update_candidate / replacement_candidate / reject；known_missing+血缘=restore（血缘未确认也不得装新装）；日报 §1B 单独渲染「恢复 / 修复」 |
| 增量证据分级（§十三） | incremental_evidence_level ∈ confirmed_absent / summary_not_found / unknown；confirmed_absent 需实际读取该族全部已装成员 SKILL.md（只读）；summary_not_found 可 watch、**不得仅此成为安装候选**；unknown 不作 strong 饱和解除依据；措辞废止「已装 Skill 明确没有」的过强断言 |

### 5.0.0.1 v2.11 数据级断言（§十四，现算；标注『必须 0』的任何一项非 0 不得冻结）

| 断言 | 实测 | 口径 |
|---|---|---|
| TEAM_COMPOSITION_SECURITY_PRIMARY | 0 | = 0 |
| BREAKDOWN_TEST_SPEC_PRIMARY | 0 | = 0 |
| YEJIAN_CONFLICT_DETECTED | 0 | = 0 |
| FRONTEND_UI_DARK_GLOBAL_NEED_FALSE_TOP | 0 | = 0 |
| PRODUCT_INTERNAL_IN_TOP | 0 | = 0 |
| PRODUCT_INTERNAL_IN_FULL_SCAN | 0 | = 0 |
| INTERNAL_CAPABILITY_IN_FULL_SCAN | 0 | = 0 |
| CONTRADICTORY_AUDIT_FIELDS | 0 | = 0 |
| KNOWN_MISSING_MISREPORTED_AS_NEW_INSTALL | 0 | = 0 |
| FAKE_UPDATED_FROM_ENRICHMENT | 0 | = 0 |
| 冲突项目数（输入 A） | 1 | 记录项（允许 >0，External 层只标记不篡改） |
| product_internal_unresolved_pool_count | 30 | 允许 >0（留池等待解除，**不再标注为必须 0**）|
| 本轮 UPDATED 计数（DAILY_DELTA） | 见 EXTERNAL_SKILLS_CONTEXT `DAILY_DELTA.UPDATED` | SYSTEM_REBASELINE 轮应为 0（引擎换代不冒充上游更新）|

### 5.0.0.2 Top 修正理由审计（§十五：留下的每条必须挂在真实证据上）

| 候选 | 修正后允许的理由 | 不得再用的理由 |
|---|---|---|
| `wshobson/agents/team-composition-patterns` | agent-governance 需求（primary） | security_audit weak gap（示例词）＋靠它成 install_candidate |
| `github/awesome-copilot/breakdown-test` | testing_qa 缺口（weak，primary 证据） | spec-driven primary（test task breakdown） |
| `microsoft/skills/frontend-ui-dark-ts` | 仅当存在兼容 React/Tailwind 的项目证据 | 不兼容时 global dashboard-viz 单独撑 Top |
| `stablyai/orca/computer-use` | restore_candidate（恢复/修复栏目，§十二） | 伪装成「外部新发现的 Skill」 |

### 5.0.0-A v2.10 轮（保留，v2.11 仍生效）

> 本轮对应审查文档《External Skill Intelligence v2.9 冻结前 Top 语义与能力饱和收口》。树内编号 v2.9 已被「产品关系与领域三态」轮占用，故本层在库内编号 **v2.10**，两轮的规则**同时生效**。以下 5.0.0.x 为本轮；5.0.1–5.0.6 为 v2.9 轮记录（保留）。

#### 5.0.0-A1 v2.10 本轮口径（§二~§十二 / §十四）

| 项 | 口径 |
|---|---|
| browser-qa primary（§二/§十） | 浏览器/Web 测试对象 **AND** 测试动作 **AND** 测试**目标**（behavior / functionality / interaction / acceptance / e2e / regression / DOM/UI state / navigation / forms / user flow，或登记测试工件短语）；『QA workflow / screenshot for QA / theme testing / design review / accessibility audit』最多 supporting |
| 新增信息标签（§二/§三/§十） | `browser_capture`（screenshot / full-page capture / webpage PDF / thumbnail）、`accessibility_audit`、`llm_documentation`；不吃缺口分，但经 TAG_FAMILY 参与饱和判定（browser_capture→browser_automation，accessibility_audit→frontend_design） |
| spec-driven（§三） | primary = 产出/维护**开发规格**（write/create + spec、requirements document、PRD、design doc、RFC、implementation plan、task breakdown、acceptance criteria、constitution、SPEC/PLAN/TASK、SDD/Spec Kit）；『following / compliant with the X specification』= supporting（遵守标准≠驱动开发） |
| capability_saturation（§四/§五） | 每候选输出 none/weak/medium/strong/strong_degraded；strong 默认 watchlist，进 Top 必须有 CLEAR_INCREMENTAL_VALUE（update / replacement / availability degraded / 明确 incremental_subcapability / 未覆盖的项目专用技术路线）；**不是硬黑名单**，条件满足即恢复 |
| incremental_subcapability（§六） | 数据驱动：子能力词形出现在候选正向文本、且不出现在该族任何已装 Skill 文本（Installed Context §6 简表，只读）才成立 |
| capability_family_quota（§七） | strong 族 Top 最多 1 条代表项；超额必须各带**未用过**的增量子能力；medium=2；weak/none=3（允许比较路线） |
| required_tech / compatible_tech（§八/§九） | 只提取**核心方法依赖**（Build … React applications / using Tailwind CSS / React Native / Expo Router / Jetpack Compose…），『SDK supports X』不算；项目兼容按映射（CSS↔HTML/Web/PWA 兼容、Tailwind 需 Tailwind、React 需 React、Expo 需 Expo/RN）；不兼容时 shared_need 单独不造项目匹配（general_need_match 保留，project_match=[]） |
| personalized_reason（§十二） | 每条 Top 带 fills_gap / matched_project / incremental_over_installed / why_now；strong 饱和候选 incremental_over_installed 必须非空 |
| Top Gate 顺序（§十四） | 1 Security → 2 validity/lineage → 3 产品/领域 scope → 4 primary 证据 → 5 required-tech 兼容 → 6 能力饱和 → 7 已装重复/增量 → 8 分数 → 9 功能族 → 10 能力族配额；不再先按分数再解释不相关 |

#### 5.0.0-A2 v2.10 已知假阳性数据断言（§十一/§十三，现算；任何一项非 0 不得声明冻结）

| 断言 | 实测 | 口径 |
|---|---|---|
| LATCHSHOT_BROWSER_QA_FALSE_POSITIVE | 0 | = 0 |
| WIKI_LLMS_SPEC_DRIVEN_FALSE_POSITIVE | 0 | = 0 |
| DESIGN_REVIEW_BROWSER_QA_FALSE_POSITIVE | 0 | = 0 |
| FRONTEND_UI_DARK_WRONG_PROJECT_MATCH | 0 | = 0 |
| TOP_STRONG_SAT_WITHOUT_INCREMENTAL | 0 | = 0 |
| frontend_design（已装 strong）族 Top 条数 | 1 | ≤1 代表项（§七/§十一） |
| REQUIRED_TECH_BLOCKED_SHARED_NEED | 5 | v2.10 §八：不兼容项目被拒绝的 shared_need 匹配数（记录项，非必须 0） |

#### 5.0.0-A3 能力饱和统计（全池 / Top）

| saturation | 全池 | Top | 说明 |
|---|---|---|---|
| none | 903 | 8 | 可进 Top |
| weak | 97 | 6 | 可进 Top |
| medium | 0 | 0 | 需明确增量 |
| strong | 106 | 2 | 默认降级 |
| strong_degraded | 0 | 0 | strong+degraded 不硬压 |

因饱和（strong/medium 无增量）被挡在 Top 外、仍留 WATCHLIST 的候选：**31** 条（可解除：update / degraded 恢复路线 / 新子能力 / 项目专用技术路线，任一成立即恢复）。

### 5.0.1 本轮口径（v2.9 轮，保留）


| 项 | 口径 |
|---|---|
| 产品关系数据 | `config/product_relationships.json`：产品 ID / 名称 / 厂商 / 类别 / 领域 / 受控能力 / 竞品关系（每条带依据）；加载时做六条完整性校验 |
| 关系类型 | `developer_tool` / `primary_target` / `mentioned` / `ambiguous` / `official_extension`；**仅名称含品牌词 = mentioned，不构成任何 Gate** |
| 领域 | 一律派生：`PRODUCT_IN[产品] = 产品.domain`；歧义词（insurance / voice / cloud / container / app / lambda）不再发明领域 |
| 领域三态 | 适用 / 不适用（必须有输入A 明确低优先级证据）/ 信息不足（未解除且未排除，默认不入推荐队列，记录解除测试） |
| 深度安全审查 | 队列覆盖全池，按分数降序；**硬 Gate 命中者不入队**；`full_scan_remaining` 必须为 0 |

### 5.0.2 旧版误判统计（v2.8 → v2.9）

| 指标 | 数值 | 说明 |
|---|---|---|
| 名字含品牌词却被 Gate 挡的残留 | 0 | §四.12 必须为 0 |
| 竞品关系命中候选 | 476 | 其中已解除 474 / 未解除 4 |
| 产品内部能力（product_internal） | 27 | 必须与产品自身内置功能同小句共现 + 操作动词 |
| 外部集成（external_integration） | 5 | MCP / API / SDK 只是通用集成能力，不算内部 |
| 判为不适用（not_applicable） | 352 | 依据 = 输入A §5「当前低优先级」明文排除 |
| 信息不足（insufficient_info） | 24 | 未解除且未排除，默认不入推荐队列（非黑名单） |
| 深度审查队列 | 入队 1021 / 完成 1021 / 剩余 0 | 被硬 Gate 挡在队列外 54 |

**v2.8 被误挡、v2.9 已恢复进入 Top 的候选**（逐条附产品关系与领域证据）：

| canonical_key | v2.9 关系与领域 | 结果 |
|---|---|---|
| `anthropics/skills/claude-api` | 产品关系=anthropic-api/developer_tool；项目分区=—；置信度=low；领域状态=applicable；适用证据=anthropic-assistants | applicable |

### 5.0.3 能力覆盖统计（§六.2：先按输入A 需求逐条列覆盖，再列无候选缺口）

| 用户需求（输入A §4） | 权重 | Top 候选 | 安装候选 | 全池命中该需求的候选 | 覆盖判定 |
|---|---|---|---|---|---|
| agent-governance | 51.0 | 5 | 1 | 21 | 已覆盖 |
| pwa-offline | 50.0 | 0 | 0 | 1 | 部分覆盖 |
| frontend-design | 48.0 | 1 | 0 | 19 | 部分覆盖 |
| desktop-app | 39.0 | 0 | 0 | 5 | 部分覆盖 |
| deploy | 38.0 | 0 | 0 | 30 | 部分覆盖 |
| python-auto | 33.0 | 0 | 0 | 3 | 部分覆盖 |
| browser-qa | 32.0 | 3 | 3 | 7 | 已覆盖 |
| llm-api | 32.0 | 1 | 0 | 10 | 部分覆盖 |
| photo-mgmt | 31.0 | 0 | 0 | 0 | 无候选 |
| secret-safety | 29.0 | 0 | 0 | 10 | 部分覆盖 |
| supabase-db | 28.0 | 0 | 0 | 1 | 部分覆盖 |
| android | 27.0 | 1 | 1 | 1 | 已覆盖 |
| dashboard-viz | 27.0 | 0 | 0 | 3 | 部分覆盖 |
| docker-infra | 27.0 | 0 | 0 | 10 | 部分覆盖 |
| privacy-local | 23.0 | 0 | 0 | 11 | 部分覆盖 |
| finance-calc | 21.0 | 0 | 0 | 7 | 部分覆盖 |
| media-transcribe | 20.0 | 0 | 0 | 7 | 部分覆盖 |
| voice-input | 19.0 | 0 | 0 | 5 | 部分覆盖 |
| spec-driven | 16.0 | 0 | 0 | 19 | 部分覆盖 |
| expo-rn | 15.0 | 1 | 0 | 3 | 部分覆盖 |
| task-integration | 15.0 | 0 | 0 | 3 | 部分覆盖 |
| responsive | 14.0 | 1 | 0 | 4 | 部分覆盖 |
| github-auto | 12.0 | 1 | 1 | 24 | 已覆盖 |
| data-pipeline | 9.0 | 0 | 0 | 10 | 部分覆盖 |

Top 内命中的能力缺口：testing_qa×3、security_audit×2、mobile_qa×1、frontend_design×1、deployment_vercel×1、windows×1、image_creative×1。
**注意：本表是「Top / 安装候选口径的覆盖」，不等于「所有能力缺口都无人支持」——『候选存在但未进 Top』的需求仍有候选，只是未过当轮质量门（§六.2 明令不得这样宣称）。**

### 5.0.4 数据级断言（§四.11 / §五.4，任何一项非 0 不得声明冻结）

| 断言 | 实测 | 要求 |
|---|---|---|
| full_scan_remaining_count | 0 | = 0 |
| competitor_unresolved_in_queue | 0 | = 0 |
| competitor_unresolved_in_top | 0 | = 0 |
| product_name_false_positive_remaining | 0 | = 0 |
| internal_capability_in_full_scan_count | 0 | = 0 |
| product_internal_in_full_scan_count | 0 | = 0 |
| product_internal_in_top_count | 0 | = 0 |
| scope_unresolved_in_top | 0 | = 0 |
| product_internal_in_top | 0 | = 0 |
| insufficient_info_in_top | 0 | = 0 |
| Top 条数 | 16 | ≥ 8（v2.10 §十五 废止数量下限『宁少不凑』，保留防呆下限） |

### 5.0.5 产品关系修复清单（§六.3 格式：候选 / 旧关系 / 新关系 / 结果 / 依据）

| canonical_key | v2.8 表现 | v2.9 关系 | 结果 | 依据 |
|---|---|---|---|---|
| `github/awesome-copilot/creating-oracle-to-postgres-migration-integration-tests` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | internal_only | internal_feature:auth ↔ supabase-postgres（同小句共现 + 操作动词）；候选服务于来源产品自身，不是 |
| `github/awesome-copilot/planning-oracle-to-postgres-migration-integration-testing` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `github/awesome-copilot/power-bi-model-design-review` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | powerbi-analytics：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/scaffolding-oracle-to-postgres-migration-test-project` | 产品词命中即降级 watch / 挡队列 | developer_tool `dotnet` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `browseros-ai/browseros/test-ui` | 产品词命中即降级 watch / 挡队列 | developer_tool `browseros` | internal_only | internal_feature:extension UI ↔ browseros（同小句共现 + 操作动词）；候选服务于来源产品自身，不是 |
| `wshobson/agents/protect-mcp-setup` | 产品词命中即降级 watch / 挡队列 | developer_tool `claude-code` | internal_only | internal_feature:projects ↔ claude（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `mvanhorn/clawdbot-skill-supabase/clawdbot-skill-supabase` | 产品词命中即降级 watch / 挡队列 | — `—` | internal_only | internal_feature:database ↔ supabase-postgres（同小句共现 + 操作动词）；候选服务于来源产品自 |
| `nariatrip191/my-claude-skills/pr-review-expert` | 产品词命中即降级 watch / 挡队列 | developer_tool `claude-code` | internal_only | internal_feature:projects ↔ claude（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `anthropics/skills/web-artifacts-builder` | 产品词命中即降级 watch / 挡队列 | official_extension `anthropic-api` | internal_only | internal_feature:artifacts ↔ claude（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `stablyai/orca/orchestration` | 产品词命中即降级 watch / 挡队列 | developer_tool `orca` | internal_only | ref:orca+internal_term:orchestration（同句共现）；候选服务于来源产品自身，不是用户通用能力 |
| `github/awesome-copilot/aws-cost-optimize` | 产品词命中即降级 watch / 挡队列 | primary_target `aws` | internal_only | internal_feature:iac ↔ aws（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `github/awesome-copilot/az-cost-optimize` | 产品词命中即降级 watch / 挡队列 | developer_tool `github` | internal_only | internal_feature:iac ↔ microsoft-azure（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通 |
| `github/awesome-copilot/creating-oracle-to-postgres-master-migration-plan` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `github/awesome-copilot/creating-oracle-to-postgres-migration-bug-report` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `github/awesome-copilot/d365-solution-blueprint` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | microsoft-office：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/declarative-agents` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | competitor_mismatch | m365-copilot↔claude-code |
| `github/awesome-copilot/entra-agent-user` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | internal_only | internal_feature:workers ↔ cloudflare-platform（同小句共现 + 操作动词）；候选服务于来源产品 |
| `github/awesome-copilot/fabric-lakehouse` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | powerbi-analytics：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/java-add-graalvm-native-image-support` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/migrating-oracle-to-postgres-data-access-code` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `github/awesome-copilot/migrating-oracle-to-postgres-stored-procedures` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/msgraph-sdk` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | microsoft-office：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/postgresql-code-review` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | supabase-backend：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/postgresql-optimization` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | supabase-backend：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/power-bi-dax-optimization` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | powerbi-analytics：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/power-bi-performance-troubleshooting` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | powerbi-analytics：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/power-bi-report-design-consultation` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | internal_only | internal_feature:report ↔ powerbi（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `github/awesome-copilot/powerbi-modeling` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | powerbi-analytics：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声 |
| `github/awesome-copilot/reviewing-oracle-to-postgres-migration` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/shopify-review-triage` | 产品词命中即降级 watch / 挡队列 | developer_tool `apple-app-store` | insufficient_info | ios-mobile：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/snowflake-semanticview` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | snowflake-warehouse：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `github/awesome-copilot/sql-code-review` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `github/awesome-copilot/sql-optimization` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项;supabase-backend：候选声明该产品/平台领 |
| `github/awesome-copilot/ssma-console` | 产品词命中即降级 watch / 挡队列 | official_extension `github-copilot` | insufficient_info | oracle-db：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `vercel-labs/agent-skills/deploy-to-vercel` | 产品词命中即降级 watch / 挡队列 | — `—` | internal_only | internal_feature:deploy ↔ vercel（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `vercel-labs/agent-skills/vercel-cli-with-tokens` | 产品词命中即降级 watch / 挡队列 | developer_tool `vercel` | internal_only | internal_feature:deploy ↔ vercel（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `google/skills/gke-ai-troubleshooting-tpu-vbar-oom` | 产品词命中即降级 watch / 挡队列 | official_extension `gemini-api` | internal_only | internal_feature:troubleshooting ↔ container-orchestration（同小句共现 + 操作动 |
| `google/skills/gke-manifest-generation` | 产品词命中即降级 watch / 挡队列 | developer_tool `container-orchestration` | internal_only | internal_feature:manifests ↔ container-orchestration（同小句共现 + 操作动词）；候选服 |
| `huggingface/skills/hf-cli` | 产品词命中即降级 watch / 挡队列 | developer_tool `huggingface` | internal_only | internal_feature:spaces ↔ huggingface（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用 |
| `huggingface/skills/huggingface-lora-space-builder` | 产品词命中即降级 watch / 挡队列 | developer_tool `huggingface` | internal_only | internal_feature:spaces ↔ huggingface（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用 |
| `huggingface/skills/huggingface-spaces` | 产品词命中即降级 watch / 挡队列 | developer_tool `huggingface` | internal_only | internal_feature:spaces ↔ huggingface（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用 |
| `huggingface/skills/huggingface-zerogpu` | 产品词命中即降级 watch / 挡队列 | — `—` | internal_only | internal_feature:spaces ↔ huggingface（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用 |
| `microsoft/skills/azure-kubernetes-app-deploy` | 产品词命中即降级 watch / 挡队列 | primary_target `container-orchestration` | internal_only | internal_feature:manifests ↔ container-orchestration（同小句共现 + 操作动词）；候选服 |
| `microsoft/skills/declarative-agent-developer` | 产品词命中即降级 watch / 挡队列 | developer_tool `m365-copilot` | internal_only | internal_feature:declarative agents ↔ github-copilot（同小句共现 + 操作动词）；候选服 |
| `microsoft/skills/m365-agent-evaluator` | 产品词命中即降级 watch / 挡队列 | developer_tool `m365-copilot` | internal_only | internal_feature:declarative agents ↔ github-copilot（同小句共现 + 操作动词）；候选服 |
| `microsoft/skills/teams-app-developer` | 产品词命中即降级 watch / 挡队列 | developer_tool `github-copilot` | internal_only | ref:github-copilot+internal_term:declarative agents（同句共现）；候选服务于来源产品自身， |
| `microsoft/skills/ui-widget-developer` | 产品词命中即降级 watch / 挡队列 | developer_tool `m365-copilot` | insufficient_info | m365-copilot：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `wshobson/agents/block-no-verify-hook` | 产品词命中即降级 watch / 挡队列 | primary_target `claude-code` | internal_only | internal_feature:hooks ↔ claude-code（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能 |
| `wshobson/agents/airflow-dag-patterns` | 产品词命中即降级 watch / 挡队列 | developer_tool `airflow` | internal_only | internal_feature:dags ↔ airflow（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户通用能力 |
| `wshobson/agents/postgresql-table-design` | 产品词命中即降级 watch / 挡队列 | developer_tool `supabase-postgres` | insufficient_info | supabase-backend：候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项 |
| `wshobson/agents/helm-chart-scaffolding` | 产品词命中即降级 watch / 挡队列 | developer_tool `container-orchestration` | internal_only | internal_feature:helm ↔ container-orchestration（同小句共现 + 操作动词）；候选服务于来源产 |
| `wshobson/agents/k8s-manifest-generator` | 产品词命中即降级 watch / 挡队列 | developer_tool `container-orchestration` | internal_only | internal_feature:manifests ↔ container-orchestration（同小句共现 + 操作动词）；候选服 |
| `wshobson/agents/superself` | 产品词命中即降级 watch / 挡队列 | — `—` | internal_only | internal_feature:CLAUDE.md ↔ claude-code（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用 |
| `wshobson/agents/mobile-android-design` | 产品词命中即降级 watch / 挡队列 | developer_tool `android-play` | internal_only | internal_feature:compose ↔ android-play（同小句共现 + 操作动词）；候选服务于来源产品自身，不是用户 |

### 5.0.6 v2.8 修掉的问题（保留，v2.9 仍生效）

v2.7 的确定性矩阵、血缘、UPDATE_LINEAGE、GCP/AWS 域框架、scope 五道门、安全 Gate、功能族、Top 不凑数**全部保持**（§十四 保留清单）。本轮把『产品专项冒充通用个人需求』的最后 7 案按**通用证据规则**收口，未新增 blacklist。

| # | 问题（v2.7 表现） | v2.8 处置 |
|---|---|---|
| 1 | `applicationinsights-web-ts` 凭『遥测 SDK 支持 React Native』命中 expo-rn、打 expo_rn_dev、成 install_candidate | expo-rn 四态化：primary=核心 RN/Expo 开发（build/develop RN、Expo Router/EAS/native module，或名称断言 RN）；『supports/plugin/works with』= supporting（×0.5 权重、不打标签、不能单独撑 Top）。react-native-design / react-native-skills 保住 primary |
| 2 | GA Admin 凭 Measurement Protocol secrets、Trackio 凭『实验看板+产品CLI』、hf-cloud-serving 凭『LLM+endpoint』、browserclaw 凭『提到 Playwright』、orca-per-workspace-env 凭『SSH host…container』——五类需求全部泛词冒充 | dashboard-viz / python-auto / llm-api / browser-qa 与 expo-rn 同表纳入 `capability_evidence_context` 四态：generic 看板与 ML 实验看板区分（`_dashboard_domain_only`，领域内全部限定 → supporting）；产品自带 CLI/automation = supporting；模型部署/serving container → model_serving 信息标签、llm-api 最多 supporting（名称即 `<provider> api/sdk` 或调用动作才 primary）；browser-qa primary = 测试动作 AND 浏览器对象（管理面排除保持）；host 名词式（SSH/remote/local/docker host）不算部署动词，仅 `host an app/site/service/model` 严格式成立。新增信息标签 ml_experiment_tracking / model_serving（不在 suppression 表，不吃缺口分）|
| 3 | 产品专项词典覆盖不足：Application Insights / M365 Copilot（ui-widget-developer）/ Hugging Face Spaces / SageMaker 系被当 generic | `_PRODUCT_OPERATION_TERMS` 补录三类 + **AWS 服务别名**进 mismatch 词典（sagemaker/cloudwatch/aws lambda/s3/ecs/eks/fargate/bedrock → aws；**裸 lambda 不收**，防数学/代码误伤）；识别按 skill_name/description/repo，绝不按 owner 一刀切（Microsoft 仓库里 frontend-design-review 等照旧可进）|
| 4 | scope 判定是散落的字符串证据，审查者无法分层核对 | §四 统一输出 **`platform_scope_evidence{scope_type,target_product,evidence[],confidence}`**：证据逐条标来源（skill_name:/description:/repo:），名称或仓库可独立指认产品=high，仅描述命中=medium；进候选 JSON，日报/对照件可查 |
| 5 | supporting 级证据仍能独自撑起 Top 位（Trackio watch 74.1 靠 dashboard+python-auto） | §十四 核心证据门：`core_evidence_ok()` —— 无 primary 级需求、无 matched_project、无 primary 证据的 gap、无 update/replacement → 不进 Top；shared_need 与『看板』定位证据同步只认 primary 级（Trackio → family-insurance-dashboard 的项目匹配随之消失）；审计行 `top_candidates_supporting_only` 必须为 0 |
| 6 | 「产品 scope 会不会变永久黑名单」的疑问必须用数据回答 | §十 解除矩阵进测试：项目档案加入 Application Insights / M365 Copilot / HF Spaces / SageMaker 后对应 scope 自动解除（`test_v28_platform_scope_evidence_layer` 逐条断言）；§十一 七案全部退出或降 watch，**判定代码里无一处按 canonical_key 分支** |

### 5.1 v2.7 修掉的问题（保留，v2.8 仍生效）

v2.6 的身份血缘 / UPDATE_LINEAGE / GCP 别名 / 产品 scope / 安全 Gate / Deep Scan / 功能族 / Canonical 去重**全部保持**（§十二）。本轮修的是复审在归档环境里实测到的一致性问题与 Top 里剩余的真实假相关——**未新增任何 blacklist**。

| # | 问题 | v2.6 表现 | v2.7 处置 |
|---|---|---|---|
| 1 | **分类随 PYTHONHASHSEED 漂移** | `_ctx` 用 `' '.join(set)` 重建 Skill 名 → `php-mcp-server-generator` 的 `mcp server` 短语随 seed 打散：seed 0/1/42/123 → mcp_usage，seed 2/3 → mcp_dev；审查环境实测 50/1/1，与回执 51+1SKIP 不一致 | `_ctx` 保存 **raw_name / normalized_name（有序）/ name_words_set**，一切名称短语判定改读有序 `name_norm`（禁止 set 回拼）；新增硬门 `test_v27_determinism_hashseed`（seed 0/1/2/3/42/123 子进程矩阵，输出必须逐字节一致，漂移即 FAIL，§十一）|
| 2 | **Question Answering 被判 Quality Assurance** | `microsoft/skills/wiki-qa`（Answers questions about a code repository）只因名含 `qa` 吃 testing_qa=weak 缺口分进 Top | 名称证据**只有裸 `qa`** 时必须有真实质保语义（quality assurance / software testing / acceptance testing / 质量保证…）；问答语境（answers questions / q&a / knowledge qa / 问答…）在无其他测试身份时一票否决；新增独立记录位 `question_answering`（不吃 testing_qa 分）。反向保护：place-journal-qa（真测试描述）/ webapp-testing 仍成立 |
| 3 | **deploy 全文任意共现** | game-engine「publishing games」凭 publishing+任意位置的 build 命中 deploy（Top #2, 76.6）；detection-engineering「deploy YARA-L rules to SecOps」被当通用部署 | 改**动词+通用部署对象邻近**（≤50 字符同句窗口）：deploy/publish/host/roll out + app/site/service/function/container/workload/artifact/pages…；rules/policies/prompts/detections/configs/dashboards/alerts/games/content/documentation **不是**通用对象；反向保护 deploy-to-vercel、python-appservice-deploy、真 app/site 部署 |
| 4 | **breakout 跨领域假匹配** | game-engine（打砖块）凭领域短语 `breakout` 匹配 pepe-doge-breakout-radar（突破行情）| `_PROJECT_DOMAIN_PHRASES` 撤掉裸 `breakout`，改 trading/price/market breakout、breakout radar/signal、backtest、量化交易等；新增 **`_AMBIGUOUS_DOMAIN_TERMS`**（breakout/native/model/agent/manager/dashboard…）：跨域高歧义**单词**一律不得独立成词面证据（只能进短语）|
| 5 | **React Native 撞上「原生」** | `react-native-design` 凭 TECH_MATCH「原生」的 `native app` 匹配 DeepSeekBalanceWidget-Mac（React Native apps ⊃ native app 子串）| **最长短语优先 + 跨度遮蔽**：`_rn_masked()` 先把 react native / react-native / nativewind 从正向视图占用，再判 native 类技术词。反向保护：Swift/AppKit/menubar 真原生描述仍可匹配 |
| 6 | **产品专项漏门 + secret 过宽** | GA Admin 凭「Measurement Protocol secrets」命中 secret-safety 进 Top；SecOps/Anthropic brand 走不进 scope 门 | ① `_PRODUCT_OPERATION_TERMS` 词典（google-analytics / google-secops / anthropic-brand / microsoft-store / SaaS 后台…）→ platform_operation + target_product，项目档案没有该产品 → 最高 watch、不进 Top（统一 `scope_unresolved()`，可解除非 blacklist）；② secret-safety = **安全对象 AND 安全动作**（rotate/scan/redact/vault/密钥管理/防泄露…），仅出现 secret 资源不成立 |
| 7 | **扫描预算饿死分类**（§一「不一致」的第二个根因）| PASS 1 预算 600 按 preliminary 排序分配；语义变化后 wiki-qa / python-appservice-deploy 落到 600 外 → 描述为空 → 一切判定基于空文本失真 | `scan_budget` 600 → **1200 覆盖全池**（raw.githubusercontent 不占 API 配额；本轮实际抓取 1,075）；副作用如实记录：verdict unscanned 506 → 31，block 5 → 9（新抓出的真 `curl\|bash`，fail-closed 方向，名单见 §3.1）|

### 5.2 v2.6 修掉的问题（保留，v2.8 仍生效）

v2.5 的来源分层、安全 Gate、Deep Scan、直接证据分级、否定窗口、Top 质量门、功能族折叠、归档自定位**全部保持**（§十四）。v2.6 只修实际复审发现的 7 类问题，**未新增任何 blacklist**，修的全是通用证据规则。

| # | 问题 | v2.5 表现 | v2.6 处置 |
|---|---|---|---|
v2.5 的来源分层、安全 Gate、Deep Scan、直接证据分级、否定窗口、Top 质量门、功能族折叠、归档自定位**全部保持**（§十四）。本轮只修实际复审发现的 7 类问题，**未新增任何 blacklist**，修的全是通用证据规则。

| # | 问题 | v2.5 表现 | v2.6 处置 |
|---|---|---|---|
| 1 | **同名 = 已安装**：身份判定不查血缘 | `KKKKhazix/khazix-skills/aihot` 与已装 `aihot`（真实上游 = Virxact / AI HOT）只因同名被判 `already_installed` **且 update_available=true**，UPDATE_CANDIDATES 把 Khazix 仓库当成 Virxact 官方更新来源；`microsoft/skills/skill-creator` 同理冒充 `anthropics/skills` 已装件 | 身份统一按 **canonical identity + lineage evidence**：`already_installed` 必须满足五条件之一（normalized upstream 一致 / owner·repo 与已装 upstream 明确一致 / 内容指纹可证 / Source Map 记载 external repo 为上游或内容同源 / 显式 lineage alias 表——leader、neat-freak 按 Source Map『逐字节一致』证据入表）。证明不了 → `same_name_unverified`（已装侧 upstream=unknown）或 `same_name_different_source`（记录的上游明确不同）：不标已装、不建立 update/replacement 关联、最高 watch、等待人工确认。名称只参与 similarity（near_duplicate / overlap）。|
| 2 | **update 从候选池找同名对象冒充上游** | 已装件 `aihot` 的更新绑到外部同名仓 | 更新检查改读 **SKILL_SOURCE_MAP.json**（canonical_id / upstream / origin_type / version_status / upstream_activity / evidence）：UPDATE_LINEAGE 逐条输出`installed_canonical_id / installed_upstream / update_upstream / lineage_evidence / lineage_verified`；`installed_upstream` 与 `update_upstream` 不一致必须有血缘证据，否则拒绝关联；候选池没有同血缘候选时更新来源直接取 Source Map 自己的 upstream，**不绑错 repo**。browseros-neo（BrowserOS 血缘一致）仍可 update ✓ |
| 3 | **GCP 产品别名漏检**：`domain_mismatch=[]` 仍能占 Top | `cloud-run-basics` / `agent-platform-deploy` / `agent-platform-endpoint-management` 明显是 Google Cloud 专项，却因词典只有 google cloud / gcp / bigquery 而漏判，`top_candidates_with_unresolved_mismatch=0` 表面正确实际漏检 | MISMATCH 词典补 14 个 GCP 产品别名（cloud run / agent platform / model garden / vertex ai / vertex / cloud build / cloud functions / firestore / gke / google kubernetes engine / cloud sql / alloydb / cloud monitoring / cloud logging）→ 全部归 `gcp` 域；**裸 `Gemini` 不算 GCP**（Gemini API 可独立使用，用户有 LLM API 需求）；另立 `microsoft-store` 域。数据级审计计数 `gcp_alias_missed` **必须为 0** |
| 4 | **产品 scope 与通用能力不分** | BrowserOS `test-ui`（"Test the BrowserOS app extension UI…"）是产品自研测试，却凭 `testing_qa=weak` 成为通用 install_candidate；Microsoft Store CLI 仅凭「用户有 Windows 电脑」成高优候选 | 新增 **`scope_type` ∈ {generic, platform_operation, product_internal} + `target_product`**：product_internal 判定以**候选来源仓库即产品仓**为前提（避免误伤「在 Supabase 上做应用」），只有用户项目档案真的在用/开发该产品才进 Top；platform_operation 复用 domain-mismatch 同一套门。`select_top` 加**第五道门**；未解除的 product_internal 最高 watch。**不是 blacklist**：项目将来开发该产品即自动解除 |
| 5 | **跨 Skill 重定向句被当本 Skill 能力** | `stablyai/orca/orca-emulator`（iOS Simulator Skill）描述尾部「For an Android device or emulator use the Android emulator skill;」——句子里的 android/emulator 是给**别的 Skill** 的 scope，却被判本 Skill 的 android 需求（w=27）、mobile_qa 缺口、并匹配 landedazi-android，误上 install≈79.4 | 新增**重定向窗口**（与否定窗口并列，先剪重定向再剪否定）：识别 For X, use/see Y · use Y instead · handled/covered by Y · X is covered by Y · 如果是X请使用Y · X请改用Y；目标 Y 必须是「另一个 Skill」形态（连字符 slug 或 『the X skill』短语，`use this skill` 不算）；被剪小句数计入 `redirect_evidence_rejected`。反向保护：`orca-emulator-android` 的 android 仍成立；orca-emulator 的 mobile_qa 保留（simulator 入 QA 证据表）。另按 §五 把 `match_projects` ①② 两路改到**正向视图**判定，并修掉 `fm_description` 300 字符截断（放宽 600 —— 截断会把重定向句切掉，属「数据不全导致规则失效」类缺陷）|
| 6 | **使用 MCP 仍被判开发**（v2.5 §六残留） | `penpot-uiux-design`「creating professional UI/UX designs in Penpot **using MCP tools**」被旧宽窗正则判 mcp_dev primary | 开发动词的**宾语必须真的是 MCP 工件**（server/client/tool/integration/protocol/sdk），且紧贴工件前不得出现 using/via/through；「using MCP tools」= **mcp_usage**（独立标签记录，不算开发、不吃 mcp_dev 缺口分）。`mcp-builder` / `php-mcp-server-generator` / `rust-mcp-server-generator` 必须仍 primary ✓；`github-issues using MCP` 不得 mcp_dev ✓ |
| 7 | **frontend_design 过宽 / image_creative 漏检 / deploy 名词 / spec 歧义** | ① `webapp-testing` 凭「verifying frontend **functionality**」命中 frontend-design（测试工具白拿最高权重需求）；② Anthropic `canvas-design`（poster / visual art / static piece / PNG·PDF）与 `generate-image`（Generate images … icons, sprites, artwork）没有 image_creative 标签，而已装侧 `image_creative = none` —— 日报漏掉真缺口；③ 「enable fast deployment」/「before production deployment」/「deployment categories」/「Ease of Deployment」被当部署能力；④ `gen-specs-as-issues`（产品规格）凭名字里的 specs 被打 testing_qa 白拿 15 分 | ① frontend_design（CAP+NEED 同步）删裸 frontend/front-end/ux/css/tailwind/shadcn/visual design，只认明确设计语义（ui design / ux design / web design / design system / visual hierarchy / typography / responsive design / styling / css design / component design / interface design / frontend design / design review…）；静态视觉艺术优先归 image_creative（词表扩充：generate images / artwork / poster / sprite / texture / visual asset / 图像生成 / 海报 / 插画 / 图标生成 / 视觉素材…）；③ deploy primary 改**纯操作语义**（deploy+对象 / publish+对象 / rollout / *deployment pipeline / deploy to X / provision deployment / 部署应用·发布站点·上线服务），裸名词 `deployment` 只能 mention，不得单独产生 deploy 需求；④ `_TESTING_NAME_TOKENS` 删除裸 spec/specs，只有 test spec / test specification / spec test / executable specification / RSpec 等测试语境成立；`test-spec-generator`、`rspec-*` 保持 ✓（反向保护）|

### 5.3 v2.5 修掉的问题（保留，v2.6–v2.8 仍生效）

v2.4 的架构、来源层、安全 Gate、Top 质量门、直接证据分级、否定窗口、功能族折叠、归档自定位**全部保持**；v2.5 只修**剩余语义误判**（android 需求证据 / 否定逗号枚举 / 词面证据 / mcp_dev / docx_xlsx / github-auto / 证据语境四态），不重做已验收机制。

| # | 问题 | v2.4 表现 | v2.5 处置 |
|---|---|---|---|
| 1 | android 需求被裸 device / build / install / launch 命中 | `google-mobile-ads-get-started` / `-validate` 只是「在 Android 应用里集成广告 SDK」，因 install / device 等词被记成 Android QA 需求（w=27） | android = 平台证据 AND **真实 QA 证据**：A 表（qa / test / e2e / adb / emulator / real device / device farm / appium / detox / maestro / espresso / xctest / instrumentation / 真机 / 自动化测试）或 B 表（signing / keystore / signed apk / apk / aab / app bundle / build verification / release build verification / 签名 / 构建验收）；裸 device / build / install / launch **禁止**作正向证据。反向回归：`orca-emulator-android` 必须仍然命中 android + mobile_qa（adb / emulator 是真证据）|
| 2 | 否定窗口在逗号枚举处把 B、C 洗回正向 | v2.4 把逗号当分句边界，`Don't use for A, B, or C.` 只有 A 被否，B / C 复活 —— `agent-platform-prompt-management` 明写不用于部署仍误命中 deploy（w=38）；`agent-platform-tuning` 同误判 | 两段式：**大句**只按 句号（需跟空白/行尾，保住 next.js / .net / node.js）/ 分号 / 换行 / 句读 切分；**逗号只在段内传播否定状态**；遇到显式对比词（but / however / instead / whereas / use for / can be used for / 但是 / 但 / 不过 / 而是 / 可用于 / 可以用于 / 适用于）才恢复正向。`Not for A, but use for B.` 与 `非用于 A、B、C，但可用于部署上线` 必须照常恢复 |
| 3 | 词面证据凭泛用技术词或裸 prompt 独立成立 | `react-view-transitions` 因 react / native 匹配 `yejian-buguangdeng`；`claude-api` 与 `breakdown-test` 因裸 `prompt` 匹配 `prompt-manager` | 泛用技术词（react / native / javascript / typescript / python / css / html / tailwind / next / nextjs / android / kotlin / expo / mobile / web / api / sdk / model / cloud…）从词面证据**全禁**；`prompt` 移出高信号词。词面独立成立只认**人工整理的领域短语**（prompt management / managed prompts / prompt library / prompt versioning / 提示词管理…）；普通词面重叠降级为**次要加分**（须与 strong_tech / positioning / shared_need 同现），单独造匹配计入 `lexical_alone_rejected` |
| 4 | 精度自检只能证明「字段非空」 | 无法回答「裸 prompt / 技术词是否又混进来了」 | 新增三个显式计数：`lexical_phrase_direct_evidence`（短语独立成立次数）、**`bare_prompt_direct_evidence` 恒为 0**、**`tech_words_used_as_lexical_direct_evidence` 恒为 0**（非 0 即回归失败）|
| 5 | 提到 MCP ≠ 具备 MCP 开发能力 | `claude-api` 描述里「支持与 MCP 配合」被打上 mcp_dev 标签、吃缺口分 | mcp_dev 需**核心开发证据**：build / create / develop / implement / write / set up … MCP（server / tool / client / Model Context Protocol implementation）/ MCP SDK / 编写 MCP / MCP 服务开发，或 Skill 名含 mcp-server / mcp-development / mcp-builder。「支持 MCP / 可与 MCP 使用 / 文档包含 MCP」只算 mention；`claude-api` 失去 mcp_dev、保留 llm-api；真实 MCP builder 不受影响 |
| 6 | PPTX 冒充 docx_xlsx | `publish-to-pages` 生成 PPTX / PDF / HTML，却被记成 docx_xlsx 能力、拿文档缺口分 | docx_xlsx 只认 docx / xlsx / Word / Excel / spreadsheet / 明确的 office document / 上下文中的文档处理·表格处理；PPTX / PowerPoint 单列 `pptx_processing` 标签，**不得**伪造 docx_xlsx |
| 7 | 裸 `github` 命中 github-auto | `breakdown-test` 只因引用 GitHub 仓库语境就被记成 github-auto 需求（且顺带带出错误的词面项目匹配） | github-auto = GitHub 平台词 AND 运维语义词（GitHub Actions / gh CLI / repository automation / issue creation / pull request automation / PR review / release automation / labels / milestones / workflow dispatch / repository sync / commit automation / GitHub API / 自动建 issue / 自动 PR / 仓库同步…）|
| 8 | 「顺带提及」与「核心能力」在评分层无统一口径 | mcp_dev / docx_xlsx / github-auto / android / deploy 各自为政，修一处漏一处 | 统一字段 `capability_evidence_context` ∈ {primary, supporting, mention, negated}：只有 primary 拿满 capability gap 分；supporting 上限 8；mention / negated 上限 2；需求侧 supporting 权重 ×0.5。以后新增误报按四态归类修，**不再手写候选黑名单** |

### 5.4 v2.4 附带修掉的两个「规则看起来对、实际不生效」缺陷（保留，v2.5–v2.8 仍生效）

v2.4 排查中发现并修掉 —— 二者都属于「写在配置里也测不出来」的类型，且会让 §五 的中文否定标记形同虚设：

| # | 缺陷 | 后果 | 处置 |
|---|---|---|---|
| A | 中文关键词命中率恒为 0 | `_WORD_RE` 是纯 ASCII（`[a-z0-9]…`），中文没有词边界，整词匹配下规则表里 **48 个 NEED_RULE + 27 个 CAP_RULE 中文关键词**，加上 TECH_MATCH 的 `容器化` / `菜单栏应用`，**全部是永不命中的死词** | 含 CJK 的关键词改走子串匹配；回归测试对规则表做**全量自检**（中文关键词不得再有死词），同时保留英文整词匹配（`ui` 命中 build 的老事故不许回归）|
| B | 分句不含逗号 → 否定窗口过度压制 | 「非用于 A，可用于 B」整句被丢弃，把逗号后的**正向证据**一起误杀 | 逗号（`,` / `，`）纳入分句边界，否定只作用于本小句；修掉后 `negated_evidence_rejected` 由 **94 降到 30**，即减少了 64 处「假压制」|

### 5.5 v2.4–v2.7 已验收通过、本轮**不重做**（提示词执行说明保留清单）

strong / secondary 技术栈分级与 `strong_tech` 直接证据 · Docker 词典删裸 `container` · 词面 stop list 与 `lexical_single_rejected` · 通用否定窗口（逗号语义在 v2.5 §五.2 收紧，窗口本体保留）· deploy 的 hosted+部署对象同现 · testing_qa 主能力证据 · 未解除 domain_mismatch 四道门（×0.7 / 不 install / 不进 Top）· PROJECT_MATCH_QUALITY 分项计数 · CJK 死词全量自检 · 17 source registry · T0/T1/T2/T3 分层 · bottom-up 非 Skill 隔离 · ClawHub 构建产物过滤 · mobile_qa / supabase-db / llm-api / voice-input 误报修复 · Security warning vs 真执行区分 · deep scan 安装候选 Gate · Top 不含 ignore/reject · Top 不凑 30 · T3 无佐证不进 Top · functional family / alternatives · source official 口径统一 · 测试 PASS/SKIP/FAIL 三分 · 包内 SKILL_CONTEXT 自定位。

本轮 §十二/§十三 重审（实际数据核对）：三处禁选项目匹配 **0**（应为 0）；假需求占 Top **0**（应为 0）；Top 内未解除平台错配 **0**（应为 0）；Top 内未解除 product scope **0**（应为 0）。

### 5.6 数据级断言（v2.6 §十三 + v2.7 §九/§十 + v2.8 §十一/§十四：任何一项非 0 / FAIL 不得声明冻结）

| 断言 | 实测 | 口径 |
|---|---|---|
| WRONG_UPDATE_LINEAGE | 0 | 血缘未验证的 update_available |
| SAME_NAME_ONLY_ALREADY_INSTALLED | 0 | 只凭同名判已安装 |
| TOP_UNRESOLVED_PRODUCT_SCOPE | 0 | Top 内未解除的 product_internal |
| GCP_ALIAS_MISSED | 0 | 含 GCP 产品词却未标 gcp 域 |
| ANDROID_REDIRECT_FALSE_POSITIVE | 0 | orca-emulator 命中 android |
| MCP_USAGE_AS_MCP_DEV | 0 | 非 primary 证据却打 mcp_dev 标签 |
| FRONTEND_TEST_AS_FRONTEND_DESIGN | 0 | webapp-testing 命中 frontend-design |
| IMAGE_CREATIVE_KNOWN_FALSE_NEGATIVE | 0 | canvas-design / generate-image 缺 image_creative |
| DEPLOY_OUTCOME_AS_DEPLOY_CAPABILITY | 0 | e2e / owasp 的 deployment 名词仍命中 deploy |
| PRODUCT_SPEC_AS_TESTING_QA | 0 | gen-specs-as-issues 被打 testing_qa |
| WIKI_QA_AS_TESTING_QA | 0 | v2.7 §九/§十 终审计 |
| GAME_ENGINE_FALSE_DEPLOY | 0 | v2.7 §九/§十 终审计 |
| BREAKOUT_CROSS_DOMAIN_FALSE_MATCH | 0 | v2.7 §九/§十 终审计 |
| REACT_NATIVE_TO_NATIVE_MACOS_FALSE_MATCH | 0 | v2.7 §九/§十 终审计 |
| GA_ADMIN_SECRET_FALSE_POSITIVE | 0 | v2.7 §九/§十 终审计 |
| SECOPS_RULE_DEPLOY_AS_GENERIC | 0 | v2.7 §九/§十 终审计 |
| **KNOWN_FALSE_POSITIVE_COUNT** | **0** | 六条合计（**必须为 0**）|
| APPSIGHTS_EXPO_SUPPORT_AS_PRIMARY | 0 | v2.8 §十一/§十四 终审计（**必须为 0**）|
| TRACKIO_DASHBOARD_PYTHON_FALSE_NEEDS | 0 | v2.8 §十一/§十四 终审计（**必须为 0**）|
| SERVING_AS_LLM_API | 0 | v2.8 §十一/§十四 终审计（**必须为 0**）|
| PLAYWRIGHT_MENTION_AS_BROWSER_QA | 0 | v2.8 §十一/§十四 终审计（**必须为 0**）|
| SSH_HOST_NOUN_AS_DEPLOY | 0 | v2.8 §十一/§十四 终审计（**必须为 0**）|
| SUPPORTING_ONLY_IN_TOP | 0 | v2.8 §十一/§十四 终审计（**必须为 0**）|
| AWS_ALIAS（sagemaker/bedrock/s3 → aws） | PASS | v2.8 §三.4：AWS 别名生效且裸 lambda 不误伤 |
| DETERMINISM | hashseed 矩阵 0/1/2/3/42/123 由 `test_v27_determinism_hashseed` 断言 | v2.7 §二/§十一：6 个 seed 输出逐字节一致才算过（classification_drift 必须为 0）|

> 同名血缘核对：`kkkkhazix/khazix-skills/aihot` rel=`same_name_different_source`（不得 already_installed）、update_available=False（不得为 True）；`microsoft/skills/skill-creator` rel=`same_name_different_source`；`anthropics/skills/skill-creator` rel=`already_installed`（同上游应已安装）。

本轮结果：Top 实际 **16/30**，跨仓同功能族折叠 **1** 条。

## 六、如何复现／核对

```bash
# 一键全流程（注册表 → 发现 → 分析 → Context → 本对照件）
python3 scripts/run_daily.py
# 只重算候选池
python3 scripts/analyze.py
# 重新生成本对照件
python3 scripts/make_digest.py -o ../CANDIDATES_DIGEST.md
# 离线测试（90 项，不联网；摘要分 PASS / SKIP / FAIL 三栏）
python3 tests/test_pipeline.py
```

**依赖的输入（缺一不可）**：

| 输入 | 解析优先序（v2.3 §九 / v2.4 §十二 保持） | 作用 |
|---|---|---|
| A 项目需求 `SKILL_CONTEXT.md` | ① `SKILL_CONTEXT_PATH` 环境变量 → ② **包内 `支撑/输入/SKILL_CONTEXT.md`**（归档包解压后自定位） → ③ 本机默认路径 | 决定 PROJECT_MATCH / 相关性否决 / matched_projects |
| B 已装侧底座 `INSTALLED_SKILLS_CONTEXT.md` + `SKILL_SOURCE_MAP.json` | ① `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH` → ② 同级 v4 文件夹自动发现（向上 3 级） → ③ 找不到则该组测试 **SKIP 并提示** | 决定 `installed_relationship` 与 `capability_gap_match` |
| C 外部候选 | `data/SKILL_CANDIDATES.json` | 本层产物 |

**路径不再写死**：`scripts/common.py` 的所有输入路径都可用环境变量覆盖，未设置时按上表优先序自动定位（归档包内也能自洽），并用 `~` 展开（不写死用户名）。命中的来源会记录在 `common.PATH_RESOLUTION` 里，可核对到底读的是哪个文件：

```bash
SKILL_REPO_ROOT=/path/to/仓库 \
SKILL_CONTEXT_PATH=/path/to/SKILL_CONTEXT.md \
SKILL_DATA_DIR=/path/to/data \
python3 scripts/run_daily.py
```

可覆盖的变量：`SKILL_REPO_ROOT` / `SKILL_CONTEXT_PATH` / `SKILL_DATA_DIR` / `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH`。换机器或跑归档副本时用环境变量指路，**不要改脚本内的路径**。

> 未找到输入 A 时：`matched_projects` 会为空、需求证据全体失效 —— 本件生成时输入 A local_default → `~/Developer/coding/1.Active/000-alw-github 档案/SKILL_CONTEXT.md`（可读）。

> **本行会随运行环境变化**（env / 包内自定位 / 本机默认），属预期；对照件其余内容在不同环境下应当逐位一致。
