#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill 日报引擎 V1.4 测试。

覆盖：V1 §二十 20 项意图 + V1.1 21~43 + V1.2 44~62 + V1.3 63~77 + V1.4 78~83
（External root resolver 四布局 subprocess 真 clean-room 测试 + 当前版本一致性审计）。
全部用合成输入在临时目录里跑（不碰真实 data/state 与 reports）；
真实数据的断言只读，或写 reports/repeat-audit-*.txt 审计文件。
SKIP 只允许 unittest.SkipTest（V1.1 §十一），真实计数。
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "scripts"))
import common as C                                     # noqa: E402
import build_daily as BD                               # noqa: E402

# §十二（V1.1）：真实池路径一律用 C.CANDIDATES_PATH（common 已适配开发仓与转送包两种布局）
REAL_CANDIDATES = C.CANDIDATES_PATH
TODAY = date(2026, 9, 24)

_COUNTS = {"pass": 0, "skip": 0, "fail": 0}
_FAILURES = []


def _run(fn):
    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
    except unittest.SkipTest as e:                 # §十一：真 SKIP 计 skip，不计 pass
        _COUNTS["skip"] += 1
        print(f"SKIP {fn.__name__}：{str(e)[:160]}")
        return
    except AssertionError as e:
        _COUNTS["fail"] += 1
        _FAILURES.append((fn.__name__, str(e)[:220]))
        print(f"FAIL {fn.__name__}：{str(e)[:220]}")
        return
    except Exception as e:
        _COUNTS["fail"] += 1
        _FAILURES.append((fn.__name__, f"{type(e).__name__}: {e}"[:220]))
        print(f"FAIL {fn.__name__}：{type(e).__name__}: {str(e)[:220]}")
        return
    _COUNTS["pass"] += 1
    for line in buf.getvalue().strip().splitlines():
        if line.strip():
            print(line)


CFG = dict(C.load_config())


def cand(key, name=None, *, action="watch", rec="watch", score=60.0,
         verdict="pass", risk="low", desc="Do something useful for the user.",
         owner=None, repo=None, needs=None, gap=None, sat=None, inc=None,
         prj=None, reason=None, rel="new_capability", src=True, path="skills/x"):
    owner = owner or (key.split("/")[0] if "/" in key else "o")
    repo = repo or (key.split("/")[1] if key.count("/") > 1 else "r")
    gm = {"matched_gap": gap, "capability_saturation": sat, "gap_level": sat or "none",
          "matched_needs": needs or [], "scope_unresolved": None,
          "product_internal_unresolved": None, "domain_mismatch_unresolved": [],
          "capability_evidence_context": {}}
    if inc:
        gm["incremental_subcapability"] = inc
        gm["incremental_evidence_level"] = {k: "confirmed_absent" for k in inc}
    c = {"canonical_key": key, "skill_name": name or key.split("/")[-1],
         "owner": owner, "repo": repo, "path": path, "description": desc,
         "recommendation": rec, "score": score, "security": {"verdict": verdict,
                                                             "risk_level": risk},
         "capability_gap_match": gm, "action_type": action,
         "installed_relationship": rel, "update_available": False,
         "source_url": f"https://github.com/{owner}/{repo}/tree/main/{path}",
         "source_tier": 1,
         "personalized_reason": reason or {},
         "project_match": {"matched_needs": [n["need"] for n in (needs or [])],
                           "matched_projects": prj or []}}
    return c


def inp(cands, deltas=None, feedback=None, daily_snap=None, conflicts=None,
        first_external=False, baseline=None):
    return dict(cands=cands, cands_doc={"version": 11, "candidates": cands},
                deltas=deltas or {}, feedback=feedback or {},
                daily_snap=daily_snap or {}, conflicts=conflicts or {"conflict_count": 0},
                candidate_baseline=baseline or {},
                first_external=first_external, today=TODAY)


def run_items(inputs, mode="daily_delta"):
    return BD.build_items(inputs, CFG, mode)


def _keys(items):
    return [x["canonical_key"] for x in items]


def _shown_entry(c, when, action, proj_sig=None):
    """V1.1 §四：构造带签名的上一日 shown 条目（默认=与当前一致，即“无变化”）。"""
    ext, proj, sec = BD._sigs(c)
    return {c["canonical_key"]: {
        "date": when, "action": action, "bucket": action,
        "action_type": c.get("action_type"), "external_signature": ext,
        "matched_project_signature": proj if proj_sig is None else proj_sig,
        "security_signature": sec}}


def _snap(entries, report_date="2026-09-23"):
    return {"report_date": report_date, "shown": entries}


def _gen(tmp, day, cands=None, deltas=None, feedback=None):
    """合成用例：注入 cands；deltas=None → 走引擎 V1.2 自有 candidate_baseline 比较。"""
    kw = dict(out_dir=tmp, quiet=True)
    if cands is not None:
        kw["cands_doc"] = {"version": 11, "candidates": cands}
    if deltas is not None:
        kw["deltas"] = deltas
    if feedback is not None:
        kw["feedback"] = feedback
    return BD.generate(day, **kw)


def _inst(i, gap=None):
    return cand(f"o/r/ins{i}", action="new_install", rec="install_candidate",
                gap=gap or f"f{i}", score=90 - i)


def _require_real():
    if not os.path.exists(REAL_CANDIDATES):
        raise unittest.SkipTest(f"真实候选池缺失：{REAL_CANDIDATES}")


# ---------- 1-4：0 变化 / NEW install / restore / update ----------
def test_t1_zero_change_day():
    a = cand("o/r/old-watch", action="watch")
    items, sup, _ic = run_items(inp([a], daily_snap=_snap(_shown_entry(a, "2026-09-23", "watch"))))
    assert not items, items
    assert sup["unchanged_watch"] == 1
    report = BD.render_report(TODAY, items, sup, {}, inp([a]), CFG, "daily_delta")
    assert "今天没有需要你处理的 Skill 变化" in report
    print("PASS 1：今日 0 变化 → 明确“无需要处理变化”，不重复 Top30")


def test_t2_new_install_candidate():
    c = cand("o/r/nice", action="new_install", rec="install_candidate",
             reason={"matched_project": "proj-a（match=40）", "fills_gap": "补 mobile_qa"})
    items, _s, _i = run_items(inp([c], deltas={"o/r/nice": ["NEW"]}))
    assert items and items[0]["action"] == "install"
    assert items[0]["report_reason_type"] == "material_delta"      # V1.2 §十二
    r = BD.render_report(TODAY, items, _s, _i, inp([c]), CFG, "daily_delta")
    assert "## 建议安装" in r and "proj-a" in r
    print("PASS 2：NEW install candidate → 建议安装（material_delta）")


def test_t3_restore_not_new():
    c = cand("stablyai/orca/computer-use", action="restore_candidate", rec="watch",
             score=40.0)
    items, _s, _i = run_items(inp([c], deltas={"stablyai/orca/computer-use": ["NEW"]}))
    assert items[0]["action"] == "restore", items
    assert "不是新 Skill" in BD._zh_one_line(items[0])
    r = BD.render_report(TODAY, items, _s, _i, inp([c]), CFG, "daily_delta")
    assert "## 建议恢复" in r and "发现一个新的" not in r
    assert "不是新 Skill" in r
    print("PASS 3：restore_candidate → 恢复/修复，低分也进（独立于 Top Score）")


def test_t4_update_lineage():
    c = cand("o/r/updatable", action="update_candidate", rec="watch")
    items, _s, _i = run_items(inp([c], deltas={"o/r/updatable": ["UPDATED"]}))
    assert items[0]["action"] == "update"
    r = BD.render_report(TODAY, items, _s, _i, inp([c]), CFG, "daily_delta")
    assert "## 建议更新" in r
    print("PASS 4：update_candidate（血缘确认 + UPDATED）→ 建议更新")


# ---------- 5-7：安全变化 / METADATA_ENRICHED / SYSTEM_REBASELINE ----------
def test_t5_security_changed_block():
    c = cand("o/r/risky", verdict="block", risk="high", action="watch", rec="reject")
    items, _s, _i = run_items(inp([c], deltas={"o/r/risky": ["SECURITY_CHANGED"]}))
    assert items and items[0]["action"] == "risk"
    assert items[0]["report_reason_type"] == "risk_change"        # §十二
    assert items[0]["priority"] == BD.PRIORITY["risk"]
    print("PASS 5：SECURITY_CHANGED→block 高优先级提示（risk_change）")


def test_t6_metadata_enriched_not_shown():
    c = cand("o/r/quiet", action="watch")
    items, sup, _i = run_items(
        inp([c], deltas={"o/r/quiet": ["METADATA_ENRICHED"]},
            daily_snap=_snap(_shown_entry(c, "2026-09-23", "watch"))))
    assert not items, items
    assert sup["metadata_only"] == 1
    print("PASS 6：METADATA_ENRICHED 默认不进用户日报")


