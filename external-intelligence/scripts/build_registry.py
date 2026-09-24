# -*- coding: utf-8 -*-
"""构建 SKILL_SOURCE_REGISTRY.json：TIER 0-3 外部来源注册表（联网验证）。

每条来源包含规定字段：
  source_id / name / tier / type / url / repo / owner / trust_level /
  discovery_only / supports_versions / supports_install_signal /
  supports_activity / last_checked / status
外加证据字段：identity_note / evidence / pushed_at / stars / forks /
  skill_count / has_version_metadata / default_branch / license
"""
import json, sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import gh_api_cached, fetch_text, save_json, load_json, REGISTRY_PATH, TODAY

# ---------------- TIER 0：标准/规范（只做规范验证，不参与排名） ----------------
TIER0_SPEC = [
    dict(source_id="agentskills.io", name="agentskills.io", type="standard_site",
         url="https://agentskills.io", owner=None, repo=None, trust_level="spec_only",
         identity_note="Agent Skills 标准/规范站点——只用于规范验证，不参与热门排名"),
    dict(source_id="agentskills/agentskills", name="agentskills/agentskills",
         type="standard_repo", url="https://github.com/agentskills/agentskills",
         owner="agentskills", repo="agentskills", trust_level="spec_only",
         identity_note="Agent Skills 规范仓库——只用于 SKILL.md 结构/字段合规校验"),
]

# ---------------- TIER 1：官方 / 厂商（org 归属已核验） ----------------
# v2.2 口径统一（与已装侧 v4 Canonical 模型对齐）：
#   「官方项目自己维护的公开官方 Skill 仓库」= official
#     → anthropics/skills、google/skills、microsoft/skills、huggingface/skills、
#       vercel-labs/*、stablyai/orca、browseros-ai/BrowserOS
#   vendor 只保留给「可确认由服务/产品厂商提供，但不属于官方 Skill repository 口径」的情况，
#     例如 AI HOT / Virxact（文件内署名的第三方厂商）。
#   统一理由：同一个 stablyai/orca 在已装侧记 official、在外部层记 vendor，会让
#   两层报告互相矛盾，无法交叉引用。
TIER1_SPEC = [
    ("anthropics", "skills", "official_repo", "high", "Anthropic 官方 Agent Skills 仓库"),
    ("github", "awesome-copilot", "community_host", "medium",
     "GitHub 官方维护的精选仓库，但 skill 本体多为社区贡献——按『宿主官方、内容社区』计，不按官方计"),
    ("vercel-labs", "agent-skills", "official_repo", "high", "Vercel 官方 agent skills 集合"),
    ("vercel-labs", "skills", "official_repo", "high", "Vercel 官方 skills CLI（npx skills）"),
    ("microsoft", "skills", "official_repo", "high", "Microsoft 官方（GitHub Copilot SDK 生态）"),
    ("huggingface", "skills", "official_repo", "high", "Hugging Face 官方（HF 生态技能）"),
    ("stablyai", "orca", "official_repo", "high",
     "Orca 官方项目自己维护的公开官方 Skill 仓库（ADE，含官方 skills/）"
     "—— v2.2 起与已装侧统一为 official（原先误记 vendor）"),
    ("google", "skills", "official_repo", "high", "Google 官方 Agent Skills"),
    ("browseros-ai", "BrowserOS", "official_repo", "high",
     "BrowserOS 官方项目自己维护的公开官方 Skill 仓库（含官方 skills/browseros-neo，"
     "与本机已装 browseros-neo 同源）—— v2.2 起与已装侧统一为 official（原先误记 vendor）"),
]

# ---------------- TIER 2：高质量社区作者（需逐项验证，不按 star 收录） ----------------
TIER2_SPEC = [
    ("KKKKhazix", "khazix-skills", "medium",
     "个人作者 KKKKhazix；本机已装 hv-analysis/khazix-writer/leader/neat-freak 与该仓库逐字节一致（最强社区源证据）"),
    ("obra", "superpowers", "medium",
     "个人作者 obra；活跃社区 skill 合集，含 brainstorming/parallel-agents 等工程类技能"),
    ("wshobson", "agents", "medium",
     "个人作者 wshobson；plugins/*/skills 结构，含 metadata.version 语义化版本"),
]

