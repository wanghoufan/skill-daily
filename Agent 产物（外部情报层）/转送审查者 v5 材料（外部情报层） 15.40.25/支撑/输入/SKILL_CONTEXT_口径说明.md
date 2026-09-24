# 输入 A 口径说明（脱敏摘要）

> **本文件不是输入 A 原文件。** 输入 A 原始文件为 `SKILL_CONTEXT.md`（14,290 B，生成于 2026-09-22 08:48），
> 其文首第 8 行自带限制：**「含私有仓库的名称与定位，仅用于本机/本仓智能体读取，勿再对外分发」**。
> 因此原文件不随本包外送，改以本摘要提供外部情报层真正消费的那部分数据。
>
> 剔除的内容：逐个仓库的名称与功能描述（原 §2「当前活跃项目」全表）。
> 保留的内容：**全部 24 项能力需求权重、17 项技术栈权重、规模聚合数字、需求 → 英文关键词映射、
> 明确不进入推荐方向的技术清单**——这些是 `PROJECT_MATCH` 与平台错配判定的全部输入，足以独立复算。

## 一、这份文件在管线中的位置

```
输入 A  SKILL_CONTEXT.md        → 用户「需要什么能力」+ 技术栈白/黑名单   → 决定 PROJECT_MATCH(25) 与平台错配降权
输入 B  INSTALLED_SKILLS_CONTEXT.md → 本机「已经有什么能力」+ 压制强度     → 决定 CAPABILITY_GAP(20) 与 installed_relationship
输入 C  EXTERNAL_SKILLS_CONTEXT.md  → 外面「发现了什么」                → 本层产出
```

生成方式：**确定性脚本从 GitHub 项目档案派生，不调用任何大模型**；权重 = 按仓库活跃度加权
（14 天内 ×3 / 30 天内 ×2 / 90 天内 ×1 / 更早 ×0.3）。

## 二、规模聚合（原 §1）

| 指标 | 值 |
|---|---|
| 仓库总数 | 42（公开 22 / 私有 20） |
| 最近 30 天活跃 | 31（其中 14 天内活跃 25） |
| 30 天活跃度占比 | 74% |

按开发类型分布（仓库数 / 其中 30 天内活跃）：

| 类型 | 仓库数 | 30 天内活跃 |
|---|---|---|
| Web / PWA | 22 | 16 |
| Expo / React Native | 4 | 4 |
| Android | 1 | 1 |
| macOS / 原生桌面 | 3 | 3 |
| .NET / Windows 桌面 | 3 | 2 |
| Python 自动化 / 数据处理 | 10 | 8 |
| AI / Agent 工具 | 15 | 11 |
| 数据库 / Supabase | 6 | 4 |
| 部署 / 基础设施 | 11 | 8 |
| Shell / 系统脚本 | 1 | 1 |

## 三、24 项能力需求权重（原 §4，`PROJECT_MATCH` 的输入）

| 需求 key | 中文 | 活跃 | 14 天内 | 权重 w | 优先级 |
|---|---|---|---|---|---|
| `agent-governance` | Agent / 多智能体治理与提示词工程 | 17 | 14 | 51.0 | P0 |
| `pwa-offline` | PWA / 离线能力与本地存储 | 16 | 15 | 50.0 | P0 |
| `frontend-design` | UI / UX 设计、视觉与设计审查 | 15 | 11 | 48.0 | P0 |
| `desktop-app` | 桌面应用 / 跨平台打包与发布 | 12 | 10 | 39.0 | P0 |
| `deploy` | 部署上线（Vercel / 静态托管 / 云端） | 11 | 11 | 38.0 | P0 |
| `python-auto` | Python 本地自动化 / 数据处理 | 11 | 8 | 33.0 | P0 |
| `browser-qa` | 浏览器端 QA / E2E 自动化验证 | 10 | 8 | 32.0 | P0 |
| `llm-api` | LLM API 接入 / 流式与结构化输出 | 10 | 7 | 32.0 | P0 |
| `photo-mgmt` | 图片素材管理 / EXIF 与相册 | 9 | 8 | 31.0 | — |
| `secret-safety` | API Key / Secret 安全与配置收敛 | 9 | 7 | 29.0 | — |
| `supabase-db` | Supabase / Postgres / Migration 治理 | 8 | 7 | 28.0 | — |
| `android` | Android 真机 QA / 构建签名 | 9 | 9 | 27.0 | — |
| `docker-infra` | Docker / 自托管服务运维 | 9 | 9 | 27.0 | — |
| `dashboard-viz` | 数据看板 / 可视化与统计口径 | 8 | 7 | 27.0 | — |
| `privacy-local` | 本地优先 / 隐私与脱敏 | 8 | 6 | 23.0 | — |
| `finance-calc` | 金融 / 投资口径与计算 | 7 | 5 | 21.0 | P1 |
| `media-transcribe` | 视频 / 音频转写与内容归档 | 7 | 5 | 20.0 | P1 |
| `voice-input` | 语音输入 / 语音识别 | 7 | 5 | 19.0 | P1 |
| `spec-driven` | SDD / SPEC / PLAN / TASK 开发流程 | 5 | 4 | 16.0 | P1 |
| `expo-rn` | Expo / React Native 开发与打包 | 5 | 5 | 15.0 | P1 |
| `task-integration` | 时间 / 任务管理工具集成 | 5 | 3 | 15.0 | P1 |
| `responsive` | 响应式 Web（桌面 + 手机同一套） | 4 | 4 | 14.0 | P1 |
| `github-auto` | GitHub 仓库自动化与内容同步 | 4 | 3 | 12.0 | P1 |
| `data-pipeline` | 抓取 / RSS / 信息聚合流水线 | 3 | 3 | 9.0 | P2 |