def test_t7_rebaseline_not_external_news():
    snap = {"shown": {}, "report_date": "2026-09-23",
            "external_snapshot_version": {"candidates_version": 10}}
    c = cand("o/x/restoreme", action="restore_candidate")
    items, _s, ic = run_items(inp([c], deltas={"o/x/restoreme": ["NEW"]},
                                 daily_snap=snap, first_external=False))
    assert ic["SYSTEM_REBASELINE"] == 1, ic
    r = BD.render_report(TODAY, items, _s, ic, inp([c], daily_snap=snap), CFG, "daily_delta")
    assert "今天不用处理的变化" in r and "系统重新建立基线：1" in r
    assert "## 外部更新" not in r
    print("PASS 7：SYSTEM_REBASELINE 只作内部脚注，不冒充外部变化")


# ---------- 8-9：watch 冷却 / 新项目匹配重新出现 ----------
def test_t8_watch_cooldown():
    c = cand("o/r/w1", action="watch")
    for gap_days in range(1, CFG["watch_repeat_days"]):
        d = (TODAY - timedelta(days=gap_days)).isoformat()
        items, sup, _i = run_items(
            inp([c], daily_snap=_snap(_shown_entry(c, d, "watch"))))
        assert not items, (gap_days, items)
        assert sup["unchanged_watch"] == 1
    snap = _snap(_shown_entry(c, "2026-09-10", "watch"))   # 14 天前
    items, sup, _i = run_items(inp([c], daily_snap=snap))
    # 冷却到期但今天也没有触发事件 → 仍不刷屏（watch 需触发）
    assert not items
    print("PASS 8：watch 无变化 7 天内不重复（周期取 config，未硬编码）")


def test_t9_watch_new_project_match_reappears():
    c = cand("o/r/w2", action="watch",
             prj=[{"project": "proj-new", "match_score": 40,
                   "direct_evidence_kinds": ["positioning"]}])
    snap = _snap(_shown_entry(c, "2026-09-23", "watch"))
    items, sup, _i = run_items(
        inp([c], deltas={"o/r/w2": ["MATCH_CHANGED"]}, daily_snap=snap))
    assert items and items[0]["action"] == "watch"
    assert "与你的匹配度有变化" in items[0]["why_today"]
    assert items[0]["bucket"] == "watch_rising", items[0]["bucket"]
    assert "用上了它的能力" in items[0]["extra_note"]
    print("PASS 9：watch 新项目匹配/变化 → 可重新出现，且按高优先观察处理")


# ---------- 10-12：反馈 ignored / poor / useful ----------
def test_t10_feedback_ignored():
    c = cand("o/r/ign", action="watch")
    fb = {"o/r/ign": {"status": "ignored", "updated_at": "2026-09-22", "user_note": ""}}
    items, sup, _i = run_items(inp([c], deltas={"o/r/ign": ["RISING"]}, feedback=fb))
    assert not items and sup["feedback"] == 1
    fb2 = {"o/r/ign": {"status": "ignored", "updated_at": "2026-09-01", "user_note": ""}}
    items2, _s, _i2 = run_items(inp([c], deltas={"o/r/ign": ["RISING"]}, feedback=fb2))
    assert items2
    print("PASS 10：feedback=ignored 冷却期内不立即重复（触发事件也要等过期）")


def test_t11_feedback_poor_family_demote():
    poor_src = cand("poor/repo/p", action="watch", gap="devops")
    fam_need = [{"need": "mobile-qa", "weight": 27, "evidence_level": "primary"}]
    same = cand("poor/repo/kin", action="watch", needs=fam_need, gap="mobile_qa")
    other = cand("fresh/repo/n", action="watch", needs=fam_need, gap="api_design")
    fb = {"poor/repo/p": {"status": "poor", "updated_at": "2026-09-20", "user_note": ""}}
    deltas = {k: ["RISING"] for k in ["poor/repo/kin", "fresh/repo/n", "poor/repo/p"]}
    items, _s, _i = run_items(inp([poor_src, same, other], deltas=deltas, feedback=fb))
    order = _keys(items)
    assert order.index("fresh/repo/n") < order.index("poor/repo/kin"), order
    kin = next(x for x in items if x["canonical_key"] == "poor/repo/kin")
    assert "不好用" in kin["feedback_effect"] and kin["feedback_reason"]
    print("PASS 11：feedback=poor → 同功能族/同来源路线降级，且给得出 feedback_reason")


def test_t12_feedback_useful_boost():
    useful = cand("good/repo/u", action="watch", gap="ui_design")
    kin = cand("good/repo/k", action="watch", gap="ui_design")
    rival = cand("other/repo/k", action="watch", gap="devops")
    fb = {"good/repo/u": {"status": "useful", "updated_at": "2026-09-20", "user_note": ""}}
    deltas = {k: ["RISING"] for k in ["good/repo/k", "other/repo/k", "good/repo/u"]}
    items, _s, _i = run_items(inp([useful, kin, rival], deltas=deltas, feedback=fb))
    order = _keys(items)
    assert order.index("good/repo/k") < order.index("other/repo/k"), order
    assert any("好用" in x["feedback_effect"] for x in items)
    print("PASS 12：feedback=useful → 同来源/同能力路线提升展示优先级")


# ---------- 13-15：冲突画像 / scope 未解除 / strong 无增量 ----------
def test_t13_conflict_suppression():
    conflicts = {"conflict_count": 1, "conflicts": [
        {"project": "proj-x", "reason": "description-tech mismatch",
         "description_tech": ["expo"], "declared_tech": ["nextjs"],
         "suppressed_strong_tech": ["Next.js", "PWA"]}]}
    c = cand("o/r/nextkit", action="new_install", rec="install_candidate",
             prj=[{"project": "proj-x", "match_score": 30,
                   "direct_evidence_kinds": ["positioning"]}])
    inputs = inp([c], deltas={"o/r/nextkit": ["NEW"]}, conflicts=conflicts)
    items, _s, _i = run_items(inputs)
    assert items and items[0]["affected_by_conflict"]
    r = BD.render_report(TODAY, items, _s, _i, inputs, CFG, "daily_delta")
    assert "数据提醒" in r and "proj-x" in r
    print("PASS 13：project_context_conflict → 不静默；冲突项目单独出数据提醒")


def test_t14_unresolved_scope_not_in_install():
    c = cand("hf/skills/spaces", action="new_install", rec="install_candidate")
    c["capability_gap_match"]["scope_unresolved"] = "huggingface-spaces"
    items, _s, _i = run_items(inp([c], deltas={"hf/skills/spaces": ["NEW"]}))
    assert not items
    c2 = cand("ms/skills/azdeploy", action="new_install", rec="install_candidate")
    c2["capability_gap_match"]["domain_mismatch_unresolved"] = ["azure"]
    items2, _s2, _i2 = run_items(inp([c2], deltas={"ms/skills/azdeploy": ["NEW"]}))
    assert not items2
    print("PASS 14：product/domain 未解除 → 不进建议安装（日报层保险带）")


def test_t15_strong_without_incremental_not_install():
    c = cand("o/r/design-clone", action="new_install", rec="install_candidate",
             sat="strong")
    items, _s, _i = run_items(inp([c], deltas={"o/r/design-clone": ["NEW"]}))
    assert not items, items
    c["capability_gap_match"]["incremental_subcapability"] = ["accessibility_audit"]
    c["personalized_reason"] = {"incremental_over_installed": "新子能力 accessibility_audit"}
    items2, _s2, _i2 = run_items(inp([c], deltas={"o/r/design-clone": ["NEW"]}))
    assert items2
    print("PASS 15：strong 饱和无增量 → 不进建议安装；带增量说明才放行")


# ---------- 16-18：不凑数 / 超 10 取前 10 / 来源可追溯 ----------
def test_t16_no_padding():
    c = cand("o/r/only1", action="new_install", rec="install_candidate", gap="g1")
    items, _s, _i = run_items(inp([c], deltas={"o/r/only1": ["NEW"]}))
    r = BD.render_report(TODAY, items[:10], _s, _i, inp([c]), CFG, "daily_delta")
    assert "今天有 1 件值得看" in r
    assert r.count("### ") == 1
    print("PASS 16：Top 不足 10 → 如实 1 条，不凑数")


def test_t17_max_10_priority():
    cands = [cand(f"o/r/i{i}", action="new_install", rec="install_candidate",
                  score=70 - i, gap=f"g{i}",
                  reason={"matched_project": "p（match=40）"} if i == 0 else {})
             for i in range(14)]
    cands.append(cand("stablyai/orca/restore-x", action="restore_candidate", score=30))
    deltas = {c["canonical_key"]: ["NEW"] for c in cands}
    items, _s, _i = run_items(inp(cands, deltas=deltas))
    shown = items[:10]
    assert len(items) == 15 and len(shown) == 10, (len(items), len(shown))
    assert shown[0]["canonical_key"] == "stablyai/orca/restore-x"      # P0 恢复压过高分安装
    assert all(x["bucket"].startswith("install") or x["bucket"] == "restore"
               for x in shown)
    print("PASS 17：超过 10 → 按优先级取最高 10 条（restore 不被高分安装挤掉）")


