# 候选池精简对照件（External Skill Intelligence v2.2）

> 数据基线：2026-09-22｜源文件 `SKILL_CANDIDATES.json`（1091 条）
> 本件是**给审查者看得完的切片视图**，用于核对；完整数据与全部字段以 JSON 为准。
> 只做发现与评估：**不安装、不删除、不升级任何 Skill**；排名/安装量只是 adoption signal，不等于推荐。

## 一、总览

| 项目 | 数值 |
|---|---|
| 来源注册表 | 17 源（T0 2 / T1 9 / T2 3 / T3 3）|
| 候选（raw → 合法池） | 1170 → 1091 |
| 数据质量 Gate | 剔除构建产物 67 条 / 非法 skill 名 1 条 |
| bottom-up 硬门 | 共 41 条搜索结果 → 过 SKILL.md 硬门 4 / 隔离 36 |
| 推荐分布 | ignore 278 / reject 5 / watch 808 |
| 与已装关系 | already_installed 14 / complement 46 / new_capability 1009 / overlap 19 / replacement_candidate 3 |
| 安全风险 | high 5 / low 388 / medium 194 / unknown 504（已静态审查 587）|
| 安全 verdict | pass 388 / review_required 194 / block 5 / unscanned 504 |
| 深度静态审查 | complete 555 / failed 32 / skipped 504 |
| 能力缺口 | none 8 / strong 943 / weak 140 |
| 命中项目需求 / 平台错配 | 229 / 312 |
| matched_projects 覆盖（高匹配候选） | 251/808 (31%) |
| update_available / replacement_candidate | 2 / 3 |

## 二、Personalized Top（target_limit 30 · 实际 30）

选取规则（与日报完全一致，复用同一函数）：① hard gates ② 真实需求匹配（含 matched_projects）③ recommendation ≥ watch ④ 分数；多样性最后执行：同仓库上限 3 条 + 同族折叠。

> **只含 `install_candidate` / `watch`，不含 `ignore` / `reject`**；符合标准的不足 30 个时就输出实际数量，不为凑数塞垃圾。

「安全」列的口径：`pass` = 静态审查无发现；`review_required` = 有语境性提及，需人工看一眼；
`block` = 高风险行为，已 reject；`unscanned` = 超出抓取预算，**最高只能是 watch**。
`T—` 表示来源未经验证（bottom-up 搜索结果），不参与安装推荐。