原文件的分级规则（原 §5）：P0 = 权重 ≥ 最高分 45% 且 14 天内活跃项目 ≥ 2；P1 = 权重 ≥ 18%；更低为 P2。

## 四、17 项技术栈权重（原 §3，平台错配判定的输入）

| 技术栈 | 活跃 | 权重 | 档位 |
|---|---|---|---|
| TypeScript | 13 | 42.0 | 高频 |
| LLM API（DeepSeek / 千问 / OpenAI 等） | 11 | 34.0 | 高频 |
| Python | 8 | 25.0 | 高频 |
| PWA / 离线与本地存储 | 7 | 23.0 | 高频 |
| React / Next.js | 7 | 23.0 | 高频 |
| Docker / 自托管 | 6 | 18.0 | 专项 |
| Tailwind / shadcn | 5 | 16.0 | 中高频 |
| Supabase / Postgres | 4 | 14.0 | 专项 |
| Expo / React Native | 4 | 12.0 | 专项 |
| Vercel / Netlify / CF Pages | 2 | 8.0 | 专项 |
| macOS 桌面 / 原生（Swift） | 3 | 7.0 | 专项 |
| 单文件 HTML 工具 | 2 | 6.0 | 专项 |
| .NET / C# / Windows 桌面 | 2 | 6.0 | 专项 |
| Cloudflare | 1 | 5.0 | 专项 |
| Android / Kotlin | 1 | 3.0 | 专项 |
| Playwright / 浏览器自动化 | 1 | 3.0 | 低频 |
| Shell / 脚本 | 1 | 3.0 | 低频 |

## 五、明确不进入推荐方向的技术（平台错配依据，原 §5 尾部）

> 原文：「项目里完全没有涉及，不进入推荐方向」

`Kubernetes / 集群编排`、`Azure`、`AWS（Lambda / S3）`、`Django / DRF`、`Flutter / Dart`、
`Unity / 游戏引擎`、`Web3 / 智能合约`、`Kafka / 消息队列`、`Terraform / IaC`

「已出现但仅个别仓库命中，按需观察」：`GCP / Firebase`（2 个仓）

这条清单就是 `analyze.py` 里 `MISMATCH_KW` 的权威来源——**这就是为什么
`azure-ai-vision-imageanalysis-java`、`bigquery-ai-ml`、`managed-airflow-migrations`
这类候选会被判为平台错配并强制降权。** 若审查者认为该清单本身需要调整，错配判定的结果会随之变化。

## 六、需求 → 检索关键词（原 §6，bottom-up 发现族的输入）

按需求权重从高到低：

```
agent orchestration prompt engineering
pwa offline indexeddb
frontend design ui review
desktop app packaging cross platform
vercel deployment static hosting
python automation scripting
browser qa playwright e2e
llm api streaming structured output
investment dashboard finance analysis
whisper transcription knowledge base
voice input speech recognition
spec driven development plan task
expo react native
task management calendar integration
responsive web design
github automation actions workflow
rss aggregation data pipeline
```

## 七、规模变化（原 §7）

- 无影响推荐方向的变化（各需求权重波动均 < 2）。
- 规模：仓库 42 → 42，30 天内活跃 31 → 31，14 天内活跃 25 → 25。

---

## 复现提示

本摘要是**只读输入**，脚本不解析本文件——`analyze.py` 实际读取的是 `common.py`
的 `SKILL_CONTEXT_PATH` 指向的原始 `SKILL_CONTEXT.md`，解析其末尾的机器块
（`<!-- SKILL_CONTEXT_STATE ... -->`，含 `needs` / `tech` / `totals` 三组数字）。

因此本摘要**等效于**审查者复算 `PROJECT_MATCH` 所需的全部输入；若要真正跑通全链路，
需自行准备一份同结构的 `SKILL_CONTEXT.md`，或用环境变量指向自己的版本：
`SKILL_CONTEXT_PATH=/path/to/SKILL_CONTEXT.md`。

关键词映射表（24 项 needs 各自对应哪些关键词、以及「整词匹配」的实现在哪）见
`支撑/scripts/analyze.py` 中的 `NEED_KW` 与 `_bag()` / `_hit()`。