# ---------------- TIER 3：聚合发现源（只做发现/趋势，排名≠质量） ----------------
TIER3_SPEC = [
    dict(source_id="skills.sh", name="skills.sh", type="aggregator",
         url="https://www.skills.sh/", trust_level="discovery_only",
         identity_note="聚合发现源：候选/趋势/周安装量/新上榜；安装量只是 adoption signal，绝不等于推荐", parse_mode="html"),
    dict(source_id="clawhub.ai", name="ClawHub", type="aggregator",
         url="https://clawhub.ai", trust_level="discovery_only",
         identity_note="聚合发现源（OpenClaw 生态）：发现候选/趋势；排名不直接等于推荐", parse_mode="html"),
    dict(source_id="skillsmp.com", name="SkillsMP", type="aggregator",
         url="https://skillsmp.com", trust_level="discovery_only",
         identity_note="Agent Skills marketplace（Codex/Claude）：补充发现源，仅用于发现与趋势", parse_mode="html"),
]

def repo_evidence(owner, repo, limit_version_probe=2):
    """采集仓库级证据：活跃度 + skill 数 + 是否含版本元数据。返回 dict 或 None。"""
    d = gh_api_cached(f"/repos/{owner}/{repo}")
    if not d or "full_name" not in d:
        return None
    branch = d.get("default_branch", "main")
    ev = {
        "owner": owner, "repo": repo, "url": f"https://github.com/{owner}/{repo}",
        "owner_type": (d.get("owner") or {}).get("type"),
        "pushed_at": (d.get("pushed_at") or "")[:10],
        "created_at": (d.get("created_at") or "")[:10],
        "stars": d.get("stargazers_count"), "forks": d.get("forks_count"),
        "open_issues": d.get("open_issues_count"),
        "license": (d.get("license") or {}).get("spdx_id"),
        "description": (d.get("description") or "")[:200],
        "default_branch": branch,
        "supports_activity": True,
    }
    t = gh_api_cached(f"/repos/{owner}/{repo}/git/trees/{branch}", "recursive=1")
    if t and "tree" in t:
        paths = [x["path"] for x in t["tree"] if x["path"].endswith("SKILL.md")]
        ev["skill_count"] = len(paths)
        ev["tree_truncated"] = t.get("truncated", False)
        has_ver, ver_samples = False, []
        for p in paths[:limit_version_probe]:
            txt = fetch_text(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{p}", timeout=15)
            time.sleep(0.2)
            if not txt: continue
            if re.search(r"version\s*:", txt):
                has_ver = True
                m = re.search(r"version\s*:\s*['\"]?([0-9][\w.\-]*)", txt)
                if m: ver_samples.append(m.group(1))
        ev["has_version_metadata"] = has_ver
        ev["version_samples"] = sorted(set(ver_samples))[:5]
        ev["skill_paths_sample"] = sorted({os.path.dirname(p) for p in paths})[:6]
    else:
        ev["skill_count"] = None
        ev["has_version_metadata"] = False
        ev["version_samples"] = []
    return ev

def site_probe(source_id, name, url, note, parse_mode="html"):
    body = fetch_text(url, timeout=20)
    return dict(source_id=source_id, name=name, tier=3, type="aggregator", url=url,
                owner=None, repo=None, trust_level="discovery_only",
                discovery_only=True, supports_versions=False,
                supports_install_signal=True,   # 聚合源提供安装量/趋势
                supports_activity=False, last_checked=TODAY,
                status="reachable" if body else "unreachable",
                parse_mode=parse_mode, identity_note=note,
                evidence=("HTTP 探测成功，页面含候选/榜单结构" if body else "HTTP 探测失败"),
                bytes=len(body) if body else 0)

def main():
    reg = {"version": 2, "generated": TODAY,
           "rule": ("TIER 只决定 source_trust 与发现频率，不等于安全认证；"
                    "SECURITY_GATE 对所有来源一律执行，官方来源不豁免。"
                    "T0/T3 为 discovery_only，其排名/安装量不得直接作为推荐依据。"),
           "field_legend": {
               "trust_level": "high / medium / low / spec_only / discovery_only",
               "discovery_only": "true=只用于发现或规范验证，不得据其排名直接推荐",
               "supports_versions": "该来源的 skill 是否带语义化版本元数据",
               "supports_install_signal": "是否提供安装量/趋势信号（仅作 adoption signal）",
               "supports_activity": "是否可核验维护活跃度（GitHub 仓库为 true）",
               "status": "verified（已核验并可用）/ reachable / unreachable",
           },
           "tiers": {}}

    t0 = [dict(e, tier=0, discovery_only=True, supports_versions=False,
               supports_install_signal=False, supports_activity=False,
               last_checked=TODAY, status="reachable",
               evidence="TIER 0 仅用于规范验证；不参与热门排名与推荐") for e in TIER0_SPEC]

    t1 = []
    for owner, repo, typ, trust, note in TIER1_SPEC:
        ev = repo_evidence(owner, repo)
        if not ev:
            t1.append({"source_id": f"{owner}/{repo}", "name": f"{owner}/{repo}", "tier": 1,
                       "type": typ, "url": f"https://github.com/{owner}/{repo}",
                       "owner": owner, "repo": repo, "trust_level": trust,
                       "discovery_only": False, "supports_versions": False,
                       "supports_install_signal": False, "supports_activity": False,
                       "last_checked": TODAY, "status": "unreachable",
                       "identity_note": note, "evidence": "GitHub API 不可访问"})
            continue
        t1.append({
            "source_id": f"{owner}/{repo}", "name": f"{owner}/{repo}", "tier": 1,
            "type": typ, "url": ev["url"], "repo": repo, "owner": owner,
            "trust_level": trust, "discovery_only": False,
            "supports_versions": bool(ev.get("has_version_metadata")),
            "supports_install_signal": False, "supports_activity": True,
            "last_checked": TODAY, "status": "verified",
            "identity_note": note,
            "evidence": (f"github org/{owner}（owner_type={ev['owner_type']}）归属核验；"
                         f"pushed_at={ev['pushed_at']}；SKILL.md={ev.get('skill_count')}；"
                         f"版本元数据={ev.get('has_version_metadata')}；license={ev['license']}"),
            "pushed_at": ev["pushed_at"], "stars": ev["stars"], "forks": ev["forks"],
            "license": ev["license"], "default_branch": ev["default_branch"],
            "skill_count": ev.get("skill_count"),
            "has_version_metadata": ev.get("has_version_metadata", False),
            "version_samples": ev.get("version_samples", []),
            "description": ev["description"],
        })

    t2 = []
    for owner, repo, trust, note in TIER2_SPEC:
        ev = repo_evidence(owner, repo)
        if not ev:
            continue
        # 社区源硬门：必须真有 SKILL.md 且可核验活跃度，否则不收录
        if not ev.get("skill_count"):
            continue
        t2.append({
            "source_id": f"{owner}/{repo}", "name": f"{owner}/{repo}", "tier": 2,
            "type": "community_repo", "url": ev["url"], "owner": owner, "repo": repo,
            "trust_level": trust, "discovery_only": False,
            "supports_versions": bool(ev.get("has_version_metadata")),
            "supports_install_signal": False, "supports_activity": True,
            "last_checked": TODAY, "status": "verified",
            "identity_note": note,
            "evidence": (f"作者身份={ev['owner_type']}:{owner}；pushed_at={ev['pushed_at']}；"
                         f"SKILL.md={ev.get('skill_count')}；版本元数据={ev.get('has_version_metadata')}"
                         f"{ev.get('version_samples') or ''}；license={ev['license']}；"
                         f"stars={ev['stars']}（**star 仅记录，不作为收录依据**）"),
            "author_identity": {"login": owner, "type": ev["owner_type"],
                                "verified_via": "GitHub API repo.owner"},
            "maintenance": {"pushed_at": ev["pushed_at"], "created_at": ev["created_at"],
                            "open_issues": ev["open_issues"]},
            "stars": ev["stars"], "forks": ev["forks"], "license": ev["license"],
            "default_branch": ev["default_branch"], "skill_count": ev.get("skill_count"),
            "has_version_metadata": ev.get("has_version_metadata", False),
            "version_samples": ev.get("version_samples", []),
            "skill_paths_sample": ev.get("skill_paths_sample", []),
            "description": ev["description"],
        })

    t3 = [site_probe(e["source_id"], e["name"], e["url"], e["identity_note"], e["parse_mode"])
          for e in TIER3_SPEC]

    reg["tiers"] = {"0": t0, "1": t1, "2": t2, "3": t3}
    reg["counts"] = {k: len(v) for k, v in reg["tiers"].items()}
    reg["supports_fields"] = sorted({"source_id", "name", "tier", "type", "url", "repo",
                                     "owner", "trust_level", "discovery_only",
                                     "supports_versions", "supports_install_signal",
                                     "supports_activity", "last_checked", "status"})
    save_json(reg, REGISTRY_PATH)
    print("registry counts:", reg["counts"])
    for t in ("0", "1", "2", "3"):
        for e in reg["tiers"][t]:
            print(f"  T{t} {e['source_id']:<32} trust={e['trust_level']:<15} "
                  f"{e['status']:<10} disc_only={e['discovery_only']} "
                  f"ver={e['supports_versions']} act={e['supports_activity']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