| # | 分数 | 推荐 | canonical_key | 来源 | 命中需求 | 最匹配项目 | 缺口 | 安全 |
|---|---|---|---|---|---|---|---|---|
| 1 | 85.0 | watch | `github/awesome-copilot/webapp-testing` | T1 github/awesome-copilot | frontend-design, browser-qa | party-night-v1-2(60)；personal-rss(60) | weak | pass |
| 2 | 84.0 | watch | `anthropics/skills/webapp-testing` | T1 anthropics/skills | frontend-design, browser-qa | party-night-v1-2(60)；personal-rss(60) | weak | review_required |
| 3 | 82.6 | watch | `github/awesome-copilot/ai-prompt-engineering-safety-review` | T1 github/awesome-copilot | agent-governance | prompt-manager(64)；party-night-v1-2(60) | weak | pass |
| 4 | 82.6 | watch | `github/awesome-copilot/ai-team-orchestration` | T1 github/awesome-copilot | agent-governance | stretch-side-timer-project(64)；party-night-v1-2(60) | weak | pass |
| 5 | 81.4 | watch | `stablyai/orca/orca-emulator-android` | T1 stablyai/orca | android | landedazi-android(94)；DeepSeekBalanceWidget-Mac(90) | none | pass |
| 6 | 75.0 | watch | `google/skills/google-mobile-ads-validate` | T1 google/skills | llm-api, android | landedazi-android(94)；stretch-side-timer-project(64) | strong | pass |
| 7 | 71.6 | watch | `wshobson/agents/bats-testing-patterns` | T2 wshobson/agents | deploy | party-night-v1-2(60)；personal-rss(60) | weak | pass |
| 8 | 71.6 | watch | `google/skills/agent-platform-endpoint-management` | T1 google/skills | deploy | personal-rss(60)；family-insurance-dashboard(60) | strong | pass |
| 9 | 71.6 | watch | `google/skills/agent-platform-model-registry` | T1 google/skills | deploy | personal-rss(60)；family-insurance-dashboard(60) | strong | pass |
| 10 | 71.5 | watch | `microsoft/skills/frontend-ui-dark-ts` | T1 microsoft/skills | frontend-design | yejian-buguangdeng(94)；party-night-v1-2(90) | strong | pass |
| 11 | 71.5 | watch | `microsoft/skills/frontend-design-review` | T1 microsoft/skills | frontend-design | party-night-v1-2(60)；personal-rss(60) | strong | pass |
| 12 | 71.5 | watch | `anthropics/skills/canvas-design` | T1 anthropics/skills | frontend-design | party-night-v1-2(60)；personal-rss(60) | strong | pass |
| 13 | 71.5 | watch | `vercel-labs/agent-skills/react-view-transitions` | T1 vercel-labs/agent-skills | frontend-design | yejian-buguangdeng(86)；party-night-v1-2(78) | strong | pass |
| 14 | 71.0 | watch | `vercel-labs/agent-skills/vercel-cli-with-tokens` | T1 vercel-labs/agent-skills | deploy, secret-safety | personal-rss(60)；family-insurance-dashboard(60) | strong | review_required |
| 15 | 70.3 | watch | `anthropics/skills/claude-api` | T1 anthropics/skills | llm-api | prompt-manager(64)；party-night-v1-2(60) | weak | review_required |
| 16 | 69.3 | watch | `wshobson/agents/e2e-testing-patterns` | T2 wshobson/agents | browser-qa | party-night-v1-2(60)；personal-rss(60) | weak | pass |
| 17 | 69.3 | watch | `wshobson/agents/llm-evaluation` | T2 wshobson/agents | llm-api | party-night-v1-2(60)；personal-rss(60) | weak | pass |
| 18 | 67.6 | watch | `vercel-labs/agent-skills/react-best-practices` | T1 vercel-labs/agent-skills | deploy | personal-rss(60)；family-insurance-dashboard(60) | strong | pass |
| 19 | 64.9 | watch | `microsoft/skills/github-issue-creator` | T1 microsoft/skills | voice-input, github-auto | personal-rss(60)；protein-calculator(60) | strong | pass |
| 20 | 57.3 | watch | `huggingface/skills/huggingface-llm-trainer` | T1 huggingface/skills | llm-api | party-night-v1-2(60)；personal-rss(60) | strong | review_required |
| 21 | 48.6 | watch | `khasky/awesome-agent-skills/awesome-bug-fix` | T—(unverified) bottom_up_search | github-auto | party-night-v1-2(60)；personal-rss(60) | weak | review_required |
| 22 | 31.1 | watch | `occupations/business-and-financial-operations-occupations/business-and-financial-operations-occupations` | T3 SkillsMP | finance-calc | github-projects-profile(60)；party-night-v1-2(60) | strong | unscanned |
| 23 | 62.8 | watch | `huggingface/skills/hf-cloud-sagemaker-deployment-planner` | T1 huggingface/skills | deploy, llm-api | party-night-v1-2(60)；personal-rss(60) | strong | pass |
| 24 | 48.6 | watch | `obra/superpowers/subagent-driven-development` | T2 obra/superpowers | agent-governance | — | strong | review_required |
| 25 | 56.0 | watch | `stablyai/orca/orca-per-workspace-env` | T1 stablyai/orca | — | personal-rss(84)；family-insurance-dashboard(84) | weak | pass |
| 26 | 52.0 | watch | `browseros-ai/browseros/test-ui` | T1 browseros-ai/BrowserOS | — | party-night-v1-2(60)；personal-rss(60) | weak | review_required |
| 27 | 47.0 | watch | `obra/superpowers/test-driven-development` | T2 obra/superpowers | — | party-night-v1-2(60)；personal-rss(60) | weak | pass |
| 28 | 30.0 | watch | `categories/testing-security/testing-security` | T3 SkillsMP | — | party-night-v1-2(60)；personal-rss(60) | weak | unscanned |
| 29 | 51.0 | watch | `stablyai/orca/computer-use` | T1 stablyai/orca | — | — | weak | pass |
| 30 | 45.0 | watch | `huggingface/skills/hf-mcp` | T1 huggingface/skills | — | — | weak | review_required |