def test_t18_source_traceable():
    c = cand("vercel-labs/agent-skills/react-native-skills", action="new_install",
             rec="install_candidate", gap="g1")
    items, _s, _i = run_items(inp([c], deltas={"vercel-labs/agent-skills/react-native-skills": ["NEW"]}))
    it = items[0]
    assert it["source_url"].startswith("https://github.com/vercel-labs/agent-skills")
    assert it["repo"] and it["skill_path"]
    r = BD.render_report(TODAY, items, _s, _i, inp([c]), CFG, "daily_delta")
    assert "来源：https://github.com/" in r and "来源：GitHub\n" not in r
    print("PASS 18：每条推荐都有可点回原处的来源（repo+path/source_url）")


# ---------- 19：无自动安装 ----------
def test_t19_no_auto_install():
    src = open(os.path.join(BASE, "scripts", "build_daily.py"), encoding="utf-8").read()
    fb = open(os.path.join(BASE, "scripts", "feedback.py"), encoding="utf-8").read()
    cm = open(os.path.join(BASE, "scripts", "common.py"), encoding="utf-8").read()
    for blob in (src, fb, cm):
        for token in ("subprocess", "os.system", "pip install", "npm install",
                      "skill-manager install", "shutil.rmtree"):
            assert token not in blob, token
    cfg = C.load_config()
    assert cfg["auto_install"] is False
    print("PASS 19：引擎无任何安装/删除/升级调用；auto_install 恒为 false")


# ---------- V1.1 §十三 20A/20B/20C：确定性三个独立测试 ----------
def test_t20a_deterministic_same_initial_state():
    _require_real()
    t1, t2 = tempfile.mkdtemp(prefix="daily-detA1-"), tempfile.mkdtemp(prefix="daily-detA2-")
    try:
        m1, r1, _s1 = _gen(t1, TODAY)
        m2, r2, _s2 = _gen(t2, TODAY)
        assert m1["report_mode"] == m2["report_mode"] == "initial_baseline"
        assert json.dumps(m1["items"], sort_keys=True) == \
            json.dumps(m2["items"], sort_keys=True)
        assert r1 == r2
        assert m1["summary"]["total_items"] > 0
        print(f"PASS 20A：两个全新相同目录同日期 → 真实池 Top {m1['summary']['total_items']} "
              "条 items 与 report 逐字节一致")
    finally:
        shutil.rmtree(t1, ignore_errors=True)
        shutil.rmtree(t2, ignore_errors=True)


