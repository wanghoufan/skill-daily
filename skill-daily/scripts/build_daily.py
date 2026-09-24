#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill 日报引擎 V1.4（build_daily.py）——确定性，不调用 LLM，不执行任何安装。

历史修复说明（允许提及旧版本号；「当前版本」以本行、argparse、engine.version 为准）：
* V1.1：全动作冷却（周期 config 化）/同日幂等/PRIMARY+alternatives/capability family quota/
  真 SKIP 计数/中文 one_line_explanation/input_provenance/suppressed 扩展/no auto install；
  shown 条目带三签名 + delta_cats，突破冷却只认相对上次展示新增的事件；
  处理顺序 硬门→反馈→实质变化→冷却→功能去重→族配额→优先级→上限。
* V1.2：candidate_baseline 全池基线与 shown 两层；缺外部快照零 NEW 风暴；
  backlog 不轮播；stale_backlog_items/non_material_daily_items 硬门；logical_path 去绝对路径。
* V1.3：生命周期收口——NO_LONGER_RELEVANT / STATUS_DOWNGRADED / STATUS_UPGRADED /
  RETURNED / replacement_candidate（第 6 类动作「建议替换」）/ tombstone 有限保留。
* V1.4：External root resolver（env/开发仓/同级转送包/legacy 四布局验证式定位 + 友好错误）
  与当前版本标签统一；业务逻辑与 V1.3 完全一致。