仓库分布：13 个仓库承载 30 条 → `github/awesome-copilot`×3、`anthropics/skills`×3、`stablyai/orca`×3、`google/skills`×3、`wshobson/agents`×3、`microsoft/skills`×3、`vercel-labs/agent-skills`×3、`huggingface/skills`×3、`obra/superpowers`×2。

## 三、安全清单（Security Gate v2）

v2.2 的核心区分：**「提到危险行为」≠「真的要求执行危险行为」**。每条 finding 带 `confidence` 与 `behavior_context`（mention / instruction / executable / remote_execution），verdict 四值 `pass / review_required / block / unscanned`。

总体：pass 388 / review_required 194 / block 5 / unscanned 504

### 3.1 block 级阻断（reject，5 条）

仅限高置信、真会被执行的高危行为：远程内容 pipe 进 shell/解释器、`rm -rf ~/` 或 `/`、凭据读取后外发、混淆 payload 执行等。官方来源**不豁免**。

| canonical_key | 来源 | 阻断规则 | 证据 |
|---|---|---|---|
| `github/awesome-copilot/containerize-aspnetcore` | T1 | destructive_rm_root | `rm -rf /` |
| `github/awesome-copilot/mcp-implementation-security-review` | T1 | destructive_rm_root | `rm -rf /` |
| `github/awesome-copilot/aspire` | T1 | pipe_to_shell | `curl -sSL https://aspire.dev/install.sh | bash` |
| `github/awesome-copilot/azure-container-registry-cli` | T1 | pipe_to_shell | `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash` |
| `github/awesome-copilot/azure-devops-cli` | T1 | pipe_to_shell | `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash` |

### 3.2 review_required 需人工复核（194 条；其中 0 条被挡在安装候选之外）

口径：属于敏感行为但**语境上只是提及/解释/示例**，或虽有指令语境但危险度不足 —— 一律不 reject，交人工判断。其中 `behavior_context` 为 instruction/executable 的高敏感项会被挡在 `install_candidate` 之外（最高 watch）。