def test_t20b_same_day_idempotence():
    _require_real()
    tmp = tempfile.mkdtemp(prefix="daily-detB-")
    try:
        m1, r1, _s1 = _gen(tmp, TODAY)
        m2, r2, _s2 = _gen(tmp, TODAY)
        assert m1["summary"]["total_items"] > 0
        assert m2["summary"]["total_items"] == m1["summary"]["total_items"], \
            "同一天重跑内容被自我抑制（§三违例）"
        assert json.dumps(m1["items"], sort_keys=True) == \
            json.dumps(m2["items"], sort_keys=True)
        assert r1 == r2
        assert m1["suppressed"]["repeat_cooldown"] == 0
        print("PASS 20B：同目录同日重跑 = 幂等")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t20c_next_day_no_repeat():
    tmp = tempfile.mkdtemp(prefix="daily-detC-")
    try:
        cands = [_inst(1, "ga"), _inst(2, "gb"),
                 cand("o/r/upd", action="update_candidate", rec="watch", gap="gc"),
                 cand("stablyai/orca/computer-use", action="restore_candidate", gap="gd"),
                 cand("o/r/wtch", action="watch", gap="ge")]
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        m2, r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), cands)
        assert m1["report_mode"] == "initial_baseline" and m1["summary"]["total_items"] == 5
        assert m2["report_mode"] == "daily_delta"
        assert m2["summary"]["total_items"] == 0, _keys(m2["items"])
        assert "今天没有需要你处理的 Skill 变化" in r2
        assert m2["suppressed"]["repeat_cooldown"] == 4          # 2 install + 1 update + 1 restore
        assert m2["suppressed"]["unchanged_watch"] == 1
        print("PASS 20C：下一天无变化 → 0 条重复（cooldown 全接管）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- V1.1 §十九 21-28：重复抑制 ----------
def test_t21_first_day_install_shown():
    c = cand("o/r/n1", action="new_install", rec="install_candidate", gap="g1")
    items, sup, _i = run_items(inp([c]), mode="initial_baseline")
    assert items and sup["repeat_cooldown"] == 0
    print("PASS 21：首日 new_install 显示")


def test_t22_install_no_repeat_next_day():
    c = cand("o/r/n2", action="new_install", rec="install_candidate", gap="g1")
    snap = _snap(_shown_entry(c, "2026-09-23", "install"))
    items, sup, _i = run_items(inp([c], daily_snap=snap))
    assert not items, items
    assert sup["repeat_cooldown"] == 1
    print("PASS 22：第二天无变化 → 同一 install 不重复（install_repeat_days=7）")


def test_t23_install_repeat_days_expiry():
    c = cand("o/r/n3", action="new_install", rec="install_candidate", gap="g1")
    within = _snap(_shown_entry(c, (TODAY - timedelta(days=6)).isoformat(), "install"))
    items, sup, _i = run_items(inp([c], daily_snap=within))
    assert not items and sup["repeat_cooldown"] == 1
    past = _snap(_shown_entry(c, (TODAY - timedelta(days=7)).isoformat(), "install"))
    items2, sup2, _i2 = run_items(inp([c], daily_snap=past))
    assert items2 and sup2["repeat_cooldown"] == 0
    assert items2[0]["report_reason_type"] == "cooldown_reminder"    # §十二
    print("PASS 23：install_repeat_days 到期 → cooldown_reminder 再次提醒")


def test_t24_update_no_repeat():
    c = cand("o/r/u1", action="update_candidate", rec="watch", gap="g1")
    snap = _snap(_shown_entry(c, "2026-09-23", "update"))
    items, sup, _i = run_items(inp([c], daily_snap=snap))
    assert not items and sup["repeat_cooldown"] == 1
    print("PASS 24：update 第二天无变化不重复")


def test_t25_restore_within_repeat_days():
    c = cand("stablyai/orca/computer-use", action="restore_candidate", gap="g1")
    snap = _snap(_shown_entry(c, "2026-09-22", "restore"))       # 2 天前，< 3
    items, sup, _i = run_items(inp([c], daily_snap=snap))
    assert not items and sup["repeat_cooldown"] == 1
    print("PASS 25：restore 在 restore_repeat_days=3 内不重复")


def test_t26_restore_expiry_realerts():
    c = cand("stablyai/orca/computer-use", action="restore_candidate", gap="g1")
    snap = _snap(_shown_entry(c, "2026-09-21", "restore"))       # 3 天前 = 到期
    items, sup, _i = run_items(inp([c], daily_snap=snap))
    assert items and sup["repeat_cooldown"] == 0
    print("PASS 26：restore 到期重新提醒")


def test_t27_security_changed_breaks_cooldown():
    c = cand("o/r/u2", action="update_candidate", rec="watch", gap="g1")
    snap = _snap(_shown_entry(c, "2026-09-23", "update"))
    items, sup, _i = run_items(
        inp([c], deltas={"o/r/u2": ["SECURITY_CHANGED"]}, daily_snap=snap))
    assert items and items[0]["action"] == "update"
    assert sup["repeat_cooldown"] == 0
    tmp = tempfile.mkdtemp(prefix="daily-persist-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, [c], deltas={c["canonical_key"]: ["NEW"]})
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [c],
                            deltas={c["canonical_key"]: ["NEW"]})
        assert m1["summary"]["total_items"] == 1
        assert m2["summary"]["total_items"] == 0, _keys(m2["items"])
        rz = cand("o/r/rz", action="reject", rec="reject", verdict="block", risk="high")
        t2 = tempfile.mkdtemp(prefix="daily-persist-rz-")
        try:
            n1, _q1, _w1 = _gen(t2, TODAY, [rz], deltas={rz["canonical_key"]: ["NEW"]})
            n2, _q2, _w2 = _gen(t2, TODAY + timedelta(days=1), [rz],
                                deltas={rz["canonical_key"]: ["NEW"]})
            assert n1["summary"]["risk"] == 1
            assert n2["summary"]["risk"] == 0, _keys(n2["items"])
        finally:
            shutil.rmtree(t2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS 27：SECURITY_CHANGED 突破冷却；持续存在的同一事件（含旧风险）不天天突破")


def test_t28_new_matched_project_breaks_cooldown():
    c = cand("o/r/n4", action="new_install", rec="install_candidate", gap="g1",
             prj=[{"project": "proj-new", "match_score": 35,
                   "direct_evidence_kinds": ["positioning"]}])
    snap = _snap(_shown_entry(c, "2026-09-23", "install", proj_sig="proj-old"))
    items, sup, _i = run_items(inp([c], daily_snap=snap))
    assert items, (items, sup)
    assert sup["repeat_cooldown"] == 0
    assert items[0]["report_reason_type"] == "project_match_change"      # §十二
    print("PASS 28：新 matched_project（签名变化）突破冷却，reason=project_match_change")


# ---------- V1.1 §十九 32-35：展示去重与族配额 ----------
def test_t32_exact_functional_duplicate_primary_plus_alternatives():
    a = cand("github/awesome-copilot/webapp-testing", name="webapp-testing",
             action="new_install", rec="install_candidate", gap="testing_qa", score=75.0)
    b = cand("anthropics/skills/webapp-testing", name="webapp-testing",
             action="new_install", rec="install_candidate", gap="testing_qa", score=71.3,
             verdict="review_required")
    d = {"github/awesome-copilot/webapp-testing": ["NEW"],
         "anthropics/skills/webapp-testing": ["NEW"]}
    items, sup, _i = run_items(inp([a, b], deltas=d))
    assert len(items) == 1, items
    prim = items[0]
    assert prim["canonical_key"] == "github/awesome-copilot/webapp-testing"   # score 决胜
    assert [x["canonical_key"] for x in prim["alternatives"]] == \
        ["anthropics/skills/webapp-testing"]
    assert sup["functional_duplicate"] == 1
    r = BD.render_report(TODAY, items, sup, _i, inp([a, b]), CFG, "daily_delta")
    assert "同功能的其它来源" in r and "anthropics/skills/webapp-testing" in r
    tmp = tempfile.mkdtemp(prefix="daily-alt-cd-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, [a, b])
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [a, b])
        assert m1["summary"]["total_items"] == 1 and m1["items"][0]["alternatives"]
        assert m2["summary"]["total_items"] == 0, _keys(m2["items"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS 32：两个不同 repo 的 webapp-testing → 1 PRIMARY + alternatives，"
          "次日 alternative 不换皮重现")


def test_t33_capability_family_quota():
    cands = [cand(f"r{i}/skills/webapp-check{i}", action="new_install",
                  rec="install_candidate", gap="testing_qa", score=80 - i)
             for i in range(3)]
    d = {c["canonical_key"]: ["NEW"] for c in cands}
    items, sup, _i = run_items(inp(cands, deltas=d))
    assert len(items) == CFG["max_install_per_capability_family"] == 2, items
    assert sup["capability_family_quota"] == 1
    print("PASS 33：testing_qa 3 条 install → family 配额 2，第 3 条记 suppressed 不删除")


def test_t34_restore_update_exempt_from_quota():
    fam = "testing_qa"
    cands = [cand("stablyai/orca/computer-use", action="restore_candidate", gap=fam),
             cand("o/r/upd", action="update_candidate", rec="watch", gap=fam),
             cand("r1/s/e2e-a", action="new_install", rec="install_candidate",
                  gap=fam, score=80),
             cand("r2/s/e2e-b", action="new_install", rec="install_candidate",
                  gap=fam, score=70),
             cand("r3/s/e2e-c", action="new_install", rec="install_candidate",
                  gap=fam, score=60)]
    d = {c["canonical_key"]: ["NEW"] for c in cands}
    items, sup, _i = run_items(inp(cands, deltas=d))
    acts = sorted(x["action"] for x in items)
    assert acts == ["install", "install", "restore", "update"], acts
    assert sup["capability_family_quota"] == 1
    print("PASS 34：restore/update 不受 capability family quota 限制")


def test_t35_no_backfill_after_dedupe():
    a = cand("github/awesome-copilot/webapp-testing", name="webapp-testing",
             action="new_install", rec="install_candidate", gap="testing_qa", score=75.0)
    b = cand("anthropics/skills/webapp-testing", name="webapp-testing",
             action="new_install", rec="install_candidate", gap="testing_qa", score=71.0)
    d = cand("wshobson/agents/e2e-testing-patterns", action="new_install",
             rec="install_candidate", gap="testing_qa", score=65.0)
    dd = {k["canonical_key"]: ["NEW"] for k in (a, b, d)}
    items, sup, _i = run_items(inp([a, b, d], deltas=dd))
    assert len(items) == 2, _keys(items)               # 去重后只剩 2，不回填
    assert "anthropics/skills/webapp-testing" not in _keys(items)
    assert sup["functional_duplicate"] == 1 and sup["capability_family_quota"] == 0
    print("PASS 35：去重后不足 10 → 就发 2 条，绝不把重复项补回来")


# ---------- V1.1 §十九 36-37：测试合同 ----------
def test_t36_real_candidates_path_flat_layout():
    if not os.path.exists(REAL_CANDIDATES):
        raise unittest.SkipTest(f"真实候选池缺失：{REAL_CANDIDATES}")
    doc = json.load(open(REAL_CANDIDATES, encoding="utf-8"))
    assert doc.get("version") == 11 and doc.get("candidates")
    print(f"PASS 36：C.CANDIDATES_PATH → version={doc['version']}, "
          f"candidates={len(doc['candidates'])}（平铺/开发双布局自适应）")


def test_t37_true_skip_counted_as_skip():
    before = dict(_COUNTS)
    def _synthetic_skip():
        raise unittest.SkipTest("合成：真实数据缺失场景")
    _run(_synthetic_skip)
    assert _COUNTS["skip"] == before["skip"] + 1, _COUNTS
    assert _COUNTS["pass"] == before["pass"], "SKIP 被计成 PASS（§十违例）"
    assert _COUNTS["fail"] == before["fail"]
    print("PASS 37：真 SKIP 计入 skip，不再计入 pass（测试合同）")


# ---------- V1.1 §十九 38-43：机器合同 + 真实两日审计 ----------
def _machine_from_synthetic(tmp):
    c = cand("o/r/mc", action="new_install", rec="install_candidate", gap="mobile_qa",
             desc="Toolkit for interacting with and testing local web applications.")
    m, r, _s = _gen(tmp, TODAY, [c])
    return m, r


def test_t38_machine_one_line_is_chinese():
    tmp = tempfile.mkdtemp(prefix="daily-m38-")
    try:
        m, r = _machine_from_synthetic(tmp)
        it = m["items"][0]
        assert re.search(r"[\u4e00-\u9fff]", it["one_line_explanation"]), it
        assert f"一句话：{it['one_line_explanation']}" in r      # Markdown 与 machine 同源
        print(f"PASS 38：machine one_line_explanation 是中文用户文案且与 Markdown 同源")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t39_source_description_excerpt_kept():
    tmp = tempfile.mkdtemp(prefix="daily-m39-")
    try:
        m, _r = _machine_from_synthetic(tmp)
        it = m["items"][0]
        assert it["source_description_excerpt"].startswith("Toolkit for interacting")
        print("PASS 39：source_description_excerpt 保存原始英文摘录，与中文文案分离")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t40_input_provenance_honest_logical():
    tmp = tempfile.mkdtemp(prefix="daily-m40-")
    try:
        m, _r = _machine_from_synthetic(tmp)
        p = m["input_provenance"]
        assert p["project_context"]["status"] == "inherited_from_external_v2.11"
        assert p["installed_context"]["status"] == "inherited_from_external_v2.11"
        assert p["external_candidates"]["status"] == "direct_loaded"
        # V1.2 §二十四：只写 logical_path，不写开发机绝对路径
        assert p["external_candidates"]["logical_path"] == \
            "external-intelligence/SKILL_CANDIDATES.json"
        assert "path" not in p["external_candidates"]
        assert "path" not in p["feedback"] and "path" not in p["external_delta_semantics"]
        assert p["external_delta_semantics"]["status"] == "reused_readonly_v2.11"
        assert p["daily_delta_comparison"]["status"] == "primary_self_baseline"
        blob = json.dumps(p, ensure_ascii=False)
        assert "/Users/" not in blob and "/home/" not in blob
        print("PASS 40：input_provenance 如实区分且只含 logical_path")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t41_unchanged_repeated_items_zero():
    _require_real()
    tmp = tempfile.mkdtemp(prefix="daily-m41-")
    try:
        _gen(tmp, TODAY)
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1))
        assert m2["report_mode"] == "daily_delta"
        assert m2["unchanged_repeated_items"] == 0, m2["unchanged_repeated_items"]
        print(f"PASS 41：真实池次日 unchanged_repeated_items = 0（day2 shown={m2['summary']['total_items']}）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t42_suppressed_fields_and_report_mode():
    tmp = tempfile.mkdtemp(prefix="daily-m42-")
    try:
        m, _r = _machine_from_synthetic(tmp)
        for k in ("repeat_cooldown", "functional_duplicate", "capability_family_quota",
                  "unchanged_watch", "metadata_only", "feedback",
                  "baseline_backlog", "non_material_today"):          # V1.2 §二十八
            assert k in m["suppressed"], k
        assert m["report_mode"] == "initial_baseline"
        assert m["pool_counts"]["shown_items"] == m["summary"]["total_items"]
        print("PASS 42：suppressed 八字段齐全 + report_mode + pool_counts 四分法（§二十六）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t43_real_two_day_simulation_audit():
    """§二十（V1.1）+ §十五（V1.2）：真实池连跑两天，DAY2 必须 0 条（无变化时）。"""
    _require_real()
    tmp = tempfile.mkdtemp(prefix="daily-audit-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY)
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1))
        k1 = _keys(m1["items"])
        k2 = _keys(m2["items"])
        repeats = sorted(set(k1) & set(k2))
        L = ["Skill 日报引擎 V1.4：真实两日重复审计",
             "=" * 60,
             "DAY1: 2026-09-24",
             f"report_mode: {m1['report_mode']}",
             f"shown: {m1['summary']['total_items']}",
             "keys:"] + [f"  {k}" for k in k1] + ["",
             "DAY2: 2026-09-25",
             f"report_mode: {m2['report_mode']}",
             f"shown: {m2['summary']['total_items']}",
             "keys:"] + [f"  {k}" for k in k2] + ["",
             "REPEAT_AUDIT:",
             f"day1_day2_key_intersection: {len(repeats)}  {repeats}",
             f"unchanged_repeated_items: {m2['unchanged_repeated_items']}",
             f"stale_backlog_items: {m2['stale_backlog_items']}",
             f"non_material_daily_items: {m2['non_material_daily_items']}",
             f"cooldown_suppressed: {m2['suppressed']['repeat_cooldown']}",
             f"baseline_backlog_suppressed: {m2['suppressed']['baseline_backlog']}",
             ""]
        out = os.path.join(C.REPORTS_DIR, "repeat-audit-2026-09-24_25.txt")
        os.makedirs(C.REPORTS_DIR, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(L))
        assert m2["unchanged_repeated_items"] == 0
        assert m2["stale_backlog_items"] == 0 and m2["non_material_daily_items"] == 0
        assert len(k1) > 0
        print(f"PASS 43：真实两日模拟 → DAY1 {len(k1)} 条 / DAY2 {len(k2)} 条，"
              "unchanged_repeated_items=0，审计写入 reports/repeat-audit-2026-09-24_25.txt")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- V1.2 §二十九 44-47：基线/backlog ----------
def test_t44_first_run_no_new_storm_full_baseline():
    """44. 首次运行（真实环境，无自有基线）：不把全池判 NEW；candidate_baseline 全池建立。"""
    _require_real()
    tmp = tempfile.mkdtemp(prefix="daily-t44-")
    try:
        m, _r, s = _gen(tmp, TODAY)
        pool = m["quota"]["candidates_total"]
        assert m["report_mode"] == "initial_baseline"
        assert len(s["candidate_baseline"]) == pool, (len(s["candidate_baseline"]), pool)
        new_items = sum(1 for x in m["items"] if "NEW" in x["delta_cats"])
        assert new_items == 0, new_items                    # §七：没有 1106 个 NEW
        assert m["delta_source"] in ("none_first_run_zero_new", "external_snapshot_aux")
        print(f"PASS 44：首跑零 NEW 风暴；candidate_baseline 覆盖全池 {pool} 条")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t45_unshown_install_absent_next_day():
    """45+48+57+62：15 个静态 install，Day1 展示 10、backlog 5；Day2 无变化 → 0 条。"""
    cands = [_inst(i) for i in range(15)]
    tmp = tempfile.mkdtemp(prefix="daily-t45-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        assert m1["summary"]["total_items"] == 10
        assert m1["baseline_backlog"]["total"] == 5 and m1["baseline_backlog"]["install"] == 5
        m2, r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), cands)
        assert m2["summary"]["total_items"] == 0, _keys(m2["items"])   # §十五
        assert m2["suppressed"]["baseline_backlog"] == 5
        assert m2["suppressed"]["repeat_cooldown"] == 10
        assert m2["stale_backlog_items"] == 0                  # §十四
        assert m2["non_material_daily_items"] == 0
        assert "今天没有需要你处理的 Skill 变化" in r2           # §六十二
        print("PASS 45：未展示的 install 次日不出现；day2 shown=0；stale/non_material=0；"
              "文案明确无变化")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t46_unshown_watch_absent_next_day():
    """46. 初始基线未展示的 watch：Day2 无变化不得出现。"""
    cands = [cand(f"o/r/w{i}", action="watch", gap=f"wg{i}") for i in range(12)]
    tmp = tempfile.mkdtemp(prefix="daily-t46-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        assert m1["summary"]["watch"] == 10
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), cands)
        assert m2["summary"]["total_items"] == 0
        assert m2["suppressed"]["unchanged_watch"] == 12
        print("PASS 46：未展示 watch 次日不出现（无触发一律不轮播）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t47_backlog_not_rotated_by_repeat_days():
    """47+54+55：Day8 —— 已展示 install 到期可提醒（cooldown_reminder）；未展示 backlog 仍不出现。"""
    cands = [_inst(i) for i in range(15)]
    tmp = tempfile.mkdtemp(prefix="daily-t47-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        k1 = set(_keys(m1["items"]))
        m8, _r8, _s8 = _gen(tmp, TODAY + timedelta(days=7), cands)
        k8 = set(_keys(m8["items"]))
        assert k8 == k1, (k8 ^ k1)
        assert all(x["report_reason_type"] == "cooldown_reminder" for x in m8["items"])
        assert m8["suppressed"]["baseline_backlog"] == 5
        assert m8["stale_backlog_items"] == 0 and m8["unchanged_repeated_items"] == 0
        print("PASS 47：Day8 只轮换 cooldown_reminder（曾展示 10 条）；backlog 5 条仍不出现；"
              "shown-install repeat PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- V1.2 §二十九 49-53：daily_delta 真事件 ----------
def test_t49_new_candidate_only_appears():
    """49. Day1 有 A/B/C，Day2 池新增 D → 只有 D 出现（真 NEW）。"""
    abc = [cand(f"o/r/abc{i}", action="new_install", rec="install_candidate",
                gap=f"cg{i}") for i in range(3)]
    d = cand("o/r/newcomer", action="new_install", rec="install_candidate", gap="cg9")
    tmp = tempfile.mkdtemp(prefix="daily-t49-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, abc)
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), abc + [d])
        assert _keys(m2["items"]) == ["o/r/newcomer"], _keys(m2["items"])
        it = m2["items"][0]
        assert "NEW" in it["delta_cats"]
        assert it["report_reason_type"] == "material_delta"
        print("PASS 49：真新增候选 → 唯一出现者（delta_source=daily_candidate_baseline）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t50_action_transition_reappears():
    """50. watch → new_install 动作迁移：即使无外部 UPDATED 也应重新进入（V1.3 §二十二算升级）。"""
    w = cand("o/r/mig", action="watch", gap="mg")
    w2 = cand("o/r/mig", action="new_install", rec="install_candidate", gap="mg")
    tmp = tempfile.mkdtemp(prefix="daily-t50-")
    try:
        _gen(tmp, TODAY, [w])
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [w2])
        assert _keys(m2["items"]) == ["o/r/mig"], _keys(m2["items"])
        assert "ACTION_CHANGED" in m2["items"][0]["delta_cats"]
        assert m2["items"][0]["report_reason_type"] == "status_upgrade"
        assert "状态提升" in m2["items"][0]["why_today"]
        assert m2["lifecycle"]["status_upgraded"] == 1
        print("PASS 50：action_type watch→install 迁移 → STATUS_UPGRADED 重新进入日报")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t51_project_match_change_reappears():
    """51. matched_projects 空→非空 → project_match_change 重新出现。"""
    x1 = cand("o/r/pm", action="watch", gap="pg")
    x2 = cand("o/r/pm", action="watch", gap="pg",
              prj=[{"project": "protein-calculator", "match_score": 42,
                    "direct_evidence_kinds": ["strong_tech"]}])
    tmp = tempfile.mkdtemp(prefix="daily-t51-")
    try:
        _gen(tmp, TODAY, [x1])
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [x2])
        assert _keys(m2["items"]) == ["o/r/pm"], _keys(m2["items"])
        it = m2["items"][0]
        assert it["report_reason_type"] == "project_match_change"
        assert "protein-calculator" in it["matched_project"]
        print("PASS 51：项目匹配 空→非空 → project_match_change 重新出现")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t52_security_signature_change_reappears():
    """52. security_signature 变化 → 重新出现。"""
    import copy
    x1 = cand("o/r/sec", action="watch", gap="sg")
    x2 = copy.deepcopy(x1)
    x2["security"] = {"verdict": "review_required", "risk_level": "medium"}
    tmp = tempfile.mkdtemp(prefix="daily-t52-")
    try:
        _gen(tmp, TODAY, [x1])
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [x2])
        assert _keys(m2["items"]) == ["o/r/sec"], _keys(m2["items"])
        assert "SECURITY_CHANGED" in m2["items"][0]["delta_cats"]
        print("PASS 52：security 签名变化 → 重新出现")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t53_feedback_change_reevaluated():
    """53. 已展示候选新增反馈 → 按反馈规则重新评估（feedback_reentry）。"""
    x = cand("fb/repo/one", action="watch", gap="fg")
    tmp = tempfile.mkdtemp(prefix="daily-t53-")
    try:
        _gen(tmp, TODAY, [x])
        fb = {"fb/repo/one": {"status": "poor", "updated_at": "2026-09-25",
                              "user_note": "试了不行"}}
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [x], feedback=fb)
        assert _keys(m2["items"]) == ["fb/repo/one"], _keys(m2["items"])
        it = m2["items"][0]
        assert it["report_reason_type"] == "feedback_reentry"
        assert "不好用" in it["feedback_effect"]
        print("PASS 53：反馈新增 → 重新评估进入（feedback_reentry + 可解释 reason）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- V1.2 §二十九 56：restore 到期只提醒展示过的 ----------
def test_t56_restore_expiry_only_shown():
    """56. Day1 展示 10 条 restore、2 条进 backlog；Day4 到期只提醒展示过的 10 条。"""
    cands = [cand(f"o/r/rs{i}", action="restore_candidate", gap=f"rg{i}",
                  score=90 - i) for i in range(12)]
    tmp = tempfile.mkdtemp(prefix="daily-t56-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        k1 = set(_keys(m1["items"]))
        assert len(k1) == 10 and m1["baseline_backlog"]["restore"] == 2
        m4, _r4, _s4 = _gen(tmp, TODAY + timedelta(days=3), cands)
        k4 = set(_keys(m4["items"]))
        assert k4 == k1, (k4 ^ k1)                        # 展示过的按 3 天周期回来
        assert m4["suppressed"]["baseline_backlog"] == 2   # backlog 不因到期自动出现
        print("PASS 56：restore 到期只提醒之前展示过的；未展示 backlog 依旧不轮播")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- V1.2 §二十九 59-61：包一致性与路径合同 ----------
def test_t59_package_report_matches_e2e_day1():
    rep_ctx = os.path.join(BASE, "DAILY_REPORT_CONTEXT.json")
    aud = os.path.join(BASE, "reports", "package-e2e-audit.txt")
    if not (os.path.exists(aud) and os.path.exists(rep_ctx)):
        raise unittest.SkipTest("package-e2e-audit.txt / 正式日报未生成（打包阶段产物）")
    m = json.load(open(rep_ctx, encoding="utf-8"))
    keys = sorted(x["canonical_key"] for x in m["items"])
    sec = open(aud, encoding="utf-8").read().split("DAY1:")[1].split("DAY2:")[0]
    akeys = sorted(re.findall(r"^\s+(\S+/\S+)$", sec, re.M))
    assert akeys == keys, (akeys, keys)
    assert m["report_mode"] == "initial_baseline"
    md = open(os.path.join(BASE, "reports", "2026-09-24.md"), encoding="utf-8").read()
    assert md.count("### ") == len(keys)
    print(f"PASS 59：包内 Day1 日报 keys == package-e2e-audit DAY1 keys（{len(keys)} 条一致）")


def test_t60_no_absolute_dev_paths_in_artifacts():
    """60. 正式交付物 grep /Users/ /home/ C:\\ /Volumes/ = 0 命中（测试代码除外）。"""
    pats = ("/Users/", "/home/", "C:\\", "/Volumes/")
    art = ["README.md", "DAILY_REPORT_CONTEXT.json", "config/daily.json",
           "reports/2026-09-24.md", "reports/feedback-demo.txt",
           "reports/repeat-audit-2026-09-24_25.txt", "reports/package-e2e-audit.txt",
           "data/SKILL_FEEDBACK.json", "data/SKILL_FEEDBACK_HISTORY.jsonl",
           "data/state/daily_snapshot.json"]
    hits = []
    for f in art:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        for pat in pats:
            if pat in txt:
                hits.append((f, pat))
    assert not hits, hits
    print(f"PASS 60：{len(art)} 类正式产物绝对路径 grep = 0 命中")


def test_t61_provenance_logical_only_in_artifact():
    ctx = os.path.join(BASE, "DAILY_REPORT_CONTEXT.json")
    if not os.path.exists(ctx):
        raise unittest.SkipTest("DAILY_REPORT_CONTEXT.json 未生成")
    m = json.load(open(ctx, encoding="utf-8"))
    for k, v in m["input_provenance"].items():
        if k in ("project_context", "installed_context"):
            continue
        assert "path" not in v, (k, "runtime path leaked")
        assert "logical_path" in v, k
        assert not any(p in json.dumps(v) for p in ("/Users/", "/home/")), k
    assert "runtime_debug_path" not in m["input_provenance"]
    print("PASS 61：交付机器摘要 input_provenance 只含 logical_path")


# ---------- V1.3 §二十五~§三十 63~77：生命周期（消失/重现/降级/升级/替换/tombstone） ----------
def test_t63_removed_shown_candidate_notified():
    """63. Day1 展示 A=new_install；Day2 A 从池中删除 → NO_LONGER_RELEVANT 用户可见。"""
    a = cand("stablyai/orca/orca-emulator-android", action="new_install",
             rec="install_candidate", gap="mobile_qa")
    tmp = tempfile.mkdtemp(prefix="daily-t63-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, [a])
        assert _keys(m1["items"]) == [a["canonical_key"]]
        m2, r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [])
        assert m2["summary"]["total_items"] == 1, _keys(m2["items"])
        it = m2["items"][0]
        assert it["action"] == "risk" and it["risk_kind"] == "no_longer_relevant"
        assert it["report_reason_type"] == "no_longer_relevant"
        assert it["event_type"] == "removed"
        assert "NO_LONGER_RELEVANT" in it["delta_cats"]
        assert m2["lifecycle"]["removed_from_pool"] == 1
        assert "## 暂不建议" in r2 and "不再属于当前候选" in r2
        assert "之前的动作：建议安装" in r2
        print("PASS 63：消失的已展示候选 → 暂不建议 + 可读卡片（不是 security 风险文案）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t64_removed_unseen_backlog_machine_only():
    """64. 未展示的 backlog 消失：用户 0 条，suppressed.no_longer_relevant_unseen += 1。"""
    cands = [_inst(i) for i in range(15)]
    gone = cands[12]["canonical_key"]
    tmp = tempfile.mkdtemp(prefix="daily-t64-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        assert gone not in _keys(m1["items"])               # 确认它在 backlog 里
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1),
                            [c for c in cands if c["canonical_key"] != gone])
        assert m2["summary"]["total_items"] == 0, _keys(m2["items"])
        assert m2["suppressed"]["no_longer_relevant_unseen"] == 1
        assert m2["lifecycle"]["removed_from_pool"] == 1
        print("PASS 64：未展示 backlog 消失只机器计数，不打扰用户")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t65_removed_notified_once():
    """65. Day3 仍没有 A：不得再次提醒 NO_LONGER_RELEVANT。"""
    a = cand("o/r/gone", action="new_install", rec="install_candidate", gap="g1")
    tmp = tempfile.mkdtemp(prefix="daily-t65-")
    try:
        _gen(tmp, TODAY, [a])
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [])
        assert m2["summary"]["total_items"] == 1
        m3, r3, _s3 = _gen(tmp, TODAY + timedelta(days=2), [])
        assert m3["summary"]["total_items"] == 0, _keys(m3["items"])
        assert "今天没有需要你处理的 Skill 变化" in r3
        print("PASS 65：消失通知只发一次，Day3 不再重复")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t66_returned_candidate_notified_once():
    """66. Day1 展示 → Day2 消失已通知 → Day3 重新进入：RETURNED 进日报一次。"""
    a = cand("o/r/ret", action="new_install", rec="install_candidate", gap="g1")
    tmp = tempfile.mkdtemp(prefix="daily-t66-")
    try:
        _gen(tmp, TODAY, [a])
        _gen(tmp, TODAY + timedelta(days=1), [])
        m3, r3, _s3 = _gen(tmp, TODAY + timedelta(days=2), [a])
        assert _keys(m3["items"]) == ["o/r/ret"], _keys(m3["items"])
        it = m3["items"][0]
        assert "RETURNED" in it["delta_cats"]
        assert it["report_reason_type"] == "candidate_returned"
        assert "重新出现" in it["why_today"] and "第一次发现" not in r3
        assert m3["lifecycle"]["returned_to_pool"] == 1
        print("PASS 66：重新出现的候选按 RETURNED 提醒一次（不冒充全新发现）")
        m4, _r4, _s4 = _gen(tmp, TODAY + timedelta(days=3), [a])
        assert m4["summary"]["total_items"] == 0, _keys(m4["items"])   # 67
        print("PASS 67 并入：Day4 无变化不得继续 RETURNED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t68_install_to_reject_downgraded():
    """68. 已展示的 new_install → reject（security 不变）→ STATUS_DOWNGRADED 不得静默。"""
    import copy
    a = cand("o/r/dg", action="new_install", rec="install_candidate", gap="g1")
    a2 = copy.deepcopy(a)
    a2["action_type"] = "reject"
    a2["recommendation"] = "reject"
    a2["recommendation_reason"] = "product scope no longer matches"
    tmp = tempfile.mkdtemp(prefix="daily-t68-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, [a])
        assert _keys(m1["items"]) == ["o/r/dg"]
        m2, r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [a2])
        assert _keys(m2["items"]) == ["o/r/dg"], _keys(m2["items"])
        it = m2["items"][0]
        assert it["action"] == "risk" and it["risk_kind"] == "status_downgrade"
        assert it["event_type"] == "status_downgraded"
        assert "STATUS_DOWNGRADED" in it["delta_cats"]
        assert "之前建议安装" in it["one_line_explanation"]
        assert "product scope" in it["extra_note"]          # 原因非安全类，如实展示
        assert m2["lifecycle"]["status_downgraded"] == 1
        assert "## 暂不建议" in r2
        print("PASS 68：install→reject 降级 → 暂不建议 + 可解释原因（不谎称安全风险）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t69_install_to_watch_downgraded_if_shown():
    """69. 已展示的 new_install → watch/ignore：STATUS_DOWNGRADED。"""
    import copy
    a = cand("o/r/dg2", action="new_install", rec="install_candidate", gap="g1")
    a2 = copy.deepcopy(a)
    a2["action_type"] = "watch"
    a2["recommendation"] = "watch"
    tmp = tempfile.mkdtemp(prefix="daily-t69-")
    try:
        _gen(tmp, TODAY, [a])
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [a2])
        assert _keys(m2["items"]) == ["o/r/dg2"], _keys(m2["items"])
        it = m2["items"][0]
        assert it["report_reason_type"] == "status_downgrade"
        assert "降为继续观察" in it["extra_note"]
        print("PASS 69：install→watch 降级（此前展示过）→ 可见")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t70_unseen_downgrade_machine_only():
    """70. 从未展示的 backlog install→ignore：只机器计数，不强制用户提醒。"""
    cands = [_inst(i) for i in range(15)]
    back = cands[12]
    import copy
    back2 = copy.deepcopy(back)
    back2["action_type"] = "watch"
    back2["recommendation"] = "watch"
    tmp = tempfile.mkdtemp(prefix="daily-t70-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, cands)
        bk = back["canonical_key"]
        assert bk not in _keys(m1["items"])
        pool2 = [back2 if c["canonical_key"] == bk else c for c in cands]
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), pool2)
        assert bk not in _keys(m2["items"])
        assert m2["lifecycle"]["status_downgraded"] >= 1
        assert m2["suppressed"]["non_material_today"] >= 1
        print("PASS 70：未展示降级只记机器统计（lifecycle.status_downgraded）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t72_reject_to_watch_improved():
    """72. 用户见过的 reject → watch：可继续观察并写清「状态已改善」。"""
    import copy
    x1 = cand("o/r/rj", action="reject", rec="reject", verdict="block", risk="high")
    x2 = copy.deepcopy(x1)
    x2["action_type"] = "watch"
    x2["recommendation"] = "watch"
    x2["security"] = {"verdict": "pass", "risk_level": "low"}
    tmp = tempfile.mkdtemp(prefix="daily-t72-")
    try:
        m1, _r1, _s1 = _gen(tmp, TODAY, [x1], deltas={x1["canonical_key"]: ["NEW"]})
        assert m1["summary"]["risk"] == 1
        m2, _r2, _s2 = _gen(tmp, TODAY + timedelta(days=1), [x2])
        assert _keys(m2["items"]) == ["o/r/rj"], _keys(m2["items"])
        it = m2["items"][0]
        assert it["action"] == "watch"
        assert it["report_reason_type"] == "status_upgrade"
        assert "提升" in it["why_today"]
        print("PASS 72：reject→watch → 状态提升可见并写清原因")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t73_replacement_candidate_supported():
    """73. action_type=replacement_candidate：不丢、有明确动作、不写成全新安装。"""
    r = cand("vendor/skills/legacy-replacer", action="replacement_candidate",
             rec="watch", gap="g1", rel="replacement_candidate")
    tmp = tempfile.mkdtemp(prefix="daily-t73-")
    try:
        m1, r1, _s1 = _gen(tmp, TODAY, [r])
        assert _keys(m1["items"]) == ["vendor/skills/legacy-replacer"], _keys(m1["items"])
        it = m1["items"][0]
        assert it["action"] == "replace" and it["action_type"] == "replacement_candidate"
        assert "建议替换" in r1
        assert "不是发现了一个新 Skill" in it["one_line_explanation"]
        assert it["source_url"].startswith("https://github.com/vendor/skills")
        assert m1["lifecycle"]["replacement_candidates"] == 1
        assert m1["summary"]["replace"] == 1
        print("PASS 73：replacement_candidate → 第 6 类动作「建议替换」（63~77 全支持）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t74_removed_goes_to_tombstone():
    a = cand("o/r/tb", action="new_install", rec="install_candidate", gap="g1")
    tmp = tempfile.mkdtemp(prefix="daily-t74-")
    try:
        _gen(tmp, TODAY, [a])
        m2, _r2, s2 = _gen(tmp, TODAY + timedelta(days=1), [])
        tb = s2["candidate_tombstones"]
        assert "o/r/tb" in tb, list(tb)
        assert tb["o/r/tb"]["last_action_type"] == "new_install"
        assert tb["o/r/tb"]["notified_no_longer_relevant"] == "2026-09-25"
        assert tb["o/r/tb"]["important"] is True
        assert tb["o/r/tb"]["last_display"]["skill_name"] == "tb"
        print("PASS 74：removed 候选进入 candidate_tombstones（含最后可读信息）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t75_tombstone_kept_within_retention():
    t0 = TODAY
    tombs = {"a/b/c": {"last_seen": (t0 - timedelta(days=29)).isoformat(),
                       "notified_no_longer_relevant": (t0 - timedelta(days=29)).isoformat(),
                       "important": True}}
    out = BD._tombstone_prune(tombs, set(), t0, 30)
    assert "a/b/c" in out
    print("PASS 75：retention（30 天）内的 tombstone 保留")


def test_t76_tombstone_cleaned_after_retention_when_notified():
    t0 = TODAY
    tombs = {"a/b/c": {"last_seen": (t0 - timedelta(days=31)).isoformat(),
                       "notified_no_longer_relevant": (t0 - timedelta(days=31)).isoformat(),
                       "important": True}}
    out = BD._tombstone_prune(tombs, set(), t0, 30)
    assert "a/b/c" not in out
    print("PASS 76：超保留期且已通知 → 允许清理（不无限增长）")


def test_t77_important_unnotified_never_prematurely_cleaned():
    t0 = TODAY
    tombs = {"a/b/c": {"last_seen": (t0 - timedelta(days=40)).isoformat(),
                       "important": True, "notified_no_longer_relevant": None}}
    out = BD._tombstone_prune(tombs, set(), t0, 30)
    assert "a/b/c" in out
    print("PASS 77：未通知的重要消失项不得提前清理")


# ---------- V1.4 §五/§十 78~83：归档自定位（subprocess 真 clean-room）与版本一致性 ----------
PROBE = ("import sys; sys.path.insert(0, 'scripts');"
         "import common, build_daily;"
         "print(common.EXTERNAL_RESOLUTION_MODE, build_daily.ENGINE_VERSION)")


def _mk_room(layout):
    """临时父目录：skill-daily 真复制 + 按布局放外部包（symlink 足够验证定位）。"""
    tmp = tempfile.mkdtemp(prefix="daily-room-")
    shutil.copytree(BASE, os.path.join(tmp, "skill-daily"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    ext = C.EXTERNAL_ROOT
    if layout == "sibling":
        os.symlink(ext, os.path.join(tmp, C.TRANSFER_DIR_NAME))
    elif layout == "legacy":
        nest = os.path.join(tmp, "Agent 产物（外部情报层）")
        os.makedirs(nest, exist_ok=True)
        os.symlink(ext, os.path.join(nest, C.TRANSFER_DIR_NAME))
    elif layout == "empty":
        pass
    return tmp


def _probe(tmp, env_extra=None):
    import subprocess
    env = dict(os.environ)
    env.pop("EXTERNAL_INTELLIGENCE_ROOT", None)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([sys.executable, "-c", PROBE],
                       cwd=os.path.join(tmp, "skill-daily"),
                       env=env, capture_output=True, text=True, timeout=120)
    return r


def test_t78_sibling_transfer_no_env():
    """78/§五：同级转送包、无环境变量，全新进程 import 必须成功且 mode=sibling_transfer_package。"""
    tmp = _mk_room("sibling")
    try:
        r = _probe(tmp)
        assert r.returncode == 0, r.stderr[-300:]
        mode, ver = r.stdout.split()
        assert mode == "sibling_transfer_package", mode
        assert ver == BD.ENGINE_VERSION
        print("PASS 78：同级转送包无 env → 新进程解析成功（sibling_transfer_package）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t79_development_repo_mode():
    dev_root = os.path.join(os.path.dirname(os.path.abspath(BASE)), "external-intelligence")
    if not os.path.isdir(dev_root):
        raise unittest.SkipTest("非开发仓环境，development_repo 布局不适用")
    assert C.EXTERNAL_RESOLUTION_MODE == "development_repo"
    print("PASS 79：开发仓布局 development_repo")


def test_t80_env_override_mode():
    tmp = _mk_room("empty")           # 同级没有任何外部包，只有 env 指路
    try:
        r = _probe(tmp, {"EXTERNAL_INTELLIGENCE_ROOT": C.EXTERNAL_ROOT})
        assert r.returncode == 0, r.stderr[-300:]
        assert r.stdout.split()[0] == "env_override"
        print("PASS 80：EXTERNAL_INTELLIGENCE_ROOT 显式覆盖 → env_override")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t81_legacy_nested_still_supported():
    tmp = _mk_room("legacy")
    try:
        r = _probe(tmp)
        assert r.returncode == 0, r.stderr[-300:]
        assert r.stdout.split()[0] == "legacy_nested"
        print("PASS 81：旧版 Agent 产物嵌套布局继续兼容（legacy_nested）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t82_friendly_error_when_external_missing():
    import subprocess
    tmp = _mk_room("empty")
    try:
        r = _probe(tmp)
        assert r.returncode != 0
        blob = (r.stderr or "") + (r.stdout or "")
        assert "找不到 External Skill Intelligence" in blob, blob[-300:]
        assert "ModuleNotFoundError" not in blob
        print("PASS 82：全部布局缺失 → 友好错误指引，不再 ModuleNotFoundError")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_t83_current_version_consistency():
    """§十 CURRENT_VERSION_CONSISTENCY：当前版本标签位全部 = V1.4，stale=0。"""
    stale = []

    def check(label, ok):
        if not ok:
            stale.append(label)
    readme = open(os.path.join(BASE, "README.md"), encoding="utf-8").read().splitlines()
    check("README 当前标题", readme and "V1.4" in readme[0])
    bd = open(os.path.join(BASE, "scripts", "build_daily.py"), encoding="utf-8").read()
    check("build_daily 模块标题", "Skill 日报引擎 V1.4（build_daily.py）" in bd)
    check("argparse description", 'description="Skill 日报引擎 V1.4' in bd)
    check("ENGINE_VERSION", "ENGINE_VERSION = \"1.4\"" in bd)
    tt = open(os.path.join(BASE, "tests", "test_daily.py"), encoding="utf-8").read()
    check("测试套件标题", "Skill 日报引擎 V1.4 测试" in tt)
    cfg = open(os.path.join(BASE, "config", "daily.json"), encoding="utf-8").read()
    check("config 当前说明", "Skill 日报引擎 V1.4 配置" in cfg)
    for art in ("reports/package-e2e-audit.txt", "reports/lifecycle-e2e-audit.txt",
                "reports/repeat-audit-2026-09-24_25.txt", "reports/feedback-demo.txt"):
        p = os.path.join(BASE, art)
        if os.path.exists(p):
            first = open(p, encoding="utf-8").read().splitlines()[0]
            check(f"审计标题 {os.path.basename(art)}", "V1.4" in first)
    ctx = os.path.join(BASE, "DAILY_REPORT_CONTEXT.json")
    if os.path.exists(ctx):
        m = json.load(open(ctx, encoding="utf-8"))
        check("machine engine.name", m["engine"].get("name") == "skill-daily")
        check("machine engine.version", m["engine"].get("version") == "1.4")
    assert not stale, stale
    print("PASS 83：当前版本标签 9 类位置全部 V1.4（stale_current_version_labels=0）")


def main():
    tests = [
        test_t1_zero_change_day, test_t2_new_install_candidate,
        test_t3_restore_not_new, test_t4_update_lineage,
        test_t5_security_changed_block, test_t6_metadata_enriched_not_shown,
        test_t7_rebaseline_not_external_news, test_t8_watch_cooldown,
        test_t9_watch_new_project_match_reappears, test_t10_feedback_ignored,
        test_t11_feedback_poor_family_demote, test_t12_feedback_useful_boost,
        test_t13_conflict_suppression, test_t14_unresolved_scope_not_in_install,
        test_t15_strong_without_incremental_not_install, test_t16_no_padding,
        test_t17_max_10_priority, test_t18_source_traceable,
        test_t19_no_auto_install,
        test_t20a_deterministic_same_initial_state, test_t20b_same_day_idempotence,
        test_t20c_next_day_no_repeat,
        test_t21_first_day_install_shown, test_t22_install_no_repeat_next_day,
        test_t23_install_repeat_days_expiry, test_t24_update_no_repeat,
        test_t25_restore_within_repeat_days, test_t26_restore_expiry_realerts,
        test_t27_security_changed_breaks_cooldown,
        test_t28_new_matched_project_breaks_cooldown,
        test_t32_exact_functional_duplicate_primary_plus_alternatives,
        test_t33_capability_family_quota, test_t34_restore_update_exempt_from_quota,
        test_t35_no_backfill_after_dedupe,
        test_t36_real_candidates_path_flat_layout, test_t37_true_skip_counted_as_skip,
        test_t38_machine_one_line_is_chinese, test_t39_source_description_excerpt_kept,
        test_t40_input_provenance_honest_logical,
        test_t41_unchanged_repeated_items_zero,
        test_t42_suppressed_fields_and_report_mode,
        test_t43_real_two_day_simulation_audit,
        test_t44_first_run_no_new_storm_full_baseline,
        test_t45_unshown_install_absent_next_day,
        test_t46_unshown_watch_absent_next_day,
        test_t47_backlog_not_rotated_by_repeat_days,
        test_t49_new_candidate_only_appears, test_t50_action_transition_reappears,
        test_t51_project_match_change_reappears,
        test_t52_security_signature_change_reappears,
        test_t53_feedback_change_reevaluated,
        test_t56_restore_expiry_only_shown,
        test_t59_package_report_matches_e2e_day1,
        test_t60_no_absolute_dev_paths_in_artifacts,
        test_t61_provenance_logical_only_in_artifact,
        test_t63_removed_shown_candidate_notified,
        test_t64_removed_unseen_backlog_machine_only,
        test_t65_removed_notified_once,
        test_t66_returned_candidate_notified_once,
        test_t68_install_to_reject_downgraded,
        test_t69_install_to_watch_downgraded_if_shown,
        test_t70_unseen_downgrade_machine_only,
        test_t72_reject_to_watch_improved,
        test_t73_replacement_candidate_supported,
        test_t74_removed_goes_to_tombstone,
        test_t75_tombstone_kept_within_retention,
        test_t76_tombstone_cleaned_after_retention_when_notified,
        test_t77_important_unnotified_never_prematurely_cleaned,
        test_t78_sibling_transfer_no_env,
        test_t79_development_repo_mode,
        test_t80_env_override_mode,
        test_t81_legacy_nested_still_supported,
        test_t82_friendly_error_when_external_missing,
        test_t83_current_version_consistency,
    ]
    for t in tests:
        _run(t)
    total = sum(_COUNTS.values())
    print()
    print("=" * 64)
    print(f"TEST SUMMARY: pass={_COUNTS['pass']} skip={_COUNTS['skip']} "
          f"fail={_COUNTS['fail']} (total {total})")
    if _FAILURES:
        print("FAILURES:")
        for n, m in _FAILURES:
            print(f"  - {n}: {m}")
    print("=" * 64)
    return 0 if _COUNTS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
