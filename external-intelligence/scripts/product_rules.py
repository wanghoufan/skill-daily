# -*- coding: utf-8 -*-
"""v2.9 产品关系 / 能力领域 / 内部能力 判定层（External Skill Intelligence）。

为什么单独一个模块（而不是继续往 match_rules.py 里塞）：
  v2.4–v2.8 的产品判断全部是**关键词词典**（MISMATCH_KW / _PRODUCT_OPERATION_TERMS /
  self_dev 正则）。词典能识别「文本里出现了 Azure」，识别不了
  「这个 Skill 服务的对象是不是用户项目里那个产品的竞品」。
  本模块把这件事改成**关系数据 + 显式证据**：

    · 产品数据 = ../config/product_relationships.json（产品 ID / 名称 / 厂商 / 类别 /
      domain / 受控能力 / 竞品关系，每条竞品关系带依据）
    · 领域一律**派生**：PRODUCT_IN[product] = 该产品的 domain，
      capability_domain(kind, tech, product) 的优先级是
      product > tech > capability；绝不凭单个歧义词（insurance→aviation 那类）现编。
    · 名称/描述/仓库/来源 URL **只用于识别产品关系**，绝不单独构成
      低质量、安全风险或不相关结论（§二.1）。
    · 本文件不是缓存，不保存排名、安装状态、评分或推荐决策（§二.1）。

红线：
  · 只有「主要服务对象 / 官方集成对象 / 被扩展的产品本身」才算竞品关系；
    示例、列表、对比、provider 枚举、重定向句里的品牌词一律只算 mentioned（§二.6）。
  · 任何产品 Gate 都必须有可解除路径与解除证据，**不是永久 blacklist**（§二.8/§三.3.3）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_rules as MR                                            # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "config", "product_relationships.json")

# --------------------------------------------------------------------------
# 一、数据加载与完整性校验（§二.9）
# --------------------------------------------------------------------------
_CACHE = {}


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[\-_/]+", " ", (s or "").lower())).strip()


def load(path=None):
    """加载产品关系数据（带进程内缓存）。同一文件重复加载结果一致（确定性）。"""
    key = os.path.realpath(path or DATA_PATH)
    if key in _CACHE:
        return _CACHE[key]
    with open(key, encoding="utf-8") as f:
        d = json.load(f)
    d["_path"] = key
    _CACHE.clear()
    _CACHE[key] = d
    return d


def validate(d=None):
    """§二.9 数据完整性校验，返回错误清单（空 = 通过）。

    ① competitor_of 双向对称；② 不允许自己与自己竞争；③ 关系必须有依据；
    ④ 产品 ID/名称/domain 非空；⑤ domain/capability 可解析且非 matched_domain；
    ⑥ 每条 capability 有用途说明。
    """
    d = d or load()
    prods = d.get("products") or {}
    doms = set(d.get("domains") or {})
    caps = d.get("capabilities") or {}
    errs = []
    for pid, pr in sorted(prods.items()):
        if not str(pid).strip():
            errs.append("空产品ID")
        for f in ("name", "domain", "category", "vendor"):
            if not str(pr.get(f) or "").strip():
                errs.append(f"{pid}: {f} 为空")
        if pr.get("domain") not in doms:
            errs.append(f"{pid}: domain 不可解析 -> {pr.get('domain')}")
        for c in pr.get("capabilities") or []:
            if c in ("matched_domain", "domain"):
                errs.append(f"{pid}: matched_domain 被当成能力")
            if c not in caps:
                errs.append(f"{pid}: capability 不可解析 -> {c}")
        for c in pr.get("capabilities") or []:
            if c in caps and not str(caps.get(c) or "").strip():
                errs.append(f"{pid}: capability 缺用途说明 -> {c}")
        for r in pr.get("competitor_of") or []:
            other = r.get("product") if isinstance(r, dict) else None
            if not other:
                errs.append(f"{pid}: 竞品关系缺对端")
                continue
            if other == pid:
                errs.append(f"{pid}: 自己与自己竞争")
            if other not in prods:
                errs.append(f"{pid}: 竞品对端不存在 -> {other}")
                continue
            if not str(r.get("evidence") or "").strip():
                errs.append(f"{pid}->{other}: 竞品关系无依据")
            back = [x.get("product") for x in prods[other].get("competitor_of") or []
                    if isinstance(x, dict)]
            if pid not in back:
                errs.append(f"{pid}->{other}: competitor_of 不对称")
    for pid, terms in sorted((d.get("product_internal_capabilities") or {}).items()):
        if pid == "comment":
            continue
        if pid not in prods:
            errs.append(f"内部能力表: 产品不存在 -> {pid}")
        if not terms:
            errs.append(f"内部能力表: {pid} 清单为空")
    return errs


# --------------------------------------------------------------------------
# 二、派生索引（§二.4：产品所在领域只能派生，不得重复手写）
# --------------------------------------------------------------------------
def idx(d=None):
    """派生索引（PRODUCT_REF / PRODUCT_IN / COMPETITOR_OF / 能力→领域）。"""
    d = d or load()
    """一次性构建派生索引；结果按 key 排序，保证跨进程确定性。"""
    if d.get("_idx"):
        return d["_idx"]
    prods = d["products"]
    # PRODUCT_IN：产品 → 领域（派生）
    product_in = {pid: pr["domain"] for pid, pr in sorted(prods.items())}
    # PRODUCT_REF：品牌词（名称 / 别名 / agent slug）→ 产品 ID（长词优先，避免裸词抢匹配）
    ref = {}
    for pid, pr in sorted(prods.items()):
        terms = {pr.get("name"), pid}
        terms |= set(pr.get("aliases") or [])
        terms |= set(pr.get("agent_slugs") or [])
        for t in terms:
            t = _norm(t if isinstance(t, str) else "")
            if len(t) >= 2 and t not in ("unknown", "null"):
                ref.setdefault(t, []).append(pid)
    # 裸品牌词（claude / codex / gemini / copilot…）映射到**品牌族**，不是具体产品
    family = {}
    for t, pids in ref.items():
        if " " not in t and t not in GENERIC_ALIAS_STOP:
            family.setdefault(t, sorted(set(pids)))
    # COMPETITOR_OF：对称集合（数据层已校验，这里只做查表）
    comp = {pid: sorted({r["product"] for r in (pr.get("competitor_of") or [])
                         if isinstance(r, dict) and r.get("product")})
            for pid, pr in sorted(prods.items())}
    # 关系依据表：(a,b) -> evidence 文本
    why = {}
    for pid, pr in sorted(prods.items()):
        for r in pr.get("competitor_of") or []:
            if isinstance(r, dict):
                why[(pid, r.get("product"))] = r.get("evidence") or ""
    # 能力 → 领域 / 技术栈 → 领域（§三.3 capability_domain 的两条派生路径）
    cap_domain = {}
    for pid, pr in sorted(prods.items()):
        for c in pr.get("capabilities") or []:
            cap_domain.setdefault(c, set()).add(pr["domain"])
    idx = {"product_in": product_in, "product_ref": {k: sorted(v) for k, v in sorted(ref.items())},
           "brand_family": {k: v for k, v in sorted(family.items()) if len(v) > 1},
           "competitor_of": comp, "competitor_evidence": why,
           "cap_domain": {k: sorted(v) for k, v in sorted(cap_domain.items())},
           "agent_slug": {s: pid for pid, pr in sorted(prods.items())
                          for s in (pr.get("agent_slugs") or [])},
           # 产品自己的仓库（owner/repo）→ 用于 official_extension 判定（§二.2）
           "repo_product": {_norm(pr["repo"]): pid for pid, pr in sorted(prods.items())
                            if pr.get("repo")}}
    d["_idx"] = idx
    return idx


def product_domain(pid):
    """PRODUCT_IN：产品所在领域（唯一来源 = 产品数据里的 domain）。"""
    return idx()["product_in"].get(pid)


def competitors(pid):
    return idx()["competitor_of"].get(pid) or []


def competitor_evidence(a, b):
    return idx()["competitor_evidence"].get((a, b)) or ""


def brand_family(term):
    """裸品牌词（claude / codex / gemini / copilot）→ 同品牌多个产品；不自动选一个。"""
    return idx()["brand_family"].get(_norm(term)) or []


def capability_domain(capability_id=None, tech=None, product=None, text=None):
    """§三.3 统一领域派生：product > tech > capability > text 词面。

    任何一条路径都必须给出来源；返回 (domain|None, source, evidence_term)。
    歧义词不在这里发明领域 —— 词面兜底只查「已登记的领域关键词」，
    且要求该词已在数据里绑定到唯一领域（多义一律返回 None）。
    """
    i = idx()
    d = load()
    if product:
        dom = i["product_in"].get(product)
        if dom:
            return dom, "product", product
    if tech:
        dom = TECH_DOMAIN.get(_norm(tech))
        if dom:
            return dom, "project_tech_stack", tech
    if capability_id:
        doms = i["cap_domain"].get(capability_id) or []
        if len(doms) == 1:
            return doms[0], "project_capability", capability_id
    if text:
        t = _norm(text)
        for kw, dom in sorted(TOKEN_DOMAIN.items()):
            if kw in t:
                return dom, "explicit_term", kw
    return None, "none", None


# --------------------------------------------------------------------------
# 三、领域词典（全部可追溯到：项目技术栈 / 能力 / 产品 / 明确低优先级）
# --------------------------------------------------------------------------
# 技术栈 → 领域（§三.1「技术栈与运行平台」）
TECH_DOMAIN = {
    "expo": "expo-react-native-mobile", "react native": "expo-react-native-mobile",
    "expo / react native": "expo-react-native-mobile",
    "android": "android-mobile", "kotlin": "android-mobile",
    "android / kotlin": "android-mobile",
    "ios": "ios-mobile", "swift": "apple-macos", "swiftui": "apple-macos",
    "macos": "apple-macos", "macos 桌面": "apple-macos", "macos 桌面 / 原生": "apple-macos",
    "windows": "microsoft-windows", ".net": "dotnet", "c#": "dotnet",
    ".net / c# / windows 桌面": "dotnet",
    "supabase": "supabase-postgres", "postgres": "supabase-postgres",
    "supabase / postgres": "supabase-postgres",
    "playwright": "web-frontend", "pwa": "web-frontend",
    "vercel": "vercel-hosting", "netlify": "netlify-hosting",
    "cloudflare": "cloudflare-platform", "docker": "container-runtime",
    "kubernetes": "container-orchestration", "terraform": "infrastructure-as-code",
    "azure": "microsoft-azure", "aws": "aws-cloud", "gcp": "google-cloud",
    "google cloud": "google-cloud",
}
# 项目需求（SKILL_CONTEXT.md §4 needs 键）→ 领域（§三.1 第 2/3/4 项）
NEED_DOMAIN = {
    "agent-governance": ["ai-coding-agent"],
    "spec-driven": [],
    "github-auto": ["github-devops"],
    "llm-api": ["openai-assistants", "anthropic-assistants", "model-platform"],
    "deploy": ["vercel-hosting", "netlify-hosting", "cloudflare-platform"],
    "browser-qa": ["web-frontend"],
    "supabase-db": ["supabase-postgres"],
    "expo-rn": ["expo-react-native-mobile"],
    "android": ["android-mobile"],
    "desktop-app": ["apple-macos", "microsoft-windows"],
    "docker-infra": ["container-runtime"],
    "pwa-offline": ["web-frontend", "local-first"],
    "privacy-local": ["local-first"],
    "media-transcribe": ["speech-transcription"],
    "voice-input": ["voice-input"],
    "data-pipeline": [], "dashboard-viz": [], "finance-calc": ["financial-analysis"],
    "photo-mgmt": ["media-processing"], "frontend-design": ["design"],
    "responsive": ["web-frontend"], "python-auto": [], "task-integration": ["calendar"],
    "secret-safety": [], "data-analytics": [],
}
# 「词面 → 领域」兜底表：只收**无歧义**的产品/平台专有名词。
# 注意：insurance / voice / cloud / app 这类一词多义**不在表里**（§三.5 明确禁止用它们定领域）。
TOKEN_DOMAIN = {
    "azure": "microsoft-azure", "aws": "aws-cloud", "amazon web services": "aws-cloud",
    "gcp": "google-cloud", "google cloud": "google-cloud", "bigquery": "google-cloud",
    "vertex ai": "google-cloud", "salesforce": "salesforce-crm", "servicenow": "service-now",
    "dynamics 365": "microsoft-office", "sharepoint": "microsoft-office",
    "snowflake": "snowflake-warehouse", "databricks": "databricks-lake",
    "oracle": "oracle-db", "power bi": "powerbi-analytics", "powerbi": "powerbi-analytics",
    "microsoft store": "microsoft-windows", "kubernetes": "container-orchestration",
    "terraform": "infrastructure-as-code", "airflow": "apache-airflow",
    "browseros": "agentic-browser", "openai": "openai-assistants",
    "anthropic": "anthropic-assistants",
}
# 产品领域 → 是否「产品/平台领域」（决定它能不能占用平台错配审计字段，§三.5）
STACK_DOMAINS = {"dotnet", "java-jvm", "web-frontend", "container-runtime",
                 "terminal-cli", "ide-editor"}
# 跨端 / 跨平台领域：只要项目里有任一端的真实证据即视为适用（§三.1）
DOMAIN_SATISFIED_BY = {
    "cross-platform-desktop": {"ios-mobile", "android-mobile", "apple-macos",
                               "microsoft-windows", "web-frontend"},
    "agentic-browser": {"web-frontend"},
    "expo-react-native-mobile": {"android-mobile", "ios-mobile"},
}

# v2.9 领域 → v2.4 旧口径域名（§三.9 兼容：审计字段沿用旧名，新语义写在 *_v29 里）
V29_TO_LEGACY = {
    "microsoft-azure": "azure", "google-cloud": "gcp", "aws-cloud": "aws",
    "java-jvm": "java", "dotnet": "dotnet", "container-orchestration": "kubernetes",
    "container-runtime": "docker", "infrastructure-as-code": "terraform",
    "oracle-db": "oracle", "salesforce-crm": "salesforce", "sap-erp": "sap",
    "snowflake-warehouse": "snowflake", "databricks-lake": "databricks",
    "apache-airflow": "airflow", "microsoft-store": "microsoft-store",
    "microsoft-office": "microsoft-business", "microsoft-windows": "windows",
    "apple-macos": "macos", "ios-mobile": "ios", "android-mobile": "android",
    "expo-react-native-mobile": "expo-rn", "agentic-browser": "browser",
    "powerbi-analytics": "powerbi", "github-devops": "github",
    "supabase-postgres": "supabase", "vercel-hosting": "vercel",
    "netlify-hosting": "netlify", "cloudflare-platform": "cloudflare",
    "service-now": "servicenow", "huggingface-hub": "huggingface",
    "m365-copilot": "m365-copilot", "knowledge-base": "obsidian",
    "content-pipeline": "rss", "local-first": "local-first",
    "web-frontend": "web", "terminal-cli": "cli", "ide-editor": "ide",
    "openai-assistants": "openai", "anthropic-assistants": "anthropic",
    "ai-coding-agent": "coding-agent", "quant-trading": "quant",
    "assistant-product": "assistant", "model-platform": "model-api",
    "model-hub": "model-hub", "distribution-platform": "store",
    "language-runtime": "runtime", "app-framework": "framework",
    "data-platform": "data", "analytics-platform": "analytics",
    "database-platform": "database", "hosting-platform": "hosting",
    "dev-platform": "devops", "saas-platform": "saas", "orchestration": "orchestration",
    "finance": "finance", "voice": "voice", "embedded": "embedded",
    "speech": "speech", "design": "design",
}


def legacy_domain(dom):
    return V29_TO_LEGACY.get(dom, dom)


# 平台/产品领域全集（派生自产品数据，不手写第二份）
def platform_domains():
    return {dom for dom in idx()["product_in"].values()} - STACK_DOMAINS


# --------------------------------------------------------------------------
# 四、产品关系识别（§二.2 / §二.3 / §二.10）
# --------------------------------------------------------------------------
# 开发工具关系：候选**开发 / 扩展 / 测试 / 集成 / 运维**某个产品
_DEV_PATTERNS = [
    r"\b(?:build|building|develop|developing|create|creating|write|writing|code|coding|"
    r"test|testing|debug|debugging|extend|extending|integrate|integrating|automate|"
    r"automating|configure|configuring|contribute|review|ship|release)\b[^.!?\n]{0,70}?\b{t}\b",
    r"\b{t}\b[^.!?\n]{0,45}?\b(?:plugin|plugins|extension|extensions|skill|skills|mcp|"
    r"server|sdk|api|cli|agent|agents|subagent|subagents|hook|hooks|command|commands|"
    r"integration|integrations|add-on|addon|template|templates|agent skills)\b",
    r"\b(?:for|in|with|inside|against|using)\s+(?:the\s+)?{t}\b"
    r"[^.!?\n]{0,45}?\b(?:plugin|extension|skill|mcp|sdk|api|cli|agent|automation|test|build)\b",
    r"\b(?:works?\s+with|compatible\s+with)\s+(?:the\s+)?{t}\b",
]
# 主要目标产品：候选内容/运营/管理/发布**面向**该产品（该产品是交付对象）
_TARGET_PATTERNS = [
    r"\b(?:generate|creating|write|writing|optimize|optimizing|produce|producing|manage|"
    r"managing|operate|operating|publish|publishing|post|posting|draft|drafting|"
    r"personalize|schedule|booking|plan|planning)\b[^.!?\n]{0,70}?\b{t}\b",
    r"\b{t}\b[^.!?\n]{0,45}?\b(?:content|copy|campaign|campaigns|ads|video|videos|"
    r"podcast|channel|profile|account|workspace|workspaces|settings|dashboard|workflow|"
    r"workflows|subscription|plan|plans|usage|metrics|reports?|knowledge|projects?|"
    r"notes?|memor(?:y|ies)|automations?|connectors?)\b",
    r"\b(?:for|to|in)\s+(?:the\s+|my\s+|your\s+)?{t}\b"
    r"[^.!?\n]{0,45}?\b(?:notes?|memory|automations?|projects?|files?|content|posts?)\b",
]
# 明确只是「举例 / 枚举 / 对比」的语境（§二.6：不构成竞品证据）
# 通用集成协议（MCP / 标准 API 客户端）不构成排他性产品关系（§四.2 / §二.10 案例 13）
_INTEGRATION_GENERIC_RE = re.compile(
    r"\b(?:mcp|model context protocol|rest api|openapi|webhook|oauth|"
    r"standard (?:api|protocol)|any (?:agent|mcp client))\b", re.I)


def is_generic_integration(ref):
    """候选与该产品的关系只是「通用协议集成」→ 不算排他关系，也不算内部能力。"""
    return bool(_INTEGRATION_GENERIC_RE.search(ref.get("quote") or ""))


# 同一小句里的通用集成语境（MCP / 标准 API / SDK / client-server）：
# 既不构成产品内部能力（§四.2），也不构成排他竞品关系（§二.6）。
_INTEGRATION_SEG_RE = re.compile(
    r"\b(?:mcp|model context protocol|rest api|openapi|webhook|oauth|sdk|api|"
    r"server|client|integrat\w*|connect\w*|expose\w*)\b", re.I)


_LISTY_RE = re.compile(r"\b(?:e\.g\.|for example|such as|including|includes?\b|vs\.?\b|"
                       r"compared (?:to|with)|alternatives?|providers?|supports?\b|"
                       r"languages?:|platforms?:|works across)\b[^.!?\n]{0,120}", re.I)


def _views(cand):
    """候选的可查视图：名称 / 仓库 / 来源 URL / 描述正向视图（否定与重定向已剪）。"""
    name = cand.get("skill_name") or cand.get("name") or ""
    desc = cand.get("description") or ""
    ctx = MR._ctx(name, desc)
    repo = _norm(f"{cand.get('owner') or ''}/{cand.get('repo') or ''}")
    url = _norm(cand.get("source_url") or cand.get("skillmd_url") or "")
    return {"name": ctx["name_norm"], "raw_name": name.lower(), "desc_pos": ctx["ptext"],
            "norm_pos": ctx["pnorm"], "text_raw": ctx["text"], "repo": repo, "url": url,
            "ctx": ctx}


def _find_terms(v, terms, views=("name", "repo", "desc_pos", "url")):
    """在候选各视图里找产品词，返回 [(term, source, quote)]；同一词只取一个来源。"""
    out = []
    seen = set()
    for term in sorted(terms, key=lambda x: (-len(x), x)):
        t = _norm(term)
        if len(t) < 2 or t in seen:
            continue
        for src in views:
            blob = v[src]
            pos = blob.find(t)
            if pos < 0:
                continue
            # 英文词要求整词边界（避免 `app` 命中 `apple`；CJK 词无词边界，直接子串）
            if re.fullmatch(r"[a-z0-9#\. ]+", t) and not re.search(
                    rf"(^|[^a-z0-9]){re.escape(t)}([^a-z0-9]|$)", blob):
                continue
            quote = blob[max(0, pos - 60):pos + len(t) + 60].strip()
            seen.add(t)
            out.append((t, src, quote))
            break
    return out


# 通用词停用表：这些词**不能**当产品识别词（否则 `skills` / `settings` / `app`
# 之类会把上千条候选全部标成「与某产品有关系」——实测 skills 一个词命中 3264 次）。
GENERIC_ALIAS_STOP = {
    "app", "apps", "web", "cloud", "chat", "image", "code", "test", "tests", "testing",
    "cli", "sdk", "api", "apis", "agent", "agents", "plugin", "plugins", "extension",
    "extensions", "skill", "skills", "workflow", "workflows", "automation", "automations",
    "memory", "memories", "settings", "config", "plan", "plans", "review", "analytics",
    "data", "model", "models", "datasets", "storage", "hub", "functions", "forms",
    "edge", "pages", "server", "metrics", "deployment", "distribution", "migration",
    "validation", "submission", "signing", "pricing", "publish", "package", "release",
    "ci", "cd", "runtime", "framework", "assistant", "account", "workspace",
    "dashboard", "content", "copy", "ads", "notes", "knowledge", "project", "projects",
    "artifacts", "contributing", "games", "iot", "quantum", "graphics", "ml", "mobile",
    "desktop", "report", "reports", "subscription", "usage", "container", "compose",
    "billing", "it", "dev", "admin", "integration", "indicators", "alerts", "screens",
    "radar", "warehouse", "lakehouse", "etl", "crm", "erp", "transaction", "performance",
    "repo", "docs", "server side", "webhooks", "completion", "mcp", "tune", "debug",
    "build", "rebuild", "review app", "onboarding", "customer", "marketing", "product",
}


def _ref_terms(pr):
    """产品的可查识别词：名称 + 非通用别名 + agent slug（不含通用词，见停用表）。"""
    out = set()
    for x in {pr.get("name")} | set(pr.get("aliases") or []) | set(pr.get("agent_slugs") or []):
        n = _norm(x if isinstance(x, str) else "")
        if len(n) >= 2 and n not in GENERIC_ALIAS_STOP:
            out.add(n)
    return out


def _covered_by_longer(v, hit, pid):
    """§二.10：`Microsoft 365 Copilot` 里的 `copilot` 不得再算成 GitHub Copilot 的关系。

    短词命中的文本区间若被**别的产品**的更长别名命中完全覆盖，则短词只是长词的一部分。
    """
    term, src, _q = hit
    d = load()
    i = idx()
    blob = v[src]
    pos = blob.find(term)
    if pos < 0:
        return False
    lo, hi = pos, pos + len(term)
    for other, pids in i["product_ref"].items():
        if other == term or len(other) <= len(term) or pid in pids:
            continue
        p = blob.find(other)
        while p >= 0:
            if p <= lo and p + len(other) >= hi:
                return True
            p = blob.find(other, p + 1)
    return False


def product_refs(cand):
    """§二.2：返回 [{product_id, ref_type, matched_terms, evidence_source, quote}]。

    ref_type ∈ developer_tool / primary_target / official_extension / mentioned / ambiguous。
    §二.2 产品官方仓库自身 → official_extension（按 owner/repo 精确相等，不按仓库名片段）。
    §二.3 只有名字含品牌词、描述没有产品专属动作 → 一律降级 mentioned。
    §二.10 同一裸品牌词映射多个产品且无单一语境证据 → ambiguous，关系不成立。
    来源 URL **只**用于 official_extension：github.com/... 这类宿主域名绝不参与品牌匹配。
    """
    d = load()
    i = idx()
    v = _views(cand)
    own_repo = _norm(f"{cand.get('owner') or ''}/{cand.get('repo') or ''}")
    refs = []
    for pid, pr in sorted(d["products"].items()):
        found = _find_terms(v, sorted(_ref_terms(pr)), views=("name", "desc_pos"))
        found = [x for x in found if not _covered_by_longer(v, x, pid)]
        is_own_repo = bool(pr.get("repo")) and own_repo == _norm(pr["repo"])
        if not found and not is_own_repo:
            continue
        ambig = [x for x, _s, _q in found
                 if len(i["product_ref"].get(x, [])) > 1
                 and x in i["brand_family"]]
        dev_q = tgt_q = None
        for x, _src, _quote in found:
            for pat in _DEV_PATTERNS:
                m = re.search(pat.replace("{t}", re.escape(x)), v["desc_pos"], re.I)
                if m:
                    dev_q = m.group(0).strip()[:120]
                    break
            if dev_q:
                break
            for pat in _TARGET_PATTERNS:
                m = re.search(pat.replace("{t}", re.escape(x)), v["desc_pos"], re.I)
                if m:
                    tgt_q = m.group(0).strip()[:120]
                    break
            if tgt_q:
                break
        only_listy = False
        if not (dev_q or tgt_q) and found:
            segs = [s for s in re.split(r"(?<=[.!?])\s", v["desc_pos"])
                    if any(x in s for x, _s2, _q2 in found)]
            only_listy = bool(segs) and all(_LISTY_RE.search(s) for s in segs)
        srcs = sorted({s for _t, s, _q in found} | ({"repo"} if is_own_repo else set()))
        terms = [x for x, _s, _q in found][:6]
        if is_own_repo and not (dev_q or tgt_q):
            refs.append({"product_id": pid, "ref_type": "official_extension",
                         "matched_terms": terms or [_norm(pr["repo"])],
                         "evidence_source": ["repo"], "quote": f"repo:{own_repo}"[:160],
                         "product_domain": pr["domain"],
                         "product_capabilities": sorted(pr.get("capabilities") or []),
                         "list_context_only": False})
            continue
        if ambig and not (dev_q or tgt_q):
            refs.append({"product_id": pid, "ref_type": "ambiguous",
                         "matched_terms": terms, "evidence_source": srcs,
                         "candidate_products_for_term": i["brand_family"][ambig[0]],
                         "quote": found[0][2][:120],
                         "note": "裸品牌词映射多个产品且无单一语境证据，不自动选一个（§二.10）"})
            continue
        if dev_q:
            rt, q = "developer_tool", dev_q
        elif tgt_q:
            rt, q = "primary_target", tgt_q
        else:
            rt, q = "mentioned", (found[0][2] if found else own_repo)
        refs.append({"product_id": pid, "ref_type": rt, "matched_terms": terms,
                     "evidence_source": srcs, "quote": q[:160],
                     "product_domain": pr["domain"],
                     "product_capabilities": sorted(pr.get("capabilities") or []),
                     "list_context_only": bool(only_listy)})
    return sorted(refs, key=lambda r: (r["product_id"], r["ref_type"]))


STRONG_REF_TYPES = ("developer_tool", "primary_target", "official_extension")


def competitor_conflicts(refs, installed_products):
    """§二.5：竞品关系 = 候选关系产品 与 已装产品 构成 competitor_of。

    只有 developer_tool / primary_target 才进入竞品判断；
    mentioned / ambiguous / 仅示例枚举 **绝不**构成竞品证据（§二.3/§二.6）。
    """
    out = []
    inst = sorted(set(installed_products or {}))
    for r in refs:
        if r["ref_type"] not in STRONG_REF_TYPES:
            continue
        if r.get("list_context_only"):
            continue
        if is_generic_integration(r):
            continue            # §四.2：MCP / 标准协议只是通用集成能力
        pid = r["product_id"]
        for ip in inst:
            if ip == pid:
                continue
            if ip in competitors(pid):
                out.append({"candidate_product": pid,
                            "installed_product": ip,
                            "relation": "competitor_of",
                            "evidence": competitor_evidence(pid, ip),
                            "ref_type": r["ref_type"],
                            "candidate_quote": r["quote"],
                            "matched_terms": r["matched_terms"][:4]})
    return sorted(out, key=lambda x: (x["candidate_product"], x["installed_product"]))


# --------------------------------------------------------------------------
# 五、项目侧能力清单：六节（§三.2）
# --------------------------------------------------------------------------
# 六节 ID（顺序固定，便于审计与 diff）
SECTIONS = ("tech_platform", "core_business", "task_types",
            "dev_workflow", "positioning_integration", "low_priority")
SECTION_LABEL = {
    "tech_platform": "技术栈与运行平台",
    "core_business": "项目核心业务能力",
    "task_types": "主要任务类型",
    "dev_workflow": "开发流程",
    "positioning_integration": "产品定位与集成",
    "low_priority": "明确低优先级 / 排除项",
}
# 需求键 → 归入哪几节（SKILL_CONTEXT.md 机器块的 needs 键）
_NEED_SECTION = {
    "agent-governance": ("dev_workflow", "task_types"),
    "spec-driven": ("dev_workflow", "task_types"),
    "github-auto": ("dev_workflow", "task_types"),
    "docker-infra": ("dev_workflow", "tech_platform"),
    "deploy": ("task_types", "tech_platform"),
    "browser-qa": ("task_types", "tech_platform"),
    "android": ("task_types", "tech_platform"),
    "python-auto": ("task_types",),
    "data-pipeline": ("task_types", "core_business"),
    "dashboard-viz": ("core_business", "task_types"),
    "finance-calc": ("core_business",),
    "photo-mgmt": ("core_business",),
    "media-transcribe": ("core_business", "task_types"),
    "voice-input": ("core_business", "task_types"),
    "llm-api": ("core_business", "tech_platform"),
    "supabase-db": ("tech_platform", "core_business"),
    "pwa-offline": ("positioning_integration", "tech_platform"),
    "privacy-local": ("positioning_integration",),
    "frontend-design": ("task_types",),
    "responsive": ("task_types",),
    "desktop-app": ("task_types", "tech_platform"),
    "expo-rn": ("tech_platform", "task_types"),
    "secret-safety": ("dev_workflow",),
    "task-integration": ("core_business",),
    "data-analytics": ("core_business",),
}
# 定位/集成短语（从项目描述里取，§三.1 第 5 项）
_POSITIONING = {
    "本地优先": "local-first", "离线": "local-first", "单文件": "local-first",
    "个人使用": "local-first", "隐私": "local-first", "免费": "local-first",
    "supabase": "supabase-postgres", "postgres": "supabase-postgres",
    "vercel": "vercel-hosting", "netlify": "netlify-hosting",
    "cloudflare": "cloudflare-platform", "github": "github-devops",
    "playwright": "web-frontend", "pwa": "web-frontend",
    "macos": "apple-macos", "windows": "microsoft-windows",
    "android": "android-mobile", "ios": "ios-mobile",
    "obsidian": "knowledge-base", "rss": "content-pipeline",
}
_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.M)


def _md_sections(text):
    """把 SKILL_CONTEXT.md 切成 {标题: 正文} （标题去掉编号前缀）。"""
    out, cur, buf = {}, None, []
    for line in (text or "").split("\n"):
        m = _HEADING_RE.match(line)
        if m:
            if cur:
                out[cur] = "\n".join(buf)
            cur, buf = re.sub(r"^\d+\.\s*", "", m.group(1)).strip(), []
        elif cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return out


def _bullets(block):
    items = []
    for line in (block or "").split("\n"):
        s = line.strip()
        if s.startswith("- "):
            items.append(s[2:].strip())
    return items


def project_sections(ctx_text=None, projects=None, state=None):
    """§三.2：从输入 A 派生六节能力清单，每项带 source（可追溯，§三.6）。

    返回 {section_id: [ {"term":…, "source":…, "domain":…?} ]}
    """
    blocks = _md_sections(ctx_text or "")
    state = state or {}
    sec = {k: [] for k in SECTIONS}

    def add(sid, term, source, domain=None):
        term = str(term or "").strip()
        if not term:
            return
        key = (_norm(term), sid)
        if key in _seen:
            return
        _seen.add(key)
        sec[sid].append({"term": term, "source": source,
                         "domain": domain or TECH_DOMAIN.get(_norm(term))})

    _seen = set()
    # ① 技术栈与运行平台：§3 高频技术栈 + 机器块 tech + 项目行技术栈
    for head, block in blocks.items():
        # §3 的技术栈条目挂在 h3 子标题（高频 / 中高频 / 专项）下，标题里没有「技术栈」三字
        if ("技术栈" in head or head in ("高频", "中高频", "专项")) \
                and not any(k in head for k in ("优先级", "需求", "变化")):
            for b in _bullets(block):
                term = b.split("—")[0].strip()
                add("tech_platform", term, f"输入A§{head}")
    for t in sorted((state.get("tech") or {})):
        add("tech_platform", t, "输入A机器块tech")
    for p in (projects or []):
        for t in (p.get("tech") or []):
            add("tech_platform", t, f"输入A项目行:{p.get('name')}")
    # ②③④ 业务能力 / 任务类型 / 开发流程：§4 需求 + 机器块 needs + §5 优先级
    for head, block in blocks.items():
        if "低优先级" in head:
            continue                                   # 排除项单独解析，绝不当任务类型
        if "开发需求" in head or "优先级" in head:
            for b in _bullets(block):
                term = b.split("—")[0].strip()
                if not term or term.startswith(("P0", "P1", "P2", "影响")):
                    continue
                if re.match(r"^(此外|项目里完全没有|已出现但)", term):
                    continue                           # 说明性散文，不是能力项
                add("task_types", term, f"输入A§{head}")
    for nid in sorted((state.get("needs") or {})):
        for sid in _NEED_SECTION.get(nid, ("task_types",)):
            add(sid, nid, "输入A机器块needs")
        # 需求本身也派生领域（§三.1 第 2/3/4 项），否则「Agent 治理」这类需求永远无领域
        for dom in NEED_DOMAIN.get(nid) or []:
            add("core_business", nid, "输入A机器块needs", dom)
    # ①⑤ 项目行 / 项目描述里明确出现的平台与集成词（云端、桌面、移动运行环境）
    for p in (projects or []):
        blob = _norm(f"{p.get('name')} {p.get('desc')} {' '.join(p.get('tech') or [])}")
        for term, dom in sorted(_POSITIONING.items()):
            if term in blob:
                add("positioning_integration", term,
                    f"输入A项目定位:{p.get('name')}", dom)
        for kw, dom in sorted(TOKEN_DOMAIN.items()):
            if re.search(rf"(^|[^a-z0-9]){re.escape(kw)}([^a-z0-9]|$)", blob):
                add("tech_platform", kw, f"输入A项目行:{p.get('name')}", dom)
    # ⑥ 明确低优先级 / 排除项：§5「当前低优先级」小节
    for head, block in blocks.items():
        if "低优先级" not in head:
            continue
        for b in _bullets(block) + [x.strip("># ").strip() for x in block.split("\n")]:
            b = re.sub(r"^(项目里完全没有[^:：]*|已出现但[^:：]*)[:：]", "", b)
            for part in re.split(r"[、,，;；/]", re.sub(r"（.*?）|\(.*?\)", "", b)):
                part = part.strip(" -—>")
                if len(part) >= 2 and not part.startswith(
                        ("不进入", "按需观察", "项目里完全", "已出现但", "GCP /")):
                    add("low_priority", part, f"输入A§{head}")
    for sid in SECTIONS:
        sec[sid] = sorted(sec[sid], key=lambda x: (x["term"], x["source"]))
    return sec


def _domains_of_items(items):
    out = set()
    for it in items:
        dom = it.get("domain")
        if dom:
            out.add(dom)
        for kw, d in sorted(TOKEN_DOMAIN.items()):
            if kw in _norm(it.get("term")):
                out.add(d)
    return out


def project_primary_domains(sections):
    """§三.1：项目主要领域只从前五节派生（明确低优先级单列，不算主要领域）。"""
    doms = set()
    for sid in ("tech_platform", "core_business", "task_types",
                "dev_workflow", "positioning_integration"):
        doms |= _domains_of_items(sections.get(sid) or [])
    return doms


def project_excluded_domains(sections):
    return _domains_of_items(sections.get("low_priority") or [])


def project_required_capabilities(sections):
    """项目所需能力（六节里的受控能力词），供竞品解除判定 §二.7 第 2 条使用。"""
    caps = set()
    for sid in ("core_business", "task_types", "dev_workflow", "positioning_integration"):
        for it in sections.get(sid) or []:
            t = _norm(it.get("term"))
            for c in sorted(load()["capabilities"]):
                if c in t or t in c:
                    caps.add(c)
    return caps


# --------------------------------------------------------------------------
# 六、领域三态（§三.3）与产品 Gate 领域三态（§三.4）
# --------------------------------------------------------------------------
def candidate_domains(cand, refs=None):
    """候选领域 = 产品关系领域 ∪ 已登记技术栈/平台词领域 ∪ 命中能力的派生领域。

    返回 {domain: {"source":…, "evidence":…}}；一律可追溯（§三.6）。
    歧义词（insurance / voice / cloud / app…）不在任何词典里 → 不会凭空产生领域。
    """
    out = {}
    for r in (refs if refs is not None else product_refs(cand)):
        if r["ref_type"] in STRONG_REF_TYPES:
            dom = product_domain(r["product_id"])
            if dom:
                out.setdefault(dom, {"source": "product_relation",
                                     "evidence": f"{r['product_id']}:{r['ref_type']}"})
    v = _views(cand)
    blob = f"{v['name']} {v['desc_pos']}"
    for kw, dom in sorted(TOKEN_DOMAIN.items()):
        if re.search(rf"(^|[^a-z0-9]){re.escape(kw)}([^a-z0-9]|$)", blob):
            out.setdefault(dom, {"source": "explicit_platform_term", "evidence": kw})
    for cap in sorted((cand.get("capability_tags") or [])):
        dom, src, ev = capability_domain(capability_id=cap)
        if dom:
            out.setdefault(dom, {"source": src or "capability", "evidence": cap})
    return out


def domain_state(cand, sections, refs=None, installed_products=()):
    """§三.3：适用 / 不适用 / 信息不足 三态。

    「适用」证据有三类：① 项目六节（技术栈/能力/任务/流程/定位）里出现该领域；
    ② 用户本机**已在用**该产品或同品牌产品（安装即使用证据）；
    ③ 该领域只是技术栈差异（secondary），不构成平台排除。
    """
    cd = candidate_domains(cand, refs)
    primary = set(project_primary_domains(sections))
    d = load()
    for pid in sorted(set(installed_products or {})):
        pr = d["products"].get(pid) or {}
        dom = pr.get("domain")
        if dom:
            primary.add(dom)
        for cap in pr.get("capabilities") or []:
            for x in idx()["cap_domain"].get(cap) or []:
                primary.add(x)
    excluded = project_excluded_domains(sections)
    plat = platform_domains()
    domains = set(cd)
    primary |= {d for d in domains
                if primary & (DOMAIN_SATISFIED_BY.get(d) or set())}
    applicable = sorted(domains & primary)
    excluded_hit = sorted(domains & excluded)
    stack_only = sorted(d for d in domains if d in STACK_DOMAINS or d not in plat)
    hard = sorted(d for d in domains if d in plat)
    unresolved = [d for d in hard if d not in primary and d not in excluded]
    if excluded_hit:
        state = "not_applicable"
    elif unresolved:
        state = "insufficient_info"
    else:
        state = "applicable"
    return {
        "state": state,
        "candidate_domains": sorted(domains),
        "applicable_evidence": [{"domain": x, **cd[x]} for x in applicable],
        "exclusion_evidence": [{"domain": x, **cd[x]} for x in excluded_hit],
        "unresolved": [{"domain": x, "reason": "候选声明该产品/平台领域，项目六节里无该领域证据且未列入排除项",
                        "evidence": cd[x], "resolution_test":
                            "任一项目技术栈/能力/产品集成指向该领域，或该领域未被明确列为低优先级"}
                       for x in unresolved],
        "secondary_stack_domains": stack_only,      # §三.5：只是另一种技术栈 → 次要信号
        "hard_platform_domains": hard,
    }


def scope_state(cand, sections, refs=None):
    """§三.4：产品 Gate 的领域三态 —— 产品领域必须映射到项目**哪一节**能力。

    high   = 候选服务对象所在的节里能找到同一领域/能力证据
    medium = 只靠关键词或同一大类间接对应
    low    = 只有名称相似，无法说明为何需要该产品
    """
    refs = refs if refs is not None else product_refs(cand)
    primary = project_primary_domains(sections)
    excluded = project_excluded_domains(sections)
    out = []
    for r in refs:
        if r["ref_type"] not in STRONG_REF_TYPES:
            continue
        dom = product_domain(r["product_id"]) or ""
        hit_sections = sorted({sid for sid in SECTIONS[:5]
                               for it in sections.get(sid) or []
                               if it.get("domain") == dom or _norm(it.get("term")) == _norm(r["product_id"])})
        conf = "high" if hit_sections else ("medium" if dom in primary or dom in excluded else "low")
        out.append({"product_id": r["product_id"], "product_domain": dom,
                    "project_scope_section": hit_sections[0] if hit_sections else None,
                    "confidence": conf, "quote": r["quote"][:120],
                    "note": None if hit_sections else "只有品牌词命中，无法说明项目为何需要该产品"})
    return out


# --------------------------------------------------------------------------
# 七、已装产品派生（§二.6：不得硬编码「本机装了 Codex / Claude Code」）
# --------------------------------------------------------------------------
def installed_products(installed_ids, agent_slugs=(), source_map=None):
    """已装产品 = 已装**智能体/产品本身**的证据映射出来的产品，不是「装了某官方 Skill」。

    证据来源（§二.11）：
      ① 已装侧身份档案里的 agent 标识（AGENT_AVAILABILITY 矩阵的 `<skill>/<agent>`）
      ② 已装 Skill 的身份档案里明确的宿主产品
    **绝不**因为「装了 anthropics/skills 的 Skill」就认定装了 Claude Code。
    返回 {product_id: [证据, …]}。
    """
    out = {}
    i = idx()
    for slug in sorted(set(_norm(s) for s in agent_slugs if s)):
        pid = i["agent_slug"].get(slug)
        if pid:
            out.setdefault(pid, []).append(f"agent_slug:{slug}")
    for sid in sorted(set(_norm(s) for s in installed_ids if s)):
        # 已装 Skill 名与产品同名的（如已装 browseros-neo → BrowserOS），只认**产品别名精确相等**
        for t, pids in i["product_ref"].items():
            if sid == t or (len(t) >= 4 and re.match(rf"^{re.escape(t)}(-|$)", sid)):
                for pid in pids:
                    out.setdefault(pid, []).append(f"installed_skill:{sid}->{pid}")
    return out


# --------------------------------------------------------------------------
# 八、产品内部能力与 Gate 结论（§四）
# --------------------------------------------------------------------------
# 只有「与产品无关也说得通」的词排除在外；`memories` / `automations` / `settings`
# 这类**必须与产品词同句共现**才算内部能力（§四.2 的护栏是共现，不是删词）。
_INTERNAL_GENERIC = {"mcp", "test", "tests", "testing", "release", "plugin", "plugins",
                     "docs", "contributing"}
# §四.2 的护栏：只有「产品自己命名的内置功能」才算内部能力。
# issues / actions / storage / metrics 这类词在任何产品里都说得通，属于**通用产品集成**。
_INTERNAL_FEATURES = {
    "memories", "memory", "automations", "automation", "settings", "config",
    "agent 配置", "内置 skills 目录", "cloud tasks", "app-autopilot",
    "claude.md", "settings.json", "subagent 定义", "output styles",
    "opencode.json", "tui 配置", "内置智能体", "内建 agents", "geminim.md",
    "artifacts", "knowledge items", "workflows",
    "app ui", "extension ui", "browser core", "browser engine", "内置 agent",
    "发布产物", "vpn 内核", "computer-use", "orchestration", "orca-cli",
    "容器内建能力", "工作区管理", "plan", "deep research", "ppt", "data table",
    "语音", "copilot 指令文件", "declarative agents", "copilot chat",
    "agent mode", "tenant 设置", "copilot 后台", "商店发布管线", "sandbox 测试",
    "ingestion 测试", "msstore 提交", "提交校验", "隐私标签", "定价与 iap 配置",
    "testflight", "play console 发布", "billing 配置", "内部构建产物",
    "平台内部发布管线", "项目设置", "microfrontends 控制面", "observability 面板",
    "站点设置", "forms 后台", "workers 运行时", "pages 发布管线", "kv 命名空间",
    "spaces 运行时", "hub 设置", "rls 策略", "edge functions 部署管线",
    "仓库内部构建管线", "资源提供程序", "订阅策略", "azure devops 内部管线",
    "服务配额", "iam 策略内部项", "bedrock 知识库", "平台配额", "组织设置",
    "模型微调管线", "ga admin api", "secops 规则", "chronicle 检测", "组织策略",
}
_SELF_DEV_VERBS = (r"test|tests|testing|develop|developing|debug|debugging|maintain|"
                   r"maintaining|contribute|build|building|package|packaging|release|"
                   r"publish|ci|cd|pipeline|refactor")
_PRODUCT_ARTIFACTS = (r"app|application|extension|core|engine|codebase|monorepo|source|"
                      r"internals|ui|dashboard|repo|repository|binary|artifact|website")


def _cooccur(blob, term, pid, window=110):
    """§四.2 红线：内部功能名必须与「该产品自身的词」同句共现才算。

    反例（不得成立）：某 Skill 只说「为任何智能体提供 memory」却提到过 Claude；
    正例：BrowserOS `test-ui`「Test the BrowserOS app extension UI」。
    """
    if not term or term not in blob:
        return False
    if not _product_terms(pid, include_brand=True):
        return False
    for m in re.finditer(re.escape(term), blob):
        seg = blob[max(0, m.start() - window):m.end() + window]
        if any(x in seg for x in _product_terms(pid, include_brand=True)):
            return True
    return False


def source_product(cand):
    """候选**自身来源**是不是某个产品的官方仓库（§四.2 的前提条件）。"""
    i = idx()
    repo = _norm(cand.get("repo"))
    owner = _norm(cand.get("owner"))
    for pid, pr in sorted(load()["products"].items()):
        r = _norm(pr.get("repo") or "")
        if r and (repo and (r == repo or r.split("/")[-1] == repo or repo.endswith(r.split("/")[-1]))):
            return pid
        if r and owner and owner == r.split("/")[0]:
            return pid
    return None


_MANAGE_VERB_RE = re.compile(
    r"\b(?:manag(?:e|ing|ement)|organiz(?:e|ing)|edit(?:ing)?|modify|modifying|author|"
    r"configur(?:e|ing)|set ?up|clean ?up|write|writing|create|creating|build|building|"
    r"packag(?:e|ing)|release|releasing|ship|shipping|debug|debugging|test|testing|"
    r"extend|plugin|develop|developing|govern|audit|wire up|wiring)\b", re.I)


def internal_via_ref(cand, refs):
    """§四.2 第二支：描述明确说明修改/管理该产品**自身的内置功能或设置**。

    成立条件：候选与该产品存在 developer_tool / primary_target 关系，
    且该产品的内部功能名与产品词**同句共现**。
    反例（不得成立）：只说「给任何智能体加 memory」的通用能力 Skill。
    """
    terms_by_pid = {}
    for r in refs:
        if r["ref_type"] not in STRONG_REF_TYPES:
            continue
        if is_generic_integration(r):
            continue            # §四.2：通用协议集成 ≠ 产品内部能力
        # §四.2：只「提到」内置功能不算，必须有操作/开发该内置功能的动词
        if not _MANAGE_VERB_RE.search(v["desc_pos"] if (v := _views(cand)) else ""):
            continue
        pid = r["product_id"]
        internals = [x for x in (load()["product_internal_capabilities"].get(pid) or [])
                     if _norm(x) not in _INTERNAL_GENERIC and len(_norm(x)) >= 3
                     and _norm(x) in _INTERNAL_FEATURES]
        blob = _norm(r.get("quote")) + " " + _views(cand)["desc_pos"]
        for term in sorted(internals):
            nt = _norm(term)
            if nt and any(x in blob and nt in blob for x in
                          _product_terms(pid, include_brand=True)):
                if re.search(rf"(^|[^a-z0-9]){re.escape(nt)}([^a-z0-9]|$)", blob):
                    return {"internal": True, "product": pid,
                            "matched_terms": [term],
                            "evidence": f"ref:{pid}+internal_term:{term}（同句共现）",
                            "via": "ref"}
    strong = [x for x in (refs or []) if x["ref_type"] in STRONG_REF_TYPES]
    if strong and all(is_generic_integration(x) for x in strong):
        st = "external_integration"
    elif strong:
        st = "not_internal"
    else:
        st = "unknown" if not (cand.get("owner") or cand.get("repo")) else "not_internal"
    return {"internal": False, "product": None, "matched_terms": [], "evidence": None,
            "via": None, "status": st}


def internal_feature_scan(cand):
    """§四.1 / §四.2：描述把某产品**自身内置功能/设置/内核**当作操作对象。

    成立 = 内部功能名（§四.5 数据）与该产品自身的词在**同一小句**共现，
    且该小句带「操作/开发/打包/治理」动词；
    不成立 = 只提到品牌、或整句是通用协议集成（MCP / API / SDK）语境（§四.2）。
    """
    d = load()
    v = _views(cand)
    blob = f"{v['name']} {v['desc_pos']}"
    for pid, internals in sorted((d["product_internal_capabilities"] or {}).items()):
        if pid == "comment" or pid not in d["products"]:
            continue
        terms = [x for x in (internals or [])
                 if _norm(x) not in _INTERNAL_GENERIC and len(_norm(x)) >= 3]
        prod_terms = _product_terms(pid, include_brand=True)
        for term in sorted(terms):
            nt = _norm(term)
            if not nt:
                continue
            for m in re.finditer(re.escape(nt), blob):
                lo = max(0, m.start() - 110)
                hi = min(len(blob), m.end() + 110)
                seg = blob[lo:hi]
                # 小句里必须出现该产品自身的词（品牌词/名称/仓库名）
                if not any(x in seg for x in prod_terms):
                    continue
                # §四.2 通用协议集成语境不算内部能力
                if _INTEGRATION_SEG_RE.search(seg):
                    continue
                if not _MANAGE_VERB_RE.search(seg):
                    continue
                return {"internal": True, "product": pid, "matched_terms": [term],
                        "evidence": f"internal_feature:{term} ↔ {pid}（同小句共现 + 操作动词）",
                        "status": "product_internal", "quote": seg[:120]}
    if not (cand.get("description") or cand.get("skill_name")):
        return {"internal": False, "product": None, "matched_terms": [], "evidence": None,
                "status": "unknown", "quote": None}
    return {"internal": False, "product": None, "matched_terms": [], "evidence": None,
            "status": "not_internal", "quote": None}


def internal_capability(cand, refs=None):
    """§四.5 / §四.2：产品自身内部功能名，且必须与该候选的**来源产品**绑定。

    §四.2 明确排除：通用 memory / MCP / subagent / test / release 能力词不算，
    操作该产品外部 API/SDK/云服务/桌面或移动界面也不算「内部组件」。
    """
    pid = source_product(cand)
    if not pid:
        return {"internal": False, "product": None, "matched_terms": [], "evidence": None,
                "status": "unknown" if not (cand.get("owner") or cand.get("repo"))
                else "not_internal"}
    terms = [t for t in (load()["product_internal_capabilities"].get(pid) or [])
             if _norm(t) not in _INTERNAL_GENERIC and len(_norm(t)) >= 3
             and _norm(t) in _INTERNAL_FEATURES]
    # 描述里同时出现「产品品牌词 + 该产品内部功能名」也算操作其内置功能（§四.2 第二支）
    brand_ok = bool(_product_terms(pid, include_brand=True) &
                    {x for x in re.split(r"[^a-z0-9\.#\+]+", blob) if x})
    v = _views(cand)
    blob = f"{v['name']} {v['desc_pos']}"
    hits = [t for t in sorted(terms) if _norm(t) and _norm(t) in blob]
    if hits and not brand_ok:
        hits = []                       # 内部功能名出现了，但没提到该产品 → 不算
    if not hits:
        return {"internal": False, "product": pid, "matched_terms": [], "evidence": None,
                "status": "external_integration" if is_generic_integration(
                    {"quote": v["desc_pos"]}) else "not_internal"}
    return {"internal": True, "product": pid, "matched_terms": hits[:5],
            "evidence": f"source_product:{pid} + internal_terms:{','.join(hits[:3])}",
            "status": "product_internal"}


def _product_terms(pid, include_brand=False):
    """产品的可查词：名称 + 别名 + agent slug；include_brand 时加裸品牌词。"""
    pr = load()["products"].get(pid) or {}
    terms = {pr.get("name"), pid} | set(pr.get("aliases") or []) \
        | set(pr.get("agent_slugs") or [])
    if include_brand and pr.get("brand"):
        terms.add(pr["brand"])
    return {t for t in (_norm(x) for x in terms if x) if len(t) >= 3}


def internal_pipeline(cand):
    """§四.3：开发产品自身的测试 / CI/CD / 发布 / 打包 / 端到端验证 / 内部组件。

    成立条件与 §四.2 一致：来源仓库即产品仓库，且描述用自研动词指向产品自身的工件。
    """
    pid = source_product(cand)
    if not pid:
        return {"internal_pipeline": False, "product": None, "evidence": None,
                "status": "unknown" if not (cand.get("owner") or cand.get("repo"))
                else "not_internal"}
    v = _views(cand)
    pr = load()["products"][pid]
    for t in sorted(_product_terms(pid, include_brand=True)):
        _ = pr
        pat = (rf"\b(?:{_SELF_DEV_VERBS})\b[^.!?\n]{{0,60}}?\b{re.escape(t)}\b"
               rf"[^.!?\n]{{0,60}}?\b(?:{_PRODUCT_ARTIFACTS})\b")
        m = re.search(pat, v["desc_pos"], re.I)
        if m:
            return {"internal_pipeline": True, "product": pid,
                    "evidence": f"self_dev:{m.group(0).strip()[:90]}",
                    "status": "product_internal"}
    return {"internal_pipeline": False, "product": pid, "evidence": None,
            "status": "not_internal"}


# --------------------------------------------------------------------------
# 九、竞品解除（§二.7）与统一 Gate 结论
# --------------------------------------------------------------------------
def extended_primary_domains(sections, installed_products=()):
    """项目六节领域 ∪ 本机在用产品生态领域（§三.1 + §二.7 同一套口径）。"""
    prim = set(project_primary_domains(sections))
    d = load()
    for pid in sorted(set(installed_products or {})):
        pr = d["products"].get(pid) or {}
        if pr.get("domain"):
            prim.add(pr["domain"])
        for cap in pr.get("capabilities") or []:
            for x in idx()["cap_domain"].get(cap) or []:
                prim.add(x)
    return prim


def resolve_competitors(conflicts, cand, sections, refs, installed_products=()):
    """§二.7：满足任一条件即解除，并记录解除依据。"""
    if not conflicts:
        return [], []
    prim = extended_primary_domains(sections, installed_products)
    need_caps = project_required_capabilities(sections)
    i = idx()
    d = load()
    installed = sorted(set(installed_products or {}))
    inst_brands = {_norm((d["products"].get(x) or {}).get("brand") or "")
                   for x in installed} - {""}
    resolved, unresolved = [], []
    by_pid = {r["product_id"]: r for r in refs}
    for cf in conflicts:
        pid = cf["candidate_product"]
        ev = []
        # ⓪ v2.9 §二.7：候选产品**自身**（或同品牌产品）就在用 → 生态并存，不是竞品冲突
        brand = _norm((d["products"].get(pid) or {}).get("brand") or "")
        if pid in installed:
            ev.append(f"installed_product:{pid}（候选产品自身已装，用户确实在用这个生态）")
        elif brand and brand in inst_brands:
            ev.append(f"installed_brand:{brand}（同品牌产品已在用，不构成竞品排除）")
        # ① 项目档案明确需要该产品自身生态能力
        for sid in ("tech_platform", "core_business", "positioning_integration"):
            for it in sections.get(sid) or []:
                t = _norm(it.get("term"))
                if t == _norm(pid) or t in i["product_ref"] and pid in i["product_ref"][t]:
                    ev.append(f"project_section:{sid}={it['term']}（来源 {it['source']}）")
        # ② 候选能力属于项目所需能力
        caps = set(by_pid.get(pid, {}).get("product_capabilities") or [])
        shared = sorted(caps & need_caps)
        if shared:
            ev.append(f"project_capability:{','.join(shared[:3])}")
        # ③ 领域是项目主要领域
        dom = product_domain(pid)
        if dom and dom in prim:
            ev.append(f"project_domain:{dom}")
        if ev:
            resolved.append({**cf, "resolution_evidence": ev[:4]})
        else:
            unresolved.append({**cf, "resolution_test":
                               "项目档案里出现该产品自身生态能力 / 该项目所需能力与产品能力重合 / 该项目主要领域与产品领域一致"})
    return sorted(resolved, key=lambda x: (x["candidate_product"], x["installed_product"])), \
        sorted(unresolved, key=lambda x: (x["candidate_product"], x["installed_product"]))


def gate_assessment(cand, sections, installed_products, refs=None):
    """统一判定：产品关系 → 领域 → Gate → 状态 → 解除路径（§二.8 / §四.10）。

    返回 dict：
      status            ：applicable / not_applicable / insufficient_info /
                          internal_only / competitor_mismatch / product_internal
      priority          ：normal / capped_watch / excluded
      blocking_excluded ：是否挡在深度审查队列外（§四.6/§四.7）
      breakdown_key     ：product_internal_blocked 的三个子计数归属（§四.11）
      evidence / resolution_test
    """
    refs = refs if refs is not None else product_refs(cand)
    strong = [r for r in refs if r["ref_type"] in STRONG_REF_TYPES]
    # §四.1/§四.5：先做「产品自身内置功能」独立扫描（不依赖 owner/repo 绑定）
    ic = internal_feature_scan(cand)
    if not ic["internal"]:
        ic = internal_capability(cand, refs)
    if not ic["internal"]:
        ic = internal_via_ref(cand, refs or [])
    ip = internal_pipeline(cand)
    ds = domain_state(cand, sections, refs, installed_products)
    conflicts = competitor_conflicts(refs, installed_products)
    res, unres = resolve_competitors(conflicts, cand, sections, refs,
                                    installed_products)
    ss = scope_state(cand, sections, refs)
    out = {"product_refs": refs, "candidate_domains": ds["candidate_domains"],
           "internal_feature_scan": ic if ic["internal"] else None,
           "domain_state": ds, "competitor_conflicts": conflicts,
           "competitor_resolved": res, "competitor_unresolved": unres,
           "internal_capability": ic, "internal_pipeline": ip,
           "scope_sections": ss,
           "product_relation_only_from_name": bool(refs) and not strong and not ic["internal"]}
    # ① 产品自身内部能力 / 内部管线（§四.4 → internal_only）
    if ic["internal"] or ip["internal_pipeline"]:
        out["status"] = "internal_only"
        out["priority"] = "excluded"
        out["blocking_excluded"] = True
        out["breakdown_key"] = "project_scope_section_not_required"
        out["reason"] = (ic["evidence"] or ip["evidence"]) + "；候选服务于来源产品自身，不是用户通用能力"
        out["resolution_test"] = "项目档案明确在开发/维护该产品 → 解除"
        return out
    # ② 未解决竞品关系（§二.5 → ignore；§四.10 不进推荐、不进 Top）
    if unres:
        out["status"] = "competitor_mismatch"
        out["priority"] = "excluded"
        out["blocking_excluded"] = True
        out["breakdown_key"] = "competitor_block"
        out["reason"] = ",".join(f"{c['candidate_product']}↔{c['installed_product']}"
                                 for c in unres[:3])
        out["resolution_test"] = unres[0]["resolution_test"]
        return out
    # ③ 产品专项 / 平台 scope：三态判定（§三.4 + §三.3.3）
    if ds["state"] == "not_applicable":
        out["status"] = "not_applicable"
        out["priority"] = "capped_watch"
        out["blocking_excluded"] = False
        out["breakdown_key"] = None
        out["reason"] = "候选领域落在输入A「明确低优先级」里：" + \
            ",".join(x["domain"] for x in ds["exclusion_evidence"][:3])
        out["resolution_test"] = "项目档案新增该技术栈/能力/产品集成 → 解除"
        return out
    if ds["state"] == "insufficient_info":
        out["status"] = "insufficient_info"
        out["priority"] = "excluded"
        out["blocking_excluded"] = True
        out["breakdown_key"] = "developer_tool_gate_unresolved"
        out["reason"] = ";".join(f"{u['domain']}：{u['reason']}" for u in ds["unresolved"][:3])
        out["resolution_test"] = ds["unresolved"][0]["resolution_test"]
        return out
    out["status"] = "applicable"
    out["priority"] = "normal"
    out["blocking_excluded"] = False
    out["breakdown_key"] = None
    out["reason"] = None
    out["resolution_test"] = None
    return out


# --------------------------------------------------------------------------
# 十、Gate 命中与全池安全审查队列（§四.6 / §四.7 / §四.11）
# --------------------------------------------------------------------------
# 挡在深度审查队列外的硬 Gate（产品关系类）。
# 注意：「仅名称含品牌词」**不是**硬 Gate（§四.7 / §四.12：那是误判源，不是拦截理由）。
HARD_SCAN_GATES = ("internal_only", "competitor_mismatch", "product_internal",
                   "scope_unresolved", "mcp_only", "primary_target_unresolved")
MCP_ONLY_GAPS = {"mcp_dev", "mcp_usage"}


def gm(cand):
    return cand.get("capability_gap_match") or {}


def blank_deep_scan(note):
    """未进队列的候选：显式标注状态，不冒充「已审查」。"""
    return {"deep_scan_status": "not_required", "scripts_scanned": 0, "script_files": [],
            "package_hooks": [], "findings": [], "blocking_rules": [],
            "deep_install_blocked": False, "scanned_paths": [], "tree_source": None,
            "note": note}


def gate_label(gate):
    """统一 Gate 结论 → 队列挡名（§四.7）。None = 可以进深度审查队列。"""
    st = gate.get("status")
    if st in ("internal_only", "competitor_mismatch"):
        return st
    if gate.get("blocking_excluded"):
        return "scope_unresolved"
    if (gate.get("domain_state") or {}).get("state") == "insufficient_info":
        return "insufficient_info"
    return None


def gate_hit(cand):
    """返回该候选命中的硬 Gate 名（无则 None）。优先读已算好的字段，避免重复判定。"""
    m = gm(cand)
    if "gate_hit" in m:
        return m.get("gate_hit")
    st = m.get("match_status")
    if st in ("internal_only", "competitor_mismatch"):
        return st
    if m.get("scope_type") == "product_internal" and m.get("product_internal_unresolved"):
        return "product_internal"
    if m.get("scope_unresolved") and m.get("scope_unresolved_target"):
        return "scope_unresolved"
    if (m.get("matched_gap") in MCP_ONLY_GAPS) and not m.get("need_evidence"):
        return "mcp_only"
    return None


def gate_breakdown(hits):
    """§四.11：product_internal_block_breakdown 三个子计数（含 0 也要输出）。"""
    b = {"project_scope_section_not_required": 0,
         "developer_tool_gate_unresolved": 0,
         "competitor_block": 0}
    for h in hits:
        if h == "competitor_mismatch":
            b["competitor_block"] += 1
        elif h in ("internal_only", "product_internal"):
            b["project_scope_section_not_required"] += 1
        else:
            b["developer_tool_gate_unresolved"] += 1
    return b


def v29_audit(cands, queue_keys, top_keys, eligible_n, complete_n):
    """§四.11 全池终审计字段（八项 + 竞品三项 + v2.11 §八 scope 计数拆分）。"""
    tk = set(top_keys)
    qk = set(queue_keys)

    def _pi_unresolved(c):
        # v2.11 §八 口径 = 原 product_internal（自研/内部能力，未解除）；
        # 产品专项 platform_operation 的未解除由 v2.8 scope 门单独记账，不混进来。
        g = gm(c)
        return (g.get("match_status") == "internal_only"
                or (g.get("scope_type") == "product_internal"
                    and g.get("product_internal_unresolved")))
    in_top = [c for c in cands if c.get("canonical_key") in tk]
    counts = {
        "full_scan_eligible": eligible_n,
        "full_scan_complete": complete_n,
        "full_scan_remaining_count": max(0, eligible_n - complete_n),
        # v2.11 §八：数据合同拆分——「池内未解除」与「队列/Top 内残留」是两回事，
        # 不再用 product_internal_remaining_count 这种名、值、注释互相矛盾的字段。
        # pool 计数允许 >0（可合法留在候选池等待解除）；full_scan / top 残留 = 0 才是硬门。
        "product_internal_unresolved_pool_count": sum(1 for c in cands if _pi_unresolved(c)),
        "product_internal_in_full_scan_count": sum(
            1 for c in cands if c.get("canonical_key") in qk and _pi_unresolved(c)),
        "product_internal_in_top_count": sum(
            1 for c in in_top if _pi_unresolved(c)),
        "product_internal_blocked": sum(1 for c in cands if gate_hit(c)),
        "internal_capability_in_full_scan_count": sum(
            1 for c in cands
            if (c.get("internal_capability") or {}).get("internal")
            and c.get("canonical_key") in qk),
        "competitor_unresolved_in_top": sum(
            1 for c in in_top if gm(c).get("competitor_unresolved")),
        "competitor_unresolved_full_scan": sum(
            1 for c in cands if c.get("canonical_key") in qk
            and gm(c).get("competitor_unresolved")),
        "product_name_false_positive_remaining": sum(
            1 for c in cands if gm(c).get("gate_hit") and
            gm(c).get("product_relation_only_from_name")),
        "scope_unresolved_in_top": sum(1 for c in in_top if gm(c).get("scope_unresolved")),
        "top_candidates_with_unresolved_mismatch": sum(
            1 for c in in_top if gm(c).get("domain_mismatch_unresolved")),
    }
    return counts


def agent_slugs_from_installed_context(text):
    """从已装侧身份档案（v4 INSTALLED_SKILLS_CONTEXT.md）派生本机智能体标识。

    §二.6：已装产品必须由身份档案派生，**不得**在代码里硬编码
    「本机装了 Codex / Claude Code」。这里读的是 AGENT_AVAILABILITY 矩阵里
    `<skill>/<agent>: available|broken|missing|not_deployed` 的 agent 段。
    返回 (排序后的 agent 标识列表, 证据列表)。
    """
    hits, ev = set(), []
    for m in re.finditer(r"^\s*-?\s*([\w.\-]+)/([\w.\-]+)\s*:\s*"
                         r"(available|broken|missing|not_deployed|ok|yes|no)\b",
                         text or "", re.M):
        agent, status = m.group(2).lower(), m.group(3).lower()
        if status in ("available", "broken", "ok", "yes"):
            hits.add(agent)
            ev.append(f"{m.group(1)}/{agent}:{status}")
    return sorted(hits), sorted(ev)[:8]
