# -*- coding: utf-8 -*-
"""候选标准化 → 合法性 Gate → canonical 去重 → 安装关系 → 能力缺口匹配
   → Security Gate v2（两阶段）→ 个性化评分 → SKILL_CANDIDATES.json

v2.2 相对 v2.1 的改动（见 HANDOFF / 整改提示词）：
  1. 合法性 Gate：ClawHub 之类聚合源的前端构建产物（.css/.js/.map/图片/字体、
     assets|static|build|dist 路径）不得进入正式候选池；错误条目只留在 raw discovery。
  2. bottom-up 搜索只是 discovery_channel，**不再等于 TIER 2**；必须过
     「存在真实 SKILL.md + 可定位 skill directory + frontmatter 可解析」硬门，
     且未在注册表验证过的来源一律 source_tier=null(unverified)、信任取最低档。
  3. 语义匹配升级为 MATCH_RULE（见 match_rules.py）：组间 AND / 组内 OR，
     杜绝「出现平台词 = 满足能力需求」的误判。
  4. matched_projects：真正回答「对我哪个项目有用」。
  5. Security Gate v2：区分「提到危险行为」与「真要求执行」。
  6. 两阶段审查：install 候选必须完成 PASS 2 深度静态审查。

v2.4（本轮）只修「项目相关性 / testing_qa 误标 / domain mismatch」：
  7. 项目匹配的直接证据分级（strong_tech / positioning / shared_need / lexical），
     泛用技术栈（TypeScript / React / Python / Docker / Shell / HTML / CSS）只能作
     secondary boost，不得单独产生 matched_project。见 match_rules.TECH_MATCH 的 tier。
  8. 平台错配（§九）真正参与排序：未解除的错配 → 总分 × DOMAIN_MISMATCH_PENALTY、
     不得 install_candidate、不得进 Personalized Top；真实项目使用该平台时自动解除。
  9. 输出 PROJECT_MATCH_QUALITY（按证据类型分列 + 被拒绝的假相关计数），
     取代旧的「351/351 字段非空率」式指标。

v2.5（本轮，冻结前最后整改）只修「剩余语义误判」，不重做 v2.4 架构：
  10. android 需求 = 平台证据 AND **真实 QA 证据**（A 表：qa/e2e/adb/emulator/真机…；
      B 表：signing/keystore/apk/aab/构建验收…），裸 device/build/install/launch 不算。
  11. 否定窗口升级为**两段式**：先按句点/分号/换行切大句，逗号仅在段内传播否定状态，
      遇到 but/however/但/可用于… 才恢复正向 —— 修掉 v2.4 逗号把 B、C 洗回正向的事故。
  12. 词面证据（lexical）不再凭泛用技术词或裸 prompt 成立：技术词全禁，
      单词面只做 boost，独立成立仅限**人工整理的领域短语**。
  13. mcp_dev / docx_xlsx / github-auto / deploy / android 统一走
      `capability_evidence_context` 四态（primary/supporting/mention/negated）：
      只有 primary 拿满缺口分，supporting 上限 8、mention/negated 上限 2；
      需求侧 supporting 权重 ×0.5。PPTX 归独立标签 pptx_processing，不冒充 docx_xlsx。

v2.6（本轮，冻结前身份血缘与语义完整性整改）不重做 v2.4/v2.5 架构：
  14. 身份血缘（§二/§三/§十一）：同名只是候选信号，already_installed 必须有
      lineage evidence（上游仓库一致 / Source Map 记载 / 内容指纹 / lineage alias）；
      证明不了 → same_name_unverified / same_name_different_source（最高 watch，等人工确认），
      不建立 update/replacement 关联；更新项带 installed_canonical_id / installed_upstream /
      update_upstream / lineage_evidence 四件套。fm_description 截断放宽到 600。
  15. 产品 scope（§四/§十）：scope_type ∈ generic / platform_operation / product_internal
      + target_product；GCP 产品别名（cloud run / agent platform / model garden / vertex…）
      归入 gcp 域，Microsoft Store 发布归 microsoft-store 域；裸 Gemini 不算 GCP；
      未解除的 product_internal 最高 watch、不进 Top（可解除，非黑名单）。
  16. 语义收口（§五~§九）：跨 Skill 重定向小句（"For X, use other-skill"）不作本 Skill
      正向证据；mcp_dev 只认「开发动词管辖 MCP 工件」（using MCP tools = mcp_usage）；
      frontend_design 需明确设计语义（裸 frontend/ux/css/visual design 出局），
      静态视觉创作归 image_creative；deploy primary 改纯操作语义，裸名词 deployment
      只算 mention；testing_qa 名称词表删除裸 spec/specs（产品 specification ≠ test spec）。

v2.7（本轮，冻结前一致性与 Top 精度修复）不重做 v2.4–v2.6 架构：
  17. 确定性硬门（§二/§十一）：_ctx 保存 raw_name / normalized_name（有序）/ name_words_set，
      一切名称短语判定禁止 " ".join(set)（实测 PYTHONHASHSEED 会翻转 mcp_dev/mcp_usage）；
      测试套件内置 hashseed 矩阵（0/1/2/3/42/123 子进程），漂移即 FAIL。
  18. qa / deploy / secret（§三/§四/§八）：名称仅裸 `qa` 时需真实质保语义，
      Question Answering（wiki-qa）出局并记 question_answering；
      deploy 改「动词 + 通用对象**邻近**」（publishing games / deploy YARA rules 出局，
      deploy-to-vercel / python-appservice-deploy 保住）；
      secret-safety = 安全对象 AND 安全动作（"Measurement Protocol secrets" 出局）。
  19. 词面与技术遮蔽（§五/§六）：_AMBIGUOUS_DOMAIN_TERMS 单词（breakout/native/agent…）
      不得独立成 lexical 项目证据；TECH_MATCH ① 先遮蔽 React Native 跨度再判「原生」词
      （React Native app ≠ native macOS App）。
  20. 产品专项扩展（§七）：_PRODUCT_OPERATION_TERMS（google-analytics / google-secops /
      anthropic-brand / microsoft-store / SaaS 后台…）→ platform_operation + target_product；
      scope_unresolved() 统一解除判定，第五道门与推荐上限同时覆盖产品专项。

v2.8（本轮，冻结前产品范围与核心需求证据最终收口）不重做 v2.4–v2.7 架构：
  21. 核心需求证据四态扩展（§五~§八）：expo-rn / python-auto / llm-api / browser-qa /
      dashboard-viz 全部进 EVIDENCE_CLASSIFIERS —— 「SDK supports RN」「产品 CLI 带
      automation」「serving container + LLM 字眼」「提到 Playwright」「experiment
      dashboard」只能 supporting/mention；新增信息标签 ml_experiment_tracking /
      model_serving（不吃缺口分）。
  22. Top 核心证据门（§十四）：supporting-only 且无真 gap/update/replacement/matched_project
      → 不得进 Top（select_top require_core_evidence；审计行 top_candidates_supporting_only
      必须为 0）；shared_need 与「看板」定位证据同步只认 primary 级。
  23. 平台 scope 证据层（§三/§四/§十）：application-insights / m365-copilot /
      huggingface-spaces 补录 + AWS 服务别名（sagemaker/bedrock/s3/ecs/eks/fargate/
      cloudwatch/aws lambda → aws；裸 lambda 不收）；输出 platform_scope_evidence
      {scope_type/target_product/evidence[]/confidence}，来源=名称/描述/repo，禁止按 owner 一刀切；
      全部可解除（§十）。
  24. deploy host 名词修正（§九）：「SSH host, or local container」的 host 是名词；
      只有 host(s|ing) + app/site/service/model 严格式算托管动作。
"""
import collections
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_json, save_json, load_installed, canonical_key, fingerprint,
                    fetch_text, fetch_cached, load_config, RAW, CANDIDATES_PATH,
                    REGISTRY_PATH, SKILL_CONTEXT_PATH, TODAY, STATE,
                    load_project_needs, INSTALLED_CTX_PATH)
import match_rules as MR
import product_rules as PR
from match_rules import bag, hit_any, load_projects, match_projects
from security_gate import security_scan, deep_scan, deep_scan_summary, repo_tree
from data_gate import is_artifact_entry, is_valid_skill_name, has_min_fm

MAX_SECURITY_FETCH = 600  # PASS 1 静态审查 SKILL.md 的抓取上限（raw.githubusercontent，不计 API 配额）

# ==========================================================================
# 一、合法性 Gate（规则实现见 data_gate.py —— discover 与 analyze 共用同一套判断）
# ==========================================================================
_verify_cache = {}