| canonical_key | 来源 | 是否挡安装 | 命中规则 |
|---|---|---|---|
| `anthropics/skills/claude-api` | T1 | 否（语境性提及） | credential_files,network_generic |
| `anthropics/skills/doc-coauthoring` | T1 | 否（语境性提及） | network_generic |
| `anthropics/skills/docx` | T1 | 否（语境性提及） | bundled_scripts |
| `anthropics/skills/mcp-builder` | T1 | 否（语境性提及） | network_generic |
| `anthropics/skills/pptx` | T1 | 否（语境性提及） | bundled_scripts |
| `anthropics/skills/webapp-testing` | T1 | 否（语境性提及） | bundled_scripts |
| `anthropics/skills/xlsx` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/agent-governance` | T1 | 否（语境性提及） | network_generic,sudo |
| `github/awesome-copilot/agent-owasp-compliance` | T1 | 否（语境性提及） | dynamic_code |
| `github/awesome-copilot/arize-ai-provider-integration` | T1 | 否（语境性提及） | credential_files |
| `github/awesome-copilot/containerize-aspnet-framework` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/convert-excel-to-md` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/doc-and-modernize` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/flowstudio-power-automate-mcp` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/github-actions-hardening` | T1 | 否（语境性提及） | credential_files |
| `github/awesome-copilot/github-copilot-starter` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/github-issues` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/github-release` | T1 | 否（语境性提及） | git_push_auto,network_generic |
| `github/awesome-copilot/mcp-create-declarative-agent` | T1 | 否（语境性提及） | credential_files,network_generic |
| `github/awesome-copilot/mcp-security-audit` | T1 | 否（语境性提及） | credential_files,network_generic |
| `github/awesome-copilot/md-to-docx` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/pr-dashboard` | T1 | 否（语境性提及） | bundled_scripts |
| `github/awesome-copilot/scoutqa-test` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/secret-scanning` | T1 | 否（语境性提及） | git_push_auto |
| `github/awesome-copilot/suggest-awesome-github-copilot-agents` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/suggest-awesome-github-copilot-instructions` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/suggest-awesome-github-copilot-skills` | T1 | 否（语境性提及） | network_generic |
| `github/awesome-copilot/test-gap-audit` | T1 | 否（语境性提及） | bundled_scripts |
| `vercel-labs/agent-skills/deploy-to-vercel` | T1 | 否（语境性提及） | credential_files,git_push_auto,network_generic |
| `vercel-labs/agent-skills/vercel-cli-with-tokens` | T1 | 否（语境性提及） | credential_files,git_push_auto,network_generic |
| `vercel-labs/agent-skills/vercel-optimize` | T1 | 否（语境性提及） | bundled_scripts,network_generic |
| `vercel-labs/agent-skills/web-design-guidelines` | T1 | 否（语境性提及） | network_generic |
| `google/skills/google-ads-api-mcp-setup` | T1 | 否（语境性提及） | network_generic,sudo |
| `google/skills/agent-platform-deploy` | T1 | 否（语境性提及） | bundled_scripts,network_generic |
| `google/skills/cloud-monitoring-chart-generation` | T1 | 否（语境性提及） | bundled_scripts |
| `google/skills/gemini-agents-api` | T1 | 否（语境性提及） | network_generic |
| `google/skills/gemini-api` | T1 | 否（语境性提及） | credential_files |
| `google/skills/gemini-interactions-api` | T1 | 否（语境性提及） | network_generic |
| `google/skills/gemini-live-api` | T1 | 否（语境性提及） | sudo |
| `google/skills/google-cloud-global-frontend-configuration` | T1 | 否（语境性提及） | network_generic |

### 3.3 install 候选的两阶段审查（PASS 2）

带 `scripts/` 的候选不能只打一个 `bundled_scripts=low` 就放行：进入 `install_candidate` 的候选会额外静态读取该 Skill 目录下的 `.py/.sh/.js/.ts/.mjs/.cjs/.ps1` 与 `package.json` 的 `postinstall`/`preinstall`。**只做静态读取，绝不执行脚本。**

深度审查状态分布：complete 555 / failed 32 / skipped 504；`install_candidate` 必须先满足 `deep_scan_status = complete` 且无 block 级 finding。

## 四、更新候选（update_available，2 条）

| canonical_key | 外部最新 | 上游活跃度 | 说明 |
|---|---|---|---|
| `browseros-ai/browseros/browseros-neo` | — | active | 已装但 version_status=outdated_version（上游 active）→ 属更新候选，不重复推荐安装，仅在 UPDAT |
| `kkkkhazix/khazix-skills/aihot` | — | unknown | 已装但 version_status=outdated_version（上游 active）→ 属更新候选，不重复推荐安装，仅在 UPDAT |

### 4.1 恢复/替换候选（replacement_candidate，3 条）

判定口径：已装侧为 `known_missing`（如 Orca 三件套主副本缺失，coverage=strong / availability=degraded），或已装侧 `version_status=outdated_version` 且上游仍活跃。**仅登记候选，不自动安装。**

| canonical_key | 说明 |
|---|---|
| `stablyai/orca/computer-use` | 中分 51：值得关注，需人工判断（未命中项目需求；仅作观察） |
| `stablyai/orca/orca-cli` | 中分 48：值得关注，需人工判断（未命中项目需求；仅作观察） |
| `stablyai/orca/orchestration` | 中分 48：值得关注，需人工判断（未命中项目需求；仅作观察） |

## 五、v2.2 修掉的问题（整改记录）

| # | 问题 | v2.1 表现 | v2.2 处置 |
|---|---|---|---|
| 1 | 聚合源把前端构建产物当 Skill | 约 50 条 `.css`/`.js` 文件名混入候选池 | 进入合法池前加 Gate，本轮剔除 **67** 条（+非法名 1 条）；原始数据仍留在 raw discovery 作证据 |
| 2 | bottom-up 搜索结果直接算 TIER 2 | 普通项目仓库（如 FastAPI 后端仓）被当成 Skill | 改为 `discovery_channel`，必须过「真实 SKILL.md + 可定位目录 + frontmatter 可解析」硬门；通过者也仅记 unverified（source_tier=null + 最低信任档），**绝不自动升 T2**；本轮隔离 **36** 条 |
| 3 | 「出现平台词 = 满足能力需求」 | `Google Mobile Ads`、`IMA DAI SDK`、`Penpot UI/UX`、`responsive-design` 只因出现 android/ios/mobile 就被记成 mobile_qa；`alloydb-basics`/`postgresql-optimization` 只因 PostgreSQL 就吃 Supabase 缺口分 | 关键词升级为 **MATCH_RULE**（组间 AND / 组内 OR / none_of / context_terms）：mobile_qa 要求「移动平台 AND QA/设备/构建验收证据」；supabase_db 要求真 Supabase 或 RLS 语境（普通 PG 归 postgres_db）；另拆出 mobile_dev / expo_rn_dev，网络/打包/自动化等宽泛需求同步收紧 |
| 4 | `matched_projects` 恒为空 | 1,184 条候选全部为空 → 日报答不出「对我哪个项目有用」 | 解析 `SKILL_CONTEXT.md` 活跃项目档案，按技术栈 + 能力→项目类型映射生成 `project / evidence / match_score`（最多 5 个）；本轮高匹配候选覆盖率 **251/808** |
| 5 | Security Gate 误伤 | 只要文本出现 `.env`/`GITHUB_TOKEN`/`eval`/`sudo` 就 high → reject | finding 增加 `confidence` + `behavior_context`，verdict 改四值；只有「真要求执行」的高危行为才 block，文档讨论/示例引用归 review_required |
| 6 | 带脚本的 Skill 直接放行 | 只记 `bundled_scripts=low` 就可成 install_candidate | 新增 PASS 2 深度静态审查，`deep_scan_status = complete` 且无 block 级 finding 才可成为安装候选 |
| 7 | 两层来源口径不一致 | 同一 `stablyai/orca` 在已装侧记 official、外部层记 vendor | 统一为 official（官方项目自维护的公开官方 Skill 仓库）；vendor 只留给非官方 skill 仓库口径的厂商 |
| 8 | Top30 用 ignore 补数量 | 第 29、30 位出现 ignore | Top 只允许 install_candidate / watch，新增 `target_limit` / `actual_count`；本轮实际 **30/30**，不足不凑 |

## 六、如何复现／核对

```bash
# 一键全流程（注册表 → 发现 → 分析 → Context → 本对照件）
python3 scripts/run_daily.py
# 只重算候选池
python3 scripts/analyze.py
# 重新生成本对照件
python3 scripts/make_digest.py -o ../CANDIDATES_DIGEST.md
# 离线测试（22 项，不联网）
python3 tests/test_pipeline.py
```

**依赖的输入（缺一不可）**：

| 输入 | 默认位置 | 作用 |
|---|---|---|
| A 项目需求 | 本机项目档案目录下的 `SKILL_CONTEXT.md` | 决定 PROJECT_MATCH / 相关性否决 / matched_projects |
| B 已装侧底座 | `转送审查者 v4 材料（Canonical 模型）/INSTALLED_SKILLS_CONTEXT.md` 与 `SKILL_SOURCE_MAP.json` | 决定 `installed_relationship` 与 `capability_gap_match` |
| C 外部候选 | `data/SKILL_CANDIDATES.json` | 本层产物 |

**路径不再写死**：`scripts/common.py` 的所有输入路径都可用环境变量覆盖，未设置时自动向上定位仓库根，并用 `~` 展开（不写死用户名）：

```bash
SKILL_REPO_ROOT=/path/to/仓库 \
SKILL_CONTEXT_PATH=/path/to/SKILL_CONTEXT.md \
SKILL_DATA_DIR=/path/to/data \
python3 scripts/run_daily.py
```

可覆盖的变量：`SKILL_REPO_ROOT` / `SKILL_CONTEXT_PATH` / `SKILL_DATA_DIR` / `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH`。换机器或跑归档副本时用环境变量指路，**不要改脚本内的路径**。

> 未找到输入 A 时：`matched_projects` 会为空、需求证据全体失效 —— 本件生成时输入 A 可读。