"""
ENGINE_NAME = "skill-daily"
ENGINE_VERSION = "1.4"
import argparse
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                   # noqa: E402
from common import (load_json, save_json, parse_date)  # noqa: E402


def _load_external_build_context():
    """只读复用 v2.11 冻结语义（classify_delta / snap_key）。

    两个包都有名为 `common` 的模块，这里临时换出本引擎的 `common`，
    让 external-intelligence 的 build_context 按它自己的口径导入；
    完成后原样换回——不写 external 层任何文件。
    """
    ext_scripts = C.EXTERNAL_SCRIPTS_DIR
    saved = sys.modules.pop("common", None)
    try:
        sys.path.insert(0, ext_scripts)
        import build_context as bc_mod
    finally:
        if ext_scripts in sys.path:
            sys.path.remove(ext_scripts)
        for m in ("build_context", "match_rules", "security_gate", "common"):
            sys.modules.pop(m, None)
        if saved is not None:
            sys.modules["common"] = saved
    return bc_mod


bc = _load_external_build_context()

# ---- 用户语言（§三 简单中文；技术词只进「技术详情」，模板不加工程术语） ----
ACTION_LABEL = {"install": "建议安装", "restore": "建议恢复", "update": "建议更新",
                "replace": "建议替换",            # V1.3 §十七/§十八：6 类动作
                "watch": "继续观察", "risk": "暂不建议"}
PRIORITY = {"restore": 0, "risk": 1, "update": 2, "replace": 3,
            "install_project": 4, "install_gap": 5,
            "watch_rising": 6, "watch_normal": 7}
# V1.3 §十：高价值动作集（降级判定与消失「值得提醒」判定共用）
HIGH_VALUE_ACTIONS = {"new_install", "update_candidate", "restore_candidate",
                      "replacement_candidate"}
DOWNGRADE_TARGETS = {"reject", "watch", "none", None}
VERDICT_RANK = {"pass": 0, "review_required": 1, "unscanned": 2, "block": 3}
REL_LABEL = {"new_capability": "没装过同类的", "complement": "和已装能力互补",
             "replacement_candidate": "可以替换现有的某个",
             "overlap": "和已装能力有重叠", "near_duplicate": "和已装能力几乎重复",
             "same_name_unverified": "名字和已装的某个相同，但还没确认是同一个",
             "same_name_different_source": "名字相同但来源不同",
             "possible_fork": "可能是已装某个的分叉", "already_installed": "已经装过"}
SEC_LABEL = {"pass": "静态检查通过（仍需人工看一眼）",
             "review_required": "有需注意项，安装前请人工复核",
             "block": "高风险，已拒绝", "unscanned": "未完成扫描，最多只能观察"}
DELTA_LABEL = {"NEW": "今天新出现", "UPDATED": "上游有真实更新", "RISING": "热度/评分明显上升",
               "FALLING": "明显下降", "SECURITY_CHANGED": "安全状态有变化",
               "SOURCE_CHANGED": "来源核验状态有变化", "MATCH_CHANGED": "与你的匹配度有变化",
               "NO_LONGER_RELEVANT": "已不在候选池",
               "ACTION_CHANGED": "动作类型有变化（如 观察→建议安装）",
               "STATUS_DOWNGRADED": "推荐状态降级（V1.3 §十）",
               "STATUS_UPGRADED": "推荐状态提升（V1.3 §二十二）",
               "RETURNED": "前几天退出候选池后，今天重新出现",
               "PROJECT_CHANGED": "与你的项目匹配状态有新变化",
               "METADATA_ENRICHED": "（系统内部）补全了元数据",
               "RECALCULATED": "（系统内部）重新计算",
               "SYSTEM_REBASELINE": "（系统内部）重建基线"}
# §十二 report_reason_type 枚举（static_backlog_rotation 被禁止出现）
REASON_LABEL = {
    "initial_baseline": "首次建立 Skill 基线，先展示当前最值得处理的几项（不是今天新发生）",
    "material_delta": "今天出现真实变化",
    "project_match_change": "今天与你的项目匹配状态发生新变化",
    "risk_change": "今天安全/来源状态有变化",
    "feedback_reentry": "你的反馈状态变化后重新评估进入",
    "cooldown_reminder": "距上次提醒已到一个周期，按配置再次提醒（状态本身无变化）",
}
# §二：能突破各动作冷却的「实质变化」事件集
MATERIAL_DELTA = {
    "install": {"NEW", "UPDATED", "RISING", "SECURITY_CHANGED", "SOURCE_CHANGED",
                "MATCH_CHANGED"},
    "update": {"UPDATED", "SOURCE_CHANGED", "SECURITY_CHANGED"},
    "restore": {"SECURITY_CHANGED", "SOURCE_CHANGED", "UPDATED", "NEW"},
    "watch": {"NEW", "UPDATED", "RISING", "SECURITY_CHANGED", "SOURCE_CHANGED",
              "MATCH_CHANGED"},
    # V1.2 §十一：risk 也必须事件驱动，事件集显式声明（旧风险不算今日事件）
    "risk": {"NEW", "UPDATED", "SECURITY_CHANGED", "SOURCE_CHANGED"},
    # V1.3 §十七：replacement 与 install 同级生命周期事件集
    "replace": {"NEW", "UPDATED", "RISING", "SECURITY_CHANGED", "SOURCE_CHANGED",
                "MATCH_CHANGED"},
}
LIFECYCLE_CATS = {"STATUS_DOWNGRADED", "STATUS_UPGRADED", "RETURNED"}
WATCH_TRIGGERS = (MATERIAL_DELTA["watch"] | {"PROJECT_CHANGED", "ACTION_CHANGED"}
                  | LIFECYCLE_CATS)
INTERNAL_ONLY = {"METADATA_ENRICHED", "RECALCULATED"}
# §十三 daily_delta「今日出现理由」的完整证据事件集（含 v2.11 语义之外的日报层事件）
MATERIAL_ALL = (set().union(*MATERIAL_DELTA.values())
                | {"PROJECT_CHANGED", "ACTION_CHANGED"} | LIFECYCLE_CATS)
REPEAT_CFG_KEY = {"install": "install_repeat_days", "update": "update_repeat_days",
                  "restore": "restore_repeat_days", "watch": "watch_repeat_days",
                  "replace": "install_repeat_days"}
# §二十四：正式交付只写逻辑路径（不泄露开发机目录，转送后可移植）
LOGICAL_PATHS = {
    "external_candidates": "external-intelligence/SKILL_CANDIDATES.json",
    "external_delta_semantics": "external-intelligence/scripts/build_context.py",
    "feedback": "skill-daily/data/SKILL_FEEDBACK.json",
    "daily_state": "skill-daily/data/state/daily_snapshot.json",
}


# ==========================================================================
# 输入
# ==========================================================================
def _cmp_cats(c, prev_snap, prev_action, prev_proj):
    """§九：日报层自己的比较——仍用 v2.11 classify_delta 语义，
    外加两个日报层事件（action_type / 项目匹配签名变化）。"""
    cats = set(bc.classify_delta(prev_snap, bc.snap_key(c)))
    if prev_action is not None and prev_action != c.get("action_type"):
        cats.add("ACTION_CHANGED")
    if prev_proj is not None:
        _, proj, _ = _sigs(c)
        if proj != prev_proj and (proj or prev_proj):
            cats.add("PROJECT_CHANGED")
    return sorted(cats)


def _transition(prev_action, prev_rec, cur_action, cur_rec):
    """V1.3 §十/§十五/§二十二：action/recommendation 迁移分类。
    只有真正改变用户动作方向的转换才算事件（watch→watch、score 小变化不算，§二十三）。"""
    prev_high = prev_action in HIGH_VALUE_ACTIONS or prev_rec == "install_candidate"
    cur_high = cur_action in HIGH_VALUE_ACTIONS or cur_rec == "install_candidate"
    if prev_high and not cur_high:
        return "STATUS_DOWNGRADED"
    if cur_high and not prev_high:
        return "STATUS_UPGRADED"
    if prev_action == "reject" and cur_action not in (None, "reject"):
        return "STATUS_UPGRADED"                 # §七十二：reject→观察=改善，文案要写清
    return None


def _build_candidate_baseline(cands):
    """§三/§十九：全池最小卡片数据（不复制完整候选）：消失当天还能生成可读卡片。"""
    base = {}
    for c in cands:
        ext, proj, sec = _sigs(c)
        base[c["canonical_key"]] = {
            "snap": bc.snap_key(c), "action_type": c.get("action_type"),
            "recommendation": c.get("recommendation"),
            "matched_projects_signature": proj, "security_signature": sec,
            "external_signature": ext,
            "skill_name": c.get("skill_name"),
            "source": f"{c.get('owner')}/{c.get('repo')}",
            "source_url": c.get("source_url") or "", "score": c.get("score")}
    return base


def _tombstone_prune(tombs, current_keys, today, retention_days):
    """§六/§七：tombstone 有限保留。
    重新出现的：当天保留（同日幂等），次日起删除；
    仍缺席的：重要且未通知 → 不提前清理（§77）；否则超过 retention 才清理。"""
    out = {}
    for k, v in (tombs or {}).items():
        if k in current_keys:
            if v.get("returned_notified_date") == today.isoformat():
                out[k] = v
            continue
        important = v.get("important")
        notified = v.get("notified_no_longer_relevant")
        if important and not notified:
            out[k] = v
            continue
        ls = parse_date(v.get("last_seen"))
        if ls is None or (today - ls).days <= retention_days:
            out[k] = v
    return out


def load_inputs(today, snapshot_path=None, cands_doc=None, feedback=None,
                deltas=None):
    doc = cands_doc or load_json(C.CANDIDATES_PATH)
    if not doc:
        raise SystemExit(f"缺少冻结输入：{C.CANDIDATES_PATH}（日报引擎不重建候选池）")
    snap_doc = load_json(C.EXTERNAL_SNAPSHOT_PATH, {}) or {}
    ext_snap = snap_doc.get("candidates") if snap_doc.get("candidates") else snap_doc
    first_external = not ext_snap
    snap_path = snapshot_path or C.DAILY_SNAPSHOT_PATH
    daily_snap = load_json(snap_path, {}) or {}
    baseline = daily_snap.get("candidate_baseline") or {}
    tombstones = daily_snap.get("candidate_tombstones") or {}
    prev_rd = daily_snap.get("report_date")
    cur_keys = {c["canonical_key"] for c in doc["candidates"]}
    # §二十一 比较顺序第 1 步：old baseline vs current keys → removed / returned
    removed = {}
    for k, b in baseline.items():
        if k not in cur_keys:
            removed[k] = dict(b, _from="baseline")
    for k, v in tombstones.items():
        if k not in cur_keys and not v.get("notified_no_longer_relevant"):
            disp = v.get("last_display") or {}
            removed[k] = dict(v, _from="tombstone_pending",
                              skill_name=disp.get("skill_name") or v.get("skill_name"),
                              source=disp.get("source") or v.get("source"),
                              source_url=disp.get("source_url") or v.get("source_url"),
                              score=disp.get("score", v.get("score")),
                              action_type=v.get("last_action_type"),
                              recommendation=v.get("last_recommendation"))
        elif (k not in cur_keys and prev_rd == today.isoformat()
              and v.get("notified_no_longer_relevant") == today.isoformat()):
            disp = v.get("last_display") or {}
            removed[k] = dict(v, _from="tombstone_rerun",
                              skill_name=disp.get("skill_name") or v.get("skill_name"),
                              source=disp.get("source") or v.get("source"),
                              source_url=disp.get("source_url") or v.get("source_url"),
                              score=disp.get("score", v.get("score")),
                              action_type=v.get("last_action_type"),
                              recommendation=v.get("last_recommendation"))
    returned = {k for k in cur_keys
                if k in tombstones and (
                    not tombstones[k].get("returned_notified_date")
                    or tombstones[k].get("returned_notified_date") == today.isoformat())}
    if deltas is None:
        # §十 优先级：1 日报自有 candidate_baseline；2 外部 last_snapshot（仅首日辅助，
        # 且辅助时缺键不判 NEW）；3 都没有 → 无事件，initial_baseline，零 NEW 风暴（§七）。
        deltas = {}
        if baseline:
            for c in doc["candidates"]:
                key = c["canonical_key"]
                b = baseline.get(key)
                if b is None:
                    cats = set(bc.classify_delta(None, bc.snap_key(c)))
                else:
                    cats = set(_cmp_cats(c, b.get("snap"), b.get("action_type"),
                                         b.get("matched_projects_signature")))
                    tr = _transition(b.get("action_type"), b.get("recommendation"),
                                     c.get("action_type"), c.get("recommendation"))
                    if tr:
                        cats.add(tr)
                if key in returned:
                    cats.add("RETURNED")
                if cats:
                    deltas[key] = sorted(cats)
        elif ext_snap:
            for c in doc["candidates"]:
                prev = ext_snap.get(c["canonical_key"])
                if prev:
                    cats = _cmp_cats(c, prev, None, None)
                    if cats:
                        deltas[c["canonical_key"]] = cats
        # §八：RETURNED 与 baseline/辅助分支无关，重新出现必须标记（空基线也要有）
        for key in returned:
            deltas[key] = sorted(set(deltas.get(key) or []) | {"RETURNED"})
    return dict(cands=doc["candidates"], cands_doc=doc, deltas=deltas,
                feedback=feedback if feedback is not None else C.load_feedback(),
                daily_snap=daily_snap,
                candidate_baseline=baseline,
                tombstones=tombstones, removed=removed, returned=returned,
                conflicts=doc.get("project_context_health") or {},
                first_external=first_external, today=today)


def _g(c, path, default=None):
    cur = c
    for seg in path:
        cur = (cur or {}).get(seg)
        if cur is None:
            return default
    return cur


def _norm_name(n):
    return re.sub(r"[-_\s]+", "-", (n or "").lower()).strip("-")


def _sigs(c):
    """§四：不需要复杂 hash，能判断「今天是否真的变了」即可。"""
    ext = "{}|{}|{}|{}".format(c.get("action_type"), c.get("recommendation"),
                               c.get("latest_version") or "", c.get("latest_commit") or "")
    proj = ",".join(sorted({m.get("project") or "" for m in
                            _g(c, ("project_match", "matched_projects"), []) or []}))
    sec = "{}|{}".format(_g(c, ("security", "verdict")), _g(c, ("security", "risk_level")))
    return ext, proj, sec


def _display_family_key(c):
    """§七：完全重复 = 规范化 skill_name + matched_gap 相同。"""
    return f"{_norm_name(c.get('skill_name'))}#{_g(c, ('capability_gap_match', 'matched_gap')) or '—'}"


def _family(c):
    return _g(c, ("capability_gap_match", "matched_gap")) or "—"


def _install_gate_ok(c):
    """§二十 14/15 保险带：未解除 scope/错配、strong 饱和无增量 → 不得进建议安装。"""
    gm = c.get("capability_gap_match") or {}
    if gm.get("scope_unresolved") or gm.get("product_internal_unresolved"):
        return False
    if gm.get("domain_mismatch_unresolved"):
        return False
    if _g(c, ("security", "verdict")) == "block":
        return False
    sat = gm.get("capability_saturation") or ""
    if sat.startswith("strong") and sat != "strong_degraded":
        if not (c.get("personalized_reason") or {}).get("incremental_over_installed") \
                and not c.get("update_available") \
                and c.get("installed_relationship") != "replacement_candidate":
            return False
    return True


def _has_strong_project(c):
    pr = c.get("personalized_reason") or {}
    if pr.get("matched_project"):
        return True
    for m in _g(c, ("project_match", "matched_projects"), []) or []:
        if set(m.get("direct_evidence_kinds") or []) & {"strong_tech", "positioning"}:
            return True
    return False


def feedback_of(inp, key):
    return (inp.get("feedback") or {}).get(key)


def _conflict_projects(conflicts_doc):
    return {x.get("project") for x in (conflicts_doc.get("conflicts") or [])}


def _zh_one_line(it):
    """§十四（V1.1）：机器与 Markdown 的 one_line_explanation 同一个中文模板。"""
    n = it["skill_name"]
    rt = it.get("report_reason_type")
    if rt == "status_downgrade":                    # V1.3 §十一：不与安全风险混写
        return f"之前建议安装「{n}」，今天系统已不再推荐它（状态降级），先不要按昨天的建议操作。"
    if rt == "no_longer_relevant":                  # §十三
        return f"「{n}」昨天还在推荐列表里，今天已经不再属于当前候选。"
    if it["action"] == "replace":                   # §十七：不写成「全新安装」
        return f"「{n}」是用来替换现有某个已装 Skill 的候选建议，不是发现了一个新 Skill。"
    if it["action"] == "restore":
        return f"这是你已装能力「{n}」的官方同来源版本；本机正本缺失，可以恢复，不是新 Skill。"
    if it["action"] == "update":
        return f"你已装的「{n}」上游出了新版本（同血缘已确认），可以更新。"
    if it["action"] == "risk":
        return f"「{n}」今天安全/来源状态变差，暂时不要装。"
    if it["action"] == "install":
        gap = (it["fills_gap"] or "").replace("能力族 ", "")
        return f"「{n}」能补你的能力缺口：{gap or '见下方项目匹配'}。"
    return f"「{n}」是今天值得观察一条的候选，先看看，不用动手。"


# ==========================================================================
# §十八 处理顺序：硬门 → 反馈 → 实质变化 → 冷却 → 去重 → 配额 → 排序 → 上限
# ==========================================================================
def build_items(inp, cfg, report_mode):
    cands, deltas, feedback = inp["cands"], inp["deltas"], inp["feedback"]
    daily_snap, today = inp["daily_snap"], inp["today"]
    shown = daily_snap.get("shown") or {}
    baseline = inp.get("candidate_baseline") or {}          # §四 baseline_seen ≠ shown
    conflict_names = _conflict_projects(inp["conflicts"])
    by_key = {c["canonical_key"]: c for c in cands}

    def _fam_repo(c):
        return (_g(c, ("capability_gap_match", "matched_gap")) or "—",
                f"{c.get('owner')}/{c.get('repo')}")

    poor_gaps, poor_repos, useful_gaps, useful_repos = set(), set(), set(), set()
    for k, fb in feedback.items():
        c = by_key.get(k)
        if not c:
            continue
        gap, repo = _fam_repo(c)
        if fb.get("status") == "poor":
            (poor_gaps.add(gap) if gap != "—" else None)
            poor_repos.add(repo)
        elif fb.get("status") == "useful":
            (useful_gaps.add(gap) if gap != "—" else None)
            useful_repos.add(repo)

    items = []
    suppressed = {"repeat_cooldown": 0, "functional_duplicate": 0,
                  "capability_family_quota": 0, "unchanged_watch": 0,
                  "metadata_only": 0, "feedback": 0,
                  "baseline_backlog": 0, "non_material_today": 0,
                  "no_longer_relevant_unseen": 0}                 # V1.3 §五/§二十四
    internal_counts = {"METADATA_ENRICHED": 0, "RECALCULATED": 0, "SYSTEM_REBASELINE": 0}

    def _fb_suppressed(key, c):
        fb = feedback.get(key)
        if not fb:
            return None
        st, when = fb.get("status"), parse_date(fb.get("updated_at"))
        gap_d = C.days_between(when, today)
        if st == "installed":
            return "已按你的反馈标记为已安装，等底座更新后以 Canonical 为准"
        if st == "ignored" and gap_d is not None and gap_d < cfg["ignored_repeat_days"]:
            return f"你之前标记为「忽略」，{cfg['ignored_repeat_days']} 天内不再重复"
        if st == "deferred" and gap_d is not None and gap_d < cfg["deferred_repeat_days"]:
            return f"你之前标记为「暂缓」，{cfg['deferred_repeat_days']} 天内不再重复"
        if st == "removed" and gap_d is not None and gap_d < cfg["removed_cooldown_days"]:
            return (f"你之前移除过同类 Skill，{cfg['removed_cooldown_days']} 天内"
                    "不重新推荐同一个")
        return None

    def _mat_set(action):
        return (MATERIAL_DELTA.get(action, set())
                | {"PROJECT_CHANGED", "ACTION_CHANGED"} | LIFECYCLE_CATS)

    def _cooldown_hit(key, action, c, cats):
        """§二/§三：冷却判定（只适用于曾被展示的候选）。同日重跑幂等；实质变化突破。"""
        prev = shown.get(key)
        if not prev or not prev.get("date"):
            return False
        pd = parse_date(prev.get("date"))
        if pd == today:                       # §三：same-day rerun = idempotent
            return False
        if prev.get("action") != action:      # 动作变了 → 重新提醒
            return False
        ext, proj, sec = _sigs(c)
        if prev.get("external_signature") and prev["external_signature"] != ext:
            return False                        # 恢复路径/动作状态/版本变了
        if prev.get("security_signature") and prev["security_signature"] != sec:
            return False
        if proj and prev.get("matched_project_signature") is not None \
                and prev["matched_project_signature"] != proj:
            return False                        # 项目命中变化（含新命中）
        fb = feedback.get(key)
        if fb and parse_date(fb.get("updated_at")) and \
                parse_date(fb["updated_at"]) > pd:
            return False                        # §五：用户反馈导致重新进入
        # 「实质变化」必须是相对上次展示时新增的事件：无外部基线时 NEW 会天天在，
        # 若不过滤就会出现「连续两天 10 条全同」的复审违例（§一）。
        prev_cats = set(prev.get("delta_cats") or [])
        if (cats - prev_cats) & _mat_set(action):
            return False                        # 新增实质 Delta 突破
        if action == "risk":
            # risk 不叠加 repeat_days：今天有新事件立刻提醒；
            # 但事件无变化的旧风险不得每天冒充「今天发生」（§二.4）。
            return not (cats - prev_cats)
        days = cfg.get(REPEAT_CFG_KEY.get(action, "watch_repeat_days"), 7)
        gap_d = C.days_between(pd, today)
        if gap_d is not None and gap_d < days:
            return True
        return False

    def _reason_and_evidence(key, action, cats, report_mode):
        """§十二/§十三：daily_delta 每条必须有今日理由；返回 (reason_type, evidence) 或 None。"""
        prev = shown.get(key)
        mat = _mat_set(action)
        evidence = sorted(cats & mat)
        if report_mode == "initial_baseline":
            return "initial_baseline", ["initial_baseline_view"]
        if not prev or not prev.get("date"):
            # V1.2 核心门：baseline_seen 但从未展示 → 无今日事件就是静态 backlog（§五）。
            # V1.3 §七十：未展示的降级只机器计数，不打扰用户（下次它再值得会被重估）。
            neg = {"FALLING", "ALREADY_INSTALLED", "NO_LONGER_RELEVANT",
                   "STATUS_DOWNGRADED"}
            if "STATUS_DOWNGRADED" in cats:
                suppressed["non_material_today"] += 1
                return "SUPPRESSED", None
            pos = cats - neg - INTERNAL_ONLY
            if pos:
                ev = sorted(pos)
                if "RETURNED" in cats:
                    return "candidate_returned", ev
                if action == "risk":
                    return "risk_change", ev
                if ev == ["PROJECT_CHANGED"]:
                    return "project_match_change", ev
                if "STATUS_UPGRADED" in cats:
                    return "status_upgrade", ev
                return "material_delta", ev
            if cats & neg:
                suppressed["non_material_today"] += 1
                return "SUPPRESSED", None
            suppressed["baseline_backlog"] += 1
            return "SUPPRESSED", None
        pv_date = parse_date(prev.get("date"))
        if pv_date == today:                    # 同日重跑幂等（§三）：沿用当天首次判定
            return (prev.get("report_reason_type") or "cooldown_reminder",
                    prev.get("material_today_evidence") or ["same_day_rerun_idempotence"])
        fb = feedback.get(key)
        fb_fresh = bool(fb and parse_date(fb.get("updated_at"))
                        and parse_date(fb["updated_at"]) > pv_date)
        if evidence:
            if "STATUS_DOWNGRADED" in cats:      # V1.3 §十：降级优先于普通 material
                return "status_downgrade", ["status_downgraded"]
            if "RETURNED" in cats:               # §八：重新出现要说「回来了」，不是全新
                return "candidate_returned", sorted(evidence)
            if "STATUS_UPGRADED" in cats:        # §二十二
                return "status_upgrade", ["status_upgraded"]
            if action == "risk":
                return "risk_change", evidence
            if evidence == ["PROJECT_CHANGED"]:
                return "project_match_change", evidence
            ev = list(evidence)
            if fb_fresh:
                ev.append("feedback_change")
            return "material_delta", ev
        ext, proj, sec = _sigs(by_key[key]) if key in by_key else ("", "", "")
        if key in by_key and (
                (prev.get("external_signature") and prev["external_signature"] != ext)
                or (prev.get("security_signature")
                    and prev["security_signature"] != sec)):
            return "material_delta", ["signature_change"]     # §十三：签名变化即今日理由
        if proj and prev.get("matched_project_signature") is not None \
                and prev["matched_project_signature"] != proj:
            return "project_match_change", ["project_match_change"]
        if action == "risk":
            return "SUPPRESSED", None           # 旧风险无今日事件（§十一）
        if fb_fresh:
            return "feedback_reentry", ["feedback_change"]
        days = cfg.get(REPEAT_CFG_KEY.get(action, "watch_repeat_days"), 7)
        gap_d = C.days_between(pv_date, today)
        if gap_d is not None and gap_d >= days:
            return "cooldown_reminder", [f"cooldown_due:{days}d"]
        suppressed["repeat_cooldown"] += 1
        return "SUPPRESSED", None

    def _why(reason_type, action, cats):
        if reason_type == "initial_baseline":
            if action == "risk":
                return "首次基线发现的当前风险（不是今天新发生）"
            if action == "restore":
                return "首次基线：这是当前缺失能力里的优先恢复项（不是新发现）"
            return REASON_LABEL["initial_baseline"]
        if reason_type == "risk_change":
            return "安全/来源状态今天有变化"
        if reason_type == "project_match_change":
            return "今天与你的项目需求新匹配上"
        if reason_type == "feedback_reentry":
            return "你的反馈状态变化后重新评估出现"
        if reason_type == "cooldown_reminder":
            return "状态自上次展示以来没有变化，但提醒周期已到，按配置再提醒你一次"
        if reason_type == "status_downgrade":
            return "昨天还在推荐列表里，今天系统已不再推荐它（状态降级，不是重复提醒）"
        if reason_type == "status_upgrade":
            return "之前只是观察/不建议，今天状态提升（不是第一次见到的新东西）"
        if reason_type == "candidate_returned":
            return "这个 Skill 前几天曾退出候选池，今天重新出现（不是全新发现）"
        if reason_type == "no_longer_relevant":
            return "候选状态发生变化，不是重复提醒"
        labels = [DELTA_LABEL[t] for t in sorted(cats)
                  if t in DELTA_LABEL and t not in INTERNAL_ONLY]
        return "今天出现真实变化：" + "、".join(labels)

    def _add(key, bucket, c, extra_note=""):
        action = ("restore" if bucket == "restore" else
                  "install" if bucket.startswith("install") else
                  "update" if bucket == "update" else
                  "replace" if bucket == "replace" else
                  "risk" if bucket == "risk" else "watch")
        cats = sorted(set(deltas.get(key) or []))
        reason_type, evidence = _reason_and_evidence(key, action, set(cats), report_mode)
        if reason_type == "SUPPRESSED":
            return
        if _cooldown_hit(key, action, c, set(cats)):
            suppressed["repeat_cooldown"] += 1
            return
        pr = dict(c.get("personalized_reason") or {})
        pm = c.get("project_match") or {}
        if not pr.get("matched_project") and (pm.get("matched_projects") or []):
            m0 = pm["matched_projects"][0]
            pr["matched_project"] = f"{m0['project']}（match={m0['match_score']}）"
        if not pr.get("fills_gap"):
            needs = pm.get("matched_needs") or []
            gap = _g(c, ("capability_gap_match", "matched_gap"))
            pr["fills_gap"] = (("命中需求：" + "/".join(needs[:3])) if needs else "") \
                + (f"；能力缺口：{gap}" if gap else "")
        gap_f, repo_f = _fam_repo(c)
        prio = PRIORITY[bucket]
        fb_effect = ""
        if (gap_f != "—" and gap_f in poor_gaps) or repo_f in poor_repos:
            prio += 2
            fb_effect = ("你之前把同类 Skill 标记为「不好用」（同能力族 "
                         f"{gap_f if gap_f in poor_gaps else '—'}/同来源 {repo_f}），"
                         "因此本次降低展示优先级。")
        elif (gap_f != "—" and gap_f in useful_gaps) or repo_f in useful_repos:
            prio = max(0, prio - 1)
            fb_effect = f"你之前把同类 Skill 标记为「好用」（同来源 {repo_f} 等），本次提升展示优先级。"
        it = {
            "canonical_key": key, "skill_name": c.get("skill_name"),
            "bucket": bucket, "action": action, "priority": prio,
            "one_line_explanation": "", "source_description_excerpt": C.clean_desc(c.get("description")),
            "why_today": _why(reason_type, action, set(cats)),
            "report_reason_type": reason_type,
            "material_today_evidence": list(evidence or []),
            "matched_project": pr.get("matched_project") or "",
            "fills_gap": pr.get("fills_gap") or "",
            "installed_overlap": REL_LABEL.get(c.get("installed_relationship"),
                                               c.get("installed_relationship") or ""),
            "security_status": SEC_LABEL.get(_g(c, ("security", "verdict")), "未扫描"),
            "source": f"{c.get('owner')}/{c.get('repo')}",
            "repo": f"https://github.com/{c.get('owner')}/{c.get('repo')}",
            "skill_path": c.get("path") or "",
            "source_url": c.get("source_url") or "",
            "source_tier": c.get("source_tier"),
            "personalized_score": c.get("score"),
            "action_type": c.get("action_type"),
            "delta_cats": cats, "feedback_effect": fb_effect, "feedback_reason": fb_effect,
            "extra_note": extra_note,
            "family": _family(c), "display_family_key": _display_family_key(c),
            "verdict_rank": VERDICT_RANK.get(_g(c, ("security", "verdict")), 9),
            "affected_by_conflict": bool(conflict_names & {m.get("project") for m in
                                                           (_g(c, ("project_match",
                                                                   "matched_projects"),
                                                             []) or [])}),
            "alternatives": [],
        }
        it["one_line_explanation"] = _zh_one_line(it)
        items.append(it)

    for c in cands:
        key = c["canonical_key"]
        at = c.get("action_type") or "watch"
        cats = set(deltas.get(key) or [])
        if cats and cats <= INTERNAL_ONLY:
            suppressed["metadata_only"] += 1
        # —— V1.3 §十：状态降级统一走「暂不建议」桶（只有曾被展示才提醒） ——
        if "STATUS_DOWNGRADED" in cats:
            if key in shown:
                note = _fb_suppressed(key, c)
                if note:
                    suppressed["feedback"] += 1
                    continue
                b = baseline.get(key) or {}
                prev_label = ACTION_LABEL.get(
                    {"new_install": "install", "update_candidate": "update",
                     "restore_candidate": "restore",
                     "replacement_candidate": "replace"}.get(
                        b.get("action_type"), ""), b.get("action_type") or "观察")
                cur_label = ("不再进入当前候选池" if at == "reject" else "降为继续观察")
                why_r = (c.get("recommendation_reason") or "").strip()
                if "SECURITY_CHANGED" in cats:
                    why_r = why_r or "安全状态变化"
                _add(key, "risk", c,
                     f"之前的动作：{prev_label}；现在：{cur_label}。"
                     f"原因：{why_r or '当前候选状态发生变化（非安全类原因会以本条为准）'}")
            else:
                suppressed["non_material_today"] += 1
            continue
        # —— 暂不建议（§三.5 + §二.4：只由今天的新事件触发，旧风险不天天重发）——
        if ("SECURITY_CHANGED" in cats or "SOURCE_CHANGED" in cats) and \
                (_g(c, ("security", "verdict")) == "block"
                 or _g(c, ("security", "risk_level")) == "high"):
            note = _fb_suppressed(key, c)
            if note:
                suppressed["feedback"] += 1
                continue
            _add(key, "risk", c,
                 "原因：高风险（静态审查发现真要求执行的危险行为）")
            continue
        if at == "reject" and ("NEW" in cats or "SECURITY_CHANGED" in cats):
            _add(key, "risk", c,
                 f"原因：{(c.get('recommendation_reason') or '')[:80]}")
            continue
        # —— 恢复（§五：独立于 Top Score；§二.3：默认 3 天冷却，可配置）——
        if at == "restore_candidate":
            note = _fb_suppressed(key, c)
            if note:
                suppressed["feedback"] += 1
                continue
            _add(key, "restore", c, "这是已有能力的恢复，不是发现新 Skill")
            continue
        # —— 建议更新 ——
        if at == "update_candidate":
            note = _fb_suppressed(key, c)
            if note:
                suppressed["feedback"] += 1
                continue
            _add(key, "update", c)
            continue
        # —— 建议替换（V1.3 §十七：External 合同已有该 action，日报不得丢） ——
        if at == "replacement_candidate":
            note = _fb_suppressed(key, c)
            if note:
                suppressed["feedback"] += 1
                continue
            if not _install_gate_ok(c):
                continue
            _add(key, "replace", c,
                 "已装里有与它同血缘/同职责的 Skill，External 层判定替换比新装更合适"
                 "（来源与血缘信息在技术详情里保留）")
            continue
        # —— 建议安装 ——
        if at == "new_install":
            note = _fb_suppressed(key, c)
            if note:
                suppressed["feedback"] += 1
                continue
            if not _install_gate_ok(c):
                continue
            bucket = "install_project" if _has_strong_project(c) else "install_gap"
            _add(key, bucket, c,
                 "" if bucket == "install_project"
                 else "补你现在没有/很弱的能力")
            continue
        # —— 继续观察（§三.4：只有变化事件值得占用日报）——
        if at == "watch" and c.get("recommendation") not in ("watch", "install_candidate"):
            continue
        if at == "watch":
            trigger = cats & WATCH_TRIGGERS
            first_daily = report_mode == "initial_baseline"
            if not trigger and not first_daily:
                # 设计决定：普通 watch 到期不自动重提（§三.4 长期 watch 不刷屏优先）；
                # 若要 watch 也参与 cooldown_reminder，去掉本 early-continue 即可。
                pv = shown.get(key)
                fb = feedback.get(key)
                fb_fresh = bool(pv and pv.get("date") and fb
                                and parse_date(fb.get("updated_at"))
                                and parse_date(fb["updated_at"])
                                > parse_date(pv["date"]))
                if not fb_fresh:                    # §B：反馈变化也是合法的再评估事件
                    suppressed["unchanged_watch"] += 1
                    continue
            note = _fb_suppressed(key, c)
            if note:
                suppressed["feedback"] += 1
                continue
            bucket = ("watch_rising" if trigger & {"RISING", "NEW", "UPDATED"}
                      or _has_strong_project(c) else "watch_normal")
            extra = ""
            if trigger and _has_strong_project(c):
                extra = "你当前的项目今天用上了它的能力（值得重看）"
            _add(key, bucket, c, extra)

    # —— V1.3 §四/§五/§十三：候选消失 → NO_LONGER_RELEVANT（只对用户关心过的可见） ——
    removed_important = set()
    removed_info = inp.get("removed") or {}
    for key, b in sorted(removed_info.items()):
        pv = shown.get(key)
        # §五：「用户真的关心过」= 曾实际展示过（含曾以 install/update/restore/risk 身份
        # 展示），或用户反馈记录过它。§二十五 64 明确：从未展示的 backlog（哪怕曾是
        # new_install）消失时只机器计数——两个合同只有这一种同时满足的读法。
        important = bool(pv) or (key in feedback)
        if not important:
            suppressed["no_longer_relevant_unseen"] += 1
            continue
        removed_important.add(key)
        prev_action = {"new_install": "建议安装", "update_candidate": "建议更新",
                       "restore_candidate": "建议恢复",
                       "replacement_candidate": "建议替换"}.get(
                           (pv or {}).get("action_type") or b.get("action_type"),
                           "曾进入日报")
        sec_sig = (b.get("security_signature") or "").split("|")[0]
        name = b.get("skill_name") or key.split("/")[-1]
        synth = {
            "canonical_key": key, "skill_name": name,
            "bucket": "risk", "action": "risk", "priority": PRIORITY["risk"],
            "one_line_explanation": "",
            "source_description_excerpt": "",
            "why_today": "候选状态发生变化，不是重复提醒",
            "report_reason_type": "no_longer_relevant",
            "material_today_evidence": ["no_longer_relevant"],
            "matched_project": "", "fills_gap": "",
            "installed_overlap": "",
            "security_status": SEC_LABEL.get(sec_sig, "未扫描"),
            "source": b.get("source") or "/".join(key.split("/")[:2]),
            "repo": f"https://github.com/{'/'.join(key.split('/')[:2])}",
            "skill_path": "", "source_url": b.get("source_url") or "",
            "source_tier": None, "personalized_score": b.get("score"),
            "action_type": b.get("action_type"),
            "delta_cats": ["NO_LONGER_RELEVANT"],
            "feedback_effect": "", "feedback_reason": "",
            "extra_note": (f"之前的动作：{prev_action}；现在：不再进入当前候选池。"
                           "原因：外部候选池已不再包含它，暂不建议继续操作。"),
            "family": "—", "display_family_key": f"{_norm_name(name)}#removed",
            "verdict_rank": VERDICT_RANK.get(sec_sig, 9),
            "affected_by_conflict": False, "alternatives": [],
        }
        synth["one_line_explanation"] = _zh_one_line(synth)
        items.append(synth)
    inp["removed_important"] = removed_important

    # —— 内部事件计数 + 引擎换代检测（§六：不作外部新闻） ——
    for key, cats in deltas.items():
        for k in internal_counts:
            if k in cats:
                internal_counts[k] += 1
    prev_ver = ((daily_snap.get("external_snapshot_version") or {})
                .get("candidates_version"))
    cur_ver = inp["cands_doc"].get("version")
    if (prev_ver and str(prev_ver) != str(cur_ver)) or inp.get("first_external"):
        internal_counts["SYSTEM_REBASELINE"] = max(1, internal_counts["SYSTEM_REBASELINE"])

    # —— §十八 7：确定性排序（优先级 → 安全 verdict → 来源 tier → 分数 → key）——
    items.sort(key=lambda x: (x["priority"], x["verdict_rank"],
                               x["source_tier"] if x["source_tier"] is not None else 9,
                               -(x["personalized_score"] or 0), x["canonical_key"]))
    # —— §七 功能完全重复：PRIMARY + alternatives ——
    kept, by_fam = [], {}
    for it in items:
        dup = by_fam.get(it["display_family_key"])
        if dup is not None:
            dup["alternatives"].append({
                "canonical_key": it["canonical_key"], "source": it["source"],
                "score": it["personalized_score"], "security": it["security_status"]
                .split("（")[0], "source_tier": it["source_tier"]})
            suppressed["functional_duplicate"] += 1
            continue
        by_fam[it["display_family_key"]] = it
        kept.append(it)
    # —— §八 能力族配额（只作用于 install / watch；restore/update/risk 豁免）——
    fam_cnt, final = {}, []
    for it in kept:
        if it["action"] == "install":
            cap = cfg["max_install_per_capability_family"]
        elif it["action"] == "watch":
            cap = cfg["max_watch_per_capability_family"]
        else:
            final.append(it)
            continue
        used = fam_cnt.get(it["family"], 0)
        if used >= cap:
            suppressed["capability_family_quota"] += 1
            continue
        fam_cnt[it["family"]] = used + 1
        final.append(it)
    return final, suppressed, internal_counts


# ==========================================================================
# 渲染（§十/§十一/§十二/§十三/§二十二：第一层只有用户语言）
# ==========================================================================
def _card(it):
    L = [f"### {it['skill_name']}", ""]
    L.append(f"一句话：{it['one_line_explanation']}")
    L.append("")
    L.append(f"{'为什么出现' if it.get('report_reason_type') == 'initial_baseline' else '为什么今天出现'}：{it['why_today']}")
    L.append("")
    if it["action"] in ("install", "watch"):
        L.append(f"对你有什么用：{it['fills_gap'] or '（见下方项目匹配）'}")
    if it["action"] == "replace":
        L.append("对你有什么用：替换掉现有的同类 Skill，而不是当新东西装。")
    if it["action"] == "restore":
        L.append("对你有什么用：把之前缺的那块能力补回来，不影响你现有配置。")
    if it["action"] == "update":
        L.append("对你有什么用：拿到上游的修复和新功能。")
    if it["action"] == "risk":
        L.append(f"为什么暂不建议：{it['extra_note']}")
    L.append("")
    L.append(f"对哪个项目有用：{it['matched_project'] or '没对上具体项目，属于通用能力'}")
    L.append("")
    L.append(f"和已装 Skill 是否重复：{it['installed_overlap']}")
    L.append("")
    L.append(f"安全：{it['security_status']}")
    L.append("")
    if it["action"] != "risk":
        L.append(f"动作：{ACTION_LABEL[it['action']]}"
                 "（引擎只给建议；请你在 Skill Manager 里人工确认后执行）")
    else:
        L.append("动作：暂不建议")
    L.append("")
    if it["alternatives"]:
        alts = "；".join(f"`{a['canonical_key']}`（T{a['source_tier']}，"
                         f"score={a['score']}，安全={a['security']}）"
                         for a in it["alternatives"])
        L.append(f"同功能的其它来源（不重复占版面，只推一个）：{alts}")
        L.append("")
    src = it["source_url"] or f"{it['repo']}/tree/main/{it['skill_path']}"
    L.append(f"来源：{src}")
    L.append("")
    if it["feedback_effect"]:
        L.append(f"你的反馈影响：{it['feedback_effect']}")
        L.append("")
    L.append("<details><summary>技术详情（可选）</summary>")
    L.append("")
    L.append(f"- canonical_key: `{it['canonical_key']}`｜source_tier=T{it['source_tier']}"
             f"｜score={it['personalized_score']}｜delta={','.join(it['delta_cats']) or '—'}")
    L.append(f"- repo={it['source']}｜skill_path={it['skill_path'] or '—'}"
             f"｜action_type={it['action_type']}")
    if it.get("source_description_excerpt"):
        L.append(f"- 原文描述：{it['source_description_excerpt']}")
    L.append("</details>")
    L.append("")
    return L


def render_report(today, items, suppressed, internal_counts, inp, cfg, report_mode):
    L = [f"# Skill 日报｜{today.isoformat()}", ""]
    if report_mode == "initial_baseline":
        L.append("> 首份基线日报：这是「当前最值得处理的几条」，不是今天新发生的变化；"
                 "从明天起只报变化和到期提醒。")
        L.append("")
    if not items:
        L.append("今天没有需要你处理的 Skill 变化。")
        L.append("")
    else:
        L.append(f"今天有 {len(items)} 件值得看。")
        L.append("")
        order = {"restore": "建议恢复", "risk": "暂不建议", "update": "建议更新",
                 "replace": "建议替换",
                 "install_project": "建议安装", "install_gap": "建议安装",
                 "watch_rising": "继续观察", "watch_normal": "继续观察"}
        groups, seen = [], set()
        for it in items:
            g = order[it["bucket"]]
            if g not in seen:
                seen.add(g)
                groups.append(g)
        for g in groups:
            L.append(f"## {g}")
            L.append("")
            for it in [x for x in items if order[x["bucket"]] == g]:
                L += _card(it)
                L.append("---")
                L.append("")
        if L and L[-1] == "":
            L.pop()
    conflict_names = _conflict_projects(inp["conflicts"])
    # §三：同日重跑幂等——「新增冲突」必须对比昨天（或更早）的已提醒集合，
    # 不能对比今天上午那次运行刚写的快照，否则提醒会在第二次运行时消失。
    prev_conflicts = set(inp.get("conflicts_notified")
                         if inp.get("conflicts_notified") is not None
                         else (inp["daily_snap"].get("conflicts") or []))
    new_conflicts = conflict_names - prev_conflicts
    affecting = any(it["affected_by_conflict"] for it in items)
    if conflict_names and (new_conflicts or affecting):
        who = "、".join(sorted(new_conflicts or conflict_names))
        L.append("数据提醒：")
        L.append(f"{who} 项目的描述和技术栈不一致，因此今天没有用冲突技术作为推荐依据。"
                 "（引擎不修改项目画像，只标记；请上游 Profile 修正）")
        L.append("")
    internal_total = sum(internal_counts.values())
    if cfg.get("show_internal_system_events") or (internal_total and items):
        L.append("## 今天不用处理的变化")
        L.append("")
        _foot = {"SYSTEM_REBASELINE": "系统重新建立基线", "METADATA_ENRICHED": "元数据补全",
                 "RECALCULATED": "引擎重算（系统内部）"}
        for k in ("SYSTEM_REBASELINE", "METADATA_ENRICHED", "RECALCULATED"):
            if internal_counts.get(k):
                L.append(f"- {_foot[k]}：{internal_counts[k]}")
        L.append("")
    sp = suppressed
    bl = inp.get("baseline_backlog") or {}
    if report_mode == "initial_baseline" and bl.get("total"):
        L.append(f"另外还有 {bl['total']} 条静态候选未展开"
                 f"（安装 {bl.get('install', 0)}／观察 {bl.get('watch', 0)} 等）。"
                 "它们不会在后续日报里自动轮播；需要时请查看完整候选清单。")
        L.append("")
    L.append(f"> 重复与去重：{sp['repeat_cooldown']} 条动作项在冷却期内不重复；"
             f"{sp['unchanged_watch']} 条无变化的观察项未重复；"
             f"{sp['functional_duplicate']} 条同功能重复来源并入 PRIMARY 的 alternatives；"
             f"{sp['capability_family_quota']} 条被能力族配额挡住（候选未删，仅不占版面）；"
             f"{sp['feedback']} 条被你的反馈规则压住；"
             f"{sp.get('baseline_backlog', 0)} 条未展示的静态 backlog 未轮播。")
    L.append("")
    L.append("> 引擎不安装 / 不删除 / 不升级任何 Skill；"
             "所有动作由你在 Skill Manager 人工确认。")
    L.append("")
    return "\n".join(L)


# ==========================================================================
# 主入口
# ==========================================================================
def generate(today=None, out_dir=None, quiet=False, snapshot_path=None,
             cands_doc=None, feedback=None, deltas=None):
    cfg = C.load_config()
    today = today or date.today()
    redirected = bool(out_dir and os.path.abspath(out_dir) != os.path.abspath(C.REPORTS_DIR))
    snap_path = snapshot_path or (
        os.path.join(out_dir, "state", "daily_snapshot.json")
        if redirected and out_dir else C.DAILY_SNAPSHOT_PATH)
    inp = load_inputs(today, snapshot_path=snap_path, cands_doc=cands_doc,
                      feedback=feedback, deltas=deltas)
    # §三 same-day rerun = idempotent：当天重跑沿用已存的 report_mode，
    # 不能因为上午自己写过快照就在下午把同一份日报抑制成 daily_delta。
    prev_rd = (inp["daily_snap"] or {}).get("report_date")
    if not prev_rd:
        report_mode = "initial_baseline"
    elif prev_rd == today.isoformat():
        report_mode = (inp["daily_snap"] or {}).get("report_mode") or "daily_delta"
    else:
        report_mode = "daily_delta"
    # §三：同一天重跑沿用当天写入的 conflicts_baseline（上午的提醒不会下午消失）
    ds = inp["daily_snap"] or {}
    if prev_rd == today.isoformat() and "conflicts_baseline" in ds:
        inp["conflicts_notified"] = ds["conflicts_baseline"]
    else:
        inp["conflicts_notified"] = ds.get("conflicts") or []
    items, suppressed, internal_counts = build_items(inp, cfg, report_mode)
    # V1.3 §十二/§十四：机器层事件类型与 risk_kind（用户桶不变，语义在机器层分清）
    _EVENT = {"initial_baseline": "baseline_view", "material_delta": "material_delta",
              "cooldown_reminder": "cooldown_reminder",
              "feedback_reentry": "feedback_reentry",
              "project_match_change": "project_match_change",
              "risk_change": "security_risk", "status_downgrade": "status_downgraded",
              "status_upgrade": "status_upgraded",
              "no_longer_relevant": "removed", "candidate_returned": "returned"}
    for x in items:
        x["event_type"] = _EVENT.get(x.get("report_reason_type"), "material_delta")
        if x["action"] == "risk":
            rt = x.get("report_reason_type")
            x["risk_kind"] = ("no_longer_relevant" if rt == "no_longer_relevant"
                              else "status_downgrade" if rt == "status_downgrade"
                              else "security" if "SECURITY_CHANGED" in x["delta_cats"]
                              else "source")
    shown = items[: int(cfg["max_daily_items"])]      # 先去重/配额，再截断（§九/§十八）

    # §二十四：生命周期统计（真实池 replacement 现为 0，也要有该字段）
    dl = inp["deltas"]
    lifecycle = {
        "removed_from_pool": len(inp.get("removed") or {}),
        "returned_to_pool": len(inp.get("returned") or {}),
        "status_downgraded": sum(1 for v in dl.values() if "STATUS_DOWNGRADED" in v),
        "status_upgraded": sum(1 for v in dl.values() if "STATUS_UPGRADED" in v),
        "replacement_candidates": sum(1 for c in inp["cands"]
                                      if c.get("action_type") == "replacement_candidate")}

    # §六/§二十六：backlog = 通过过滤但没进日报位的静态候选（只报数量，不轮播）
    backlog_by = {}
    for x in items[len(shown):]:
        backlog_by[x["action"]] = backlog_by.get(x["action"], 0) + 1
    inp["baseline_backlog"] = {"total": len(items) - len(shown), **backlog_by}

    # §十四：stale backlog / non-material 审计硬门（直接按最终 shown 复算，不手工声明）
    stale_backlog = non_material = 0
    if report_mode == "daily_delta":
        base_seen = inp.get("candidate_baseline") or {}
        prev_shown_keys = inp["daily_snap"].get("shown") or {}
        for it in shown:
            # V1.3 §三十一：生命周期事件是真实变化，不算 backlog 轮播
            cats_mat = set(it["delta_cats"]) & (MATERIAL_ALL | {"NO_LONGER_RELEVANT"})
            ev = it.get("material_today_evidence") or []
            if not cats_mat and not any(
                    str(e).startswith(("cooldown_due", "feedback_change")) for e in ev):
                non_material += 1
            if (it["canonical_key"] not in prev_shown_keys
                    and it["canonical_key"] in base_seen and not cats_mat):
                stale_backlog += 1

    # §十七：unchanged_repeated_items 直接按上一日快照复算（硬门 = 0）
    prev_shown = inp["daily_snap"].get("shown") or {}
    prev_date = parse_date(inp["daily_snap"].get("report_date"))
    unchanged_repeated = 0
    if report_mode == "daily_delta" and prev_date and prev_date < today:
        byk = {c["canonical_key"]: c for c in inp["cands"]}
        for it in shown:
            pv = prev_shown.get(it["canonical_key"])
            if not pv or pv.get("date") == today.isoformat():
                continue
            src = byk.get(it["canonical_key"])
            if src is None or pv.get("action") != it["action"]:
                continue
            ext, proj, sec = _sigs(src)
            if (set(it["delta_cats"]) - set(pv.get("delta_cats") or [])) \
                    & MATERIAL_DELTA.get(it["action"], set()):
                continue                       # 明确新 Delta：允许的再提醒
            if (pv.get("external_signature") not in (None, "", ext)
                    or pv.get("matched_project_signature") not in (None, proj)
                    or pv.get("security_signature") not in (None, sec)):
                continue                       # 签名变化（含新项目命中 / 安全变化）
            fb = feedback_of(inp, it["canonical_key"])
            if fb and parse_date(fb.get("updated_at")) and \
                    parse_date(fb["updated_at"]) > prev_date:
                continue                       # 用户反馈导致的重新进入
            gap_d = C.days_between(parse_date(pv.get("date")), today)
            days_cfg = cfg.get(REPEAT_CFG_KEY.get(it["action"], "watch_repeat_days"), 7)
            if gap_d is not None and gap_d < days_cfg:
                unchanged_repeated += 1        # 冷却窗口内的无变化重复 = 违规

    report = render_report(today, shown, suppressed, internal_counts, inp, cfg,
                           report_mode)
    out_dir = out_dir or C.REPORTS_DIR
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, f"{today.isoformat()}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    def _cnt(b):
        return sum(1 for x in shown if x["bucket"].startswith(b))
    material_today = sum(1 for x in shown
                         if x["report_reason_type"] in
                         ("material_delta", "project_match_change", "risk_change"))
    static_actionables = sum(1 for c in inp["cands"] if (c.get("action_type") or "")
                             in ("new_install", "update_candidate", "restore_candidate"))
    delta_source = ("daily_candidate_baseline" if inp.get("candidate_baseline")
                    else ("external_snapshot_aux" if not inp.get("first_external")
                          else "none_first_run_zero_new"))
    prov = {
        "project_context": {
            "status": "inherited_from_external_v2.11",
            "evidence": "SKILL_CANDIDATES.json 的 local_projects/project_context_health"
                        "（引擎也直接从该文件读取）"},
        "installed_context": {
            "status": "inherited_from_external_v2.11",
            "evidence": "candidate.capability_gap_match / action_type / "
                        "personalized_reason（由 external 层读取冻结底座后嵌入）"},
        "external_candidates": {"status": "direct_loaded",
                                "logical_path": LOGICAL_PATHS["external_candidates"]},
        "external_delta_semantics": {"status": "reused_readonly_v2.11",
                                     "logical_path": LOGICAL_PATHS["external_delta_semantics"]},
        "feedback": {"status": "direct_loaded", "logical_path": LOGICAL_PATHS["feedback"]},
        "daily_delta_comparison": {
            "status": "primary_self_baseline",
            "logical_path": LOGICAL_PATHS["daily_state"],
            "external_snapshot_role": "first_run_aux_only"},
    }
    if os.environ.get("SKILL_DAILY_DEBUG_PATHS") == "1":   # 默认不写真实路径（§二十五）
        prov["runtime_debug_path"] = {"candidates": C.CANDIDATES_PATH,
                                      "snapshot": snap_path}
    machine = {
        "generated": today.isoformat(),
        "report_mode": report_mode,
        "summary": {"total_items": len(shown), "install": _cnt("install"),
                    "restore": _cnt("restore"), "update": _cnt("update"),
                    "replace": _cnt("replace"),
                    "watch": _cnt("watch"), "risk": _cnt("risk")},
        "items": [{k: v for k, v in x.items()
                   if k not in ("affected_by_conflict", "display_family_key",
                                "verdict_rank", "family")} for x in shown],
        "suppressed": dict(suppressed),
        "lifecycle": lifecycle,
        "unchanged_repeated_items": unchanged_repeated,
        "stale_backlog_items": stale_backlog,
        "non_material_daily_items": non_material,
        "delta_source": delta_source,
        "baseline_backlog": dict(inp["baseline_backlog"]),
        "pool_counts": {                                # §二十六：静态可装 ≠ 今天要提醒
            "current_static_actionables": static_actionables,
            "material_today_items": material_today,
            "baseline_backlog": inp["baseline_backlog"]["total"],
            "shown_items": len(shown)},
        "internal_events": internal_counts,
        "quota": {"max_daily_items": cfg["max_daily_items"],
                  "candidates_total": len(inp["cands"]),
                  "delta_items": len(inp["deltas"]),
                  "actionable_pool": len(items)},
        "input_provenance": prov,
        "external_resolution": {                       # V1.4 §六：实际解析布局如实记录
            "mode": C.EXTERNAL_RESOLUTION_MODE,
            "env_override_used": "yes" if os.environ.get("EXTERNAL_INTELLIGENCE_ROOT")
                                 else "no"},
        "engine": {"name": ENGINE_NAME, "version": ENGINE_VERSION,
                   "auto_install": False, "language": cfg.get("language"),
                   "external_candidates_version": inp["cands_doc"].get("version")},
    }
    ctx_path = (os.path.join(out_dir, "DAILY_REPORT_CONTEXT.json")
                if out_dir != C.REPORTS_DIR else C.CONTEXT_OUT_PATH)
    save_json(machine, ctx_path)

    snap_shown = dict(prev_shown)
    byk = {c["canonical_key"]: c for c in inp["cands"]}
    removed_info = inp.get("removed") or {}
    for x in shown:
        entry = {"date": today.isoformat(), "action": x["action"], "bucket": x["bucket"],
                 "action_type": x.get("action_type"),
                 "delta_cats": x["delta_cats"],
                 "report_reason_type": x["report_reason_type"],
                 "material_today_evidence": x["material_today_evidence"],
                 # §二十：消失当天还要能生成可读卡片——展示过的条目留最后可读信息
                 "skill_name": x["skill_name"], "source": x["source"],
                 "source_url": x["source_url"], "last_action": x["action"],
                 "last_reason": x["report_reason_type"]}
        src = byk.get(x["canonical_key"])
        if src is not None:
            ext, proj, sec = _sigs(src)
        else:                                   # V1.3 removed item：签名取消失前记录
            b = removed_info.get(x["canonical_key"]) or {}
            ext, proj, sec = (b.get("external_signature", ""),
                              b.get("matched_projects_signature", ""),
                              b.get("security_signature", ""))
        entry.update({"external_signature": ext, "matched_project_signature": proj,
                      "security_signature": sec})
        snap_shown[x["canonical_key"]] = entry
        # §六/§七：alternatives 与 PRIMARY 共享同一个版面位，提醒状态也必须一致，
        # 否则次日 PRIMARY 冷却后 duplicate 会「换皮重现」。
        for alt in x["alternatives"]:
            ac = byk.get(alt["canonical_key"])
            if not ac:
                continue
            aext, aproj, asec = _sigs(ac)
            snap_shown[alt["canonical_key"]] = {
                "date": today.isoformat(), "action": x["action"], "bucket": x["bucket"],
                "action_type": ac.get("action_type"), "external_signature": aext,
                "matched_project_signature": aproj, "security_signature": asec,
                "delta_cats": sorted(set(inp["deltas"].get(alt["canonical_key"]) or [])),
                "skill_name": ac.get("skill_name"),
                "source": f"{ac.get('owner')}/{ac.get('repo')}",
                "source_url": ac.get("source_url") or "",
                "shown_as_alternative_of": x["canonical_key"]}

    # §六/§七：tombstone 台账 —— removed 记录 / 通知一次 / returned 标记 / 保留期剪枝
    tombs = {k: dict(v) for k, v in (inp.get("tombstones") or {}).items()}
    imp = inp.get("removed_important") or set()
    cur_keys = set(byk)
    shown_keys = {x["canonical_key"] for x in shown}
    prev_rd_str = inp["daily_snap"].get("report_date")
    for key, b in removed_info.items():
        e = tombs.setdefault(key, {})
        # 来源可能是昨天的 baseline（b 即基线条目）或历史 tombstone
        src_b = b if "snap" in b else {
            "snap": b.get("last_snapshot"), "action_type": b.get("last_action_type"),
            "recommendation": b.get("last_recommendation")}
        disp = src_b or {}
        if not e.get("last_seen"):
            e["last_seen"] = (prev_rd_str or
                              (today - timedelta(days=1)).isoformat())
        e["last_action_type"] = disp.get("action_type", e.get("last_action_type"))
        e["last_recommendation"] = disp.get("recommendation", e.get("last_recommendation"))
        e["last_snapshot"] = disp.get("snap", e.get("last_snapshot"))
        last_disp = e.get("last_display") or {}
        for kk in ("skill_name", "source", "source_url", "score"):
            last_disp[kk] = last_disp.get(kk) or src_b.get(kk) or disp.get(kk)
        e["last_display"] = last_disp
        e["important"] = bool(e.get("important")) or key in imp
        if key in shown_keys or key not in imp:
            # 已通知（用户可见），或仅机器计数（unseen）→ 视为已处理，只通知一次
            if not e.get("notified_no_longer_relevant"):
                e["notified_no_longer_relevant"] = today.isoformat()
    for key in (inp.get("returned") or set()):
        if key in tombs and key in shown_keys:
            tombs[key]["returned_notified_date"] = today.isoformat()
    tombs = _tombstone_prune(tombs, cur_keys, today,
                             int(cfg.get("tombstone_retention_days", 30)))
    snap = {
        "report_date": today.isoformat(),
        "report_mode": report_mode,
        "shown_candidate_keys": [x["canonical_key"] for x in shown],
        "shown": snap_shown,
        "candidate_baseline": _build_candidate_baseline(inp["cands"]),   # §三：全池基线
        "candidate_tombstones": tombs,                                    # §六
        "action_types": machine["summary"],
        "last_feedback_state": {k: v.get("status") for k, v in inp["feedback"].items()},
        "external_snapshot_version": {
            "candidates_version": inp["cands_doc"].get("version"),
            "external_generated": inp["cands_doc"].get("generated")},
        "conflicts": sorted(_conflict_projects(inp["conflicts"])),
        "conflicts_baseline": sorted(set(inp.get("conflicts_notified") or [])),
    }
    save_json(snap, snap_path)
    if not quiet:
        print(f"daily report written: {report_path}")
        print(f"machine context written: {ctx_path}")
        print(f"[{report_mode}] shown {len(shown)} / pool {len(inp['cands'])} | "
              f"install={machine['summary']['install']} "
              f"restore={machine['summary']['restore']} "
              f"update={machine['summary']['update']} watch={machine['summary']['watch']} "
              f"risk={machine['summary']['risk']} | suppressed={machine['suppressed']} | "
              f"unchanged_repeated_items={unchanged_repeated} "
              f"stale_backlog_items={stale_backlog} "
              f"non_material_daily_items={non_material} delta_source={delta_source}")
    return machine, report, snap


def main():
    ap = argparse.ArgumentParser(description="Skill 日报引擎 V1.4（只读冻结输入，不安装）")
    ap.add_argument("--date", default=None, help="报告日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--out-dir", default=None, help="报告输出目录（默认 skill-daily/reports）")
    a = ap.parse_args()
    generate(date.fromisoformat(a.date) if a.date else None, a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
