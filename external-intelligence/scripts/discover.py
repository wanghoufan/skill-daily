# -*- coding: utf-8 -*-
"""双向发现：Top-down（Tier1 官方动态 + Tier3 聚合榜）+ Bottom-up（能力缺口搜索）。
产出 data/raw/*.json。只发现，不安装。"""
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (gh_api_cached, fetch_text, save_json, load_json, load_installed,
                    load_project_needs, RAW, REGISTRY_PATH, TODAY)
from data_gate import is_valid_skill_name, ARTIFACT_DIRS
from security_gate import SCRIPT_EXT, SKIP_DIRS

MAX_SEARCH_QUERIES = 12
TOP_TIER3 = 50  # 聚合榜取前 N 条

def _default_branch(e):
    return e.get("default_branch", "main")

# ---------- Top-down A1: 仓库级发现（TIER 1 官方 / TIER 2 社区） ----------
TIER_ORIGIN = {"official_repo": "official", "vendor_repo": "vendor",
               "community_host": "community", "community_repo": "community"}

def repo_skill_dirs(owner, repo, branch):
    """tree API 精确定位 SKILL.md，返回 (dirs, truncated, paths)。

    **附带返回全部文件路径**：analyze 的 PASS 2 深度静态审查需要列出每个 Skill 目录下的
    脚本文件（.py/.sh/.js/.ts/… 与 package.json）。在同一轮里复用这份 tree 结果，
    可以让深度审查做到**零额外 API 调用** —— 否则每个候选都要再来一次 tree API，
    未认证配额（60 次/小时）根本不够用（v2.2 实测踩过：32 个候选全部 deep_scan=failed）。
    """
    t = gh_api_cached(f"/repos/{owner}/{repo}/git/trees/{branch}", "recursive=1")
    if not t or "tree" not in t:
        return None, None, None
    paths = [x["path"] for x in t["tree"] if x.get("type") == "blob"]
    dirs = sorted({os.path.dirname(p) for p in paths if p.endswith("SKILL.md")})
    return dirs, t.get("truncated", False), paths


def collect_scripts(paths, skill_dir, limit=40):
    """从仓库文件树里挑出某 Skill 目录下的「可执行/脚本文本」（PASS 2 深度审查用）。"""
    prefix = (skill_dir or "").rstrip("/")
    prefix = (prefix + "/") if prefix else ""
    out = []
    for p in paths or []:
        if prefix and not p.startswith(prefix):
            continue
        rel = p[len(prefix):] if prefix else p
        if any(seg in SKIP_DIRS for seg in rel.split("/")[:-1]):
            continue
        if os.path.splitext(p)[1].lower() in SCRIPT_EXT or os.path.basename(p) == "package.json":
            out.append(p)
    return out[:limit]


def discover_repo_tier(registry, tier):
    out = []
    for e in registry["tiers"].get(str(tier), []):
        owner, repo = e["owner"], e["repo"]
        branch = e.get("default_branch", "main")
        dirs, truncated, paths = repo_skill_dirs(owner, repo, branch)
        if dirs is None:
            out.append({"source": f"{owner}/{repo}", "tier": tier, "owner": owner, "repo": repo,
                        "error": "tree 不可读", "skills": [], "scanned_at": TODAY}); continue
        skills = []
        for d in dirs:
            name = os.path.basename(d)
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", name): continue
            skills.append({"skill_name": name, "path": d,
                           "html_url": f"https://github.com/{owner}/{repo}/tree/{branch}/{d}",
                           # PASS 2 深度静态审查的脚本清单（零额外 API 调用）
                           "scripts": collect_scripts(paths, d)})
        out.append({"source": f"{owner}/{repo}", "tier": tier, "owner": owner, "repo": repo,
                    "branch": branch, "pushed_at": e.get("pushed_at"), "skills": skills,
                    "origin_type": TIER_ORIGIN.get(e.get("type"), "unknown"),
                    "tree_truncated": bool(truncated), "scanned_at": TODAY})
    return out

# ---------- Top-down A2: 官方/社区仓库近期更新（commits touching repo） ----------
def repo_recent_updates(registry, tier):
    out = []
    for e in registry["tiers"].get(str(tier), []):
        d = gh_api_cached(f"/repos/{e['owner']}/{e['repo']}/commits", "per_page=5")
        if isinstance(d, list):
            out.append({"source": f"{e['owner']}/{e['repo']}", "tier": tier,
                        "recent_commits": [{"sha": c["sha"][:8],
                                            "date": c["commit"]["committer"]["date"][:10],
                                            "msg": (c["commit"]["message"] or "").split("\n")[0][:90]}
                                           for c in d]})
    return out

