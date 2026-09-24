# -*- coding: utf-8 -*-
"""生成 EXTERNAL_SKILLS_CONTEXT.md（日报读取的轻量文件）。

机器可读区固定 11 节：
SOURCE_HEALTH / CANDIDATE_POOL_SUMMARY / NEW_DISCOVERIES / HIGH_MATCH_CANDIDATES /
CAPABILITY_GAP_CANDIDATES / TRENDING_RELEVANT / UPDATE_CANDIDATES / SECURITY_REJECTED /
WATCHLIST / PERSONALIZED_TOP30 / DAILY_DELTA
正文只突出 5-10 个「今天真正有变化或值得看」的候选，避免每天重复同样 30 个。
机器块另含 v2.8 §十四 的 supporting_only 审计行（Top 内必须为 0）。
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_json, save_json, load_config, CANDIDATES_PATH, CONTEXT_OUT,
                    SNAPSHOT_PATH, REGISTRY_PATH, TODAY, load_installed)
from security_gate import deep_scan_summary

DELTA_CATS = ["NEW", "RISING", "FALLING", "UPDATED", "SECURITY_CHANGED",
              "SOURCE_CHANGED", "MATCH_CHANGED", "ALREADY_INSTALLED", "NO_LONGER_RELEVANT",
              # v2.11 §九/§十：元数据补全与引擎重算不得冒充「上游更新」
              "METADATA_ENRICHED", "RECALCULATED", "SYSTEM_REBASELINE"]

# v2.11 §十：快照必须携带 schema / 引擎版本；两者任一变化 → SYSTEM_REBASELINE
SNAPSHOT_SCHEMA_VERSION = 2

def snap_key(c):
    return {"score": c["score"], "recommendation": c["recommendation"],
            "risk": c["security"]["risk_level"], "source_tier": c["source_tier"],
            "verdict": c["security"].get("verdict"),
            "deep_scan": c["security"].get("deep_scan_status"),
            "gap": c["capability_gap_match"]["gap_level"],
            "install_count": c.get("install_count") or 0,
            "latest_version": c.get("latest_version"),
            "latest_commit": c.get("latest_commit"),
            "relationship": c["installed_relationship"],
            "activity": c.get("upstream_activity")}

def classify_delta(old, new):
    """v2.11 §十：UPDATED 只承认「两侧都有值且上游真的前进了」。

    * version：old、new 均非空且不同 → UPDATED；null→值 / 值→null → METADATA_ENRICHED；
    * commit：均非空且 new > old（ISO 日期串可直排）→ UPDATED；
      均非空但不前进（回退/修正）或一侧为空 → METADATA_ENRICHED；
    * upstream_activity 变化（unknown→active 等）永远只是 METADATA_ENRICHED；
    * score / recommendation / gap 变化 → MATCH_CHANGED / RISING / FALLING，绝不 UPDATED。
    """
    cats = set()
    if old is None:
        cats.add("NEW")
        if new.get("relationship") == "already_installed": cats.add("ALREADY_INSTALLED")
        return cats
    if new["score"] > old["score"] + 3: cats.add("RISING")
    if new["score"] < old["score"] - 3: cats.add("FALLING")
    if new["recommendation"] != old["recommendation"]: cats.add("MATCH_CHANGED")
    if new["risk"] != old["risk"] or new.get("verdict") != old.get("verdict"):
        cats.add("SECURITY_CHANGED")
    if new.get("deep_scan") != old.get("deep_scan"): cats.add("SECURITY_CHANGED")
    if new["source_tier"] != old["source_tier"]: cats.add("SOURCE_CHANGED")
    if new["gap"] != old["gap"]: cats.add("MATCH_CHANGED")
    lv_o, lv_n = old.get("latest_version"), new.get("latest_version")
    if lv_o and lv_n and lv_o != lv_n:
        cats.add("UPDATED")
    elif lv_o != lv_n:
        cats.add("METADATA_ENRICHED")
    lc_o, lc_n = old.get("latest_commit"), new.get("latest_commit")
    if lc_o and lc_n and lc_n > lc_o:
        cats.add("UPDATED")
    elif lc_o != lc_n:
        cats.add("METADATA_ENRICHED")
    if new.get("activity") != old.get("activity"): cats.add("METADATA_ENRICHED")
    if (new["install_count"] or 0) > (old["install_count"] or 0) * 1.5: cats.add("RISING")
    if new.get("relationship") == "already_installed" and old.get("relationship") != "already_installed":
        cats.add("ALREADY_INSTALLED")
    return cats

# ---------- Top30 选取（个性化底线 + 多样性） ----------
def rank_candidate(c):
    """排序键（字典序，越靠前越优先），严格对应 §八 规定的执行顺序：

      ① hard gates  —— 在调用方已做（已安装 / 硬门未过 / ignore / reject 已剔出池）
      ② 真实需求匹配 —— need_evidence 优先，其次命中具体项目（matched_projects）
      ③ recommendation >= watch —— 池内已是 install_candidate 或 watch，install 优先
      ④ score
      ⑤ diversity —— 由 select_top30 在最后执行（同仓库 ≤3 + 同族折叠）

    原则：多样性可以保留，但**不得压过质量**——不为「凑够不同能力」把 ignore 填进来。
    """
    pm = c.get("project_match") or {}
    mps = pm.get("matched_projects") or []
    return (-(1 if pm.get("need_evidence") else 0),
            -(1 if mps else 0),
            -(0 if pm.get("domain_mismatch") else 1),
            -(1 if c["recommendation"] == "install_candidate" else 0),
            -c["score"])

def same_family(a, b):
    """同族判定（词元序列）：最长公共前缀 ≥3，或短者是长者的完整前缀（且短者 ≥2 词）。
    例：google-mobile-ads-get-started / -interstitial（公共前缀 3）→ 同族
        orca-emulator vs orca-emulator-android（前者是后者前缀）→ 同族"""
    n = min(len(a), len(b))
    lcp = 0
    while lcp < n and a[lcp] == b[lcp]:
        lcp += 1
    if lcp >= 3: return True
    return (a[:n] == b[:n] or b[:n] == a[:n]) and n >= 2

# ---------- v2.3：质量门 + 跨仓功能族折叠（§三 / §五 / §八） ----------
def norm_skill_name(name):
    """规范化 Skill 名：小写、连接符统一，用于跨仓同名/近名判定。"""
    return re.sub(r"[-_\s]+", "-", (name or "").lower()).strip("-")

def _desc_token_set(c):
    import match_rules as MR
    words, _t, _n = MR.bag(c.get("skill_name"), c.get("description"))
    return {w for w in words if len(w) >= 3}

def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def functional_family(a, b, sim_threshold=0.62):
    """判断两个候选是否属**同一功能族**（§三：跨 repo 折叠依据）。

    综合三类信号（至少一类成立）：
      ① normalized skill name 完全相同且够长（github/…/webapp-testing 与
         anthropics/skills/webapp-testing）
      ② description 高度相似 **且** 名称同前缀
      ③ content_fingerprint 完全相同（逐字节同一份 SKILL.md）
    返回 (是否同族, 依据文字)。
    """
    na, nb = norm_skill_name(a.get("skill_name")), norm_skill_name(b.get("skill_name"))
    if na and na == nb and len(na) >= 5:
        return True, "同名同功能"
    fa, fb = a.get("content_fingerprint"), b.get("content_fingerprint")
    if fa and fb and fa == fb:
        return True, "内容指纹相同"
    sim = _jaccard(_desc_token_set(a), _desc_token_set(b))
    if sim >= sim_threshold and na[:4] and na[:4] == nb[:4]:
        return True, f"描述相似 {sim:.2f} + 名称同前缀"
    return False, ""

def build_update_lineage(cands, inst):
    """v2.6 §三/§二.6：更新项由 Installed Source Map 驱动，不从候选池找同名对象冒充上游。

    每条输出 installed_canonical_id / installed_upstream / update_upstream /
    lineage_evidence / lineage_verified；`installed_upstream` 与 `update_upstream`
    不一致时必须由血缘证据撑起，否则不建立关联（候选池里没有同血缘候选时，
    更新来源直接取 Source Map 自己的 upstream 声明）。
    日报与对照件共用本函数，避免两处口径不一致。
    """
    cand_by_installed = {}
    for c in cands:
        if c["installed_relationship"] == "already_installed" and c.get("overlap_with_installed"):
            cand_by_installed.setdefault(c["overlap_with_installed"], c)
    items = []
    for name, e in sorted((inst.get("all_known") or {}).items()):
        vs, ia = e.get("version_status"), e.get("upstream_activity")
        if not e.get("canonical", {}).get("installed_canonical"):
            continue
        if vs not in ("outdated_version", "historical_official_version") or ia != "active":
            continue
        up = e.get("upstream") or "unknown"
        bound = cand_by_installed.get(name)
        if bound:
            lin = bound.get("lineage_evidence") or []
            items.append({
                "installed_canonical_id": name,
                "installed_upstream": up,
                "update_upstream": f"{bound['owner']}/{bound['repo']}",
                "lineage_evidence": "；".join(lin) or "Source Map 未记录可核对的上游",
                "lineage_verified": bool(lin),
                "note": bound.get("update_note") or ""})
        else:
            items.append({
                "installed_canonical_id": name,
                "installed_upstream": up,
                "update_upstream": up,
                "lineage_evidence": (e.get("evidence") or "见 Installed Source Map")[:120],
                "lineage_verified": True,
                "note": "候选池中无同血缘候选；更新来源直接取 Installed Source Map 的 upstream 证据"})
    return items


def unresolved_mismatch(c):
    """§九：取「未解除的平台错配」（老数据无该字段时退回 domain_mismatch）。"""
    gm = c.get("capability_gap_match") or {}
    if "domain_mismatch_unresolved" in gm:
        return gm.get("domain_mismatch_unresolved") or []
    return gm.get("domain_mismatch") or []

def _pi_unresolved(c):
    """v2.11 §八：product_internal（产品自研/内部能力，未解除）——与
    product_rules.v29_audit 的 pool 计数同一口径；Top/队列残留必须为 0。
    产品专项 platform_operation 未解除由 unresolved_scope()（v2.8 门）单独记账。"""
    gm = c.get("capability_gap_match") or {}
    return (gm.get("match_status") == "internal_only"
            or (gm.get("scope_type") == "product_internal"
                and gm.get("product_internal_unresolved")))

def unresolved_scope(c):
    """v2.6 §十 / v2.7 §七：未解除的产品 scope（product_internal 或产品专项
    platform_operation）→ 不进 Top。

    platform_operation 中由 GCP/Azure 等平台词触发的（platform_terms:…）由
    domain-mismatch 同一套门处理，这里不重复记账。
    """
    gm = c.get("capability_gap_match") or {}
    pi = gm.get("product_internal_unresolved")
    if pi:
        return [pi]
    if gm.get("scope_unresolved") and gm.get("scope_unresolved_target"):
        return [gm["scope_unresolved_target"]]
    return []

def v29_scope_note(c):
    """v2.9 §三.4：一句可审计摘要 —— 产品关系、项目能力分区、置信度、解除证据。

    build_context（日报）与 make_digest（对照件）共用同一函数，避免两处口径漂移。
    """
    gm = c.get("capability_gap_match") or {}
    refs = [r for r in (gm.get("product_refs") or [])
            if r.get("ref_type") in ("developer_tool", "primary_target")]
    if not refs:
        if gm.get("product_refs"):
            return "产品关系=仅名称/描述提及(mentioned)，不构成 Gate"
        return "产品关系=无"
    r = refs[0]
    dom = (c.get("capability_domains") or {})
    bits = [f"产品关系={r['product_id']}/{r['ref_type']}",
            f"项目分区={SECTION_LABEL_CN.get(c.get('project_scope_section'), '—')}",
            f"置信度={c.get('project_scope_section_confidence') or '—'}",
            f"领域状态={dom.get('state') or gm.get('domain_mismatch_state') or '—'}"]
    ev = [x.get("domain") for x in (dom.get("applicable_evidence") or [])][:2]
    res = (gm.get("competitor_resolved") or [])
    if ev:
        bits.append("适用证据=" + "/".join(ev))
    if res:
        bits.append("解除=" + "/".join(sorted({x["candidate_product"] for x in res})[:2]))
    if gm.get("gate_resolution_test") and gm.get("match_status") in (
            "internal_only", "competitor_mismatch", "insufficient_info", "not_applicable"):
        bits.append("解除测试=" + str(gm["gate_resolution_test"])[:40])
    return "；".join(bits)


SECTION_LABEL_CN = {
    "tech_platform": "技术栈与运行平台", "core_business": "项目核心业务能力",
    "task_types": "主要任务类型", "dev_workflow": "开发流程",
    "positioning_integration": "产品定位与集成", "low_priority": "明确低优先级",
    None: "—",
}

def core_evidence_ok(c):
    """v2.8 §十四：Top 资格的「核心需求证据」底线（v2.11 §六 加强）。

    只有 supporting / mention 级需求证据，且没有 真实 capability gap（primary 证据）、
    update、replacement、真实 matched_project —— 不得进 Personalized Top。
    v2.11 §六：某 matched_need 若「承载它的项目全部与候选 required_tech 不兼容」
    （need_project_compatibility=none），该需求**不能**再算 primary 个性化证据——
    「需求名匹配」不能脱离「需求对应项目能不能用」。仍可 general_interest / watch。
    """
    pm = c.get("project_match") or {}
    gm = c.get("capability_gap_match") or {}
    levels = pm.get("matched_need_evidence_levels") or {}
    npc = pm.get("need_project_compatibility") or {}
    needs = [n for n in (pm.get("matched_needs") or [])
             if (npc.get(n) or {}).get("need_project_compatibility") != "none"]
    if needs and (not levels or any(v == "primary" for v in
                                    (levels.get(n) for n in needs))):
        return True
    if pm.get("matched_projects"):
        return True
    if gm.get("matched_gap") and gm.get("gap_level") in ("none", "weak"):
        lvl = (gm.get("capability_evidence_context") or {}).get(gm["matched_gap"], "primary")
        if lvl == "primary":
            return True
    return bool(c.get("update_available")) \
        or c.get("installed_relationship") == "replacement_candidate"

def has_personalized_evidence(c):
    """§五 质量门①：必须有真实个性化证据。

    matched need / capability gap / update / replacement 至少一个成立。
    只靠「来源看起来不错」不得进 Personalized Top。
    """
    pm = c.get("project_match") or {}
    gap = c.get("capability_gap_match") or {}
    return bool(pm.get("need_evidence")
                or pm.get("matched_projects")
                or gap.get("gap_level") in ("none", "weak")
                or c.get("update_available")
                or c.get("installed_relationship") == "replacement_candidate")

def is_t3_uncorroborated(c, corroborated_repos):
    """§五 质量门③：T3 / discovery_only 来源若无 T1·T2·官方交叉佐证 → 不进 Top，只留 WATCHLIST。"""
    if c.get("source_tier") != 3 and c.get("origin_type") != "discovery_only":
        return False
    key = f"{c.get('owner','')}/{c.get('repo','')}".lower()
    return key not in (corroborated_repos or set())


# ---------- v2.10（审查文档 §四~§七 / §十二 / §十四）：能力饱和 + 家族配额 + 推荐理由 ----------
SATURATION_LEVELS = ("none", "weak", "medium", "strong", "strong_degraded")
# §七 capability_family_quota：strong 族默认最多 1 条代表项（第 2 条起必须带
# 明确的 incremental_subcapability）；medium 族 2 条；weak / none 族允许 3 条比较路线。
FAMILY_QUOTA = {"strong": 1, "strong_degraded": 1, "medium": 2, "weak": 3, "none": 3}


def strong_incremental_value(c):
    """v2.10 §五/§六：CLEAR_INCREMENTAL_VALUE 判定（5 种合法来源，任一成立）。

    返回 (是否成立, 依据列表)。这不是硬 blacklist：update / 可用性退化 /
    明确新子能力 / 未被覆盖的项目专用技术路线都能重新进入 Top。
    """
    gm = c.get("capability_gap_match") or {}
    reasons = []
    if c.get("update_available"):
        reasons.append("update_available")
    if c.get("installed_relationship") == "replacement_candidate":
        reasons.append("replacement_candidate")
    if gm.get("capability_saturation") == "strong_degraded":
        reasons.append("availability_degraded")
    subs = gm.get("incremental_subcapability") or []
    if subs:
        reasons.append("incremental_subcapability:" + "/".join(subs))
    # §五.4：解决当前具体项目的直接痛点，且现有 strong Skill 不覆盖该方法/平台
    # —— 数据侧代理：项目匹配里存在 strong_tech 专用技术栈直接命中。
    for m in (c.get("project_match") or {}).get("matched_projects") or []:
        if "strong_tech" in (m.get("direct_evidence_kinds") or []):
            reasons.append("project_specific_tech:" + m["project"])
            break
    return bool(reasons), reasons


def saturation_gate_ok(c):
    """v2.10 §五：capability_saturation 分级 Top 资格。

    none / weak → 正常竞争；medium → 必须有明确增量（项目直接匹配 / 子能力 /
    update / replacement）；strong → 默认 watchlist，除非存在 CLEAR_INCREMENTAL_VALUE；
    strong + availability degraded → 不硬压制。
    """
    sat = (c.get("capability_gap_match") or {}).get("capability_saturation") or "none"
    if sat in ("none", "weak"):
        return True
    if sat == "strong_degraded":
        return True
    if sat == "medium":
        pm = c.get("project_match") or {}
        return bool(pm.get("matched_projects")) or strong_incremental_value(c)[0]
    return strong_incremental_value(c)[0]


def family_quota_state_ok(c, fam_state):
    """v2.10 §七：能力族级 Top 配额（strong 族最多 1 条代表项；
    超出必须带**未被用过**的 incremental_subcapability）。"""
    gm = c.get("capability_gap_match") or {}
    fam = gm.get("matched_gap") or gm.get("saturation_family")
    if not fam:
        return True
    sat = gm.get("capability_saturation") or "none"
    quota = FAMILY_QUOTA.get(sat, 3)
    st = fam_state.setdefault(fam, {"n": 0, "sat": sat, "subs": set()})
    subs = set(gm.get("incremental_subcapability") or [])
    if st["n"] < quota:
        st["n"] += 1
        st["subs"] |= subs
        return True
    if sat in ("strong", "strong_degraded") and subs and not (subs & st["subs"]):
        st["n"] += 1
        st["subs"] |= subs
        return True
    return False


def build_personalized_reason(c):
    """v2.10 §十二：日报必须能回答「我已经有类似 Skill，为什么今天还推荐这个？」

    Top 候选至少一条非空强理由；已装能力 saturated=strong 的候选
    `incremental_over_installed` 必须非空（saturation Gate 保证）。
    """
    gm = c.get("capability_gap_match") or {}
    pm = c.get("project_match") or {}
    sat = gm.get("capability_saturation") or "none"
    fam = gm.get("matched_gap") or gm.get("saturation_family")
    subs = gm.get("incremental_subcapability") or []
    levels = pm.get("matched_need_evidence_levels") or {}
    primary_needs = [n for n in (pm.get("matched_needs") or [])
                     if levels.get(n, "primary") == "primary"]
    out = {"fills_gap": "", "matched_project": "",
           "incremental_over_installed": "", "why_now": ""}
    if fam and sat in ("none", "weak"):
        out["fills_gap"] = f"能力族 {fam} 当前饱和={sat}，优先补齐"
    elif primary_needs:
        out["fills_gap"] = "命中需求（primary 证据）：" + "/".join(primary_needs[:3])
    mps = pm.get("matched_projects") or []
    if mps:
        m = mps[0]
        out["matched_project"] = (f"{m['project']}（match={m['match_score']}，"
                                  f"直接证据：{'/'.join(m.get('direct_evidence_kinds') or [])}）")
    inc = []
    if subs:
        levels = gm.get("incremental_evidence_level") or {}
        parts = []
        for s in subs:
            if levels.get(s) == "confirmed_absent":
                parts.append(f"新增子能力 {s}（该族已装成员完整 SKILL.md 均已读取且未提及"
                             "= confirmed_absent）")
            else:
                parts.append(f"新增子能力 {s}（底座摘要未发现=summary_not_found；"
                             "仅可观察，不得单独支撑安装推荐）")
        inc.append("；".join(parts))
    if c.get("update_available"):
        inc.append("已装版本落后，候选上游有更新")
    if c.get("installed_relationship") == "replacement_candidate":
        inc.append("可作为现有已装 Skill 的替代/升级")
    if sat == "strong_degraded":
        inc.append("同族已装能力 availability=degraded，需要恢复路线")
    for r in strong_incremental_value(c)[1]:
        if r.startswith("project_specific_tech:"):
            inc.append(f"项目专用技术路线直接命中：{r.split(':', 1)[1]}"
                       "（现有已装强能力不覆盖该技术/平台组合）")
    out["incremental_over_installed"] = "；".join(inc)
    if c.get("update_available"):
        out["why_now"] = "上游版本更新已出现"
    elif sat in ("none", "weak"):
        out["why_now"] = f"真实缺口（饱和={sat}），当前池内该族最优路线"
    elif mps:
        out["why_now"] = "当前活跃项目直接命中"
    else:
        out["why_now"] = "primary 级需求证据仍然成立"
    return out



def build_corroborated_repos(reg, cands):
    """§五 质量门③的佐证集合：T0/T1/T2 注册源 + 本轮 official/vendor 候选的 owner/repo。

    单独抽成函数，让 build_context（日报）与 make_digest（对照件）用同一份口径，
    避免两处 Top 对「谁有交叉佐证」判断不一致。
    """
    repos = set()
    for t in ("0", "1", "2"):
        for e in (reg.get("tiers", {}) or {}).get(t, []) or []:
            sid = (e.get("source_id") or "").lower()
            if sid:
                repos.add(sid)
    for c in cands:
        if c.get("origin_type") in ("official", "vendor"):
            repos.add(f"{c.get('owner','')}/{c.get('repo','')}".lower())
    return repos

def select_top(ranked, limit=30, *, min_score=None, require_evidence=True,
               corroborated_repos=None, fold_cross_repo=True, require_no_mismatch=True,
               require_no_unresolved_scope=True, require_core_evidence=True,
               max_per_repo=3, require_saturation=True, apply_quota=True):
    """选出 Personalized Top，返回 (selected, alternatives_map)。`alts[primary_key] = [dup...]`。

    v2.3 三道质量门（§五）+ 跨仓功能族折叠（§三）：
      · score ≥ min_score（配置化最低阈值）
      · 有真实个性化证据（has_personalized_evidence）
      · T3/discovery_only 无 T1·T2·官方交叉佐证不得入 Top
      · 跨 repo 同功能族只展示 PRIMARY，其余进 alternatives
      · 同仓库 ≤3 条 + 同仓库内同族折叠（v2.2 保留）
    不足 limit 时如实返回实际条数 —— **不凑数**。

    v2.4 第四道门（§九）：**存在未解除的平台错配 → 不进 Personalized Top**。
    错配只是「当前没有证据使用该技术栈」，不是永久黑名单：用户真实项目一旦用上
    该平台，analyze 会把该域标为 resolved，这道门自动放行。

    v2.6 第五道门（§四/§十）：**未解除的 product_internal 不进 Top**
    （BrowserOS test-ui 事故：产品自研 Skill ≠ 通用能力）。同样可解除，非黑名单。

    v2.8 核心证据门（§十四）：只有 supporting/mention 级需求证据、又没有
    真 gap（primary 证据）/ update / replacement / 真实 matched_project 的候选，
    不得单独进 Top——「支持 React Native / 包含 dashboard / 提到 Playwright /
    用了 Python API」撑不起个人推荐位。

    v2.10 §十四：**Gate 最终顺序固定**（不再「先按分数、再解释为什么不相关」）：
      1 Security Gate（池外：reject/ignore 已被 recommendation 层剔除）
      2 Candidate validity / lineage（池外：already_installed 不进池；same_name_* 最高 watch）
      3 Product / domain scope（未解除错配、product_internal、竞品/内部/信息不足三态）
      4 Primary evidence（个性化证据 + 核心需求证据门）
      5 Required-tech compatibility（match_projects 层：不兼容的 required_tech
        已让 shared_need 无法单独造项目匹配 —— 这里不再重复记账）
      6 Capability saturation（strong 默认降权，§五）
      7 Installed overlap / incremental value（CLEAR_INCREMENTAL_VALUE，§五/§六）
      8 Score threshold
      9 Functional family 折叠
      10 Capability family quota（strong 族 1 条，§七）
    入选条目会被写入 `personalized_reason`（§十二）。
    """
    def _gate_reason(c):
        """按 §十四 顺序返回第一个拦下该候选的 Gate 名；None = 通过。"""
        gm = c.get("capability_gap_match") or {}
        # ③ 产品 / 领域 scope
        if require_no_mismatch and bool(unresolved_mismatch(c)):
            return "domain_mismatch"
        if require_no_unresolved_scope and bool(unresolved_scope(c)):
            return "product_scope"
        # v2.9 §二.11 / §三.3.3 / §四.4：未解决竞品、产品内部能力、领域信息不足
        if gm.get("match_status") in ("internal_only", "competitor_mismatch",
                                      "insufficient_info", "not_applicable"):
            return "gate_status"
        if gm.get("competitor_unresolved"):
            return "competitor_unresolved"
        # ④ Primary evidence（个性化 + 核心需求证据）
        if require_evidence and not has_personalized_evidence(c):
            return "no_personalized_evidence"
        if require_core_evidence and not core_evidence_ok(c):
            return "supporting_only"
        # ⑥/⑦ 能力饱和 + 增量价值（§五/§六/§七）
        if require_saturation and not saturation_gate_ok(c):
            return "capability_saturation"
        # ⑧ 分数阈值
        if min_score is not None and c.get("score", 0) < min_score:
            return "score"
        return None

    def _passes_gates(c):
        return _gate_reason(c) is None and not is_t3_uncorroborated(c, corroborated_repos)

    out, alts, repo_cnt, fam_tokens = [], {}, {}, {}
    fam_state = {}
    for c in ranked:
        if len(out) >= limit:
            break
        if _gate_reason(c) or is_t3_uncorroborated(c, corroborated_repos):
            continue
        # ⑨ 跨仓同功能族折叠
        if fold_cross_repo:
            dup = next((o for o in out if functional_family(o, c)[0]), None)
            if dup is not None:
                alts.setdefault(dup["canonical_key"], []).append({
                    "canonical_key": c["canonical_key"],
                    "skill_name": c.get("skill_name"),
                    "source": f"{c.get('owner','')}/{c.get('repo','')}",
                    "score": c.get("score"),
                    "reason": functional_family(dup, c)[1]})
                continue
        # 同仓库上限 + 同仓库内同族折叠（v2.2 保留）
        rk = f"{c.get('owner','')}/{c.get('repo','')}".lower()
        if repo_cnt.get(rk, 0) >= max_per_repo:
            continue
        toks = tuple(t for t in re.split(r"[-_\s]+", (c.get("skill_name") or "").lower()) if t)
        seen = fam_tokens.setdefault(rk, [])
        if toks and any(same_family(toks, s) for s in seen):
            continue
        # ⑩ capability family quota（§七）
        if apply_quota and not family_quota_state_ok(c, fam_state):
            continue
        seen.append(toks)
        repo_cnt[rk] = repo_cnt.get(rk, 0) + 1
        c["personalized_reason"] = build_personalized_reason(c)   # §十二
        out.append(c)
    # §三/§八 补漏：同功能族的兄弟条目若在**主循环里就落选**（例如先被同仓库上限
    # 拦下、或它排在 PRIMARY 之前但当时还没有同族入选），也必须登记进 ALTERNATIVES，
    # 不能无声消失 —— §三 要求「其余放进 alternatives」。
    if fold_cross_repo and out:
        selected_keys = {c.get("canonical_key") for c in out}
        known = {d["canonical_key"] for v in alts.values() for d in v}
        for c in ranked:
            ck = c.get("canonical_key")
            if ck in selected_keys or ck in known:
                continue
            if not _passes_gates(c):
                continue
            fam = next((o for o in out if functional_family(o, c)[0]), None)
            if fam is None:
                continue
            alts.setdefault(fam["canonical_key"], []).append({
                "canonical_key": ck,
                "skill_name": c.get("skill_name"),
                "source": f"{c.get('owner','')}/{c.get('repo','')}",
                "score": c.get("score"),
                "reason": functional_family(fam, c)[1]})
            known.add(ck)
    return out, alts

def select_top30(ranked, limit=30):
    """向后兼容入口：只返回选中的候选列表（不含 alternatives）。"""
    return select_top(ranked, limit)[0]

def main():
    data = load_json(CANDIDATES_PATH)
    reg = load_json(REGISTRY_PATH, {"counts": {}})
    if not data: print("no candidates"); return 1
    cands = data["candidates"]
    for c in cands:
        c.pop("personalized_reason", None)   # v2.10 §十二：每轮重建，旧 Top 字段不残留
    prev_raw = load_json(SNAPSHOT_PATH, {})
    first_run = not prev_raw
    # v2.11 §十：快照带 schema / 引擎版本；任一变化 → SYSTEM_REBASELINE，
    # 本轮不把「引擎升级 / 元数据补全」造成的全池变化冒充为外部上游更新。
    _engine = str(data.get("version"))
    _same_base = bool(prev_raw.get("candidates")) \
        and prev_raw.get("snapshot_schema_version") == SNAPSHOT_SCHEMA_VERSION \
        and str(prev_raw.get("analysis_engine_version")) == _engine
    prev = prev_raw.get("candidates") if _same_base else {}
    rebaselined = bool(prev_raw) and not _same_base and not first_run

    counts = data.get("counts", {})
    rel = {}
    for c in cands: rel[c["installed_relationship"]] = rel.get(c["installed_relationship"], 0) + 1
    gap = {}
    for c in cands: gap[c["capability_gap_match"]["gap_level"]] = gap.get(c["capability_gap_match"]["gap_level"], 0) + 1
    rec = {}
    for c in cands: rec[c["recommendation"]] = rec.get(c["recommendation"], 0) + 1
    sec = {}
    for c in cands: sec[c["security"]["risk_level"]] = sec.get(c["security"]["risk_level"], 0) + 1
    # v2.2：安全结论按 verdict（pass / review_required / block / unscanned）与深度审查状态统计
    vd = {}
    for c in cands:
        k = c["security"].get("verdict")
        vd[k] = vd.get(k, 0) + 1
    dss = {}
    for c in cands:
        k = c["security"].get("deep_scan_status")
        dss[k] = dss.get(k, 0) + 1
    # matched_projects 覆盖度（§三/§十六：**高匹配候选**必须答出具体项目名）
    # 分母只取「真有需求证据」的候选 —— 把全部 watch 都算进来会把无关候选稀释进分母，
    # 使覆盖率这个指标失去意义（v2.2 修正）。
    hm_all = [c for c in cands if c["recommendation"] in ("install_candidate", "watch")
              and (c.get("project_match") or {}).get("need_evidence")]
    hm_with_proj = [c for c in hm_all
                    if (c.get("project_match") or {}).get("matched_projects")]

    # ---- delta ----
    deltas = {}
    if not rebaselined:
        for c in cands:
            cats = classify_delta(prev.get(c["canonical_key"]), snap_key(c))
            if cats: deltas[c["canonical_key"]] = sorted(cats)
        for ck in prev:
            if ck not in {c["canonical_key"] for c in cands}:
                deltas[ck] = ["NO_LONGER_RELEVANT"]
    delta_by_cat = {k: 0 for k in DELTA_CATS}
    for cats in deltas.values():
        for k in cats:
            if k in delta_by_cat: delta_by_cat[k] += 1
    if rebaselined:
        delta_by_cat["SYSTEM_REBASELINE"] = 1

    # ---- Top30 / 每日重点（§七：不得塞 ignore / reject 补数量） ----
    # Top30 的定义 = 「值得用户看的 Personalized Top candidates」：
    #   允许 install_candidate / watch，**禁止 ignore / reject**。
    #   如果本轮符合标准的只有 23 个，就输出 Top23 —— 不为凑 30 个数字塞垃圾。
    # 池内排序见 rank_candidate；多样性（同仓库 ≤3 / 同族折叠）在 select_top30 里最后执行。
    cfg = load_config()
    top_cfg = cfg.get("top_candidates", {})
    target_limit = top_cfg.get("target_limit", 30)
    min_top_score = top_cfg.get("min_score")
    allowed_rec = tuple(top_cfg.get("allowed_recommendations",
                                    ["install_candidate", "watch"]))
    # §五 质量门③：T3 / discovery_only 必须有 T1·T2·官方来源交叉佐证才可进 Top
    corroborated_repos = build_corroborated_repos(reg, cands)
    pool = [c for c in cands if c["installed_relationship"] != "already_installed"
            and c["recommendation"] in allowed_rec]
    ranked = sorted(pool, key=rank_candidate)
    top30, top_alts = select_top(ranked, limit=target_limit, min_score=min_top_score,
                                 max_per_repo=top_cfg.get("max_per_repo", 3),
                                 corroborated_repos=corroborated_repos)
    t3_unc = [c for c in ranked if is_t3_uncorroborated(c, corroborated_repos)]
    functional_dupes = sum(len(v) for v in top_alts.values())
    # v2.4 §九/§十四：未解除的平台错配必须在 Top 里为 0（被挡在 Top 外的要如实计数）
    top_mismatch = [c for c in top30 if unresolved_mismatch(c)]
    mismatch_blocked = [c for c in ranked if unresolved_mismatch(c)]
    # v2.6 §四/§十：未解除的 product_internal 同样必须为 0（第五道门）
    top_scope = [c for c in top30 if unresolved_scope(c)]
    scope_blocked = [c for c in ranked if unresolved_scope(c)]
    # v2.4 §十：PROJECT_MATCH_QUALITY（按证据类型分列 + 被拒绝的假相关），
    # 取代旧的「direct_evidence 字段非空率」——非空不等于语义有效。
    pmq = dict(data.get("project_match_quality") or {})
    mp_entries = [m for c in cands
                  for m in ((c.get("project_match") or {}).get("matched_projects") or [])]
    pmq.setdefault("matched_project_entries", len(mp_entries))
    pmq.setdefault("unresolved_mismatch_candidates",
                   sum(1 for c in cands if unresolved_mismatch(c)))
    direct_rate = (sum(1 for m in mp_entries if m.get("direct_evidence")) / len(mp_entries)
                   if mp_entries else 1.0)

    # 每日正文只放「今天真的变了」的候选：Top30 无变化时不重复输出同样内容。
    # 首次运行（无基线）例外：展示 install_candidate 作为初始观察面。
    meaningful = {k: v for k, v in deltas.items() if "NO_LONGER_RELEVANT" not in v}
    if first_run or rebaselined:
        # v2.11 §十：引擎/schema 换代 = 重建基线（SYSTEM_REBASELINE），
        # 不逐候选输出被重算出来的伪变化；正文回到「初始观察面」模式。
        ic_ranked = [c for c in ranked if c["recommendation"] == "install_candidate"]
        # 正文同样走质量门与多样性规则：不出现同一 SDK 的多个变体占版面
        body = select_top(ic_ranked, limit=10, min_score=min_top_score,
                          corroborated_repos=corroborated_repos)[0]
        if not body: body = top30[:5]
    else:
        changed_keys = [k for k in meaningful]
        by_key = {c["canonical_key"]: c for c in cands}
        body = select_top(sorted([by_key[k] for k in changed_keys
                                  if k in by_key
                                  and by_key[k]["recommendation"] in allowed_rec
                                  and by_key[k]["installed_relationship"] != "already_installed"],
                                 key=lambda c: (-len(meaningful[c["canonical_key"]]), -c["score"])),
                          limit=10, min_score=min_top_score,
                          corroborated_repos=corroborated_repos)[0]

    high_match = [c for c in cands if c["recommendation"] == "install_candidate"]
    rejected = [c for c in cands if c["recommendation"] == "reject"]
    watchlist = [c for c in cands if c["recommendation"] == "watch"]
    gap_cands = [c for c in cands if c["capability_gap_match"]["gap_level"] in ("none", "weak")]
    trending = [c for c in cands if c.get("trend_signal") in ("high_installs", "rising")
                and c["installed_relationship"] in ("new_capability", "complement")]
    update_flags = [c for c in cands if c.get("update_available")]
    # v2.6 §三：UPDATE_CANDIDATES 由「已装侧血缘」驱动（与对照件共用 build_update_lineage）
    try:
        _inst = load_installed()
    except Exception:
        _inst = {"all_known": {}}
    update_items = build_update_lineage(cands, _inst)
    updated = [c for c in cands if c["canonical_key"] in deltas
               and {"UPDATED", "MATCH_CHANGED"} & set(deltas[c["canonical_key"]])]
    update_all = sorted({c["canonical_key"]: c for c in (updated + update_flags)}.values(),
                        key=lambda c: -c["score"])
    t3 = load_json(os.path.join(os.path.dirname(CANDIDATES_PATH), "raw", "discovery_latest.json"), {}).get("tier3", {})

    L = []
    L.append("# External Skills Context（外部 Skill 情报 · 日报底座）")
    L.append("")
    L.append(f"> 生成日期：{TODAY}｜来源注册表 v{reg.get('version')}："
             f"T0 {reg.get('counts',{}).get('0',0)} / T1 {reg.get('counts',{}).get('1',0)} / "
             f"T2 {reg.get('counts',{}).get('2',0)} / T3 {reg.get('counts',{}).get('3',0)}")
    L.append("> 本层只做「发现 → 标准化 → 去重 → 匹配 → 安全审查 → 个性化排序」。"
             "**不安装、不删除、不升级任何 Skill**；安装一律在 Skill Manager 人工执行。")
    L.append("> 排名/安装量只是 adoption signal，绝不等于质量或推荐依据。完整数据：`data/SKILL_CANDIDATES.json`")
    L.append("")

    # ================= 机器可读区（11 节） =================
    L.append("```")
    L.append("SOURCE_HEALTH:")
    for t in ("0", "1", "2", "3"):
        for e in reg.get("tiers", {}).get(t, []):
            L.append(f"  - T{t} {e['source_id']}: {e.get('status','?')}"
                     + (f" (trust={e.get('trust_level')})" if e.get('trust_level') else ""))
    L.append(f"  - skills.sh entries_today: {len(t3.get('skills_sh', {}).get('entries', []))}"
             f" (healthy={t3.get('skills_sh', {}).get('healthy')})")
    L.append(f"  - clawhub entries_today: {len(t3.get('clawhub', {}).get('entries', []))}"
             f" (healthy={t3.get('clawhub', {}).get('healthy')})")
    L.append("")
    L.append("CANDIDATE_POOL_SUMMARY:")
    L.append(f"  raw: {counts.get('raw_candidates')}")
    L.append(f"  canonical: {counts.get('after_canonical_dedup')}")
    L.append(f"  invalid_artifacts_removed: {counts.get('invalid_artifacts_removed', 0)}   # 构建产物/静态资源（§一.1）")
    L.append(f"  invalid_names_removed: {counts.get('invalid_names_removed', 0)}   # 非法 skill slug")
    L.append(f"  bottom_up_total: {counts.get('bottom_up_total', 0)}")
    L.append(f"  bottom_up_verified: {counts.get('bottom_up_verified', 0)}   # 过 SKILL.md 硬门")
    L.append(f"  bottom_up_quarantined: {counts.get('bottom_up_quarantined', 0)}   # 已隔离，不入正式池")
    for k in ("already_installed", "same_name_unverified", "same_name_different_source",
              "possible_fork", "near_duplicate", "overlap", "complement",
              "new_capability", "replacement_candidate"):
        # v2.6 §二：same_name_* / possible_fork 只有真出现才写行，不把 0 伪装成结论
        if rel.get(k, 0) or not k.startswith(("same_name", "possible_fork")):
            L.append(f"  {k}: {rel.get(k, 0)}")
    L.append(f"  gap_none: {gap.get('none',0)}")
    L.append(f"  gap_weak: {gap.get('weak',0)}")
    L.append(f"  gap_medium: {gap.get('medium',0)}")
    L.append(f"  gap_strong: {gap.get('strong',0)}")
    L.append("")
    L.append(f"NEW_DISCOVERIES: {delta_by_cat['NEW']}")
    L.append(f"HIGH_MATCH_CANDIDATES: {len(high_match)}")
    L.append(f"CAPABILITY_GAP_CANDIDATES: {len(gap_cands)}   # gap_level ∈ {{none, weak}}")
    L.append(f"TRENDING_RELEVANT: {len(trending)}")
    L.append(f"UPDATE_CANDIDATES: {len(update_all)}   # delta 变化 + 已装但版本落后（update_available）")
    L.append(f"SECURITY_REJECTED: {len(rejected)}")
    L.append(f"WATCHLIST: {len(watchlist)}")
    L.append("")
    # v2.11 §十二：行动类型——「恢复/修复已有能力」与「外面发现的新 Skill」分开
    at_cnt = {}
    for c in cands:
        k = c.get("action_type") or "—"
        at_cnt[k] = at_cnt.get(k, 0) + 1
    _ak = _inst.get("all_known") or {}

    def _known_missing_target(c):
        tgt = ((_ak.get(c.get("overlap_with_installed") or "") or {}).get("canonical") or {})
        return bool(tgt) and not tgt.get("installed_canonical")
    mis = sum(1 for c in cands
              if c.get("action_type") == "new_install" and _known_missing_target(c))
    L.append("ACTION_TYPES:")
    for k in ("new_install", "watch", "restore_candidate", "update_candidate",
              "replacement_candidate", "reject"):
        L.append(f"  {k}: {at_cnt.get(k, 0)}")
    L.append(f"  known_missing_misreported_as_new_install: {mis}   # v2.11 §十二/§十六：必须为 0（缺失能力不得伪装成新装推荐）")
    L.append("")
    # v2.6 §三/§二.6：更新项按「已装侧血缘」逐条列出，四件套字段齐全；
    # installed_upstream 与 update_upstream 不一致时必须 lineage_evidence 撑起，否则不得关联。
    L.append(f"UPDATE_LINEAGE: {len(update_items)}   # 更新项来源=Installed Source Map，不绑同名外部仓")
    for it in update_items:
        L.append(f"  - installed_canonical_id: {it['installed_canonical_id']}")
        L.append(f"    installed_upstream: {it['installed_upstream']}")
        L.append(f"    update_upstream: {it['update_upstream']}")
        L.append(f"    lineage_evidence: {it['lineage_evidence'][:110]}")
        L.append(f"    lineage_verified: {'true' if it['lineage_verified'] else 'false'}")
    L.append("")
    # v2.4 §十：PROJECT_MATCH_QUALITY —— 取代「direct_evidence 字段非空率」。
    # 非空 ≠ 语义有效；这里按**证据类型**分列，并把「被拒掉的假相关」显式记出来。
    L.append("PROJECT_MATCH_QUALITY:")
    L.append(f"  matched_candidates: {pmq.get('matched_candidates', 0)}   # 至少有一个 matched_project 的候选数")
    L.append(f"  matched_project_entries: {pmq.get('matched_project_entries', 0)}   # matched_project 总条数（候选×项目）")
    L.append(f"  strong_tech_evidence: {pmq.get('strong_tech_evidence', 0)}   # 专用技术栈直接命中（Expo/RN/Android/Supabase/Next.js/PWA/Vercel/.NET…）")
    L.append(f"  positioning_evidence: {pmq.get('positioning_evidence', 0)}   # 项目定位/功能语义命中")
    L.append(f"  shared_need_evidence: {pmq.get('shared_need_evidence', 0)}   # 项目自身需求与候选能力命中")
    L.append(f"  lexical_evidence: {pmq.get('lexical_evidence', 0)}   # 词面证据（v2.5：独立成立仅限领域短语；词级重叠只作次要加分）")
    L.append(f"  secondary_tech_only_rejected: {pmq.get('secondary_tech_only_rejected', 0)}   # 只靠泛用技术栈（TS/React/Python/Docker…）硬凑、已被拒的候选数")
    L.append(f"  negated_evidence_rejected: {pmq.get('negated_evidence_rejected', 0)}   # 被否定窗口/排除语境压制掉的命中次数")
    L.append(f"  lexical_single_rejected: {pmq.get('lexical_single_rejected', 0)}   # 词面重叠只因单个低区分度词（manager/service…）而不足以成立的次数")
    L.append(f"  lexical_alone_rejected: {pmq.get('lexical_alone_rejected', 0)}   # v2.5 §三：词面 boost（≥2 词）想**独立**造匹配、被拒的次数（词面只作次要加分）")
    L.append(f"  lexical_phrase_direct_evidence: {pmq.get('lexical_phrase_direct_evidence', 0)}   # v2.5 §五：靠人工整理的领域短语独立成立的词面证据条数")
    L.append(f"  bare_prompt_direct_evidence: {pmq.get('bare_prompt_direct_evidence', 0)}   # v2.5 §四：裸 prompt 被当直接证据的次数（**必须为 0**）")
    L.append(f"  tech_words_used_as_lexical_direct_evidence: {pmq.get('tech_words_used_as_lexical_direct_evidence', 0)}   # v2.5 §四：泛用技术词充当词面直接证据的次数（**必须为 0**）")
    L.append(f"  unresolved_mismatch_candidates: {pmq.get('unresolved_mismatch_candidates', 0)}   # 存在未解除平台错配的候选数（只作观察）")
    # v2.6 §五/§二/§四：重定向压制 + 身份血缘 + GCP 别名 + 产品 scope 的数据级审计行
    L.append(f"  redirect_evidence_rejected: {pmq.get('redirect_evidence_rejected', 0)}   # v2.6 §五：跨 Skill 重定向小句被剪掉的次数")
    L.append(f"  required_tech_blocked_shared_need: {pmq.get('required_tech_blocked_shared_need', 0)}   # v2.10 §八：required_tech 与项目不兼容 → shared_need 单独不造项目匹配的次数")
    L.append(f"  same_name_only_already_installed: {pmq.get('same_name_only_already_installed', 0)}   # v2.6 §二：只凭同名判已安装的条数（**必须为 0**）")
    L.append(f"  wrong_update_lineage: {pmq.get('wrong_update_lineage', 0)}   # v2.6 §三：血缘未验证的 update_available（**必须为 0**）")
    L.append(f"  same_name_unverified_candidates: {pmq.get('same_name_unverified_candidates', 0)}   # 同名但血缘未确认（最高 watch，等人工确认）")
    L.append(f"  gcp_alias_missed: {pmq.get('gcp_alias_missed', 0)}   # v2.6 §四：描述含 GCP 产品别名却未标 gcp 域的条数（**必须为 0**）")
    L.append(f"  product_internal_unresolved_candidates: {pmq.get('product_internal_unresolved_candidates', 0)}   # v2.6 §十：未解除的产品自研 Skill 数")
    # v2.7 §二/§七：确定性 + 产品专项 scope 的审计行
    L.append(f"  product_specific_scope_unresolved: {pmq.get('product_specific_scope_unresolved', 0)}   # v2.7 §七：未解除的产品专项 platform_operation 数（GA Admin / SecOps / anthropic-brand…）")
    L.append("  determinism: hashseed_matrix（0/1/2/3/42/123）已由 tests/test_pipeline.py::test_v27_determinism_hashseed 作为硬门   # v2.7 §二")
    L.append("  note: 四个 *_evidence 是「候选×项目」条数，同一条可同时具备多种证据；")
    L.append("        所有 projected 条目都必须至少带 1 类直接证据（direct_evidence 非空率 "
             f"{direct_rate:.0%}，仅作完整性自检，不作 KPI）")
    L.append("")
    # v2.11 §五：输入 A 项目画像健康度（只标记、不篡改；冲突侧 strong_tech 已抑制）
    pch = data.get("project_context_health") or {}
    L.append("PROJECT_CONTEXT_HEALTH:")
    L.append(f"  conflict_count: {pch.get('conflict_count', 0)}   # v2.11 §四：描述 ↔ 技术栈互相矛盾的项目数（外部层不修改输入 A，只标记）")
    for it in (pch.get("conflicts") or []):
        L.append(f"  - project: {it['project']}")
        L.append(f"    reason: {it['reason']}")
        L.append(f"    description_tech: {'/'.join(it.get('description_tech') or []) or '—'}")
        L.append(f"    missing_tech: {'/'.join(it.get('missing_tech') or []) or '—'}")
        L.append(f"    declared_tech: {'/'.join(it.get('declared_tech') or []) or '—'}")
        L.append(f"    suppressed_strong_tech: {'/'.join(it.get('suppressed_strong_tech') or []) or '—'}   # 冲突解决前不得凭这些造 strong_tech 匹配")
    L.append(f"  conflict_strong_tech_suppressed: {pmq.get('conflict_strong_tech_suppressed', 0)}   # 候选×项目 被抑制的冲突 strong_tech 证据次数")
    L.append("")
    L.append("PERSONALIZED_TOP30:")
    L.append(f"  target_limit: {target_limit}")
    L.append(f"  actual_count: {len(top30)}   # 不足 target 时输出实际数量，不塞 ignore/reject 补数量")
    L.append(f"  min_score: {min_top_score if min_top_score is not None else 'none (未配置质量门)'}")
    L.append(f"  functional_duplicates: {functional_dupes}   # 跨仓同功能族被折叠进 alternatives 的条目数（§三）")
    L.append(f"  t3_uncorroborated: {len(t3_unc)}   # T3/discovery_only 无 T1·T2·官方交叉佐证，挡在 Top 外（只留 WATCHLIST）")
    L.append(f"  alternative_families: {len(top_alts)}")
    L.append(f"  contains_ignore: {'yes' if any(c['recommendation'] == 'ignore' for c in top30) else 'no'}")
    L.append(f"  contains_reject: {'yes' if any(c['recommendation'] == 'reject' for c in top30) else 'no'}")
    L.append(f"  generated: {'yes' if top30 else 'no'}")
    L.append(f"  high_match_count: {len(high_match)}")
    L.append(f"  matched_projects_coverage: {len(hm_with_proj)}/{len(hm_all)}   # 高匹配候选中答出具体项目名的比例（准确率优先，不再要求 90%+）")
    L.append(f"  top_candidates_with_unresolved_mismatch: {len(top_mismatch)}   # §九：必须为 0")
    L.append(f"  mismatch_blocked_from_top: {len(mismatch_blocked)}   # 因未解除平台错配被挡在 Top 外（仍留 WATCHLIST）")
    L.append(f"  top_candidates_with_unresolved_product_scope: {len(top_scope)}   # v2.6 §十：必须为 0（第五道门）")
    L.append(f"  scope_blocked_from_top: {len(scope_blocked)}   # 因未解除 product_internal 被挡在 Top 外（可解除，非黑名单）")
    top_core_bad = [c for c in top30 if not core_evidence_ok(c)]
    core_blocked = [c for c in ranked if not core_evidence_ok(c)]
    L.append(f"  top_candidates_supporting_only: {len(top_core_bad)}   # v2.8 §十四：Top 内仅有 supporting/mention 级核心证据的条数（**必须为 0**）")
    L.append(f"  core_evidence_blocked_from_top: {len(core_blocked)}   # 因缺核心需求证据被挡在 Top 外（仍留 WATCHLIST）")
    # ---- v2.10 §四~§七 / §十一 / §十二：能力饱和 + 家族配额 + 推荐理由审计 ----
    def _sat_of(c):
        return (c.get("capability_gap_match") or {}).get("capability_saturation") or "none"

    def _fam_of(c):
        gm = c.get("capability_gap_match") or {}
        return gm.get("matched_gap") or gm.get("saturation_family")

    sat_blocked = [c for c in ranked if not saturation_gate_ok(c)]
    top_strong_sat = [c for c in top30 if _sat_of(c) in ("strong", "strong_degraded")]
    top_strong_no_inc = [c for c in top_strong_sat
                         if not (c.get("personalized_reason") or {})
                         .get("incremental_over_installed")]
    fd_strong_top = [c for c in top30 if _fam_of(c) == "frontend_design"
                     and _sat_of(c) in ("strong", "strong_degraded")]
    L.append(f"  top_candidates_strong_saturation: {len(top_strong_sat)}   # v2.10 §五：Top 内 strong 饱和族候选数（每条都必须带增量价值）")
    L.append(f"  top_strong_without_incremental_reason: {len(top_strong_no_inc)}   # v2.10 §十二：strong 饱和但 incremental_over_installed 为空（**必须为 0**）")
    L.append(f"  saturation_blocked_from_top: {len(sat_blocked)}   # v2.10 §五：strong/medium 饱和且无明确增量 → 挡在 Top 外（可解除，非黑名单）")
    L.append(f"  frontend_design_strong_top_count: {len(fd_strong_top)}   # v2.10 §十一：frontend_design（已装 strong）族在 Top 的条数")
    L.append(f"  capability_family_quota: strong=1 / medium=2 / weak|none=3   # v2.10 §七")
    L.append(f"  security_scanned: {sec.get('low',0) + sec.get('medium',0) + sec.get('high',0)}")
    L.append(f"  security_unscanned: {sec.get('unknown',0)}")
    L.append(f"  security_verdict_pass: {vd.get('pass',0)}")
    L.append(f"  security_verdict_review_required: {vd.get('review_required',0)}")
    L.append(f"  security_verdict_block: {vd.get('block',0)}")
    L.append(f"  deep_scan_complete: {dss.get('complete',0)}   # 真正做了深度静态审查的（= install 候选）")
    L.append(f"  deep_scan_failed: {dss.get('failed',0)}")
    L.append(f"  deep_scan_pending: {dss.get('pending',0)}   # 超预算未扫，fail-closed")
    L.append(f"  deep_scan_not_required: {dss.get('not_required',0)}   # 未进安装候选，未触发")
    L.append(f"  deep_scan_skipped: {dss.get('skipped',0)}   # 无目录/未扫描")
    # ---- v2.9 §四.8：安全完整审查进度（独立机器块，另见 SECURITY_REVIEW_GATE 段）----
    _au = data.get("security_review_gate") or {}
    _bk = _au.get("product_internal_block_breakdown") or {}
    L.append(f"  full_scan_eligible: {_au.get('full_scan_eligible', 0)}   # 入队候选（硬 Gate 命中者不入队）")
    L.append(f"  full_scan_complete: {_au.get('full_scan_complete', 0)}")
    L.append(f"  full_scan_remaining: {_au.get('full_scan_remaining_count', 0)}   # **必须为 0**")
    L.append(f"  full_scan_gated_out: {_au.get('product_internal_blocked', 0)}   # 被硬 Gate 挡在队列外")
    L.append("  top10:")
    for c in top30[:10]:
        L.append(f"    - {c['canonical_key']} | score={c['score']} | gap={c['capability_gap_match']['gap_level']}"
                 f" | rel={c['installed_relationship']} | risk={c['security']['risk_level']}"
                 f" | verdict={c['security'].get('verdict')} | rec={c['recommendation']}")
    L.append("")
    # ---- v2.9 §四.8：安全完整审查进度 + 产品关系终审计（独立机器块）----
    au = data.get("security_review_gate") or {}
    bk = au.get("product_internal_block_breakdown") or {}
    top_comp_unres = sum(1 for c in top30
                         if (c.get("capability_gap_match") or {}).get("competitor_unresolved"))
    top_scope_unres = sum(1 for c in top30
                          if (c.get("capability_gap_match") or {}).get("match_status")
                          in ("internal_only", "competitor_mismatch", "insufficient_info"))
    L.append("SECURITY_REVIEW_GATE:")
    L.append(f"  full_scan_complete: {au.get('full_scan_complete', 0)}   # 本轮真正完成深度静态审查的候选数")
    L.append(f"  full_scan_eligible: {au.get('full_scan_eligible', 0)}   # 入队候选（硬 Gate 命中者不入队）")
    L.append(f"  full_scan_queue: {au.get('full_scan_eligible', 0)}   # 队列长度（明细见 data/state/full_scan_queue.json）")
    L.append(f"  full_scan_remaining: {au.get('full_scan_remaining_count', 0)}   # **必须为 0**（不得只报计划）")
    L.append(f"  product_internal_unresolved: {au.get('product_internal_unresolved', 0)}")
    L.append(f"  product_internal_blocked: {au.get('product_internal_blocked', 0)}   # 被硬 Gate 挡在队列外")
    L.append(f"  product_internal_block_breakdown:")
    L.append(f"    project_scope_section_not_required: {bk.get('project_scope_section_not_required', 0)}   # §四.11 即使为 0 也必须输出")
    L.append(f"    developer_tool_gate_unresolved: {bk.get('developer_tool_gate_unresolved', 0)}   # scope unresolved / mcp-only / 主目标未解决")
    L.append(f"    competitor_block: {bk.get('competitor_block', 0)}   # 未解决竞品关系")
    L.append(f"  resolved_remaining_count: {au.get('resolved_remaining_count', 0)}   # 被挡但已具备解除证据（可复核后放行）的条数")
    L.append(f"  completed_at: {au.get('completed_at') or data.get('generated')}")
    L.append("V29_FINAL_AUDIT:")
    L.append(f"  competitor_unresolved_in_top: {top_comp_unres}   # **必须为 0**（§四.11）")
    L.append(f"  competitor_unresolved_full_scan: {au.get('competitor_unresolved_full_scan', 0)}   # **必须为 0**")
    L.append(f"  product_name_false_positive_remaining: {au.get('product_name_false_positive_remaining', 0)}   # 名字含品牌词却被 Gate 挡的残留（**必须为 0**）")
    L.append(f"  product_internal_unresolved_pool_count: {au.get('product_internal_unresolved_pool_count', 0)}   # v2.11 §八：全池未解除计数（**允许 >0**，可合法留池等待解除）")
    L.append(f"  product_internal_in_full_scan_count: {au.get('product_internal_in_full_scan_count', 0)}   # 深度审查队列内残留（**必须为 0**）")
    L.append(f"  product_internal_in_top_count: {sum(1 for c in top30 if _pi_unresolved(c))}   # Top 内残留（**必须为 0**，build_context 现算）")
    L.append(f"  internal_capability_in_full_scan_count: {au.get('internal_capability_in_full_scan_count', 0)}   # 队列内残留的产品内部能力（**必须为 0**）")
    L.append(f"  scope_unresolved_in_top: {top_scope_unres}   # **必须为 0**")
    L.append(f"  top_candidates_with_unresolved_mismatch: {len(top_mismatch)}   # §九/§三.5：必须为 0（只算产品/平台领域）")
    L.append("")
    L.append(f"DAILY_DELTA:   # 与昨日快照相比；Top30 无变化时不要重复输出同样内容")
    L.append(f"  first_run: {'yes' if first_run else 'no'}")
    L.append(f"  changed_total: {len(deltas)}")
    L.append(f"  snapshot_schema_version: {SNAPSHOT_SCHEMA_VERSION}")
    L.append(f"  analysis_engine_version: {data.get('version')}")
    L.append(f"  system_rebaseline: {'yes' if rebaselined else 'no'}   "
             f"# v2.11 §十：schema/引擎换代本轮重建基线，不冒充上游更新")
    for k in DELTA_CATS:
        L.append(f"  {k}: {delta_by_cat[k]}")
    L.append("```")
    L.append("")

    # ================= 正文 =================
    if rebaselined:
        L.append("## 0. Delta 说明（SYSTEM_REBASELINE · 引擎/快照换代）")
        L.append("")
        L.append("- 本轮快照 schema 或分析引擎版本变化："
                 "**今日重建基线**；此前 `UPDATED 数百条` 属「元数据补全 / 引擎重算」冒充"
                 "上游更新，已按 §九/§十 废止——明日开始只报真实变化"
                 "（UPDATED=两侧都有值且前进；补空=METADATA_ENRICHED；评分/需求变化=MATCH_CHANGED）。")
        L.append("")
    elif first_run:
        L.append("## 0. Delta 说明（首次运行）")
        L.append("")
        L.append("- 今日建立基线快照：无昨日可比，明日开始输出 "
                 "NEW / RISING / FALLING / UPDATED / SECURITY_CHANGED / SOURCE_CHANGED / "
                 "MATCH_CHANGED / ALREADY_INSTALLED / NO_LONGER_RELEVANT。")
        L.append("")
    else:
        changed = {k: v for k, v in deltas.items() if "NO_LONGER_RELEVANT" not in v}
        L.append(f"## 0. 今日 Delta（{len(changed)} 项变化 · 按变化数排序）")
        L.append("")
        if not changed:
            L.append("- 今日无变化：候选池与昨日一致 —— **日报不要重复输出同样内容**。")
        for ck, cats in sorted(changed.items(), key=lambda x: -len(x[1]))[:15]:
            L.append(f"- `{ck}`：{', '.join(cats)}")
        L.append("")

    if body:
        L.append(f"## 1. 今日重点（{len(body)} 个 · 回答七问）")
        L.append("")
    else:
        L.append("## 1. 今日重点：**无**（Top30 与昨日一致，不重复输出）")
        L.append("")
        L.append("> 日报请只报告下方 `DAILY_DELTA` 的变化；候选池无变化时不要重复罗列同样的 Skill。")
        L.append("")
        L.append("> 需要完整清单时看第 2 节 Top30 表或 `data/SKILL_CANDIDATES.json`。")
        L.append("")
    for i, c in enumerate(body, 1):
        gm = c["capability_gap_match"]
        needs = [n["need"] for n in gm["matched_needs"]]
        L.append(f"### {i}. {c['skill_name']}（{c['owner']}/{c['repo']}）")
        L.append(f"1. **它是什么**：{(c.get('description') or '(无描述，需人工查看)')[:160]}")
        # §三：这一问必须真正答出「项目名」，不能只给能力标签
        mps = (c.get("project_match") or {}).get("matched_projects") or []
        if mps:
            # v2.5 §十一：依据必须展示**直接证据**（strong_tech/positioning/shared_need/
            # lexical 领域短语），不得回退到旧的泛化标签「技术栈词面重叠」
            proj_txt = "；".join(
                f"`{m['project']}`（匹配度 {m['match_score']}｜依据："
                f"{'/'.join((m.get('direct_evidence') or m['evidence'])[:2])}）"
                for m in mps[:3])
        else:
            proj_txt = ("未匹配到具体项目"
                        + (f"；能力标签命中：{', '.join(needs)}" if needs else ""))
        L.append(f"2. **对我哪个项目有用**：{proj_txt}")
        L.append(f"3. **我现在有没有类似能力**：{c['installed_relationship']}"
                 + (f"（与已装 `{c['overlap_with_installed']}` 相关，jaccard={c.get('token_jaccard')}）"
                    if c.get("overlap_with_installed") else "")
                 + (f"；已装侧 version_status={c.get('replacement_side_version_status') or '未比对'}"
                    if c.get("replacement_candidate_reason") else "")
                 + f"；能力饱和度={gm.get('capability_saturation', 'n/a')}"     # v2.10 §五
                 + (f"；required_tech={'/'.join(c.get('required_tech') or [])}"
                    if c.get("required_tech") else ""))                          # v2.10 §八
        L.append(f"4. **为什么今天值得看**：{', '.join(deltas.get(c['canonical_key'], ['首次入池']))}"
                 f"；能力缺口={gm['gap_level']}；上游活跃度={c.get('upstream_activity')}")
        pr = c.get("personalized_reason") or {}
        if pr:
            L.append("4b. **personalized_reason（v2.10 §十二）**："
                     f"补什么缺口={pr.get('fills_gap') or '—'}；"
                     f"匹配项目={pr.get('matched_project') or '—'}；"
                     f"比已装强在哪={pr.get('incremental_over_installed') or '—'}；"
                     f"为什么是现在={pr.get('why_now') or '—'}")
        L.append(f"5. **来源是谁**：TIER{c['source_tier']}｜{c['source']}｜{c['source_url']}"
                 f"（origin={c['origin_type']}）")
        flag_keys = ["shell_exec", "network_access", "filesystem_write", "destructive_commands",
                     "secret_access", "remote_instruction_fetch", "external_dependencies"]
        flags_on = [k for k in flag_keys if c["security"].get(k)]
        sec_line = (f"{c['security']['status']} / verdict={c['security'].get('verdict')}"
                    f" / risk={c['security']['risk_level']}")
        if flags_on:
            sec_line += "｜行为：" + ", ".join(flags_on)
        if c["security"]["findings"]:
            sec_line += ("｜规则命中：" + "; ".join(
                f"{f['rule']}[{f.get('severity')}/{f.get('behavior_context')}]"
                for f in c["security"]["findings"][:4]))
        sec_line += f"｜深度审查：{deep_scan_summary(c['security'])}"
        L.append(f"6. **安全状态**：{sec_line}")
        L.append(f"7. **推荐**：**{c['recommendation'].upper()}** — {c['recommendation_reason']}"
                 f"（score={c['score']}）"
                 + (f"；action_type={c['action_type']}" if c.get("action_type") else ""))
        L.append("")

    # v2.11 §十二：恢复 / 修复 与 「新发现的 Skill」 分开展示
    restore_items = [c for c in top30
                     if (c.get("action_type") or "") in ("restore_candidate",
                                                          "update_candidate",
                                                          "replacement_candidate")]
    if restore_items:
        L.append(f"## 1B. 恢复 / 修复（{len(restore_items)} 条 · "
                 "已有能力的恢复路线，不是外部新发现的 Skill）")
        L.append("")
        for c in restore_items:
            L.append(f"- `{c['canonical_key']}` action_type=**{c['action_type']}**"
                     f"（recommendation={c['recommendation']}；"
                     f"{(c.get('recommendation_reason') or '')[:90]}）")
        L.append("")
        L.append("> 日报引擎必须把本节单独渲染为「恢复 / 修复」，"
                 "不得表述成「推荐安装一个全新的 Skill」（v2.11 §十二）。")
        L.append("")

    L.append(f"## 2. Personalized Top（target_limit {target_limit} · 实际 {len(top30)}）")
    L.append("")
    L.append("> 定义 = **值得用户看的候选**：只含 `install_candidate` / `watch`，"
             "**不含 ignore / reject**；且必须按 v2.10 §十四 的固定顺序同时过十道门"
             "（1 Security → 2 validity/lineage → 3 产品/领域 scope → 4 primary 核心需求证据 → "
             "5 required-tech 兼容 → 6 能力饱和 → 7 已装重复/增量价值 → 8 分数阈值 → "
             "9 功能族折叠 → 10 能力族配额）："
             f"① score ≥ {min_top_score if min_top_score is not None else '—'}"
             "（配置化最低阈值）② 有真实个性化证据（命中需求 / 能力缺口 / 更新 / 恢复）"
             "③ T3·discovery_only 来源需有 T1·T2·官方交叉佐证"
             "④ **无未解除的平台错配**（Azure / AWS / GCP / .NET / Microsoft Store 等：项目档案里没有项目用该平台"
             " → 只留 WATCHLIST，不占个人 Top）"
             "⑤ **无未解除的 product_internal**（v2.6 §十：产品自研/维护 Skill —— 如 BrowserOS "
             "test-ui —— 只有用户项目真的在做这个产品才进 Top)"
             "⑥ **v2.9 §二/§三/§四**：无未解决竞品关系、非产品自身内部能力、"
             "领域三态不为「信息不足 / 不适用」——**名字含 Claude/Codex/Copilot/Gemini 本身不构成这道门**。"
             "⑦ **v2.10 §五/§六/§七**：能力族 saturated=strong 默认 watchlist，"
             "除非有 CLEAR_INCREMENTAL_VALUE（update / availability degraded / 明确新子能力 / "
             "未覆盖的项目专用技术路线）；strong 族 Top 最多 1 条代表项。"
             f"符合标准的不足 {target_limit} 个时就输出实际数量，**不为凑数塞低质量 watch**。")
    L.append("")
    L.append("> 跨仓库**同功能族**只展示一条 PRIMARY（§三）："
             "如 `github/awesome-copilot/webapp-testing` 与 `anthropics/skills/webapp-testing` "
             "只出一条，其余进下方 ALTERNATIVES。")
    L.append("")
    L.append("| # | Skill | owner/repo | 分 | 缺口 | 饱和 | 关系 | verdict | 最匹配项目 | 产品关系与领域状态 | 推荐 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top30, 1):
        mps = (c.get("project_match") or {}).get("matched_projects") or []
        proj = f"{mps[0]['project']}（{mps[0]['match_score']}）" if mps else "—"
        L.append(f"| {i} | {c['skill_name']} | {c['owner']}/{c['repo']} | {c['score']} | "
                 f"{c['capability_gap_match']['gap_level']} | "
                 f"{c['capability_gap_match'].get('capability_saturation', 'n/a')} | "
                 f"{c['installed_relationship']} | "
                 f"{c['security'].get('verdict')} | {proj} | {v29_scope_note(c)} | "
                 f"{c['recommendation']} |")
    L.append("")
    L.append("> 安装候选 ≠ 自动安装；任何 Skill 的安装都需用户在 Skill Manager 中人工执行，"
             "并另行安全复核。")
    L.append("")
    if top_alts:
        L.append("### 2.1 ALTERNATIVES（同功能族的其他上游 · 不重复推荐）")
        L.append("")
        L.append("> 候选池按 `owner/repo/skill` 各自独立记账；这里只做**展示层折叠**（§八）："
                 "同一功能族选一条 PRIMARY，其余列在此处备查。")
        L.append("")
        L.append("| PRIMARY | 同功能来源 | 折叠依据 |")
        L.append("|---|---|---|")
        for _pk, _dups in list(top_alts.items())[:15]:
            for _d in _dups[:3]:
                L.append(f"| `{_pk}` | `{_d['canonical_key']}`（{_d['source']}，"
                         f"score={_d['score']}） | {_d['reason']} |")
        L.append("")
    L.append(f"- Top 内跨仓同功能族折叠：**{functional_dupes}** 条；"
             f"T3 无交叉佐证被挡在 Top 外：**{len(t3_unc)}** 条（仍留在 WATCHLIST）。")
    L.append("")

    L.append("## 3. 安全拒绝清单（SECURITY_REJECTED，Gate 优先于分数）")
    L.append("")
    L.append("> v2.2 起只有 **block 级**（真要求执行的高危行为）才 reject；"
             "文档讨论 `.env`/`sudo`、示例引用 token 等属 `review_required`，不再误伤。")
    L.append("")
    if rejected:
        L.append("| Skill | owner/repo | verdict | 阻断规则 |")
        L.append("|---|---|---|---|")
        for c in rejected[:25]:
            blocks = "; ".join(c["security"].get("blocking_rules") or [])[:120]
            L.append(f"| {c['skill_name']} | {c['owner']}/{c['repo']} | "
                     f"{c['security'].get('verdict')} | {blocks} |")
    else:
        L.append("- 无（今日 0 个 block 级拒绝）")
    L.append("")

    L.append("## 4. 能力缺口候选（按缺口优先级）")
    L.append("")
    focus = data.get("focus_capabilities", [])
    if focus:
        L.append("当前焦点能力（读取已装侧 CAPABILITY_SUPPRESSION + CAPABILITY_AVAILABILITY 动态派生）：")
        L.append("")
        L.append("| 能力 | 覆盖 | 可用性 | 优先级 |")
        L.append("|---|---|---|---|")
        for f in focus:
            L.append(f"| {f['capability']} | {f['level']} | {f['availability']} | {f['priority']} |")
        L.append("")
    L.append(f"- 命中 none/weak 缺口的候选：**{len(gap_cands)}** 个（完整清单见 SKILL_CANDIDATES.json）")
    L.append("")

    repl = [c for c in cands if c["installed_relationship"] == "replacement_candidate"]
    L.append("## 5. 更新候选与恢复候选")
    L.append("")
    if update_items:
        L.append("**已装但版本落后（v2.6 §三：更新项由 Installed Source Map 的血缘驱动，"
                 "不再从候选池找同名对象冒充上游）**")
        L.append("")
        L.append("| installed_canonical_id | installed_upstream | update_upstream | 血缘已验证 | 依据 |")
        L.append("|---|---|---|---|---|")
        for it in update_items[:12]:
            L.append(f"| `{it['installed_canonical_id']}` | {it['installed_upstream'][:60]} | "
                     f"{it['update_upstream'][:40]} | {'是' if it['lineage_verified'] else '**否**'} | "
                     f"{it['lineage_evidence'][:80]} |")
        L.append("")
    if repl:
        L.append("**恢复/替换候选（replacement_candidate）**")
        L.append("")
        L.append("| Skill | owner/repo | 对应已装/已知 | 分数 | 上游 | 依据 |")
        L.append("|---|---|---|---|---|---|")
        for c in repl[:12]:
            L.append(f"| {c['skill_name']} | {c['owner']}/{c['repo']} | {c.get('overlap_with_installed') or '—'} | "
                     f"{c['score']} | {c.get('upstream_activity')} | {(c.get('replacement_candidate_reason') or '')[:110]} |")
        L.append("")
    if not update_items and not repl:
        L.append("- 今日无（无版本落后项、无恢复/替换候选）")
        L.append("")

    open(CONTEXT_OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    # v2.10 §十二：Top 入选者的 personalized_reason 回写候选数据（只加这一个字段，
    # 其余内容原样），让日报 / 对照件 / JSON 三处口径一致。
    # v2.11 §八：Top 侧 product_internal 计数同样在此回写（build_context 是 Top 唯一出口）。
    if isinstance(data.get("security_review_gate"), dict):
        data["security_review_gate"]["product_internal_in_top_count"] = \
            sum(1 for c in top30 if _pi_unresolved(c))
    save_json(data, CANDIDATES_PATH)
    # v2.11 §十：快照改带版本信封；engine/schema 变化时下一轮自动 SYSTEM_REBASELINE
    save_json({"snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
               "analysis_engine_version": data.get("version"),
               "generated": TODAY,
               "candidates": {c["canonical_key"]: snap_key(c) for c in cands}},
              SNAPSHOT_PATH)
    print(f"context written | top {len(top30)}/{target_limit} | daily body {len(body)} | "
          f"delta {len(deltas)} | first_run={first_run} | high_match {len(high_match)} | "
          f"projects {len(hm_with_proj)}/{len(hm_all)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