def verify_bottom_up(owner, repo, branch="main"):
    """bottom-up 仓库硬门校验（§一.2）。

    返回 dict：
      ok=True  → 定位到真实 SKILL.md（含目录与文本）
      ok=False → 确认不是 Skill（无 SKILL.md），不得进正式候选池
      ok=None  → 无法校验（文件树/网络不可用），隔离处理
    """
    k = f"{owner}/{repo}"
    if k in _verify_cache:
        return _verify_cache[k]
    paths = repo_tree(owner, repo, branch)
    if paths is None and branch == "main":
        paths = repo_tree(owner, repo, "master")
        if paths is not None:
            branch = "master"
    if paths is None:
        res = {"ok": None, "reason": "file_tree_unavailable", "branch": branch}
        _verify_cache[k] = res
        return res
    skill_mds = [p for p in paths if p.endswith("SKILL.md")]
    if not skill_mds:
        res = {"ok": False, "reason": "no_skill_md", "branch": branch}
        _verify_cache[k] = res
        return res
    # 优先取根 SKILL.md，否则取路径最短的
    skill_mds.sort(key=lambda p: (p.count("/"), len(p)))
    p = skill_mds[0]
    txt = fetch_cached(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{p}", timeout=12)
    res = {"ok": True, "skill_md": p, "dir": os.path.dirname(p), "branch": branch,
           "fm_ok": has_min_fm(txt),
           "skill_name": os.path.basename(os.path.dirname(p)) or repo}
    _verify_cache[k] = res
    return res


# ---------- 安装关系 ----------
STRONG_TOKENS = {"claude", "skill", "agent"}


def _tokens(s):
    return {t for t in re.split(r"[\s_\-/]+", (s or "").lower())
            if len(t) > 2 and t not in STRONG_TOKENS}


# ---------- v2.6 §二/§三/§十一：身份血缘（同名 ≠ 同一来源） ----------
# 事故：`KKKKhazix/khazix-skills/aihot` 与本机已装 `aihot`（Virxact / AI HOT 发布）
# 只因同名被判 already_installed + update_available，更新源被绑到了错误仓库。
# 身份统一按「canonical identity + lineage evidence」判定；名称只作为候选信号，
# 其余一律走相似度（near_duplicate / overlap）。
_GH_UP_RE = re.compile(r"github\.com/([\w.\-]+)/([\w.\-]+)", re.I)

# §二 条件 5：显式 lineage alias（已装 canonical → owner/repo + Source Map 证据摘录）。
# 只收「Source Map evidence 明确记载内容同源」的条目，无证据不进表。
LINEAGE_ALIASES = {
    "leader": ("kkkkhazix/khazix-skills",
               "Source Map evidence：内容与 github.com/KKKKhazix/khazix-skills 同名 skill 逐字节一致（本地 018fe973901c == 上游实测）"),
    "neat-freak": ("kkkkhazix/khazix-skills",
                   "Source Map evidence：内容与 github.com/KKKKhazix/khazix-skills 同名 skill 逐字节一致（本地 c4dbe94169ed == 上游实测）"),
}


def _upstream_repo(entry):
    """从已装 Source Map 的 upstream 声明里解析 github 仓库（owner/repo，小写）；无则 None。"""
    m = _GH_UP_RE.search(entry.get("upstream") or "")
    return f"{m.group(1)}/{m.group(2)}".lower().rstrip("/") if m else None


def lineage_confirmed(cand, installed_name, entry):
    """§二 五条件：满足其一才允许认定「同一个 Skill」。返回证据列表（空 = 不能凭同名确认）。

    1/2. normalized upstream / external owner-repo 与已装 upstream 明确一致；
    3.   内容 fingerprint 相同（两侧都有记录时才可判）；
    4.   Installed Source Map 已把该 external repo 记为上游（同 1/2，走 upstream 字段）；
    5.   显式 lineage alias 表有证据映射（LINEAGE_ALIASES）。
    """
    repo = f"{cand.get('owner', '')}/{cand.get('repo', '')}".lower()
    ev = []
    ur = _upstream_repo(entry or {})
    if ur and ur == repo:
        ev.append(f"upstream_repo:{ur}")
    alias = LINEAGE_ALIASES.get(installed_name)
    if alias and alias[0] == repo:
        ev.append("lineage_alias：" + alias[1][:70])
    ch = (entry or {}).get("content_fingerprint") or (entry or {}).get("content_sha256") \
        or (entry or {}).get("content_sha1_12")
    if ch and cand.get("fingerprint") \
            and str(ch).lower()[-12:] == str(cand["fingerprint"]).lower()[-12:]:
        ev.append("content_fingerprint")
    return ev


SAME_NAME_UNVERIFIED = ("same_name_unverified", "same_name_different_source",
                        "possible_fork")


def installed_relationship(cand, installed):
    """v2.6 §二：返回 (relationship, match, jaccard, lineage_evidence)。

    同名只是**候选信号**：lineage_confirmed 成立才允许 already_installed；
    已装侧记录了别的上游 → same_name_different_source；上游 unknown → same_name_unverified。
    两者都不产生 already_installed / update_available / replacement 自动关联，
    最多等待人工确认（§二）。
    """
    cname = cand["skill_name"].lower().replace("-", " ")
    ctokens = _tokens(cand["skill_name"] + " " + cand.get("description", ""))
    best, best_j = None, 0.0
    for n, e in installed.items():
        nlow = n.lower().replace("-", " ")
        if cname == nlow:
            lin = lineage_confirmed(cand, n, e)
            if lin:
                return "already_installed", n, 1.0, lin
            up = (e.get("upstream") or "").strip()
            if up and up.lower() != "unknown":
                return "same_name_different_source", n, 1.0, []
            return "same_name_unverified", n, 1.0, []
        j = len(ctokens & _tokens(n + " " + (e.get("description") or "")))
        union = len(ctokens | _tokens(n + " " + (e.get("description") or ""))) or 1
        score = j / union
        if score > best_j:
            best, best_j = n, score
    if best_j >= 0.55:
        return "near_duplicate", best, best_j, []
    if best_j >= 0.30:
        return "overlap", best, best_j, []
    if best_j >= 0.15:
        return "complement", best, best_j, []
    return "new_capability", None, best_j, []


# ---------- 能力缺口匹配 ----------
def capability_tags(cand):
    """候选 → 已装侧能力命名空间（CAP_RULE，见 match_rules.py）。"""
    return MR.capability_tags(cand)


def domain_mismatch(cand):
    return MR.domain_mismatch(cand)


# v2.4 §九：平台错配的「解除」判定。
#   命中错配平台 且 没有任何 matched_project 明确使用该平台 → penalty（不得进安装候选、
#   不得进 Personalized Top、总分显著降权）。
#   一旦用户真实项目里出现该平台（或候选匹配到的项目就是该平台的项目）→ 自动解除。
#   不做永久 blacklist：只是「当前没有证据使用该技术栈 → 不该占个人 Top」。
DOMAIN_MISMATCH_PENALTY = 0.7    # 未解除错配时的总分成乘数（显著 penalty）


def unresolved_mismatch(gm):
    """取「未解除的平台错配」；老数据没有该字段时退回 domain_mismatch（向后兼容）。"""
    if gm is None:
        return []
    if "domain_mismatch_unresolved" in gm:
        return gm.get("domain_mismatch_unresolved") or []
    return gm.get("domain_mismatch") or []


_FULLTEXT_CACHE = {}
_FAMILY_MEMBERS_CACHE = {}


def _installed_skill_full_text(name, inst):
    """只读已装 Skill 的完整 SKILL.md（v2.11 §十三）。路径来自 Installed Source Map
    的 registry_central_path；读不到返回 None（调用方降为 summary_not_found）。
    **绝不写入 / 修改任何已装文件。**"""
    if name in _FULLTEXT_CACHE:
        return _FULLTEXT_CACHE[name]
    e = ((inst.get("all_known") or {}).get(name) or {})
    p = (((e.get("canonical") or {}).get("registry") or {})
         .get("registry_central_path") or "")
    out = None
    if p:
        md = os.path.join(os.path.expanduser(p), "SKILL.md")
        if os.path.isfile(md):
            try:
                with open(md, encoding="utf-8", errors="replace") as fh:
                    out = fh.read()
            except OSError:
                out = None
    _FULLTEXT_CACHE[name] = out
    return out


def _family_installed_members(family, inst):
    """该能力族在已装侧的成员 = §6 简表行里能力标签命中 family 的已装 Skill 名。"""
    key = (family, tuple(sorted((inst.get("installed_texts") or {}).keys())))
    if key in _FAMILY_MEMBERS_CACHE:
        return _FAMILY_MEMBERS_CACHE[key]
    members = []
    for name, txt in (inst.get("installed_texts") or {}).items():
        if family in MR.capability_tags({"skill_name": name, "description": txt or ""}):
            members.append(name)
    _FAMILY_MEMBERS_CACHE[key] = members
    return members


def _p_need_set(p):
    """项目自身的 NEED_RULE 命中集合（缓存进 p，供需求兼容性统计）。"""
    if "need_set" not in p:
        p["need_set"] = {need for need, _e in MR.rule_hits(
            {"skill_name": p["name"], "description": p["desc"]}, MR.NEED_RULE)}
    return p["need_set"]


def action_type_of(c, inst):
    """v2.11 §十二：恢复 / 修复 / 替代 / 新装 —— known_missing 不得伪装成「推荐新 Skill」。

    known_missing（来源档案在案但本机 canonical 缺失）+ 血缘确认 → restore_candidate；
    outdated + 血缘确认（update_available）→ update_candidate；
    真替代来源 → replacement_candidate；其余按 recommendation 映射 new_install / watch / reject。
    """
    rec = c.get("recommendation")
    if rec == "reject":
        return "reject"
    tgt = ((inst.get("all_known") or {}).get(c.get("overlap_with_installed") or "") or {})
    can = (tgt.get("canonical") or {})
    c["overlap_known_missing"] = bool(can) and not can.get("installed_canonical")
    upstream = (tgt.get("upstream") or "").lower()
    lineage = bool(c.get("lineage_evidence")) or bool(
        upstream and f"{c.get('owner', '')}/{c.get('repo', '')}".lower() in upstream)
    if can and not can.get("installed_canonical"):
        # known_missing：来源档案在案但本机 canonical 缺失——绝不允许伪装成「发现新 Skill」
        return "restore_candidate" if lineage else "watch"
    if c.get("update_available") and lineage:
        return "update_candidate"
    if c.get("installed_relationship") == "replacement_candidate":
        return "replacement_candidate"
    if rec == "install_candidate":
        return "new_install"
    return "watch"


def gap_match(cand, inst, config):
    """能力缺口 + 真实需求匹配（需求侧走 NEED_RULE）。"""
    tags = cand["capability_tags"]
    gaps = inst["suppression"]
    avail = inst["availability"]
    rank = {"none": 4, "weak": 3, "medium": 2, "strong": 1}
    best_eff, best_cap, best_r = None, None, 0
    for cap in tags:
        lv = gaps.get(cap)
        if lv is None:
            continue
        av = avail.get(cap, {}).get("availability", "ok")
        if lv == "strong" and av == "degraded":
            # coverage=strong 但 availability=degraded → 不按正常 strong 压制，按恢复需求计 medium
            eff, r = "medium", 2
        else:
            eff, r = lv, rank[lv]
        if r > best_r:
            best_r, best_eff, best_cap = r, eff, cap
    if best_cap is None:
        best_eff, best_cap = "strong", None   # 未命中任何已登记能力 → 无缺口证据
    # ---------- v2.9 §四/§五：capability_saturation（none/weak/medium/strong/strong_degraded） ----------
    # 饱和族 = 撑起本候选排名的能力族：matched_gap；matched_gap 为 None（只有信息标签）时
    # 顺 TAG_FAMILY 找信息标签实际所属的已登记族（§六：名字不同 ≠ new_capability）。
    sat_family = best_cap
    if sat_family is None:
        for cap in tags:
            fam = MR.TAG_FAMILY.get(cap)
            if fam and gaps.get(fam) in ("strong", "medium"):
                sat_family = fam
                break
    sat = gaps.get(sat_family) if sat_family else None
    if sat == "strong" and (avail.get(sat_family) or {}).get("availability") == "degraded":
        sat = "strong_degraded"          # §五：strong + availability degraded → 不硬压制
    sat = sat or "none"
    # v2.11 §十三：子能力增量证据分级 —— 只有实际读取该族全部已装成员 SKILL.md
    # （只读，不修改冻结底座）才允许 confirmed_absent；否则最多 summary_not_found。
    full_texts, members_checked = None, False
    if sat_family and (inst.get("installed_texts") or {}):
        members = _family_installed_members(sat_family, inst)
        if members:
            texts = {m: _installed_skill_full_text(m, inst) for m in members}
            members_checked = all(v is not None for v in texts.values())
            full_texts = texts if members_checked else None
    subcaps = MR.incremental_subcapability(
        cand, sat_family, inst.get("installed_texts") or {},
        full_texts=full_texts, members_checked=members_checked)
    sub_ids = [s for s, _lv in subcaps if _lv != "unknown"]
    matched = MR.matched_needs(cand, config.get("_project_needs", {}))
    return {"capability_tags": tags, "gap_level": best_eff, "matched_gap": best_cap,
            "capability_saturation": sat, "saturation_family": sat_family,
            "incremental_subcapability": sub_ids,
            "incremental_evidence_level": {s: lv for s, lv in subcaps},
            "matched_needs": matched,
            # v2.5 §九：统一「证据语境」四态字段（primary/supporting/mention/negated）
            "capability_evidence_context": MR.evidence_context(cand),
            "domain_mismatch": domain_mismatch(cand),
            "need_evidence": bool(matched)}


# ---------- 评分 ----------
SCORE_KEYS = ["PROJECT_MATCH", "CAPABILITY_GAP", "SOURCE_TRUST", "SECURITY",
              "MAINTENANCE", "ADOPTION_TREND", "DETOUR_REDUCTION", "NOVELTY_VS_INSTALLED"]


def score_candidate(c, W, tiers_trust):
    """Security Gate 优先于分数：block 级 → 0 分（后续 reject）。"""
    sec = c["security"]
    if sec.get("verdict") == "block" or sec.get("risk_level") == "high":
        c["gates_failed"] = True
        c["scores"] = {k.lower(): 0 for k in SCORE_KEYS}
        c["scores"]["total"] = 0
        return 0
    gm = c["capability_gap_match"]
    ne = gm.get("need_evidence", bool(gm.get("matched_needs")))
    pts = {}
    # PROJECT_MATCH 25：命中 SKILL_CONTEXT.md 的真实需求权重后归一化（wsum/2.6）。
    # 无需求证据 → 0 分（不给「有标签就送分」的噪音奖励）。
    # v2.5 §九：supporting 级证据只拿一半权重（如「可与 MCP 使用」≠ MCP 开发能力）。
    wsum = sum((n["weight"] or 0) * (0.5 if n.get("evidence_level") == "supporting" else 1)
               for n in gm["matched_needs"])
    pts["PROJECT_MATCH"] = min(W["PROJECT_MATCH"], round(wsum / 2.6, 1)) if wsum else 0
    # 项目级加成：命中具体项目（matched_projects）说明不是「能力像」而是「真用得上」
    mps = (c.get("project_match") or {}).get("matched_projects") or []
    if mps:
        pts["PROJECT_MATCH"] = min(W["PROJECT_MATCH"],
                                   pts["PROJECT_MATCH"] + min(3.0, len(mps) * 1.0))
    # 平台错配降权：用户技术栈里没有该平台，仍可能含通用方法，故只降权不否决
    if gm.get("domain_mismatch"):
        pts["PROJECT_MATCH"] = round(pts["PROJECT_MATCH"] * 0.35, 1)

    # CAPABILITY_GAP 20
    gl = gm["gap_level"]
    pts["CAPABILITY_GAP"] = {"none": 20, "weak": 15, "medium": 8, "strong": 2}.get(gl, 2)
    # v2.5 §九：只有证据语境为 primary 的能力才可拿满缺口分；
    # supporting 上限 8，mention/negated 上限 2（老数据无此字段时不受影响）
    ec = gm.get("capability_evidence_context") or {}
    ec_lvl = ec.get(gm.get("matched_gap"))
    if ec_lvl == "supporting":
        pts["CAPABILITY_GAP"] = min(pts["CAPABILITY_GAP"], 8)
    elif ec_lvl in ("mention", "negated"):
        pts["CAPABILITY_GAP"] = min(pts["CAPABILITY_GAP"], 2)
    if c["installed_relationship"] in ("overlap", "near_duplicate") \
            or c["installed_relationship"] in SAME_NAME_UNVERIFIED:
        # v2.6 §二：同名未确认血缘的候选按「近似重复」对待，缺口分封顶
        pts["CAPABILITY_GAP"] = min(pts["CAPABILITY_GAP"], 5)
    if not ne:
        pts["CAPABILITY_GAP"] = min(pts["CAPABILITY_GAP"], 5)
    # SOURCE_TRUST 15（tier 为 None=unverified 时取最低档）
    tier = c.get("source_tier")
    trust = {"official": 15, "vendor": 13, "community": 8, "unknown": 4}.get(c.get("origin_type"), 4)
    cap_by_tier = tiers_trust.get(str(tier), tiers_trust.get("unverified", 3))
    pts["SOURCE_TRUST"] = min(trust, cap_by_tier)
    # SECURITY 15：按 verdict（pass/review_required/block/unscanned）
    v = c["security"].get("verdict")
    pts["SECURITY"] = {"pass": 15, "review_required": 7, "block": 0,
                       "unscanned": 4}.get(v, 4)
    # MAINTENANCE 10
    lp = c.get("latest_commit", "")
    if lp:
        import datetime
        try:
            days = (datetime.date.today() - datetime.date.fromisoformat(lp[:10])).days
            pts["MAINTENANCE"] = 10 if days <= 30 else 7 if days <= 90 else 3 if days <= 365 else 1
        except Exception:
            pts["MAINTENANCE"] = 4
    else:
        pts["MAINTENANCE"] = 4
    # ADOPTION_TREND 5
    wi = (c.get("adoption_signal") or {}).get("install_count") or 0
    pts["ADOPTION_TREND"] = min(5, 5 * wi / 2000) if wi else (
        2 if (c.get("adoption_signal") or {}).get("stars") else 0)
    # DETOUR_REDUCTION 5
    detour_kws = ["qa", "test", "tests", "testing", "security", "deploy", "deployment",
                  "migration", "responsive", "transcript", "photo", "offline", "playwright"]
    w, t, n = bag(c.get("skill_name"), c.get("description"))
    pts["DETOUR_REDUCTION"] = 5 if hit_any(w, t, n, detour_kws) else 1
    # NOVELTY_VS_INSTALLED 5
    rel = c["installed_relationship"]
    pts["NOVELTY_VS_INSTALLED"] = {"new_capability": 5, "complement": 4,
                                   "replacement_candidate": 3, "overlap": 1,
                                   "near_duplicate": 0, "already_installed": 0,
                                   # v2.6 §二：同名但血缘未确认 → 不给新颖性奖励，等人工确认
                                   "same_name_unverified": 0,
                                   "same_name_different_source": 0,
                                   "possible_fork": 0}.get(rel, 2)
    capped = {k: round(min(pts[k], W[k]), 1) for k in SCORE_KEYS}
    total = round(sum(capped.values()), 1)
    # v2.4 §九：未解除的平台错配 → 总分再乘一次显著 penalty。
    # 说明：total 因此**不等于**各分项之和，这是刻意的（显式降权，可审计：
    # 系数记在 c["domain_mismatch_penalty"]）。域一旦被真实项目解除，惩罚自动消失。
    unres = unresolved_mismatch(gm)
    if unres:
        total = round(total * DOMAIN_MISMATCH_PENALTY, 1)
        c["domain_mismatch_penalty"] = DOMAIN_MISMATCH_PENALTY
    else:
        c["domain_mismatch_penalty"] = None
    c["scores"] = {k.lower(): v for k, v in capped.items()}
    c["scores"]["total"] = total
    return total


def recommend_of(c, cfg):
    """取值域：install_candidate / watch / ignore / reject（永不自动安装）。

    顺序原则：Security Gate 先于一切（含「已安装」判定）。
    v2.2：只有 block 级才 reject；review_required 不再等于 reject，
          但真在指令/可执行语境里的高敏感项会挡在安装候选之外。
    """
    sec = c["security"]
    # ① Security Gate 优先
    if sec.get("verdict") == "block" or sec.get("risk_level") == "high":
        blocks = sec.get("blocking_rules") or [f["rule"] for f in sec.get("findings", [])
                                               if f.get("level") == "block"]
        reason = "安全 Gate 阻断（block 级）：" + ", ".join(blocks or ["high risk"])
        if c["installed_relationship"] == "already_installed":
            reason += "；该 Skill 本机已安装（安装决策不适用），此条仅作安全提示"
        return "reject", reason
    if c.get("gates_failed"):
        return "reject", "硬门未过（来源/结构不可确认）"
    # ② 已安装
    if c["installed_relationship"] == "already_installed":
        return "ignore", ("已安装（canonical 在册 + 血缘确认），仅作版本更新观察，不再推荐"
                          + ("；另有版本更新可用（见 UPDATE_CANDIDATES）"
                             if c.get("update_available") else ""))
    # ②b v2.6 §二：与已装同名但血缘未确认 → 最高 watch，等人工确认；
    #     不标已安装、不建立 update/replacement 关联，也不当新能力重复推荐。
    if c["installed_relationship"] in SAME_NAME_UNVERIFIED:
        note = {"same_name_different_source": "已装侧 Source Map 记录的上游与本候选明确不同",
                "same_name_unverified": "已装侧上游记录为 unknown，血缘无法证明",
                "possible_fork": "疑似 fork"}.get(c["installed_relationship"], "")
        return "watch", (f"与已装 `{c.get('overlap_with_installed')}` 同名但血缘未确认"
                         f"（{note}）→ 最高 watch，等待人工确认（§二），"
                         f"不标已安装、不建立更新/替换关联")
    s = c["score"]
    gm = c["capability_gap_match"]
    th = cfg.get("thresholds", {"install_candidate": 62, "watch": 45})
    # ③ 平台错配（v2.4 §九 / v2.9 §三.3.3）：错配且项目档案既无证据、也未明确排除
    #    → 状态 insufficient_info，最高 watch，且不进深度审查队列（v2.9 §四.6）。
    #    且默认进 watchlist（不进 Personalized Top）。用户真实项目用了该平台时自动解除。
    unres = unresolved_mismatch(gm)
    if unres:
        # 保持「平台错配」这一措辞：既有测试与对照件都按这个口径解释
        why = f"平台错配：{'/'.join(unres)}（项目档案里没有任何项目使用该平台，penalty 未解除）"
        if s >= th.get("watch", 45):
            return "watch", (f"分数 {s} 但{why} → 相关性否决，不得进安装候选，"
                             f"也不进 Personalized Top（§九）")
        return "ignore", f"低分 {s} 且{why} → 与当前项目无相关性"
    # ③aa v2.9 §二.5 / §四.4 / §四.10：产品关系 Gate 优先于分数
    mstat = gm.get("match_status")
    if mstat == "competitor_mismatch":
        cf = gm.get("competitor_unresolved") or []
        pairs = "/".join(sorted({f"{x['candidate_product']}↔{x['installed_product']}"
                                 for x in cf[:3]}))
        return "ignore", (f"分数 {s}，但候选的产品关系与已装产品构成竞品（{pairs}）"
                          f"且项目档案无解除证据 → competitor_mismatch，不进推荐、"
                          f"不进 Top、不进深度审查队列（§二.5）。"
                          f"解除测试：{gm.get('gate_resolution_test') or '—'}")
    if mstat == "internal_only":
        return "ignore", (f"分数 {s}，但这是产品自身内部能力 / 内部管线"
                          f"（{gm.get('gate_reason') or ''}）→ internal_only，"
                          f"不是用户通用能力，不进深度审查队列（§四.4/§四.7）。"
                          f"解除测试：{gm.get('gate_resolution_test') or '—'}")
    if mstat == "not_applicable":
        if s >= th.get("watch", 45):
            return "watch", (f"分数 {s}，但候选领域 {gm.get('gate_reason')} → 状态 not_applicable"
                             f"（输入A 明确列为低优先级/排除项，不是「信息不足」）；"
                             f"解除测试：{gm.get('gate_resolution_test') or '—'}")
        return "ignore", f"低分 {s} 且候选领域被项目档案明确排除 → 与当前项目无相关性"
    # ③c v2.6 §十 / v2.7 §七：未解除的产品 scope → 最高 watch。
    #     product_internal（BrowserOS test-ui 事故）与产品专项 platform_operation
    #     （Google Analytics Admin / Google SecOps / Anthropic brand 事故）同一道门：
    #     「管理那个产品」≠「用户项目的通用能力」。不进安装候选、不进 Personalized Top；
    #     项目档案真的用上该产品即自动解除——**非黑名单**。
    if gm.get("product_internal_unresolved") or gm.get("scope_unresolved"):
        tname = gm.get("scope_unresolved_target") or gm.get("product_internal_unresolved")
        stype = gm.get("scope_type") or "product_internal"
        return "watch", (f"分数 {s}，但这是 `{tname}` 的产品专项 Skill（scope_type={stype}，"
                         f"项目档案无该产品）→ 不得作通用安装候选、"
                         f"不进 Personalized Top（§七/§十）；非黑名单，项目将来用上该产品即自动解除")
    # ③b 相关性否决
    if s >= th.get("install_candidate", 62) and not gm.get("need_evidence"):
        return "watch", (f"分数 {s} 但未命中任何项目需求（SKILL_CONTEXT.md needs）"
                         f" → 相关性否决，不得进安装候选")
    # ④ 未验证来源（bottom-up 直出的普通仓库）不得升级为安装候选
    if c.get("source_tier") is None or c.get("tier2_verified") is False:
        if s >= th.get("watch", 45):
            return "watch", (f"分数 {s}，但来源未经验证（source_tier=unverified，"
                             f"{c.get('unverified_reason') or 'bottom-up 搜索结果'}）"
                             f"→ 只能作观察，需人工确认是否为真实 Skill")
        return "ignore", f"低分 {s}：未验证来源且与当前需求关联弱"
    # ⑤ 深度审查硬门（§五）：有脚本却未完成 PASS 2 → 最高 watch
    ds = sec.get("deep_scan_status")
    if ds in ("pending", "failed"):
        return "watch", (f"分数 {s}，但深度静态审查未完成（deep_scan_status={ds}）"
                         f"→ 不得成为安装候选，需先完成脚本静态审查")
    # ⑥ 安全上被挡（高敏感项出现在指令/可执行语境）
    if sec.get("install_blocked"):
        items = "; ".join(f"{f['rule']}({f['behavior_context']})"
                          for f in sec.get("findings", [])
                          if f.get("severity") in ("high", "medium")
                          and f.get("behavior_context") != "mention")[:120]
        return "watch", (f"分数 {s}，但安全项需人工复核：{items}"
                         f"（静态审查判定为『真要求执行』而非『文档提及』）")
    # v2.11 §十三：strong 饱和候选若只凭「底座摘要未发现该子能力」（summary_not_found，
    # 未读全文 SKILL.md）宣称增量——允许 watch，**不得仅此成为安装候选**。
    if (gm.get("capability_saturation", "").startswith("strong")
            and gm.get("capability_saturation") != "strong_degraded"
            and not c.get("update_available")
            and c.get("installed_relationship") != "replacement_candidate"
            and gm.get("incremental_subcapability")
            and all((gm.get("incremental_evidence_level") or {}).get(s) == "summary_not_found"
                    for s in gm["incremental_subcapability"])):
        return "watch", (f"分数 {s}：声称的增量子能力仅达到 `summary_not_found` 证据级"
                         f"（底座摘要未发现，未读取全部已装成员 SKILL.md 全文）→"
                         f"可观察，但不得仅此升为安装候选（§十三）")
    if s >= th.get("install_candidate", 62) and gm["gap_level"] in ("none", "weak") \
            and sec.get("verdict") in ("pass", "review_required") and sec.get("status") == "scanned":
        review_note = ""
        mentions = [f["rule"] for f in sec.get("findings", [])
                    if f.get("behavior_context") == "mention" and f.get("level") == "review"]
        if mentions:
            review_note = f"，另有人工复核项（语境性提及）：{', '.join(mentions[:3])}"
        return "install_candidate", (
            f"高分 {s}：命中需求 {', '.join(n['need'] for n in gm['matched_needs'][:3]) or '—'}"
            f"（能力缺口 {gm.get('matched_gap') or '—'}）"
            f"，安全 verdict={sec.get('verdict')}"
            f"，深度审查 {deep_scan_summary(sec)}{review_note}")
    if s >= th.get("watch", 45):
        extra = ""
        if not gm.get("need_evidence"):
            extra = "（未命中项目需求；仅作观察）"
        if gm.get("domain_mismatch") and not unres:
            # 错配已被真实项目解除：记一下，便于审查者核对「解除」确实发生
            extra += f"（平台错配 {('/'.join(gm['domain_mismatch']))} 已由项目 {gm.get('domain_mismatch_resolved_by') or '档案'} 解除）"
        return "watch", f"中分 {s}：值得关注，需人工判断" + extra + (
            "（安全 review_required，人工复核）" if sec.get("verdict") == "review_required" else
            "（安全未扫描，不得升级为安装候选）" if sec.get("status") != "scanned" else "")
    return "ignore", f"低分 {s}：与当前需求关联弱或与既有能力重复"


# ==========================================================================
# 主流程
# ==========================================================================
def evaluate(cands, inst, cfg, W, tiers_trust, projects, ctx_text=None,
             agent_slugs=(), state=None):
    """匹配 + 评分 + 推荐（PASS 1 与 PASS 2 之后各跑一次）。

    v2.9 §二/§三/§四：多出来的三个入参用于「产品关系 + 项目六节能力清单」，
    不传则退化成 v2.8 行为（老 63 项测试继续可跑，§三.9 兼容）。
    """
    v29 = None
    if ctx_text is not None or projects:
        sections = PR.project_sections(ctx_text or "", projects, state or {})
        installed_products = PR.installed_products(
            list((inst or {}).get("installed") or {}), agent_slugs=agent_slugs)
        v29 = (sections, installed_products)
    for c in cands:
        c["capability_tags"] = capability_tags(c)
        # v2.10 §八/§九：required_tech（hard requirement）与 compatible_tech（通用 Web 标准）
        c["required_tech"], c["compatible_tech"] = MR.tech_requirements(c)
        rel, match, j, lin = installed_relationship(c, inst["installed"])
        c["installed_relationship"] = rel
        c["overlap_with_installed"] = match
        c["token_jaccard"] = round(j, 2)
        # v2.6 §二：血缘证据显式落档（already_installed 必须拿得出一条，否则不成立）
        c["lineage_evidence"] = lin or None
        c["capability_gap_match"] = gap_match(c, inst, cfg)
        gm = c["capability_gap_match"]
        mps = match_projects(c, projects) if projects else []
        # ---- v2.11 §六：NEED_PROJECT_COMPATIBILITY ----
        # 逐 primary 需求记录「承载该需求的项目里，哪些与候选 required_tech 兼容」。
        # 全部不兼容 → need_project_compatibility=none：该 need 不能独自撑起 Personalized Top
        # （「需求名匹配」不得脱离「需求对应项目是否能用」），但仍可 general_interest / watch。
        _npc = {}
        _req = c.get("required_tech") or []
        if projects:
            for _n in gm["matched_needs"]:
                _carriers = [p for p in projects if _p_need_set(p) and _n["need"] in _p_need_set(p)]
                if not _carriers:
                    continue
                _comp = [p["name"] for p in _carriers
                         if not MR.tech_project_conflicts(_req, p)]
                _inc = [p["name"] for p in _carriers if p["name"] not in _comp]
                _lvl = "all" if not _inc else ("partial" if _comp else "none")
                _npc[_n["need"]] = {
                    "evidence_level": _n.get("evidence_level", "primary"),
                    "compatible_projects": _comp,
                    "incompatible_projects": _inc,
                    "need_project_compatibility": _lvl}
        # ---- v2.4 §九：平台错配的解除判定 ----
        # 解除条件（§九 / §十一.18）：「用户真实项目明确使用 Azure / AWS / .NET / 对应平台」。
        # 因此看的是**整个项目档案**的技术面，不是「该候选恰好匹配到的项目」——
        # 否则一个 Azure 候选只要没别的直接证据匹配不上项目，就永远无法解除，
        # 变成事实上的永久 blacklist，而 §九 明确要求「不要永久 blacklist」。
        # 没有该平台的任何证据 → 记为 unresolved：不得 install_candidate、
        # 不得进 Personalized Top、总分乘 DOMAIN_MISMATCH_PENALTY。
        mism_doms = sorted({MR.MISMATCH_DOMAIN.get(t, t)
                            for t in (gm.get("domain_mismatch") or [])})
        proj_doms, resolvers = set(), []
        for _p in (projects or []):
            _d = MR.project_domains(_p)
            if _d:
                proj_doms |= _d
                if _d & set(mism_doms):
                    resolvers.append(_p["name"])
        gm["domain_mismatch_domains"] = mism_doms
        gm["domain_mismatch_resolved"] = sorted(set(mism_doms) & proj_doms)
        gm["domain_mismatch_unresolved"] = sorted(set(mism_doms) - proj_doms)
        gm["domain_mismatch_resolved_by"] = sorted(set(resolvers))
        # ---- v2.6 §四/§十：产品 scope（generic / platform_operation / product_internal） ----
        sc_type, sc_target, sc_ev = MR.product_scope(c)
        pi_unres, pi_res = MR.product_internal_unresolved((sc_type, sc_target, sc_ev), projects)
        # v2.7 §七：统一解除判定（product_internal + 产品专项 platform_operation）
        sc_unres, sc_unres_target, sc_res_by = MR.scope_unresolved(
            (sc_type, sc_target, sc_ev), projects)
        gm["scope_type"] = sc_type
        gm["target_product"] = sc_target
        gm["scope_evidence"] = sc_ev
        gm["product_internal_unresolved"] = pi_unres
        gm["product_internal_resolved_by"] = pi_res
        gm["scope_unresolved"] = sc_unres
        gm["scope_unresolved_target"] = sc_unres_target
        gm["scope_resolved_by"] = sc_res_by
        # v2.8 §四：统一「平台 scope 证据层」——证据来源逐条可查（name/description/repo），
        # 不靠 owner 一刀切；confidence 由证据形态给出。
        _ev_raw = sc_ev or ""
        _conf = "n/a"
        if "conf=" in _ev_raw:
            _ev_raw, _conf = _ev_raw.rsplit("conf=", 1)
        _src = _ev_raw.split(":", 1)[1] if ":" in _ev_raw else _ev_raw
        c["platform_scope_evidence"] = {
            "scope_type": sc_type,
            "target_product": sc_target,
            "evidence": [x for x in _src.split(",") if x][:5],
            "confidence": _conf,
        }
        # ---- v2.9 §二/§三/§四：产品关系、能力领域、Gate 与解除证据 ----
        if v29:
            sections, installed_products = v29
            gate = PR.gate_assessment(c, sections, installed_products)
            c["candidate_product_refs"] = gate["product_refs"]
            c["capability_domains"] = {
                "domains": gate["domain_state"]["candidate_domains"],
                "applicable_evidence": gate["domain_state"]["applicable_evidence"],
                "exclusion_evidence": gate["domain_state"]["exclusion_evidence"],
                "unresolved": gate["domain_state"]["unresolved"],
                "secondary_stack_domains": gate["domain_state"]["secondary_stack_domains"],
                "state": gate["domain_state"]["state"],
            }
            c["internal_capability"] = gate["internal_capability"]
            c["internal_pipeline"] = gate["internal_pipeline"]
            c["project_scope_section"] = (gate["scope_sections"][0]["project_scope_section"]
                                           if gate["scope_sections"] else None)
            c["project_scope_section_confidence"] = (
                gate["scope_sections"][0]["confidence"] if gate["scope_sections"] else None)
            c["competitor_evidence"] = gate["competitor_conflicts"]
            gm["product_refs"] = gate["product_refs"]
            # §二.10 / §四.11：新字段名（旧名 product_internal_unresolved 保留为兼容镜像）
            gm["candidate_product_internal_unresolved"] = (
                gate["internal_capability"].get("product")
                if gate["status"] == "internal_only"
                else (pi_unres or None))   # v2.6 旧字段的镜像也要有新字段可对账
            gm["developer_tool_gate_unresolved"] = bool(
                gate["domain_state"]["unresolved"]
                and any(r["ref_type"] in ("developer_tool", "official_extension")
                        for r in gate["product_refs"]))
            c["product_scope_sections"] = gate["scope_sections"]
            gm["match_status"] = gate["status"]
            gm["gate_priority"] = gate["priority"]
            gm["gate_reason"] = gate["reason"]
            gm["gate_resolution_test"] = gate["resolution_test"]
            gm["product_relation_only_from_name"] = gate["product_relation_only_from_name"]
            # §三.5：domain_mismatch_unresolved 只允许**产品/平台领域**占用；
            # §三.9：字段值沿用 v2.4 旧域名（azure/gcp/aws…），v2.9 新语义写在 *_v29。
            _prim_legacy = {PR.legacy_domain(x)
                            for x in PR.project_primary_domains(sections)}
            _excl_legacy = {PR.legacy_domain(x)
                            for x in PR.project_excluded_domains(sections)}
            gm["domain_mismatch_unresolved"] = sorted(
                ({PR.legacy_domain(u["domain"])
                  for u in gate["domain_state"]["unresolved"]}
                 | set(mism_doms)) - _prim_legacy)
            gm["domain_mismatch_not_applicable"] = sorted(
                set(mism_doms) & _excl_legacy)
            gm["domain_mismatch_state"] = gate["domain_state"]["state"]
            gm["secondary_stack_domains"] = gate["domain_state"]["secondary_stack_domains"]
            # §二.5/§二.7：竞品字段（competitor_block 为 legacy 兼容镜像）
            gm["competitor_conflicts"] = gate["competitor_conflicts"]
            gm["competitor_resolved"] = gate["competitor_resolved"]
            gm["competitor_unresolved"] = gate["competitor_unresolved"]
            gm["competitor_block"] = gate["competitor_unresolved"]
            gm["internal_only"] = gate["status"] == "internal_only"
            # 兼容旧字段名（v2.4–v2.8 的第五道门读 scope_unresolved）
            if gate["status"] in ("internal_only", "competitor_mismatch"):
                gm["scope_unresolved"] = True
                gm["scope_unresolved_target"] = (
                    (gate["internal_capability"].get("product")
                     or (gate["competitor_unresolved"][0]["candidate_product"]
                         if gate["competitor_unresolved"] else None)))
            # Gate 命中要随最终一轮评估一起落盘（evaluate 会重建 gm，不能只在队列阶段记）
            gm["gate_hit"] = PR.gate_label(gate)
        c["project_match"] = {
            "matched_needs": [n["need"] for n in gm["matched_needs"]],
            "matched_need_weights": {n["need"]: n["weight"] for n in gm["matched_needs"]},
            "matched_need_evidence": {n["need"]: n.get("evidence", []) for n in gm["matched_needs"]},
            # v2.5 §九：需求侧证据语境四态（primary/supporting…），供审查者核对降权
            "matched_need_evidence_levels": {n["need"]: n.get("evidence_level", "primary")
                                             for n in gm["matched_needs"]},
            # v2.11 §六：需求 ↔ 项目兼容性（none = 承载该需求的项目全部与 required_tech 不兼容）
            "need_project_compatibility": _npc,
            "need_evidence": gm.get("need_evidence", False),
            "domain_mismatch": gm.get("domain_mismatch", []),
            "domain_mismatch_domains": mism_doms,
            "domain_mismatch_unresolved": gm["domain_mismatch_unresolved"],
            # v2.6 §四/§十：产品 scope 三态（unresolved 的 product_internal 不进 Top）
            "scope_type": sc_type,
            "target_product": sc_target,
            "product_internal_unresolved": pi_unres,
            # v2.7 §七：产品专项 platform_operation 的未解除标记（同走 Top 门）
            "scope_unresolved": sc_unres,
            # v2.9 §二/§三：产品关系与领域三态（新口径，供日报与审计消费）
            "match_status": (gm.get("match_status")),
            "product_refs": gm.get("product_refs", []),
            "competitor_unresolved": gm.get("competitor_unresolved", []),
            "competitor_block": gm.get("competitor_block", []),
            "domain_mismatch_state": gm.get("domain_mismatch_state"),
            "secondary_stack_domains": gm.get("secondary_stack_domains", []),
            "product_relation_only_from_name": gm.get("product_relation_only_from_name"),
            "matched_projects": mps,
            "priority": (mps[0]["match_score"] if mps else None),
        }
        meta = meta_by_repo.get(f"{c['owner']}/{c['repo']}".lower(), {})
        lp = meta.get("pushed_at")
        c["latest_commit"] = lp
        c["latest_commit_source"] = "repo_pushed_at" if lp else None
        if c.get("latest_version") is None:
            c["latest_version"] = None
        c["adoption_signal"] = {
            "install_count": c.get("install_count"),
            "weekly_installs": c.get("install_count"),
            "stars": c.get("stars"),
            "signal_source": ("aggregator_install_telemetry"
                              if c.get("source_tier") == 3 and c.get("install_count")
                              else "repo_stars" if c.get("stars") else "none"),
            "note": "仅作 adoption signal；安装量/star 绝不等于质量或推荐依据",
        }
        if lp:
            import datetime as _dt
            try:
                days = (_dt.date.today() - _dt.date.fromisoformat(lp[:10])).days
                c["upstream_activity"] = "active" if days <= 90 else (
                    "stale" if days <= 365 else "deprecated")
            except Exception:
                c["upstream_activity"] = "unknown"
        else:
            c["upstream_activity"] = "unknown"
        # ---- replacement_candidate（v2.6 §二/§三/§十一：名称匹配只是线索，必须过血缘门） ----
        known_by_norm = {k.lower().replace("-", " "): k for k in inst["all_known"]}
        kn = known_by_norm.get(c["skill_name"].lower().replace("-", " "))
        c["update_available"] = False
        c["update_note"] = None
        c["update_lineage"] = None
        if kn and c["installed_relationship"] not in ("already_installed",) + SAME_NAME_UNVERIFIED:
            ke = inst["all_known"][kn]
            ke_lin = lineage_confirmed(c, kn, ke)
            if (not ke.get("canonical", {}).get("installed_canonical")) and ke_lin:
                c["installed_relationship"] = "replacement_candidate"
                c["overlap_with_installed"] = kn
                c["replacement_candidate_reason"] = (
                    f"对应 canonical `{kn}` 当前不在本机安装集（known_missing）"
                    f"且血缘确认（{'；'.join(ke_lin)}，来源档案在案：{ke.get('upstream')}）→ 该候选可用于恢复")
            elif not ke.get("canonical", {}).get("installed_canonical"):
                # §三：不得为了找「候选对象」而绑错 repo —— 同名但血缘不成立 → 不建立恢复关联
                c["same_name_lineage_rejected"] = f"known_missing `{kn}` 血缘未确认，不建立 replacement 关联"
        elif c["installed_relationship"] in ("overlap", "near_duplicate") \
                and c["upstream_activity"] == "active" and match:
            ie = inst["installed"].get(match) or inst["all_known"].get(match) or {}
            vs, ia = ie.get("version_status"), ie.get("upstream_activity")
            if (vs in ("outdated_version", "historical_official_version") or (ia and ia != "active")) \
                    and lineage_confirmed(c, match, ie):
                c["installed_relationship"] = "replacement_candidate"
                c["replacement_candidate_reason"] = (
                    f"与已装 {match} 重叠（jaccard={round(j,2)}）且血缘确认，"
                    f"已装侧 version_status={vs or '未比对'} / upstream_activity={ia or 'unknown'}，"
                    f"候选上游 active → 具备替换/升级价值（仍需人工确认）")
        # ---- update_available：只对 lineage 确认的 already_installed 生效（§二/§三） ----
        if c["installed_relationship"] == "already_installed":
            iname = match or kn
            ie = inst["all_known"].get(iname) or {}
            vs, ia = ie.get("version_status"), ie.get("upstream_activity")
            if vs in ("outdated_version", "historical_official_version") and ia == "active":
                c["update_available"] = True
                c["update_note"] = (f"已装但 version_status={vs}（上游 active）→ 属更新候选，"
                                    f"不重复推荐安装，仅在 UPDATE_CANDIDATES 提示")
                # §三/§二.6：更新项必须带完整血缘四件套，update_upstream 只绑同一血缘
                c["update_lineage"] = {
                    "installed_canonical_id": iname,
                    "installed_upstream": ie.get("upstream") or "unknown",
                    "update_upstream": f"{c['owner']}/{c['repo']}",
                    "lineage_evidence": "；".join(lin) or "见 Source Map",
                    "lineage_verified": bool(lin),
                }
        c["trend_signal"] = ("high_installs" if (c.get("install_count") or 0) >= 1000
                             else "rising" if (c.get("install_count") or 0) >= 100
                             else "active_repo" if c["upstream_activity"] == "active" else "unknown")
        c["score"] = score_candidate(c, W, tiers_trust)
        c["scores"]["total"] = c["score"]
        rec, reason = recommend_of(c, cfg)
        c["recommendation"] = rec
        c["recommendation_reason"] = reason
        c["action_type"] = action_type_of(c, inst)      # v2.11 §十二
        c["latest_release"] = None


def main():
    raw = load_json(os.path.join(RAW, "discovery_latest.json"))
    if not raw:
        print("no discovery data — run discover.py")
        return 1
    inst = load_installed()
    cfg = load_config()
    needs_meta = raw.get("project_needs", {})
    cfg["_project_needs"] = needs_meta
    W = cfg.get("weights", {"PROJECT_MATCH": 25, "CAPABILITY_GAP": 20, "SOURCE_TRUST": 15,
                            "SECURITY": 15, "MAINTENANCE": 10, "ADOPTION_TREND": 5,
                            "DETOUR_REDUCTION": 5, "NOVELTY_VS_INSTALLED": 5})
    tiers_trust = cfg.get("tier_trust_ceiling", {"0": 0, "1": 15, "2": 10, "3": 9})
    tiers_trust.setdefault("unverified", 3)

    # ---- 本地项目档案（matched_projects 数据源；仅本地使用，不外传） ----
    projects = []
    if os.path.exists(SKILL_CONTEXT_PATH):
        try:
            projects = load_projects(open(SKILL_CONTEXT_PATH, encoding="utf-8").read())
        except Exception:
            projects = []

    global meta_by_repo
    reg_all = load_json(REGISTRY_PATH, {"tiers": {}})
    meta_by_repo = {}
    for t in ("0", "1", "2", "3"):
        for e in reg_all.get("tiers", {}).get(t, []):
            if e.get("owner") and e.get("repo"):
                meta_by_repo[f"{e['owner']}/{e['repo']}".lower()] = e

    pool = {}
    quarantine = {"invalid_artifacts": [], "unverified_bottom_up": [],
                  "invalid_bottom_up": [], "invalid_names": []}
    stats = {"raw": 0, "artifact_filtered": 0, "invalid_name_filtered": 0,
             "bottom_up_total": 0, "bottom_up_verified": 0, "bottom_up_quarantined": 0}

    def add(owner, repo, skill_name, tier, source_url, origin_type, description="",
            install_count=None, stars=None, path=None, source_id=None,
            tier2_verified=None, unverified_reason=None, scripts=None):
        ck = canonical_key(owner, repo, skill_name)
        e = pool.get(ck)
        if not e:
            e = {"canonical_key": ck, "skill_name": skill_name, "owner": owner, "repo": repo,
                 "source": source_id or f"tier{tier}:{owner}/{repo}",
                 "source_url": source_url, "sources": [], "source_tier": tier,
                 "origin_type": origin_type, "description": description,
                 "install_count": install_count, "stars": stars, "path": path,
                 "scripts": list(scripts) if scripts else [],
                 "tier2_verified": tier2_verified, "unverified_reason": unverified_reason,
                 "discovered_at": TODAY, "last_seen_at": TODAY}
            pool[ck] = e
        src = f"tier{tier}:" + (source_url or f"{owner}/{repo}")
        if src not in e["sources"]:
            e["sources"].append(src)
        if tier is not None and (e["source_tier"] is None or tier < e["source_tier"]):
            e["source_tier"] = tier
            if tier2_verified:
                e["tier2_verified"] = True
                e["unverified_reason"] = None
        if description and not e["description"]:
            e["description"] = description
        if install_count and (e["install_count"] or 0) < install_count:
            e["install_count"] = install_count
        if stars and (e["stars"] or 0) < stars:
            e["stars"] = stars
        if path and not e.get("path"):
            e["path"] = path
        if scripts and not e.get("scripts"):
            e["scripts"] = list(scripts)
        e["last_seen_at"] = TODAY
        return e

    # ---- 合法性 Gate：名称必须像 Skill（§一.1） ----
    def accept_name(owner, repo, name, origin_label):
        stats["raw"] += 1
        if is_artifact_entry(name):
            stats["artifact_filtered"] += 1
            quarantine["invalid_artifacts"].append(
                {"name": name, "owner": owner, "repo": repo, "reason": "构建产物/静态资源",
                 "source": origin_label})
            return False
        if not is_valid_skill_name(name):
            stats["invalid_name_filtered"] += 1
            quarantine["invalid_names"].append(
                {"name": name, "owner": owner, "repo": repo, "reason": "不是合法 skill slug",
                 "source": origin_label})
            return False
        return True

    # ---- TIER 1（官方）+ TIER 2（已验证社区） ----
    for tier in (1, 2):
        for blk in raw.get(f"tier{tier}", []):
            owner, repo = blk.get("owner"), blk.get("repo")
            if not owner:
                continue
            meta = meta_by_repo.get(f"{owner}/{repo}".lower(), {})
            origin = blk.get("origin_type") or ("official" if tier == 1 else "community")
            for sk in blk.get("skills", []):
                if not accept_name(owner, repo, sk["skill_name"], f"tier{tier}:{owner}/{repo}"):
                    continue
                add(owner, repo, sk["skill_name"], tier, sk["html_url"], origin,
                    path=sk.get("path"), stars=meta.get("stars"),
                    source_id=f"{owner}/{repo}",
                    tier2_verified=(tier == 2) or None,
                    scripts=sk.get("scripts"))
    # ---- TIER 3 聚合榜（只作发现） ----
    for src_key in ("skills_sh", "clawhub", "skillsmp"):
        blk = raw.get("tier3", {}).get(src_key, {})
        for e in blk.get("entries", []):
            name = e.get("skill_name") or e.get("repo")
            if not accept_name(e.get("owner"), e.get("repo"), name, blk.get("source", src_key)):
                continue
            add(e.get("owner"), e.get("repo"), name, 3, e.get("source_url"), "unknown",
                install_count=e.get("weekly_installs"), source_id=blk.get("source", src_key))
    # ---- Bottom-up 搜索结果（§一.2：只是 discovery_channel，不等于 TIER 2） ----
    bu_budget = cfg.get("bottom_up_verify_budget", 40)
    bu_seen = []
    for q in raw.get("bottom_up", []):
        for r in q.get("results", []):
            bu_seen.append((q.get("capability_gap"), r))
    # 按 stars 降序取前 N 个做硬门校验，控制 GitHub API 用量
    bu_seen.sort(key=lambda x: -(x[1].get("stars") or 0))
    for cap, r in bu_seen:
        stats["bottom_up_total"] += 1
        stats["raw"] += 1
        if not is_valid_skill_name(r["repo"]):
            stats["invalid_name_filtered"] += 1
            quarantine["invalid_names"].append(
                {"name": r["repo"], "owner": r["owner"], "repo": r["repo"],
                 "reason": "不是合法 skill slug", "source": "bottom_up_search"})
            continue
        if bu_budget <= 0:
            break
        bu_budget -= 1
        v = verify_bottom_up(r["owner"], r["repo"])
        if v.get("ok") is False:
            stats["bottom_up_quarantined"] += 1
            quarantine["invalid_bottom_up"].append(
                {"owner": r["owner"], "repo": r["repo"], "reason": v.get("reason"),
                 "capability_gap": cap, "url": r.get("url")})
            continue
        if v.get("ok") is None:
            stats["bottom_up_quarantined"] += 1
            quarantine["unverified_bottom_up"].append(
                {"owner": r["owner"], "repo": r["repo"], "reason": v.get("reason"),
                 "capability_gap": cap, "url": r.get("url")})
            continue
        stats["bottom_up_verified"] += 1
        # 验证通过：定位到真实 SKILL.md → 进池，但**仍是 unverified 来源**（绝不自动升 T2）
        add(r["owner"], r["repo"], v.get("skill_name") or r["repo"], None, r.get("url"),
            "community", description=r.get("description", ""), stars=r.get("stars"),
            path=v.get("dir"), source_id="bottom_up_search",
            tier2_verified=False,
            unverified_reason="bottom-up 搜索结果，非注册表已验证 T2")

    updates = raw.get("tier1_updates", [])
    cands = list(pool.values())

    # ---- PASS 1：预排序 + 并发抓取 SKILL.md ----
    focus_caps = {f["capability"] for f in
                  load_json(os.path.join(RAW, "gap_focus.json"), {}).get("focus_capabilities", [])}
    for c in cands:
        c["capability_tags"] = capability_tags(c)

    def prelim(c):
        tags = set(c["capability_tags"])
        need_hit = 1 if MR.matched_needs(c, needs_meta) else 0
        hit = 0 if ((tags & focus_caps) or need_hit) else 1
        return (hit, c["source_tier"] if c["source_tier"] is not None else 9,
                -(c.get("install_count") or 0), -(c.get("stars") or 0))

    cands.sort(key=prelim)
    branch_of = {}
    for tier in (1, 2):
        for blk in raw.get(f"tier{tier}", []):
            if blk.get("owner"):
                branch_of[f"{blk['owner']}/{blk['repo']}"] = blk.get("branch", "main")
    tasks, fetched = [], 0
    budget = cfg.get("scan_budget", MAX_SECURITY_FETCH)
    for c in cands:
        if len(tasks) >= budget:
            break
        if c["owner"] and c["repo"] and c.get("path"):
            branch = branch_of.get(f"{c['owner']}/{c['repo']}", c.get("branch") or "main")
            tasks.append((c, f"https://raw.githubusercontent.com/{c['owner']}/{c['repo']}"
                             f"/{branch}/{c['path']}/SKILL.md"))
    if tasks:
        from concurrent.futures import ThreadPoolExecutor
        workers = cfg.get("scan_workers", 10)

        def _probe(job):
            c, url = job
            return c, url, fetch_cached(url, timeout=10)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for c, url, txt in ex.map(_probe, tasks):
                fetched += 1
                if txt:
                    if not c["description"]:
                        d = fm_description(txt)
                        if d:
                            c["description"] = d
                    mv = re.search(r"^\s*version\s*:\s*['\"]?([0-9][\w.\-]*)", txt, re.M)
                    if mv:
                        c["latest_version"] = mv.group(1)
                    c["security"] = security_scan(txt, has_scripts="scripts/" in txt)
                    c["content_fingerprint"] = fingerprint(txt)
                    c["skillmd_url"] = url
                else:
                    c["security"] = security_scan(None, has_scripts=False)
    for c in cands:
        if "security" not in c:
            c["security"] = security_scan(None, has_scripts=False)
        c["security"]["deep_scan_status"] = None

    # ---- v2.9 §三.2：项目六节能力清单 + 已装智能体（供产品关系层用） ----
    try:
        CTX_TEXT = open(SKILL_CONTEXT_PATH, encoding="utf-8").read()
    except OSError:
        CTX_TEXT = ""
    STATE_A = load_project_needs()
    try:
        INST_TEXT = open(INSTALLED_CTX_PATH, encoding="utf-8").read()
    except OSError:
        INST_TEXT = ""
    AGENT_SLUGS, AGENT_SLUG_EVIDENCE = PR.agent_slugs_from_installed_context(INST_TEXT)

    # ---- 阶段 B：首次评估（决定谁有资格进 install 候选） ----
    evaluate(cands, inst, cfg, W, tiers_trust, projects,
             ctx_text=CTX_TEXT, agent_slugs=AGENT_SLUGS, state=STATE_A)

    # ---- v2.9 §四.6/§四.7：全池安全完整审查队列（硬 Gate 优先于排队分数） ----
    # Gate 命中者不得因分数高重新进入队列；**仅名称含品牌词不算 Gate**（§四.12）。
    ds_budget = cfg.get("deep_scan_budget", 80)
    gated_pairs, queue, unscannable = [], [], []
    for c in cands:
        hit = PR.gate_hit(c)
        if hit:
            c["capability_gap_match"]["gate_hit"] = hit
            gated_pairs.append(hit)
            c["deep_scan"] = PR.blank_deep_scan(f"硬 Gate={hit} → 不进深度审查队列")
            c["security"]["deep_scan_status"] = "not_required"
            continue
        if not (c.get("path") and (c.get("security") or {}).get("status") == "scanned"):
            unscannable.append(c)
            c["deep_scan"] = PR.blank_deep_scan("无 SKILL.md 目录或未过 PASS 1，无可执行文件可查")
            c["security"]["deep_scan_status"] = "skipped"
            continue
        # v2.11 §八：未解除的 product_internal 是硬 Gate 级别——不入深度审查队列
        # （与 v2.9 §四.6「硬 Gate 命中者不入队」同一原则；项目档案用上该产品即自动解除）。
        gm0 = c.get("capability_gap_match") or {}
        if (gm0.get("scope_type") == "product_internal"
                and gm0.get("product_internal_unresolved")):
            gated_pairs.append("product_internal")
            c["deep_scan"] = PR.blank_deep_scan(
                f"product_internal 未解除（{gm0.get('product_internal_unresolved')}）"
                "→ 不进深度审查队列（v2.11 §八）")
            c["security"]["deep_scan_status"] = "not_required"
            continue
        queue.append(c)
    queue.sort(key=lambda c: (-float(c.get("score") or 0), c["canonical_key"]))
    queue_full = list(queue)
    queue = queue[:ds_budget]
    fs_done = fs_failed = 0
    for qi, c in enumerate(queue, 1):
        c["full_scan_queue_index"] = qi
        branch = branch_of.get(f"{c['owner']}/{c['repo']}", "main")
        ds = deep_scan(c["owner"], c["repo"], c.get("path"), branch,
                       max_files=cfg.get("deep_scan_max_files", 8),
                       known_scripts=c.get("scripts"))
        c["deep_scan"] = ds
        c["security"]["deep_scan_status"] = ds["deep_scan_status"]
        c["security"]["deep_scan_files"] = ds.get("script_files", [])
        c["security"]["deep_scan_scripts"] = ds.get("scripts_scanned", 0)
        c["security"]["deep_scan_hooks"] = ds.get("package_hooks", [])
        if ds["deep_scan_status"] == "failed":
            fs_failed += 1
            continue
        fs_done += 1
        if ds.get("blocking_rules"):
            c["security"]["findings"] = (c["security"].get("findings") or []) + ds["findings"]
            c["security"]["blocking_rules"] = sorted(
                set(c["security"].get("blocking_rules") or []) | set(ds["blocking_rules"]))
            c["security"]["verdict"] = "block"
            c["security"]["risk_level"] = "high"
            c["security"]["install_blocked"] = True
            c["security"]["note"] += "；PASS 2 深度审查发现 block 级行为"
        elif ds.get("deep_install_blocked"):
            c["security"]["findings"] = (c["security"].get("findings") or []) + ds["findings"]
            c["security"]["install_blocked"] = True
            c["security"]["note"] += "；PASS 2 深度审查发现需人工复核的高敏感项"
        elif ds.get("findings"):
            c["security"]["findings"] = (c["security"].get("findings") or []) + ds["findings"]
    for c in unscannable:
        c.setdefault("full_scan_queue_index", None)
    FULL_SCAN = {
        "eligible": len(queue), "complete": fs_done, "failed": fs_failed,
        "remaining": max(0, len(queue) - fs_done - fs_failed),
        "gated_out": len(gated_pairs), "gate_breakdown": PR.gate_breakdown(gated_pairs),
        "queue_size_before_budget": len(queue_full), "unscannable": len(unscannable),
        "budget": ds_budget,
        "finished_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    save_json({
        "generated": FULL_SCAN["finished_at"], "summary": FULL_SCAN,
        "queue": [{"rank": c["full_scan_queue_index"], "key": c["canonical_key"],
                   "score": c.get("score"), "deep_scan_status":
                   (c.get("deep_scan") or {}).get("deep_scan_status")} for c in queue],
        "gated_out": [{"key": c["canonical_key"],
                       "gate": (c.get("capability_gap_match") or {}).get("gate_hit")}
                      for c in cands
                      if (c.get("capability_gap_match") or {}).get("gate_hit")]},
              os.path.join(STATE, "full_scan_queue.json"))

    # ---- 阶段 D：带上深度审查结果重新评估 ----
    # v2.4 §十：先把质量计数清零，让 PROJECT_MATCH_QUALITY 统计的是**最终一轮**的候选级结果
    MR.reset_quality()
    evaluate(cands, inst, cfg, W, tiers_trust, projects,
             ctx_text=CTX_TEXT, agent_slugs=AGENT_SLUGS, state=STATE_A)
    # v2.4 §十：PROJECT_MATCH_QUALITY —— 不再只报「字段非空率」，而是按证据类型分列，
    # 并显式记录「被拒绝的假相关」（secondary 技术栈硬凑 / 否定窗口压制 / 单词词面重叠）。
    quality = dict(MR.QUALITY)
    quality["matched_project_entries"] = sum(
        len((c.get("project_match") or {}).get("matched_projects") or []) for c in cands)
    quality["unresolved_mismatch_candidates"] = sum(
        1 for c in cands
        if (c.get("capability_gap_match") or {}).get("domain_mismatch_unresolved"))
    # v2.6 §十三：身份血缘的数据级断言（任何一项非 0 都不得声明冻结）
    quality["same_name_only_already_installed"] = sum(
        1 for c in cands if c["installed_relationship"] == "already_installed"
        and not c.get("lineage_evidence"))
    quality["wrong_update_lineage"] = sum(
        1 for c in cands if c.get("update_available")
        and not (c.get("update_lineage") or {}).get("lineage_verified"))
    quality["same_name_unverified_candidates"] = sum(
        1 for c in cands if c["installed_relationship"] in SAME_NAME_UNVERIFIED)
    quality["product_internal_unresolved_candidates"] = sum(
        1 for c in cands
        if (c.get("capability_gap_match") or {}).get("product_internal_unresolved"))
    # v2.7 §七：产品专项 platform_operation（非 domain 触发）的未解除数
    quality["product_specific_scope_unresolved"] = sum(
        1 for c in cands
        if (c.get("capability_gap_match") or {}).get("scope_unresolved"))
    _gcp_kws = [kw for kw in MR.MISMATCH_KW if MR.MISMATCH_DOMAIN.get(kw) == "gcp"]
    quality["gcp_alias_missed"] = sum(
        1 for c in cands
        if MR.hit_any(*MR.bag(c.get("skill_name"), c.get("description")), _gcp_kws)
        and "gcp" not in ((c.get("capability_gap_match") or {})
                          .get("domain_mismatch_domains") or []))

    # ---- v2.9 §四.11 / §三.7：全池终审计（含产品关系与领域三态） ----
    # Top 侧三项（competitor_unresolved_in_top / scope_unresolved_in_top /
    # top_candidates_with_unresolved_mismatch）由 build_context 在选完 Top 后补齐——
    # 它才是 Top 的唯一出口，这里不另算一套，避免两份口径。
    audit = PR.v29_audit(
        cands, [c["canonical_key"] for c in queue], [],
        FULL_SCAN["eligible"], FULL_SCAN["complete"])
    for _k in ("competitor_unresolved_in_top", "scope_unresolved_in_top",
               "top_candidates_with_unresolved_mismatch"):
        # v2.11 §八：Top 侧计数由 build_context（Top 唯一出口）现算补齐；
        # product_internal_in_top_count 保留占位键，由 build_context 回写真实值。
        audit.pop(_k, None)
    audit["product_internal_block_breakdown"] = FULL_SCAN["gate_breakdown"]
    audit["candidate_product_internal_unresolved_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get(
            "candidate_product_internal_unresolved"))
    audit["developer_tool_gate_unresolved_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get(
            "developer_tool_gate_unresolved"))
    audit["internal_capability_status_counts"] = {
        k: sum(1 for c in cands
               if (c.get("internal_capability") or {}).get("status") == k)
        for k in ("product_internal", "external_integration", "not_internal", "unknown")}
    audit["candidate_product_internal_unresolved_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get(
            "candidate_product_internal_unresolved"))
    audit["developer_tool_gate_unresolved_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get(
            "developer_tool_gate_unresolved"))
    quality["product_ref_type_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get("product_refs"))
    for _rt in ("developer_tool", "primary_target", "mentioned", "ambiguous"):
        quality[f"product_ref_{_rt}_candidates"] = sum(
            1 for c in cands if any(r["ref_type"] == _rt
                                    for r in (c.get("capability_gap_match") or {}).get("product_refs") or []))
    quality["competitor_conflict_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get("competitor_conflicts"))
    quality["competitor_resolved_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get("competitor_resolved"))
    quality["competitor_unresolved_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get("competitor_unresolved"))
    quality["internal_only_candidates"] = sum(
        1 for c in cands if (c.get("capability_gap_match") or {}).get("match_status") == "internal_only")
    for _st in ("applicable", "not_applicable", "insufficient_info"):
        quality[f"domain_state_{_st}"] = sum(
            1 for c in cands if (c.get("capability_gap_match") or {}).get("match_status") == _st)
    quality["domain_mismatch_state_counts"] = dict(collections.Counter(
        (c.get("capability_gap_match") or {}).get("domain_mismatch_state") or "none"
        for c in cands))
    quality["product_relation_only_from_name_candidates"] = sum(
        1 for c in cands
        if (c.get("capability_gap_match") or {}).get("product_relation_only_from_name"))
    # 「保险 → 金融」这类**能力领域**是允许的正常派生，但必须与平台领域分开记
    quality["capability_only_domain_matches"] = sum(
        1 for c in cands if (c.get("capability_domains") or {}).get("state") == "applicable"
        and not (c.get("capability_gap_match") or {}).get("product_refs"))
    for c in cands:
        c.pop("gap_match", None)
        c.pop("score_breakdown", None)

    # 聚合源解析层已挡掉的构建产物（发生在 discover 阶段，见 parse_clawhub / parse_skillsmp）
    agg_filtered = sum(int((blk or {}).get("filtered_artifacts", 0) or 0)
                       for blk in (raw.get("tier3") or {}).values())
    out = {"version": 11, "generated": TODAY,
           "model": ("canonical_key=owner/repo/skill（去重只认 canonical source，不按名称）；"
                     "安装/能力判定读取已装侧 CANONICAL_SKILL 真相源（v4，只读）；"
                     "recommendation 取值 install_candidate/watch/ignore/reject；"
                     "Security Gate 优先于分数（v2：区分『提到风险』与『执行风险』）；"
                     "install 候选须完成 PASS 2 深度静态审查；本层只发现不安装；"
                     "v2.4：项目匹配必须带**分级直接证据**（strong_tech / positioning / "
                     "shared_need / lexical），泛用技术栈只能作 secondary boost；"
                     "词面重叠需 ≥2 个高区分度词或 1 个项目域高信号词；"
                     "NEED_RULE 支持否定窗口；未解除的平台错配不得进安装候选与 Personalized Top；"
                     "v2.5：android 需求需真实 QA/构建验收证据；否定窗口按大句切分、"
                     "逗号只在段内传播否定；词面证据禁泛用技术词与裸 prompt，"
                     "独立成立仅限整理过的领域短语；mcp_dev/docx_xlsx/github-auto/"
                     "deploy/android 统一走 capability_evidence_context 四态，"
                     "非 primary 不得拿满缺口分；PPTX 单列 pptx_processing；"
                     "v2.6：身份按血缘不按同名（already_installed 必须 lineage 可证，"
                     "否则 same_name_unverified/different_source，update/replacement 不自动关联）；"
                     "产品 scope 三态（generic/platform_operation/product_internal + target_product，"
                     "GCP 产品别名补齐）；跨 Skill 重定向句不作本 Skill 能力；"
                     "mcp_dev 只认开发动词管辖 MCP 工件（using MCP tools=mcp_usage）；"
                     "frontend_design 需设计语义、静态视觉创作归 image_creative；"
                     "裸 deployment 名词不是部署能力；裸 spec/specs 不是测试身份；"
                     "v2.7：分类与 hash seed 无关（名称短语走有序 normalized_name）；"
                     "qa 名需真实质保语义（Question Answering 出局）；"
                     "deploy=动词+通用对象邻近（发布游戏/部署规则不算通用部署）；"
                     "secret-safety=安全对象 AND 安全动作；"
                     "跨域歧义单词不得独立成词面证据；React Native 先遮蔽再判原生；"
                     "产品专项词典进 platform_operation 门；"
                     "v2.8：expo-rn/python-auto/llm-api/browser-qa/dashboard-viz 走核心证据四态"
                     "（支持型提及不再撑起个人 Top）；平台 scope 输出证据层（名称/描述/repo，"
                     "不按 owner 一刀切）+ AWS 服务别名；SSH host 名词不是部署动词；"
                     "v2.9：产品关系走 config/product_relationships.json（PRODUCT_REF / "
                     "COMPETITOR_OF / PRODUCT_IN 派生，竞品关系逐条带依据），名称含品牌词"
                     "只算 mentioned、不构成质量或安全结论；项目能力清单拆六节、"
                     "领域三态（适用/不适用/信息不足）且每个领域可追溯来源；"
                     "产品内部能力必须与来源产品同句共现；深度安全审查队列覆盖全池"
                     "但硬 Gate 命中者不入队"),
           "counts": {"raw_candidates": stats["raw"],
                      "after_canonical_dedup": len(cands),
                      "invalid_artifacts_removed": stats["artifact_filtered"] + agg_filtered,
                      "invalid_artifacts_removed_aggregator": agg_filtered,
                      "invalid_artifacts_removed_pool": stats["artifact_filtered"],
                      "invalid_names_removed": stats["invalid_name_filtered"],
                      "bottom_up_total": stats["bottom_up_total"],
                      "bottom_up_verified": stats["bottom_up_verified"],
                      "bottom_up_quarantined": stats["bottom_up_quarantined"]},
           "quarantine": quarantine,
           "weights": W,
           "focus_capabilities": [f for f in
                                  load_json(os.path.join(RAW, "gap_focus.json"), {})
                                  .get("focus_capabilities", [])],
           "local_projects": [{"name": p["name"], "tech": p["tech"], "date": p["date"],
                               "conflict": p.get("conflict")}
                              for p in projects],
           # v2.11 §四/§五：输入 A 只标记、不篡改；冲突侧 strong_tech 已在 match_projects 抑制
           "project_context_health": {
               "conflict_count": sum(1 for p in projects if p.get("conflict")),
               "conflicts": [
                   {"project": p["name"],
                    "reason": p["conflict"]["conflict_reason"],
                    "description_tech": p["conflict"]["description_tech"],
                    "missing_tech": p["conflict"]["missing_tech"],
                    "declared_tech": p["conflict"]["declared_tech"],
                    "suppressed_strong_tech": p["conflict"]["suppressed_labels"]}
                   for p in projects if p.get("conflict")],
               "note": "v2.11 §五：description-tech mismatch → 冲突侧 strong_tech 不得单独造项目匹配"},
           "project_match_quality": quality,
           "security_review_gate": audit,
           "product_capabilities": sorted(PR.load()["capabilities"]),
           "product_domains": sorted(PR.load()["domains"]),
           "tier1_updates": updates,
           "candidates": cands}
    save_json(out, CANDIDATES_PATH)
    rec_n = sum(1 for c in cands if c["recommendation"] == "install_candidate")
    print(f"raw {stats['raw']} → pool {len(cands)} | 过滤构建产物 "
          f"{stats['artifact_filtered'] + agg_filtered}（聚合源解析层 {agg_filtered} + 入池前 "
          f"{stats['artifact_filtered']}） / 非法名 {stats['invalid_name_filtered']} | "
          f"install_candidate {rec_n} | watch "
          f"{sum(1 for c in cands if c['recommendation']=='watch')} | reject "
          f"{sum(1 for c in cands if c['recommendation']=='reject')} | fetched {fetched} | "
          f"deep_scan {FULL_SCAN['complete']} | projects {len(projects)}")
    print("PROJECT_MATCH_QUALITY | " + " ".join(f"{k}={v}" for k, v in quality.items()))
    return 0


def fm_description(txt):
    """从 SKILL.md 文本取 description；正确处理 YAML 块标量（> / >- / | / |-）。"""
    if not txt:
        return ""
    m = re.search(r"^description:\s*(.*)$", txt, re.M)
    if not m:
        return ""
    head, rest = m.group(1).strip(), txt[m.end():]
    if head in ("", ">", ">-", ">+", "|", "|-", "|+"):
        lines = []
        for line in rest.split("\n"):
            if not line.strip():
                if lines:
                    lines.append("")
                continue
            if re.match(r"^\S", line):
                break
            lines.append(line.strip())
        val = " ".join(x for x in lines if x).strip()
    else:
        val = head.strip("'\"")
    # v2.6 §五：300 字符会把「For an Android device or emulator, use
    # orca-emulator-android.」这类句尾截断，重定向语境因此读不到 —— 放宽到 600。
    return re.sub(r"\s+", " ", val)[:600]


meta_by_repo = {}

if __name__ == "__main__":
    sys.exit(main())