# ---------- Top-down B: Tier3 聚合榜 ----------
def parse_skills_sh():
    h = fetch_text("https://www.skills.sh/", timeout=25)
    if not h: return {"source": "skills.sh", "healthy": False}
    repos = re.findall(r'font-mono[^>]*>\s*([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)\s*<', h)
    wk = [int(x.replace(",", "")) for x in re.findall(r'aria-label="Weekly installs: ([0-9,]+)', h)]
    titles = re.findall(r'<p[^>]*class="[^"]*font-medium[^"]*"[^>]*>([^<]{2,80})</p>', h)
    n = min(len(repos), len(wk))
    entries = []
    for i in range(n):
        name = titles[i].strip() if i < len(titles) else ""
        owner_repo = repos[i]
        owner, _, repo = owner_repo.partition("/")
        entries.append({"skill_name": name, "owner": owner, "repo": repo,
                        "weekly_installs": wk[i], "source_url": f"https://www.skills.sh/{owner_repo}"})
    entries.sort(key=lambda x: -x["weekly_installs"])
    return {"source": "skills.sh", "healthy": True, "scanned_at": TODAY, "entries": entries[:TOP_TIER3]}

def parse_clawhub():
    h = fetch_text("https://clawhub.ai", timeout=25)
    if not h: return {"source": "ClawHub", "healthy": False}
    entries, filtered = [], 0
    # 容错解析：抓 owner/repo 或 slug 与描述
    for m in re.finditer(r'href="/(?:skills?/)?([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"[^>]*>', h):
        owner, _, repo = m.group(1).partition("/")
        if owner.lower() in ("www", "docs", "api"): continue
        # §一.1 数据质量 Gate：ClawHub 会把前端构建产物当 Skill 收录
        #（assets/design-system-xxxx.css、index-xxxx.js …）→ 解析层就拦掉
        if owner.lower() in ARTIFACT_DIRS or not is_valid_skill_name(repo):
            filtered += 1
            continue
        entries.append({"skill_name": repo, "owner": owner, "repo": repo,
                        "source_url": f"https://clawhub.ai/{m.group(1)}"})
    seen, uniq = set(), []
    for e in entries:
        k = (e["owner"], e["repo"])
        if k not in seen: seen.add(k); uniq.append(e)
    return {"source": "ClawHub", "healthy": True, "scanned_at": TODAY,
            "entries": uniq[:TOP_TIER3], "filtered_artifacts": filtered,
            "note": "HTML 容错解析；已在解析层过滤构建产物（.css/.js/.map/图片/字体）；如结构变化请人工复核"}

# ---------- Bottom-up: 能力缺口搜索（查询族，中英双语） ----------
# ⚠️ v2.2 重要口径：本函数产出的是 **discovery_channel 结果**，不是 source tier。
#    GitHub 搜索命中的多是「普通项目仓库」，不等于 Skill。这些结果必须再过
#    「存在真实 SKILL.md + 可定位 skill directory + frontmatter 可解析」硬门
#    （见 analyze.verify_bottom_up），且**绝不自动升级为 TIER 2**——
#    TIER 2 只留给注册表里已验证的高质量社区来源。
GAP_QUERY_FAMILIES = {
    "mobile_qa": ["mobile app testing appium", "react native testing detox", "移动端自动化测试"],
    "image_creative": ["image generation editing skill", "creative image pipeline", "图片处理生成"],
    "data_analytics": ["data analysis visualization skill agent", "csv analysis report", "数据分析报表"],
    "security_audit": ["security audit code review skill", "owasp vulnerability scan", "安全审计"],
    "supabase_db": ["supabase postgres migration skill", "database schema migration agent", "数据库迁移治理"],
    "testing_qa": ["e2e testing playwright skill", "qa automation test suite", "自动化测试"],
    "docx_xlsx": ["docx xlsx office documents skill", "spreadsheet word automation", "Office 文档处理"],
    "mcp_dev": ["mcp server development skill", "model context protocol builder", "MCP 开发"],
}
def bottom_up_search(focus_caps):
    out = []
    queries = []
    for cap in focus_caps:
        for q in GAP_QUERY_FAMILIES.get(cap, [cap.replace("_", " ")])[:2]:
            queries.append((cap, q))
    queries = queries[:MAX_SEARCH_QUERIES]
    for cap, q in queries:
        d = gh_api_cached("/search/repositories", f"q={urllib.parse.quote(q)}&sort=updated&per_page=5")
        hits = []
        if d and d.get("items"):
            for it in d["items"][:5]:
                hits.append({"owner": it["owner"]["login"], "repo": it["name"],
                             "url": it["html_url"], "stars": it["stargazers_count"],
                             "pushed_at": it["pushed_at"][:10],
                             "default_branch": it.get("default_branch") or "main",
                             "archived": bool(it.get("archived")),
                             "description": (it.get("description") or "")[:160]})
        out.append({"capability_gap": cap, "query": q, "results": hits, "searched_at": TODAY,
                    "channel": "bottom_up_search",
                    "note": "discovery_channel（非 source tier）；进池前必须过 SKILL.md 硬门"})
    return out

def parse_skillsmp():
    h = fetch_text("https://skillsmp.com", timeout=25)
    if not h: return {"source": "SkillsMP", "healthy": False}
    entries, filtered = [], 0
    for m in re.finditer(r'href="/(?:skills?/)?([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"[^>]*>', h):
        owner, _, repo = m.group(1).partition("/")
        if owner.lower() in ("www", "docs", "api", "blog", "assets", "static"): continue
        if owner.lower() in ARTIFACT_DIRS or not is_valid_skill_name(repo):
            filtered += 1
            continue
        entries.append({"skill_name": repo, "owner": owner, "repo": repo,
                        "source_url": f"https://skillsmp.com/{m.group(1)}"})
    seen, uniq = set(), []
    for e in entries:
        k = (e["owner"], e["repo"])
        if k not in seen: seen.add(k); uniq.append(e)
    return {"source": "SkillsMP", "healthy": True, "scanned_at": TODAY,
            "entries": uniq[:TOP_TIER3], "filtered_artifacts": filtered,
            "note": "补充聚合源（HTML 容错解析，已过滤构建产物）；仅用于发现与趋势，排名不参与评分依据"}

import urllib.parse

def main():
    registry = load_json(REGISTRY_PATH)
    if not registry:
        print("registry missing — run build_registry.py first"); return 1
    inst = load_installed()
    # 焦点能力：none→高优先；weak→优先；medium→仅明显增强；
    # strong 但 availability=degraded → recovery（不按正常 strong 压制，允许恢复/补足类候选进入高优先关注）
    focus = []
    for cap, lv in inst["suppression"].items():
        av = inst["availability"].get(cap, {}).get("availability", "ok")
        if lv == "none":
            focus.append({"capability": cap, "level": lv, "availability": av, "priority": "high"})
        elif lv == "weak":
            focus.append({"capability": cap, "level": lv, "availability": av, "priority": "medium"})
        elif lv == "strong" and av == "degraded":
            focus.append({"capability": cap, "level": lv, "availability": av, "priority": "recovery"})
    save_json({"date": TODAY, "focus_capabilities": focus}, os.path.join(RAW, "gap_focus.json"))

    raw = {
        "date": TODAY,
        "tier1": discover_repo_tier(registry, 1),
        "tier2": discover_repo_tier(registry, 2),
        "tier1_updates": repo_recent_updates(registry, 1),
        "tier3": {"skills_sh": parse_skills_sh(), "clawhub": parse_clawhub(),
                  "skillsmp": parse_skillsmp()},
        "bottom_up": bottom_up_search([f["capability"] for f in focus
                                       if f["priority"] in ("high", "medium", "recovery")]),
        "project_needs": load_project_needs().get("needs", {}),
    }
    save_json(raw, os.path.join(RAW, f"discovery_{TODAY}.json"))
    save_json(raw, os.path.join(RAW, "discovery_latest.json"))
    n1 = sum(len(x.get("skills", [])) for x in raw["tier1"])
    n2 = sum(len(x.get("skills", [])) for x in raw["tier2"])
    print(f"tier1 skills: {n1} | tier2 skills: {n2} "
          f"| tier3 skills_sh: {len(raw['tier3']['skills_sh'].get('entries', []))} "
          f"(healthy={raw['tier3']['skills_sh']['healthy']}) | clawhub: {len(raw['tier3']['clawhub'].get('entries', []))} "
          f"| skillsmp: {len(raw['tier3']['skillsmp'].get('entries', []))} "
          f"| bottom_up queries: {len(raw['bottom_up'])} "
          f"| focus: {[(f['capability'], f['priority']) for f in focus]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
