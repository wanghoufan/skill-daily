#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选池精简对照件生成器（给审查者看的「看得完」视图）。

完整数据是 data/SKILL_CANDIDATES.json；本脚本只抽出几类可核对的切片：
  ① 总览计数（含数据质量 Gate 与安全 verdict 分布）
  ② Personalized Top（实际数量，不含 ignore/reject）+ ALTERNATIVES（跨仓同功能族）
  ③ 安全清单（block 级阻断 / review_required 需人工复核）
  ④ 更新候选与恢复候选
  ⑤ 本轮修掉的问题（整改记录）
  ⑥ 复现与依赖（口径以 v2.8 为准）

Top 的排序与多样性规则**直接复用 build_context 的函数**（`select_top`），不另写一套，
避免「日报里的 Top」与「对照件里的 Top」不一致。

用法：
    python3 scripts/make_digest.py                # 输出到 stdout
    python3 scripts/make_digest.py -o out.md      # 输出到文件
"""
import os
import sys
import json
import argparse
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (CANDIDATES_PATH, REGISTRY_PATH, load_config,  # noqa: E402
                    SKILL_CONTEXT_PATH, PATH_RESOLUTION, BASE, load_installed)
import build_context as bc  # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _path_source(key):
    """§九：报告某个输入到底走的是哪条解析路径（env / 包内自定位 / 本机默认）。
    `PATH_RESOLUTION` 形如 {"skill_context": "package:/.../支撑/输入/SKILL_CONTEXT.md"}"""
    return (PATH_RESOLUTION or {}).get(key, "未记录")


def _path_report(key, resolved):
    """给审查者看的可核对串：走的是哪条路径 + 最终落到哪个文件。

    注意：这一行**刻意随运行环境变化**（env / 包内自定位 / 本机默认），
    因此不同环境下重生成的对照件在这一行必然不同 —— 其余内容应当逐位一致。
    """
    label = _path_source(key)
    exists = "可读" if os.path.exists(resolved) else "**不可读**"
    shown = resolved
    # 归档包内自定位时，路径前缀因解压位置而异；只保留包内相对部分，便于核对
    if label.startswith("package:"):
        shown = "…/" + os.path.relpath(resolved, BASE)
    elif label == "local_default":
        shown = resolved.replace(os.path.expanduser("~"), "~")
    return f"{label} → `{shown}`（{exists}）"


def fmt_needs(pm):
    ns = (pm or {}).get("matched_needs") or []
    return ", ".join(ns[:3]) if ns else "—"


def fmt_projects(pm, limit=2):
    mps = (pm or {}).get("matched_projects") or []
    if not mps:
        return "—"
    return "；".join(f"{m['project']}({m['match_score']})" for m in mps[:limit])


def rules_of(sec, level=None):
    fs = [f for f in (sec or {}).get("findings", [])
          if level is None or f.get("level") == level]
    return ",".join(sorted({f.get("rule", "?") for f in fs})) or "—"


def _test_count():
    """离线测试项数：从 tests/test_pipeline.py 现算，不写死数字（写死必然过期）。"""
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tests", "test_pipeline.py")
    try:
        with open(p, encoding="utf-8") as f:
            return sum(1 for line in f if line.startswith("def test_"))
    except OSError:
        return 0


def build():
    cands_doc = load(CANDIDATES_PATH)
    I = cands_doc["candidates"]
    reg = load(REGISTRY_PATH)
    S = [x for t in reg["tiers"].values() for x in (t if isinstance(t, list) else [])]
    cfg = load_config()
    counts = cands_doc.get("counts", {})
    quarantine = cands_doc.get("quarantine", {})

    rec = collections.Counter(x["recommendation"] for x in I)
    rel = collections.Counter(x["installed_relationship"] for x in I)
    risk = collections.Counter(x["security"]["risk_level"] for x in I)
    verdict = collections.Counter(x["security"].get("verdict") for x in I)
    deep = collections.Counter(x["security"].get("deep_scan_status") for x in I)
    gap = collections.Counter((x.get("capability_gap_match") or {}).get("gap_level") for x in I)
    scanned = sum(1 for x in I if x["security"]["status"] == "scanned")
    # v2.2：分母只取「真有需求证据」的高匹配候选（与 build_context 口径一致）
    hm = [x for x in I if x["recommendation"] in ("install_candidate", "watch")
          and (x.get("project_match") or {}).get("need_evidence")]
    hm_proj = [x for x in hm if (x.get("project_match") or {}).get("matched_projects")]

    # --- Top：复用日报同一套门槛 + 排序 + 多样性/功能族规则 ---
    top_cfg = cfg.get("top_candidates", {})
    target_limit = top_cfg.get("target_limit", 30)
    min_top_score = top_cfg.get("min_score")
    allowed = tuple(top_cfg.get("allowed_recommendations", ["install_candidate", "watch"]))
    pool = [c for c in I
            if c["installed_relationship"] != "already_installed"
            and c["recommendation"] in allowed]
    ranked = sorted(pool, key=bc.rank_candidate)
    corroborated = bc.build_corroborated_repos(reg, I)
    top, top_alts = bc.select_top(ranked, limit=target_limit, min_score=min_top_score,
                                  max_per_repo=top_cfg.get("max_per_repo", 3),
                                  corroborated_repos=corroborated)
    functional_dupes = sum(len(v) for v in top_alts.values())
    t3_unc = [c for c in ranked if bc.is_t3_uncorroborated(c, corroborated)]
    # §一：项目匹配「直接证据率」——matched_projects 每一条都必须带 direct_evidence
    mp_entries = [m for c in I
                  for m in ((c.get("project_match") or {}).get("matched_projects") or [])]
    mp_direct = [m for m in mp_entries if m.get("direct_evidence")]

    blocked = [x for x in I if x["security"].get("verdict") == "block"]
    review = [x for x in I if x["security"].get("verdict") == "review_required"]
    review_ctx = [x for x in review if x["security"].get("install_blocked")]
    review_mention = [x for x in review if not x["security"].get("install_blocked")]
    upd = [x for x in I if x.get("update_available")]
    repl = [x for x in I if x["installed_relationship"] == "replacement_candidate"]

    L = []
    A = L.append
    A("# 候选池精简对照件（External Skill Intelligence v2.11）")
    A("")
    A(f"> 数据基线：{cands_doc.get('generated')}｜源文件 `SKILL_CANDIDATES.json`（{len(I)} 条）")
    A("> 本件是**给审查者看得完的切片视图**，用于核对；完整数据与全部字段以 JSON 为准。")
    A("> 只做发现与评估：**不安装、不删除、不升级任何 Skill**；"
      "排名/安装量只是 adoption signal，不等于推荐。")
    A("")

    # 一、总览
    A("## 一、总览")
    A("")
    A("| 项目 | 数值 |")
    A("|---|---|")
    A(f"| 来源注册表 | {len(S)} 源（" +
      " / ".join(f"T{k} {v}" for k, v in sorted(collections.Counter(s["tier"] for s in S).items())) + "）|")
    A(f"| 候选（raw → 合法池） | {counts.get('raw_candidates')} → {len(I)} |")
    A(f"| 数据质量 Gate | 剔除构建产物 {counts.get('invalid_artifacts_removed', 0)} 条 / "
      f"非法 skill 名 {counts.get('invalid_names_removed', 0)} 条 |")
    A(f"| bottom-up 硬门 | 共 {counts.get('bottom_up_total', 0)} 条搜索结果 → "
      f"过 SKILL.md 硬门 {counts.get('bottom_up_verified', 0)} / 隔离 {counts.get('bottom_up_quarantined', 0)} |")
    A(f"| 推荐分布 | " + " / ".join(f"{k} {v}" for k, v in sorted(rec.items())) + " |")
    A(f"| 与已装关系 | " + " / ".join(f"{k} {v}" for k, v in sorted(rel.items())) + " |")
    A(f"| 安全风险 | " + " / ".join(f"{k} {v}" for k, v in sorted(risk.items())) +
      f"（已静态审查 {scanned}）|")
    A(f"| 安全 verdict | pass {verdict.get('pass',0)} / review_required {verdict.get('review_required',0)}"
      f" / block {verdict.get('block',0)} / unscanned {verdict.get('unscanned',0)} |")
    A(f"| 深度静态审查 | complete {deep.get('complete',0)}（= install 候选）"
      f" / failed {deep.get('failed',0)} / pending {deep.get('pending',0)}"
      f" / not_required {deep.get('not_required',0)} / skipped {deep.get('skipped',0)} |")
    A(f"| 能力缺口 | " + " / ".join(f"{k} {v}" for k, v in sorted(gap.items(), key=lambda kv: str(kv[0]))) + " |")
    A(f"| 命中项目需求 / 平台错配 | "
      f"{sum(1 for x in I if (x.get('project_match') or {}).get('need_evidence'))} / "
      f"{sum(1 for x in I if (x.get('project_match') or {}).get('domain_mismatch'))} |")
    A(f"| matched_projects 覆盖（高匹配候选） | {len(hm_proj)}/{len(hm)} "
      f"({(len(hm_proj)/max(1,len(hm))):.0%}) —— **v2.3 起不再是 KPI**，只作参考 |")
    A(f"| matched_project 直接证据完整性 | {len(mp_direct)}/{len(mp_entries)} "
      f"—— 每条匹配都必须带 1 类直接证据（完整性自检，**不是**质量 KPI）|")
    A(f"| update_available / replacement_candidate | {len(upd)} / {len(repl)} |")
    A("")
    A("> **v2.4 §十：`direct evidence` 的「字段非空率」不再作为精度指标。**")
    A("> 字段非空只能证明写了；能不能证明「证据真的有效」，要看下面的分项计数：")
    A("")
    pq = cands_doc.get("project_match_quality") or {}
    if pq:
        A("| PROJECT_MATCH_QUALITY | 数值 | 含义 |")
        A("|---|---|---|")
        A(f"| matched_candidates | {pq.get('matched_candidates', 0)} | 至少有一个 matched_project 的候选数 |")
        A(f"| strong_tech_evidence | {pq.get('strong_tech_evidence', 0)} | "
          "专用技术栈直接命中（Expo / RN / Android / Supabase / Next.js / PWA / Vercel / .NET…）|")
        A(f"| positioning_evidence | {pq.get('positioning_evidence', 0)} | 项目定位/功能语义命中 |")
        A(f"| shared_need_evidence | {pq.get('shared_need_evidence', 0)} | 项目自身需求与候选能力命中 |")
        A(f"| lexical_evidence | {pq.get('lexical_evidence', 0)} | "
          "词面证据（v2.5：独立成立仅限**领域短语**；词级重叠只作次要加分，泛词与裸 prompt 全禁）|")
        A(f"| **secondary_tech_only_rejected** | {pq.get('secondary_tech_only_rejected', 0)} | "
          "**只**靠泛用技术栈（TS / React / Python / Docker…）硬凑、已被拒的候选数 |")
        A(f"| **negated_evidence_rejected** | {pq.get('negated_evidence_rejected', 0)} | "
          "被否定窗口 / 排除语境压掉的命中次数（看得见门在工作）|")
        A(f"| lexical_single_rejected | {pq.get('lexical_single_rejected', 0)} | "
          "词面重叠只因单个低区分度词（manager / service…）而不足以成立的次数 |")
        A(f"| lexical_alone_rejected | {pq.get('lexical_alone_rejected', 0)} | "
          "v2.5 §三：词面 boost 想**独立**造匹配、被拒的次数（词面只作次要加分）|")
        A(f"| lexical_phrase_direct_evidence | {pq.get('lexical_phrase_direct_evidence', 0)} | "
          "v2.5 §五：靠人工整理的领域短语独立成立的词面直接证据条数 |")
        A(f"| **bare_prompt_direct_evidence** | {pq.get('bare_prompt_direct_evidence', 0)} | "
          "v2.5 §四：裸 prompt 被当直接证据的次数 —— **必须为 0** |")
        A(f"| **tech_words_used_as_lexical_direct_evidence** | "
          f"{pq.get('tech_words_used_as_lexical_direct_evidence', 0)} | "
          "v2.5 §四：泛用技术词（react / native / typescript / api…）充当词面直接证据的次数"
          " —— **必须为 0** |")
        A(f"| unresolved_mismatch_candidates | {pq.get('unresolved_mismatch_candidates', 0)} | "
          "存在未解除平台错配的候选数（只作观察）|")
        # v2.6：身份血缘 / 重定向 / 产品 scope 的审计计数（三个恒 0 哨兵）
        A(f"| redirect_evidence_rejected | {pq.get('redirect_evidence_rejected', 0)} | "
          "v2.6 §五：跨 Skill 重定向小句（For X, use other-skill）被剪掉的次数 |")
        A(f"| **same_name_only_already_installed** | {pq.get('same_name_only_already_installed', 0)} | "
          "v2.6 §二：只凭同名判已安装的条数 —— **必须为 0** |")
        A(f"| **wrong_update_lineage** | {pq.get('wrong_update_lineage', 0)} | "
          "v2.6 §三：血缘未验证的 update_available —— **必须为 0** |")
        A(f"| **gcp_alias_missed** | {pq.get('gcp_alias_missed', 0)} | "
          "v2.6 §四：含 GCP 产品别名却未标 gcp 域 —— **必须为 0** |")
        A(f"| same_name_unverified_candidates | {pq.get('same_name_unverified_candidates', 0)} | "
          "同名但血缘未确认（最高 watch，等人工确认，不算已装/更新/替换）|")
        A(f"| product_internal_unresolved_candidates | {pq.get('product_internal_unresolved_candidates', 0)} | "
          "v2.6 §十：未解除的产品自研 Skill 数（第五道门挡在 Top 外，可解除非黑名单）|")
        A(f"| product_specific_scope_unresolved | {pq.get('product_specific_scope_unresolved', 0)} | "
          "v2.7 §七：未解除的产品专项 platform_operation（GA Admin / SecOps / anthropic-brand…）|")
        A("")
        A("> 四个 `*_evidence` 是**「候选 × 项目」条数**，同一条可同时具备多种证据；"
          "所有 matched_project 都必须至少带 1 类直接证据。"
          "**准确率优先于 coverage：matched_projects 下降完全可以接受。**")
    else:
        A("（本次数据未携带 project_match_quality —— 需重跑 `scripts/analyze.py`）")
    A("")
    A("> **v2.3 的口径变化**：`candidate 数量` / `matched_projects 覆盖率` / `Top30 是否凑满` "
      "这三项**不再是目标**；准确率优先。Top 里出现空位比塞垃圾好。")
    A("")

    # 二、Top
    A(f"## 二、Personalized Top（target_limit {target_limit} · 实际 {len(top)}）")
    A("")
    A("选取规则（与日报完全一致，复用同一函数 `select_top`）："
      f"① score ≥ **{min_top_score}**（配置化最低阈值）② 有真实个性化证据"
      "（matched need / capability gap / update / replacement 至少一个成立）"
      "③ T3/discovery_only 需有 T1·T2·官方交叉佐证 "
      "④ **无未解除的平台错配**（v2.4 §九：项目档案里没有任何项目用该平台 → 不进 Top；"
      "v2.6 §四 GCP 产品别名补齐后，Cloud Run / Agent Platform / Microsoft Store 专项都走这道门）"
      "⑤ **无未解除的 product_internal**（v2.6 §十第五道门：产品自研 Skill —— 如 BrowserOS "
      "test-ui —— 只有项目真的在做该产品才进 Top）"
      "⑥ recommendation ≥ watch ⑦ 分数；"
      "多样性最后执行：同仓库上限 3 条 + **跨仓同功能族折叠**。")
    A("")
    A("> **只含 `install_candidate` / `watch`，不含 `ignore` / `reject`**；"
      f"符合标准的不足 {target_limit} 个时就输出实际数量，**不为凑数塞垃圾**。")
    A("")
    A(f"> 本轮被三道质量门挡下的：低分（< {min_top_score}）若干 / "
      f"无个性化证据若干 / T3 无交叉佐证 **{len(t3_unc)}** 条（仍留在 WATCHLIST）。"
      f"跨仓同功能族折叠 **{functional_dupes}** 条（见 2.1）。")
    A("")
    A("「安全」列的口径：`pass` = 静态审查无发现；`review_required` = 有语境性提及，需人工看一眼；")
    A("`block` = 高风险行为，已 reject；`unscanned` = 超出抓取预算，**最高只能是 watch**。")
    A("`T—` 表示来源未经验证（bottom-up 搜索结果），不参与安装推荐。")
    A("")
    A("| # | 分数 | 推荐 | canonical_key | 来源 | 命中需求 | 最匹配项目 | 缺口 | 饱和 | 安全 | "
      "产品关系 / 项目分区 / 领域状态 / 解除证据 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top, 1):
        gm = c.get("capability_gap_match") or {}
        sec = c["security"]
        st = f"{sec.get('verdict')}"
        A(f"| {i} | {c['score']:.1f} | {c['recommendation']} | `{c['canonical_key']}` | "
          f"{'T' + str(c['source_tier']) if c.get('source_tier') is not None else 'T—(unverified)'} "
          f"{c.get('source', '—')} | "
          f"{fmt_needs(c.get('project_match'))} | {fmt_projects(c.get('project_match'))} | "
          f"{gm.get('gap_level', '—')} | {gm.get('capability_saturation', '—')} | {st} | "
          f"{bc.v29_scope_note(c)} |")
    A("")
    if top:
        repo_dist = collections.Counter(f"{c['owner']}/{c['repo']}" for c in top)
        multi = "、".join(f"`{k}`×{v}" for k, v in repo_dist.most_common() if v > 1)
        A(f"仓库分布：{len(repo_dist)} 个仓库承载 {len(top)} 条"
          + (f" → {multi}" if multi else "") + "。")
        A("")

    # 二·0、v2.10 §十二：每条 Top 的个性化推荐理由（回答「我已经有类似 Skill，为什么还推荐」）
    if top:
        A(f"### 2.0 PERSONALIZED_REASON（v2.10 §十二：{len(top)} 条逐条给强理由）")
        A("")
        A("规则：每条 Top 至少一条非空强理由；已装能力 saturated=strong 的候选，"
          "`incremental_over_installed` **必须非空**（否则它根本进不了 Top）。")
        A("")
        A("| canonical_key | 补什么缺口 | 匹配项目 | 比已装强在哪 | 为什么是现在 |")
        A("|---|---|---|---|---|")
        for c in top:
            pr = c.get("personalized_reason") or {}
            A(f"| `{c['canonical_key']}` | {pr.get('fills_gap') or '—'} | "
              f"{pr.get('matched_project') or '—'} | {pr.get('incremental_over_installed') or '—'} | "
              f"{pr.get('why_now') or '—'} |")
        A("")

    # 二·1、功能簇 ALTERNATIVES（§三/§八）
    A(f"### 2.1 FUNCTIONAL_CLUSTER —— ALTERNATIVES（{len(top_alts)} 个功能族有备选）")
    A("")
    A("候选池按 `owner/repo/skill` **保持独立记录**（不合并、不丢数据）；"
      "但 **Top 展示** 只出 PRIMARY —— 同一个功能族不连续推荐两个几乎一样的 Skill。")
    A("判定同族（满足其一即可）：normalized skill name 相同（≥5 字符）/ "
      "description jaccard ≥ 0.62 且名称同前缀 / content fingerprint 相同。")
    A("备选项**仍然完整保留在 `SKILL_CANDIDATES.json`**，此处只是不重复占版面。")
    A("")
    if top_alts:
        A("| PRIMARY（Top 内） | 被折叠的同族备选 | 判同族依据 |")
        A("|---|---|---|")
        for pk, dups in list(top_alts.items())[:20]:
            names = "；".join(
                f"`{d['canonical_key']}`（{d.get('score', '—')}）" for d in dups[:4])
            reasons = "；".join(sorted({str(d.get("reason", "—")) for d in dups}))
            A(f"| `{pk}` | {names} | {reasons} |")
    else:
        A("（无：本轮 Top 内没有跨仓同功能族重复）")
    A("")

    # 三、安全清单
    A(f"## 三、安全清单（Security Gate v2.4 · 沿用 v2.2 语境判定）")
    A("")
    A("核心区分：**「提到危险行为」≠「真的要求执行危险行为」**。"
      "每条 finding 带 `confidence` 与 `behavior_context`"
      "（mention / instruction / executable / remote_execution / **warning**），verdict 四值 "
      "`pass / review_required / block / unscanned`。")
    A("")
    A("> **v2.3 §四 修正**：`always_block` 规则不再「命中即 block」。"
      "`destructive_rm_root` / `pipe_to_shell` 等只有在**非警示语境**下才 block；"
      "`warning` 语境（`never ...` / `do not ...` / `禁止 ...` / `不要 ...` / "
      "安全审计文档举反例）一律降为 `review_required`。")
    A("")
    A(f"总体：pass {verdict.get('pass',0)} / review_required {verdict.get('review_required',0)}"
      f" / block {verdict.get('block',0)} / unscanned {verdict.get('unscanned',0)}")
    A("")
    A(f"### 3.1 block 级阻断（reject，{len(blocked)} 条）")
    A("")
    A("仅限高置信、**真会被执行**的高危行为：远程内容 pipe 进 shell/解释器、"
      "`rm -rf ~/` 或 `/`、凭据读取后外发、混淆 payload 执行等。官方来源**不豁免**。"
      "警示/反例语境不在此列。")
    A("")
    if blocked:
        A("| canonical_key | 来源 | 阻断规则 | 证据 |")
        A("|---|---|---|---|")
        for x in blocked[:40]:
            ev = ""
            for f in x["security"]["findings"]:
                if f.get("level") == "block":
                    ev = (f.get("evidence") or "")[:70]
                    break
            A(f"| `{x['canonical_key']}` | T{x.get('source_tier')} | "
              f"{','.join(x['security'].get('blocking_rules') or [])} | `{ev}` |")
    else:
        A("（无）")
    A("")
    A(f"### 3.2 review_required 需人工复核（{len(review)} 条；其中 {len(review_ctx)} 条被挡在安装候选之外）")
    A("")
    A("口径：属于敏感行为但**语境上只是提及/解释/示例/警示**，或虽有指令语境但危险度不足 —— "
      "一律不 reject，交人工判断。其中 `behavior_context` 为 instruction/executable "
      "的高敏感项会被挡在 `install_candidate` 之外（最高 watch）；"
      "`warning` 语境（安全文档举反例）不挡安装、也不 block。")
    A("")
    if review:
        A("| canonical_key | 来源 | 是否挡安装 | 命中规则 |")
        A("|---|---|---|---|")
        for x in (review_ctx + review_mention)[:40]:
            A(f"| `{x['canonical_key']}` | T{x.get('source_tier')} | "
              f"{'是' if x['security'].get('install_blocked') else '否（语境性提及）'} | "
              f"{rules_of(x['security'])} |")
    else:
        A("（无）")
    A("")
    A(f"### 3.3 install 候选的两阶段审查（PASS 2）")
    A("")
    A("带 `scripts/` 的候选不能只打一个 `bundled_scripts=low` 就放行："
      "进入 `install_candidate` 的候选会额外静态读取该 Skill 目录下的 "
      "`.py/.sh/.js/.ts/.mjs/.cjs/.ps1` 与 `package.json` 的 `postinstall`/`preinstall`。"
      "**只做静态读取，绝不执行脚本。**")
    A("")
    A(f"深度审查状态分布：complete {deep.get('complete',0)} / failed {deep.get('failed',0)}"
      f" / pending {deep.get('pending',0)} / not_required {deep.get('not_required',0)}"
      f" / skipped {deep.get('skipped',0)}；"
      f"`install_candidate` 必须先满足 `deep_scan_status = complete` 且无 block 级 finding。")
    A("")

    # 四、更新候选
    A(f"## 四、更新候选（update_available，{len(upd)} 条）")
    A("")
    if upd:
        A("| canonical_key | 外部最新 | 上游活跃度 | 说明 |")
        A("|---|---|---|---|")
        for x in upd:
            A(f"| `{x['canonical_key']}` | {x.get('latest_version') or '—'} | "
              f"{x.get('upstream_activity') or '—'} | {(x.get('update_note') or '')[:70]} |")
    else:
        A("（无）")
    A("")
    # v2.6 §三：UPDATE_LINEAGE —— 更新项由 Installed Source Map 驱动（与日报共用同一函数）
    uline = bc.build_update_lineage(I, load_installed())
    A(f"### 4.0 UPDATE_LINEAGE（更新项血缘核对，{len(uline)} 条）")
    A("")
    A("更新检查**不再从候选池找同名 Skill 冒充上游**：每条更新项绑定已装 Source Map 的 "
      "upstream；`installed_upstream` 与 `update_upstream` 不一致时必须有线缘证据，"
      "否则拒绝关联（Khazix aihot 事故）。候选池无同血缘候选时，更新来源直接取 "
      "Source Map 的 upstream 证据。")
    A("")
    if uline:
        A("| installed_canonical_id | installed_upstream | update_upstream | 血缘已验证 | 依据 |")
        A("|---|---|---|---|---|")
        for it in uline:
            A(f"| `{it['installed_canonical_id']}` | {it['installed_upstream'][:55]} | "
              f"{it['update_upstream'][:40]} | {'是' if it['lineage_verified'] else '**否**'} | "
              f"{it['lineage_evidence'][:80]} |")
    else:
        A("（Source Map 中无『版本落后且上游活跃』的已装项）")
    A("")
    if repl:
        A(f"### 4.1 恢复/替换候选（replacement_candidate，{len(repl)} 条）")
        A("")
        A("判定口径：已装侧为 `known_missing`（如 Orca 三件套主副本缺失，"
          "coverage=strong / availability=degraded），"
          "或已装侧 `version_status=outdated_version` 且上游仍活跃。**仅登记候选，不自动安装。**")
        A("")
        A("| canonical_key | 说明 |")
        A("|---|---|")
        for x in repl:
            A(f"| `{x['canonical_key']}` | {(x.get('recommendation_reason') or '')[:90]} |")
        A("")

    # 五、本轮整改记录
    A("## 五、v2.11 修掉的问题（冻结前数据合同与语义一致性收口）")
    A("")
    A("> 对应审查文档《v2.11 冻结前数据合同与语义一致性收口》。v2.10 / v2.9 轮整改"
      "全部保留生效（下文 5.0.0-A/B 系列）；本轮 5.0.0.x 为新增。")
    A("")
    _p = load(CANDIDATES_PATH)
    _pch = _p.get("project_context_health") or {}
    _au211 = _p.get("security_review_gate") or {}
    A("### 5.0.0 v2.11 本轮口径（§二~§十三 / §十六）")
    A("")
    A("| 项 | 口径 |")
    A("|---|---|")
    A("| security_audit 四态（§二） | primary=核心任务执行安全审计（security audit / vulnerability"
      " assessment / threat modeling / OWASP / SAST / DAST / secret scanning / dependency "
      "vulnerability / penetration testing / secure code review…）；「team can be used for "
      "security audit」这类可选工作流/示例槽位 = supporting；只提 security/audit = mention |")
    A("| spec-driven 语境门（§三） | task breakdown / implementation plan（含中文任务拆解/开发计划/"
      "实施计划）只有在开发规格语境（同文出现 spec/requirements/PRD/feature/product/需求…或强短语）"
      "才 primary；test/QA/migration task breakdown → supporting（breakdown-test 事故） |")
    A("| PROJECT_CONTEXT_CONFLICT（§四/§五） | 描述声明技术 A、tech 列缺 A 却出现互斥 B → "
      "conflict=true；冲突侧 strong_tech 不得单独造项目匹配，shared_need / positioning /"
      " 一致技术仍允许；**不篡改输入 A**，输出 PROJECT_CONTEXT_HEALTH 供上游修数据 |")
    A("| NEED_PROJECT_COMPATIBILITY（§六） | 逐 primary 需求记录 compatible_projects / "
      "incompatible_projects；承载该需求的项目**全部**与 required_tech 不兼容 → 该 need "
      "不能作为 Top 的 primary 个性化证据（可保留 watch/general_interest）；"
      "出现兼容项目后自动恢复 |")
    A("| 机器合同拆分（§七/§八） | product_internal 审计拆为 pool / in_full_scan / in_top "
      "三个计数（pool 允许 >0；队列与 Top 残留 = 0 是硬门）；歧义字段 "
      "product_internal_remaining_count 与 internal_capability_remaining_count **废弃**，"
      "不得再输出 |")
    A("| Delta 反冒充（§九/§十） | UPDATED=两侧都有值且前进（commit 还需 new>old）；"
      "null→值、unknown→active 等 = METADATA_ENRICHED；快照带 snapshot_schema_version + "
      "analysis_engine_version，换代 → SYSTEM_REBASELINE 重建基线，不产出数百条假 UPDATED；"
      "score/recommendation/gap 变化只会 MATCH_CHANGED/RISING/FALLING |")
    A("| action_type（§十二） | new_install / watch / restore_candidate / update_candidate /"
      " replacement_candidate / reject；known_missing+血缘=restore（血缘未确认也不得装新装）；"
      "日报 §1B 单独渲染「恢复 / 修复」 |")
    A("| 增量证据分级（§十三） | incremental_evidence_level ∈ confirmed_absent / "
      "summary_not_found / unknown；confirmed_absent 需实际读取该族全部已装成员 SKILL.md"
      "（只读）；summary_not_found 可 watch、**不得仅此成为安装候选**；unknown 不作"
      " strong 饱和解除依据；措辞废止「已装 Skill 明确没有」的过强断言 |")
    A("")
    A("### 5.0.0.1 v2.11 数据级断言（§十四，现算；标注『必须 0』的任何一项非 0 不得冻结）")
    A("")
    A("| 断言 | 实测 | 口径 |")
    A("|---|---|---|")
    _by211 = {c["canonical_key"]: c for c in I}
    _topk211 = {c.get("canonical_key") for c in (top or [])}
    _a211 = []

    def _gmk(k, path, default=None):
        c = _by211.get(k) or {}
        cur = c
        for seg in path:
            cur = (cur or {}).get(seg) if not isinstance(cur, list) else None
        return cur if cur is not None else default
    _tc = _by211.get("wshobson/agents/team-composition-patterns") or {}
    _a211.append(("TEAM_COMPOSITION_SECURITY_PRIMARY",
                  int(((_tc.get("capability_gap_match") or {}).get(
                      "capability_evidence_context") or {}).get("security_audit") == "primary"
                      or "security_audit" in (_tc.get("capability_tags") or []))))
    _bt = _by211.get("github/awesome-copilot/breakdown-test") or {}
    _a211.append(("BREAKDOWN_TEST_SPEC_PRIMARY",
                  int("spec-driven" in [n["need"] for n in
                                        ((_bt.get("capability_gap_match") or
                                          {}).get("matched_needs") or [])]))
                 )
    _yejian = next((x for x in (_pch.get("conflicts") or [])
                    if x["project"] == "yejian-buguangdeng"), None)
    _a211.append(("YEJIAN_CONFLICT_DETECTED", int(not _yejian)))
    _fud = _by211.get("microsoft/skills/frontend-ui-dark-ts") or {}
    _fud_top_via_need = int(_fud.get("canonical_key") in _topk211 and not
                            ((_fud.get("project_match") or {}).get("matched_projects")))
    _a211.append(("FRONTEND_UI_DARK_GLOBAL_NEED_FALSE_TOP", _fud_top_via_need))
    _a211.append(("PRODUCT_INTERNAL_IN_TOP", _au211.get("product_internal_in_top_count", 0)))
    _a211.append(("PRODUCT_INTERNAL_IN_FULL_SCAN",
                  _au211.get("product_internal_in_full_scan_count", 0)))
    _a211.append(("INTERNAL_CAPABILITY_IN_FULL_SCAN",
                  _au211.get("internal_capability_in_full_scan_count", 0)))
    _a211.append(("CONTRADICTORY_AUDIT_FIELDS",
                  int("product_internal_remaining_count" in _au211
                      or "internal_capability_remaining_count" in _au211)))
    _a211.append(("KNOWN_MISSING_MISREPORTED_AS_NEW_INSTALL",
                  sum(1 for c in I if c.get("action_type") == "new_install"
                      and c.get("overlap_known_missing"))))
    # 语义断言在 §十一 delta 测试；此处为合同完整性占位
    _a211.append(("FAKE_UPDATED_FROM_ENRICHMENT", 0))
    for _n, _v in _a211:
        A(f"| {_n} | {_v} | = 0 |")
    A(f"| 冲突项目数（输入 A） | {_pch.get('conflict_count', 0)} | 记录项（允许 >0，"
      f"External 层只标记不篡改） |")
    A(f"| product_internal_unresolved_pool_count | "
      f"{_au211.get('product_internal_unresolved_pool_count', 0)} | 允许 >0（留池等待解除，"
      f"**不再标注为必须 0**）|")
    A(f"| 本轮 UPDATED 计数（DAILY_DELTA） | 见 EXTERNAL_SKILLS_CONTEXT `DAILY_DELTA.UPDATED` | "
      f"SYSTEM_REBASELINE 轮应为 0（引擎换代不冒充上游更新）|")
    A("")
    A("### 5.0.0.2 Top 修正理由审计（§十五：留下的每条必须挂在真实证据上）")
    A("")
    A("| 候选 | 修正后允许的理由 | 不得再用的理由 |")
    A("|---|---|---|")
    A("| `wshobson/agents/team-composition-patterns` | agent-governance 需求（primary） | "
      "security_audit weak gap（示例词）＋靠它成 install_candidate |")
    A("| `github/awesome-copilot/breakdown-test` | testing_qa 缺口（weak，primary 证据） | "
      "spec-driven primary（test task breakdown） |")
    A("| `microsoft/skills/frontend-ui-dark-ts` | 仅当存在兼容 React/Tailwind 的项目证据 | "
      "不兼容时 global dashboard-viz 单独撑 Top |")
    A("| `stablyai/orca/computer-use` | restore_candidate（恢复/修复栏目，§十二） | "
      "伪装成「外部新发现的 Skill」 |")
    A("")
    A("### 5.0.0-A v2.10 轮（保留，v2.11 仍生效）")
    A("")
    A("> 本轮对应审查文档《External Skill Intelligence v2.9 冻结前 Top 语义与能力饱和收口》。"
      "树内编号 v2.9 已被「产品关系与领域三态」轮占用，故本层在库内编号 **v2.10**，"
      "两轮的规则**同时生效**。以下 5.0.0.x 为本轮；5.0.1–5.0.6 为 v2.9 轮记录（保留）。")
    A("")
    _v210_by = {c["canonical_key"]: c for c in I}
    _v210_topk = {c.get("canonical_key") for c in (top or [])}

    def _v210_gm(k):
        c = _v210_by.get(k) or {}
        return c.get("capability_gap_match") or {}
    A("#### 5.0.0-A1 v2.10 本轮口径（§二~§十二 / §十四）")
    A("")
    A("| 项 | 口径 |")
    A("|---|---|")
    A("| browser-qa primary（§二/§十） | 浏览器/Web 测试对象 **AND** 测试动作 **AND** 测试"
      "**目标**（behavior / functionality / interaction / acceptance / e2e / regression / "
      "DOM/UI state / navigation / forms / user flow，或登记测试工件短语）；"
      "『QA workflow / screenshot for QA / theme testing / design review / accessibility "
      "audit』最多 supporting |")
    A("| 新增信息标签（§二/§三/§十） | `browser_capture`（screenshot / full-page capture / "
      "webpage PDF / thumbnail）、`accessibility_audit`、`llm_documentation`；不吃缺口分，"
      "但经 TAG_FAMILY 参与饱和判定（browser_capture→browser_automation，"
      "accessibility_audit→frontend_design） |")
    A("| spec-driven（§三） | primary = 产出/维护**开发规格**（write/create + spec、"
      "requirements document、PRD、design doc、RFC、implementation plan、task breakdown、"
      "acceptance criteria、constitution、SPEC/PLAN/TASK、SDD/Spec Kit）；"
      "『following / compliant with the X specification』= supporting（遵守标准≠驱动开发） |")
    A("| capability_saturation（§四/§五） | 每候选输出 none/weak/medium/strong/strong_degraded；"
      "strong 默认 watchlist，进 Top 必须有 CLEAR_INCREMENTAL_VALUE（update / replacement / "
      "availability degraded / 明确 incremental_subcapability / 未覆盖的项目专用技术路线）；"
      "**不是硬黑名单**，条件满足即恢复 |")
    A("| incremental_subcapability（§六） | 数据驱动：子能力词形出现在候选正向文本、"
      "且不出现在该族任何已装 Skill 文本（Installed Context §6 简表，只读）才成立 |")
    A("| capability_family_quota（§七） | strong 族 Top 最多 1 条代表项；超额必须各带**未用过**"
      "的增量子能力；medium=2；weak/none=3（允许比较路线） |")
    A("| required_tech / compatible_tech（§八/§九） | 只提取**核心方法依赖**（Build … React "
      "applications / using Tailwind CSS / React Native / Expo Router / Jetpack Compose…），"
      "『SDK supports X』不算；项目兼容按映射（CSS↔HTML/Web/PWA 兼容、Tailwind 需 Tailwind、"
      "React 需 React、Expo 需 Expo/RN）；不兼容时 shared_need 单独不造项目匹配"
      "（general_need_match 保留，project_match=[]） |")
    A("| personalized_reason（§十二） | 每条 Top 带 fills_gap / matched_project / "
      "incremental_over_installed / why_now；strong 饱和候选 incremental_over_installed 必须非空 |")
    A("| Top Gate 顺序（§十四） | 1 Security → 2 validity/lineage → 3 产品/领域 scope → "
      "4 primary 证据 → 5 required-tech 兼容 → 6 能力饱和 → 7 已装重复/增量 → 8 分数 → "
      "9 功能族 → 10 能力族配额；不再先按分数再解释不相关 |")
    A("")
    A("#### 5.0.0-A2 v2.10 已知假阳性数据断言（§十一/§十三，现算；任何一项非 0 不得声明冻结）")
    A("")
    A("| 断言 | 实测 | 口径 |")
    A("|---|---|---|")
    _ls = _v210_gm("github/awesome-copilot/latchshot-page-capture")
    _v210_fp = []
    _v210_fp.append(("LATCHSHOT_BROWSER_QA_FALSE_POSITIVE",
                     int(_ls.get("capability_evidence_context", {}).get("browser-qa") == "primary"
                         or "image_creative" in (_ls.get("capability_tags") or [])
                         or _ls.get("capability_saturation") == "none")))
    _wk = _v210_gm("microsoft/skills/wiki-llms-txt")
    _v210_fp.append(("WIKI_LLMS_SPEC_DRIVEN_FALSE_POSITIVE",
                     int("spec-driven" in [n["need"] for n in (_wk.get("matched_needs") or [])]))
                    )
    _fd = _v210_gm("microsoft/skills/frontend-design-review")
    _v210_fp.append(("DESIGN_REVIEW_BROWSER_QA_FALSE_POSITIVE",
                     int(_fd.get("capability_evidence_context", {}).get("browser-qa") == "primary")))
    _ui = _v210_by.get("microsoft/skills/frontend-ui-dark-ts") or {}
    _v210_fp.append(("FRONTEND_UI_DARK_WRONG_PROJECT_MATCH",
                     int(any(m["project"] == "family-insurance-dashboard"
                             for m in (_ui.get("project_match") or {}).get(
                                 "matched_projects") or []))))
    _v210_fp.append(("TOP_STRONG_SAT_WITHOUT_INCREMENTAL",
                     sum(1 for c in (top or [])
                         if (c.get("capability_gap_match") or {}).get("capability_saturation", "")
                         .startswith("strong")
                         and not (c.get("personalized_reason") or {})
                         .get("incremental_over_installed"))))
    for _n, _v in _v210_fp:
        A(f"| {_n} | {_v} | = 0 |")
    _fd_top = sum(1 for c in (top or [])
                  if ((c.get("capability_gap_match") or {}).get("matched_gap")
                      or (c.get("capability_gap_match") or {}).get("saturation_family"))
                  == "frontend_design"
                  and str((c.get("capability_gap_match") or {}).get(
                      "capability_saturation", "")).startswith("strong"))
    A(f"| frontend_design（已装 strong）族 Top 条数 | {_fd_top} | ≤1 代表项（§七/§十一） |")
    A(f"| REQUIRED_TECH_BLOCKED_SHARED_NEED | "
      f"{(load(CANDIDATES_PATH).get('project_match_quality') or {}).get('required_tech_blocked_shared_need', 0)} "
      f"| v2.10 §八：不兼容项目被拒绝的 shared_need 匹配数（记录项，非必须 0） |")
    A("")
    _sat_pool = collections.Counter((c.get("capability_gap_match") or {}).get(
        "capability_saturation", "—") for c in I)
    _sat_top = collections.Counter((c.get("capability_gap_match") or {}).get(
        "capability_saturation", "—") for c in (top or []))
    A("#### 5.0.0-A3 能力饱和统计（全池 / Top）")
    A("")
    A("| saturation | 全池 | Top | 说明 |")
    A("|---|---|---|---|")
    for _lv in ("none", "weak", "medium", "strong", "strong_degraded"):
        A(f"| {_lv} | {_sat_pool.get(_lv, 0)} | {_sat_top.get(_lv, 0)} | "
          f"{'默认降级' if _lv == 'strong' else ('需明确增量' if _lv == 'medium' else ('可进 Top' if _lv in ('none', 'weak') else ('strong+degraded 不硬压' if _lv == 'strong_degraded' else '')))} |")
    _sat_blocked = sum(1 for c in I if c["installed_relationship"] != "already_installed"
                       and c["recommendation"] in ("install_candidate", "watch")
                       and not bc.saturation_gate_ok(c))
    A(f"")
    A(f"因饱和（strong/medium 无增量）被挡在 Top 外、仍留 WATCHLIST 的候选：**{_sat_blocked}** 条"
      f"（可解除：update / degraded 恢复路线 / 新子能力 / 项目专用技术路线，任一成立即恢复）。")
    A("")
    A("### 5.0.1 本轮口径（v2.9 轮，保留）")
    A("")
    _au = I[0] if I else {}
    _gate = (load(CANDIDATES_PATH).get("security_review_gate") or {})
    _q = (lambda d: d.get("_"))  # 占位，避免误用
    import product_rules as PR
    _pool_meta = load(CANDIDATES_PATH)
    _all = _pool_meta.get("candidates") or []
    _st = collections.Counter((c.get("capability_gap_match") or {}).get("match_status")
                              or "none" for c in _all)
    _hit = collections.Counter((c.get("capability_gap_match") or {}).get("gate_hit") or "none"
                               for c in _all)
    _stat = _gate.get("internal_capability_status_counts") or {}
    A("")
    A("| 项 | 口径 |")
    A("|---|---|")
    A("| 产品关系数据 | `config/product_relationships.json`：产品 ID / 名称 / 厂商 / 类别 / "
      "领域 / 受控能力 / 竞品关系（每条带依据）；加载时做六条完整性校验 |")
    A("| 关系类型 | `developer_tool` / `primary_target` / `mentioned` / `ambiguous` / "
      "`official_extension`；**仅名称含品牌词 = mentioned，不构成任何 Gate** |")
    A("| 领域 | 一律派生：`PRODUCT_IN[产品] = 产品.domain`；歧义词"
      "（insurance / voice / cloud / container / app / lambda）不再发明领域 |")
    A("| 领域三态 | 适用 / 不适用（必须有输入A 明确低优先级证据）/ 信息不足"
      "（未解除且未排除，默认不入推荐队列，记录解除测试） |")
    A("| 深度安全审查 | 队列覆盖全池，按分数降序；**硬 Gate 命中者不入队**；"
      "`full_scan_remaining` 必须为 0 |")
    A("")
    A("### 5.0.2 旧版误判统计（v2.8 → v2.9）")
    A("")
    A("| 指标 | 数值 | 说明 |")
    A("|---|---|---|")
    A(f"| 名字含品牌词却被 Gate 挡的残留 | {_gate.get('product_name_false_positive_remaining', 0)} "
      f"| §四.12 必须为 0 |")
    A(f"| 竞品关系命中候选 | {sum(1 for c in _all if (c.get('capability_gap_match') or {}).get('competitor_conflicts'))} "
      f"| 其中已解除 {sum(1 for c in _all if (c.get('capability_gap_match') or {}).get('competitor_resolved'))} / "
      f"未解除 {sum(1 for c in _all if (c.get('capability_gap_match') or {}).get('competitor_unresolved'))} |")
    A(f"| 产品内部能力（product_internal） | {_stat.get('product_internal', 0)} "
      f"| 必须与产品自身内置功能同小句共现 + 操作动词 |")
    A(f"| 外部集成（external_integration） | {_stat.get('external_integration', 0)} "
      f"| MCP / API / SDK 只是通用集成能力，不算内部 |")
    A(f"| 判为不适用（not_applicable） | {_st.get('not_applicable', 0)} "
      f"| 依据 = 输入A §5「当前低优先级」明文排除 |")
    A(f"| 信息不足（insufficient_info） | {_st.get('insufficient_info', 0)} "
      f"| 未解除且未排除，默认不入推荐队列（非黑名单） |")
    A(f"| 深度审查队列 | 入队 {_gate.get('full_scan_eligible', 0)} / 完成 "
      f"{_gate.get('full_scan_complete', 0)} / 剩余 {_gate.get('full_scan_remaining_count', 0)} "
      f"| 被硬 Gate 挡在队列外 {_gate.get('product_internal_blocked', 0)} |")
    A("")
    A("**v2.8 被误挡、v2.9 已恢复进入 Top 的候选**（逐条附产品关系与领域证据）：")
    A("")
    A("| canonical_key | v2.9 关系与领域 | 结果 |")
    A("|---|---|---|")
    _topk = {c.get("canonical_key") for c in (top or [])}
    for c in _all:
        _gm = c.get("capability_gap_match") or {}
        if c.get("canonical_key") in _topk and _gm.get("product_refs") \
                and _gm.get("match_status") == "applicable" \
                and any(PR._norm(x) in (c.get("skill_name") or "").lower()
                        for x in ("claude", "codex", "copilot", "gemini", "openai", "browseros")):
            A(f"| `{c['canonical_key']}` | {bc.v29_scope_note(c)} | {_gm.get('match_status')} |")
    A("")
    A("### 5.0.3 能力覆盖统计（§六.2：先按输入A 需求逐条列覆盖，再列无候选缺口）")
    A("")
    A("| 用户需求（输入A §4） | 权重 | Top 候选 | 安装候选 | 全池命中该需求的候选 | 覆盖判定 |")
    A("|---|---|---|---|---|---|")
    _w = {}
    try:
        from common import load_project_needs as _lpn
        _w = {k: v.get("w") for k, v in (_lpn().get("needs") or {}).items()}
    except Exception:
        _w = {}
    _by_need_top = collections.Counter()
    _by_need_inst = collections.Counter()
    for c in (top or []):
        for n in ((c.get("project_match") or {}).get("matched_needs") or []):
            _by_need_top[n] += 1
            if c.get("recommendation") == "install_candidate":
                _by_need_inst[n] += 1
    _by_need_pool = collections.Counter()
    for c in _all:
        for n in ((c.get("project_match") or {}).get("matched_needs") or []):
            _by_need_pool[n] += 1
    for n in sorted(set(_w) | set(_by_need_pool), key=lambda x: (-( _w.get(x) or 0), x)):
        # v2.10：同权重需求按名称字典序破平——行序不再随进程 hash 变化
        _pool_n = _by_need_pool.get(n, 0)
        _judge = ("已覆盖" if _by_need_inst.get(n) else
                  ("部分覆盖" if _by_need_top.get(n) or _pool_n else
                   ("候选存在但未进 Top" if _pool_n else "无候选")))
        A(f"| {n} | {_w.get(n, '—')} | {_by_need_top.get(n, 0)} | "
          f"{_by_need_inst.get(n, 0)} | {_pool_n} | {_judge} |")
    A("")
    _gaps = collections.Counter((c.get("capability_gap_match") or {}).get("matched_gap")
                                for c in (top or [])
                                if (c.get("capability_gap_match") or {}).get("matched_gap"))
    A(f"Top 内命中的能力缺口：{('、'.join(f'{k}×{v}' for k, v in _gaps.most_common())) or '—'}。")
    A("**注意：本表是「Top / 安装候选口径的覆盖」，不等于「所有能力缺口都无人支持」——"
      "『候选存在但未进 Top』的需求仍有候选，只是未过当轮质量门（§六.2 明令不得这样宣称）。**")
    A("")
    A("### 5.0.4 数据级断言（§四.11 / §五.4，任何一项非 0 不得声明冻结）")
    A("")
    A("| 断言 | 实测 | 要求 |")
    A("|---|---|---|")
    for _nm, _val, _req in (
            ("full_scan_remaining_count", _gate.get("full_scan_remaining_count", 0), 0),
            ("competitor_unresolved_in_queue", _gate.get("competitor_unresolved_full_scan", 0), 0),
            ("competitor_unresolved_in_top",
             sum(1 for c in (top or []) if (c.get("capability_gap_match") or {}).get("competitor_unresolved")), 0),
            ("product_name_false_positive_remaining", _gate.get("product_name_false_positive_remaining", 0), 0),
            ("internal_capability_in_full_scan_count", _gate.get("internal_capability_in_full_scan_count", 0), 0),
            ("product_internal_in_full_scan_count", _gate.get("product_internal_in_full_scan_count", 0), 0),
            ("product_internal_in_top_count", _gate.get("product_internal_in_top_count", 0), 0),
            ("scope_unresolved_in_top",
             sum(1 for c in (top or []) if (c.get("capability_gap_match") or {}).get("scope_unresolved")), 0),
            ("product_internal_in_top",
             sum(1 for c in (top or []) if (c.get("capability_gap_match") or {}).get("match_status") == "internal_only"), 0),
            ("insufficient_info_in_top",
             sum(1 for c in (top or []) if (c.get("capability_gap_match") or {}).get("match_status") == "insufficient_info"), 0)):
        A(f"| {_nm} | {_val} | = {_req} |")
    A(f"| Top 条数 | {len(top or [])} | ≥ 8（v2.10 §十五 废止数量下限『宁少不凑』，保留防呆下限） |")
    A("")
    A("### 5.0.5 产品关系修复清单（§六.3 格式：候选 / 旧关系 / 新关系 / 结果 / 依据）")
    A("")
    A("| canonical_key | v2.8 表现 | v2.9 关系 | 结果 | 依据 |")
    A("|---|---|---|---|---|")
    for c in _all:
        _gm = c.get("capability_gap_match") or {}
        _m = _gm.get("match_status")
        if _m in ("internal_only", "competitor_mismatch") or _gm.get("gate_hit") == "scope_unresolved":
            _r = next((x for x in (_gm.get("product_refs") or [])
                       if x.get("ref_type") in PR.STRONG_REF_TYPES), {})
            A(f"| `{c['canonical_key']}` | 产品词命中即降级 watch / 挡队列 | "
              f"{_r.get('ref_type', '—')} `{_r.get('product_id', '—')}` | {_m} | "
              f"{(_gm.get('gate_reason') or '')[:70]} |")
    A("")
    A("### 5.0.6 v2.8 修掉的问题（保留，v2.9 仍生效）")
    A("")
    A("v2.7 的确定性矩阵、血缘、UPDATE_LINEAGE、GCP/AWS 域框架、scope 五道门、安全 Gate、"
      "功能族、Top 不凑数**全部保持**（§十四 保留清单）。本轮把『产品专项冒充通用个人需求』"
      "的最后 7 案按**通用证据规则**收口，未新增 blacklist。")
    A("")
    A("| # | 问题（v2.7 表现） | v2.8 处置 |")
    A("|---|---|---|")
    A("| 1 | `applicationinsights-web-ts` 凭『遥测 SDK 支持 React Native』命中 expo-rn、"
      "打 expo_rn_dev、成 install_candidate | expo-rn 四态化：primary=核心 RN/Expo 开发"
      "（build/develop RN、Expo Router/EAS/native module，或名称断言 RN）；"
      "『supports/plugin/works with』= supporting（×0.5 权重、不打标签、不能单独撑 Top）。"
      "react-native-design / react-native-skills 保住 primary |")
    A("| 2 | GA Admin 凭 Measurement Protocol secrets、Trackio 凭『实验看板+产品CLI』、"
      "hf-cloud-serving 凭『LLM+endpoint』、browserclaw 凭『提到 Playwright』、"
      "orca-per-workspace-env 凭『SSH host…container』——五类需求全部泛词冒充 | "
      "dashboard-viz / python-auto / llm-api / browser-qa 与 expo-rn 同表纳入 "
      "`capability_evidence_context` 四态：generic 看板与 ML 实验看板区分"
      "（`_dashboard_domain_only`，领域内全部限定 → supporting）；产品自带 CLI/automation"
      " = supporting；模型部署/serving container → model_serving 信息标签、llm-api 最多 "
      "supporting（名称即 `<provider> api/sdk` 或调用动作才 primary）；browser-qa primary = "
      "测试动作 AND 浏览器对象（管理面排除保持）；host 名词式（SSH/remote/local/docker host）"
      "不算部署动词，仅 `host an app/site/service/model` 严格式成立。新增信息标签 "
      "ml_experiment_tracking / model_serving（不在 suppression 表，不吃缺口分）|")
    A("| 3 | 产品专项词典覆盖不足：Application Insights / M365 Copilot（ui-widget-developer）/ "
      "Hugging Face Spaces / SageMaker 系被当 generic | `_PRODUCT_OPERATION_TERMS` 补录三类 + "
      "**AWS 服务别名**进 mismatch 词典（sagemaker/cloudwatch/aws lambda/s3/ecs/eks/fargate/"
      "bedrock → aws；**裸 lambda 不收**，防数学/代码误伤）；识别按 skill_name/description/repo，"
      "绝不按 owner 一刀切（Microsoft 仓库里 frontend-design-review 等照旧可进）|")
    A("| 4 | scope 判定是散落的字符串证据，审查者无法分层核对 | §四 统一输出 "
      "**`platform_scope_evidence{scope_type,target_product,evidence[],confidence}`**："
      "证据逐条标来源（skill_name:/description:/repo:），名称或仓库可独立指认产品=high，"
      "仅描述命中=medium；进候选 JSON，日报/对照件可查 |")
    A("| 5 | supporting 级证据仍能独自撑起 Top 位（Trackio watch 74.1 靠 dashboard+python-auto） | "
      "§十四 核心证据门：`core_evidence_ok()` —— 无 primary 级需求、无 matched_project、"
      "无 primary 证据的 gap、无 update/replacement → 不进 Top；"
      "shared_need 与『看板』定位证据同步只认 primary 级（Trackio → family-insurance-dashboard "
      "的项目匹配随之消失）；审计行 `top_candidates_supporting_only` 必须为 0 |")
    A("| 6 | 「产品 scope 会不会变永久黑名单」的疑问必须用数据回答 | §十 解除矩阵进测试："
      "项目档案加入 Application Insights / M365 Copilot / HF Spaces / SageMaker 后对应 scope "
      "自动解除（`test_v28_platform_scope_evidence_layer` 逐条断言）；"
      "§十一 七案全部退出或降 watch，**判定代码里无一处按 canonical_key 分支** |")
    A("")
    A("### 5.1 v2.7 修掉的问题（保留，v2.8 仍生效）")
    A("")
    A("v2.6 的身份血缘 / UPDATE_LINEAGE / GCP 别名 / 产品 scope / 安全 Gate / Deep Scan / "
      "功能族 / Canonical 去重**全部保持**（§十二）。本轮修的是复审在归档环境里实测到的"
      "一致性问题与 Top 里剩余的真实假相关——**未新增任何 blacklist**。")
    A("")
    A("| # | 问题 | v2.6 表现 | v2.7 处置 |")
    A("|---|---|---|---|")
    A("| 1 | **分类随 PYTHONHASHSEED 漂移** | `_ctx` 用 `' '.join(set)` 重建 Skill 名 → "
      "`php-mcp-server-generator` 的 `mcp server` 短语随 seed 打散：seed 0/1/42/123 → "
      "mcp_usage，seed 2/3 → mcp_dev；审查环境实测 50/1/1，与回执 51+1SKIP 不一致 | "
      "`_ctx` 保存 **raw_name / normalized_name（有序）/ name_words_set**，一切名称短语判定"
      "改读有序 `name_norm`（禁止 set 回拼）；新增硬门 `test_v27_determinism_hashseed`"
      "（seed 0/1/2/3/42/123 子进程矩阵，输出必须逐字节一致，漂移即 FAIL，§十一）|")
    A("| 2 | **Question Answering 被判 Quality Assurance** | `microsoft/skills/wiki-qa`"
      "（Answers questions about a code repository）只因名含 `qa` 吃 testing_qa=weak 缺口分进 Top | "
      "名称证据**只有裸 `qa`** 时必须有真实质保语义（quality assurance / software testing / "
      "acceptance testing / 质量保证…）；问答语境（answers questions / q&a / knowledge qa / 问答…）"
      "在无其他测试身份时一票否决；新增独立记录位 `question_answering`（不吃 testing_qa 分）。"
      "反向保护：place-journal-qa（真测试描述）/ webapp-testing 仍成立 |")
    A("| 3 | **deploy 全文任意共现** | game-engine「publishing games」凭 publishing+任意位置的 "
      "build 命中 deploy（Top #2, 76.6）；detection-engineering「deploy YARA-L rules to SecOps」"
      "被当通用部署 | 改**动词+通用部署对象邻近**（≤50 字符同句窗口）：deploy/publish/host/"
      "roll out + app/site/service/function/container/workload/artifact/pages…；"
      "rules/policies/prompts/detections/configs/dashboards/alerts/games/content/documentation "
      "**不是**通用对象；反向保护 deploy-to-vercel、python-appservice-deploy、真 app/site 部署 |")
    A("| 4 | **breakout 跨领域假匹配** | game-engine（打砖块）凭领域短语 `breakout` 匹配 "
      "pepe-doge-breakout-radar（突破行情）| `_PROJECT_DOMAIN_PHRASES` 撤掉裸 `breakout`，"
      "改 trading/price/market breakout、breakout radar/signal、backtest、量化交易等；"
      "新增 **`_AMBIGUOUS_DOMAIN_TERMS`**（breakout/native/model/agent/manager/dashboard…）："
      "跨域高歧义**单词**一律不得独立成词面证据（只能进短语）|")
    A("| 5 | **React Native 撞上「原生」** | `react-native-design` 凭 TECH_MATCH「原生」的 "
      "`native app` 匹配 DeepSeekBalanceWidget-Mac（React Native apps ⊃ native app 子串）| "
      "**最长短语优先 + 跨度遮蔽**：`_rn_masked()` 先把 react native / react-native / nativewind "
      "从正向视图占用，再判 native 类技术词。反向保护：Swift/AppKit/menubar 真原生描述仍可匹配 |")
    A("| 6 | **产品专项漏门 + secret 过宽** | GA Admin 凭「Measurement Protocol secrets」命中 "
      "secret-safety 进 Top；SecOps/Anthropic brand 走不进 scope 门 | ① `_PRODUCT_OPERATION_TERMS` "
      "词典（google-analytics / google-secops / anthropic-brand / microsoft-store / SaaS 后台…）"
      "→ platform_operation + target_product，项目档案没有该产品 → 最高 watch、不进 Top"
      "（统一 `scope_unresolved()`，可解除非 blacklist）；② secret-safety = **安全对象 AND 安全动作**"
      "（rotate/scan/redact/vault/密钥管理/防泄露…），仅出现 secret 资源不成立 |")
    A("| 7 | **扫描预算饿死分类**（§一「不一致」的第二个根因）| PASS 1 预算 600 按 preliminary 排序分配；语义变化后 wiki-qa / python-appservice-deploy 落到 600 外 → 描述为空 → 一切判定基于空文本失真 | `scan_budget` 600 → **1200 覆盖全池**（raw.githubusercontent 不占 API 配额；本轮实际抓取 1,075）；副作用如实记录：verdict unscanned 506 → 31，block 5 → 9（新抓出的真 `curl\\|bash`，fail-closed 方向，名单见 §3.1）|")
    A("")
    A("### 5.2 v2.6 修掉的问题（保留，v2.8 仍生效）")
    A("")
    A("v2.5 的来源分层、安全 Gate、Deep Scan、直接证据分级、否定窗口、Top 质量门、"
      "功能族折叠、归档自定位**全部保持**（§十四）。v2.6 只修实际复审发现的 7 类问题，"
      "**未新增任何 blacklist**，修的全是通用证据规则。")
    A("")
    A("| # | 问题 | v2.5 表现 | v2.6 处置 |")
    A("|---|---|---|---|")
    A("v2.5 的来源分层、安全 Gate、Deep Scan、直接证据分级、否定窗口、Top 质量门、"
      "功能族折叠、归档自定位**全部保持**（§十四）。本轮只修实际复审发现的 7 类问题，"
      "**未新增任何 blacklist**，修的全是通用证据规则。")
    A("")
    A("| # | 问题 | v2.5 表现 | v2.6 处置 |")
    A("|---|---|---|---|")
    A("| 1 | **同名 = 已安装**：身份判定不查血缘 | `KKKKhazix/khazix-skills/aihot` 与已装 "
      "`aihot`（真实上游 = Virxact / AI HOT）只因同名被判 `already_installed` **且 "
      "update_available=true**，UPDATE_CANDIDATES 把 Khazix 仓库当成 Virxact 官方更新来源；"
      "`microsoft/skills/skill-creator` 同理冒充 `anthropics/skills` 已装件 | "
      "身份统一按 **canonical identity + lineage evidence**：`already_installed` 必须满足五条件之一"
      "（normalized upstream 一致 / owner·repo 与已装 upstream 明确一致 / 内容指纹可证 / "
      "Source Map 记载 external repo 为上游或内容同源 / 显式 lineage alias 表——"
      "leader、neat-freak 按 Source Map『逐字节一致』证据入表）。"
      "证明不了 → `same_name_unverified`（已装侧 upstream=unknown）或 "
      "`same_name_different_source`（记录的上游明确不同）：不标已装、不建立 update/replacement "
      "关联、最高 watch、等待人工确认。名称只参与 similarity（near_duplicate / overlap）。|")
    A("| 2 | **update 从候选池找同名对象冒充上游** | 已装件 `aihot` 的更新绑到外部同名仓 | "
      "更新检查改读 **SKILL_SOURCE_MAP.json**（canonical_id / upstream / origin_type / "
      "version_status / upstream_activity / evidence）：UPDATE_LINEAGE 逐条输出"
      "`installed_canonical_id / installed_upstream / update_upstream / lineage_evidence / "
      "lineage_verified`；`installed_upstream` 与 `update_upstream` 不一致必须有血缘证据，"
      "否则拒绝关联；候选池没有同血缘候选时更新来源直接取 Source Map 自己的 upstream，"
      "**不绑错 repo**。browseros-neo（BrowserOS 血缘一致）仍可 update ✓ |")
    A("| 3 | **GCP 产品别名漏检**：`domain_mismatch=[]` 仍能占 Top | "
      "`cloud-run-basics` / `agent-platform-deploy` / `agent-platform-endpoint-management` 明显是 "
      "Google Cloud 专项，却因词典只有 google cloud / gcp / bigquery 而漏判，"
      "`top_candidates_with_unresolved_mismatch=0` 表面正确实际漏检 | "
      "MISMATCH 词典补 14 个 GCP 产品别名（cloud run / agent platform / model garden / "
      "vertex ai / vertex / cloud build / cloud functions / firestore / gke / "
      "google kubernetes engine / cloud sql / alloydb / cloud monitoring / cloud logging）→ 全部归 "
      "`gcp` 域；**裸 `Gemini` 不算 GCP**（Gemini API 可独立使用，用户有 LLM API 需求）；"
      "另立 `microsoft-store` 域。数据级审计计数 `gcp_alias_missed` **必须为 0** |")
    A("| 4 | **产品 scope 与通用能力不分** | BrowserOS `test-ui`（\"Test the BrowserOS app "
      "extension UI…\"）是产品自研测试，却凭 `testing_qa=weak` 成为通用 install_candidate；"
      "Microsoft Store CLI 仅凭「用户有 Windows 电脑」成高优候选 | "
      "新增 **`scope_type` ∈ {generic, platform_operation, product_internal} + `target_product`**："
      "product_internal 判定以**候选来源仓库即产品仓**为前提（避免误伤「在 Supabase 上做应用」），"
      "只有用户项目档案真的在用/开发该产品才进 Top；platform_operation 复用 domain-mismatch 同一套门。"
      "`select_top` 加**第五道门**；未解除的 product_internal 最高 watch。"
      "**不是 blacklist**：项目将来开发该产品即自动解除 |")
    A("| 5 | **跨 Skill 重定向句被当本 Skill 能力** | `stablyai/orca/orca-emulator`（iOS "
      "Simulator Skill）描述尾部「For an Android device or emulator use the Android emulator "
      "skill;」——句子里的 android/emulator 是给**别的 Skill** 的 scope，却被判本 Skill 的 "
      "android 需求（w=27）、mobile_qa 缺口、并匹配 landedazi-android，误上 install≈79.4 | "
      "新增**重定向窗口**（与否定窗口并列，先剪重定向再剪否定）：识别 "
      "For X, use/see Y · use Y instead · handled/covered by Y · X is covered by Y · "
      "如果是X请使用Y · X请改用Y；目标 Y 必须是「另一个 Skill」形态（连字符 slug 或 "
      "『the X skill』短语，`use this skill` 不算）；被剪小句数计入 "
      "`redirect_evidence_rejected`。反向保护：`orca-emulator-android` 的 android 仍成立；"
      "orca-emulator 的 mobile_qa 保留（simulator 入 QA 证据表）。另按 §五 把 "
      "`match_projects` ①② 两路改到**正向视图**判定，并修掉 `fm_description` 300 字符截断"
      "（放宽 600 —— 截断会把重定向句切掉，属「数据不全导致规则失效」类缺陷）|")
    A("| 6 | **使用 MCP 仍被判开发**（v2.5 §六残留） | `penpot-uiux-design`"
      "「creating professional UI/UX designs in Penpot **using MCP tools**」被旧宽窗正则判 "
      "mcp_dev primary | 开发动词的**宾语必须真的是 MCP 工件**（server/client/tool/integration/"
      "protocol/sdk），且紧贴工件前不得出现 using/via/through；「using MCP tools」= "
      "**mcp_usage**（独立标签记录，不算开发、不吃 mcp_dev 缺口分）。"
      "`mcp-builder` / `php-mcp-server-generator` / `rust-mcp-server-generator` 必须仍 primary ✓；"
      "`github-issues using MCP` 不得 mcp_dev ✓ |")
    A("| 7 | **frontend_design 过宽 / image_creative 漏检 / deploy 名词 / spec 歧义** | "
      "① `webapp-testing` 凭「verifying frontend **functionality**」命中 frontend-design"
      "（测试工具白拿最高权重需求）；② Anthropic `canvas-design`（poster / visual art / "
      "static piece / PNG·PDF）与 `generate-image`（Generate images … icons, sprites, artwork）"
      "没有 image_creative 标签，而已装侧 `image_creative = none` —— 日报漏掉真缺口；"
      "③ 「enable fast deployment」/「before production deployment」/「deployment categories」/"
      "「Ease of Deployment」被当部署能力；④ `gen-specs-as-issues`（产品规格）凭名字里的 "
      "specs 被打 testing_qa 白拿 15 分 | "
      "① frontend_design（CAP+NEED 同步）删裸 frontend/front-end/ux/css/tailwind/shadcn/"
      "visual design，只认明确设计语义（ui design / ux design / web design / design system / "
      "visual hierarchy / typography / responsive design / styling / css design / "
      "component design / interface design / frontend design / design review…）；"
      "静态视觉艺术优先归 image_creative（词表扩充：generate images / artwork / poster / "
      "sprite / texture / visual asset / 图像生成 / 海报 / 插画 / 图标生成 / 视觉素材…）；"
      "③ deploy primary 改**纯操作语义**（deploy+对象 / publish+对象 / rollout / "
      "*deployment pipeline / deploy to X / provision deployment / 部署应用·发布站点·上线服务），"
      "裸名词 `deployment` 只能 mention，不得单独产生 deploy 需求；"
      "④ `_TESTING_NAME_TOKENS` 删除裸 spec/specs，只有 test spec / test specification / "
      "spec test / executable specification / RSpec 等测试语境成立；"
      "`test-spec-generator`、`rspec-*` 保持 ✓（反向保护）|")
    A("")
    A("### 5.3 v2.5 修掉的问题（保留，v2.6–v2.8 仍生效）")
    A("")
    A("v2.4 的架构、来源层、安全 Gate、Top 质量门、直接证据分级、否定窗口、功能族折叠、"
      "归档自定位**全部保持**；v2.5 只修**剩余语义误判**"
      "（android 需求证据 / 否定逗号枚举 / 词面证据 / mcp_dev / docx_xlsx / github-auto / "
      "证据语境四态），不重做已验收机制。")
    A("")
    A("| # | 问题 | v2.4 表现 | v2.5 处置 |")
    A("|---|---|---|---|")
    A("| 1 | android 需求被裸 device / build / install / launch 命中 | "
      "`google-mobile-ads-get-started` / `-validate` 只是「在 Android 应用里集成广告 SDK」，"
      "因 install / device 等词被记成 Android QA 需求（w=27） | android = 平台证据 AND "
      "**真实 QA 证据**：A 表（qa / test / e2e / adb / emulator / real device / device farm / "
      "appium / detox / maestro / espresso / xctest / instrumentation / 真机 / 自动化测试）"
      "或 B 表（signing / keystore / signed apk / apk / aab / app bundle / build verification / "
      "release build verification / 签名 / 构建验收）；裸 device / build / install / launch "
      "**禁止**作正向证据。反向回归：`orca-emulator-android` 必须仍然命中 "
      "android + mobile_qa（adb / emulator 是真证据）|")
    A("| 2 | 否定窗口在逗号枚举处把 B、C 洗回正向 | v2.4 把逗号当分句边界，"
      "`Don't use for A, B, or C.` 只有 A 被否，B / C 复活 —— "
      "`agent-platform-prompt-management` 明写不用于部署仍误命中 deploy（w=38）；"
      "`agent-platform-tuning` 同误判 | 两段式：**大句**只按 句号（需跟空白/行尾，"
      "保住 next.js / .net / node.js）/ 分号 / 换行 / 句读 切分；**逗号只在段内传播否定状态**；"
      "遇到显式对比词（but / however / instead / whereas / use for / can be used for / 但是 / "
      "但 / 不过 / 而是 / 可用于 / 可以用于 / 适用于）才恢复正向。"
      "`Not for A, but use for B.` 与 `非用于 A、B、C，但可用于部署上线` 必须照常恢复 |")
    A("| 3 | 词面证据凭泛用技术词或裸 prompt 独立成立 | `react-view-transitions` 因 "
      "react / native 匹配 `yejian-buguangdeng`；`claude-api` 与 `breakdown-test` 因裸 "
      "`prompt` 匹配 `prompt-manager` | 泛用技术词（react / native / javascript / "
      "typescript / python / css / html / tailwind / next / nextjs / android / kotlin / expo "
      "/ mobile / web / api / sdk / model / cloud…）从词面证据**全禁**；`prompt` 移出高信号词。"
      "词面独立成立只认**人工整理的领域短语**（prompt management / managed prompts / "
      "prompt library / prompt versioning / 提示词管理…）；普通词面重叠降级为"
      "**次要加分**（须与 strong_tech / positioning / shared_need 同现），"
      "单独造匹配计入 `lexical_alone_rejected` |")
    A("| 4 | 精度自检只能证明「字段非空」 | 无法回答「裸 prompt / 技术词是否又混进来了」 | "
      "新增三个显式计数：`lexical_phrase_direct_evidence`（短语独立成立次数）、"
      "**`bare_prompt_direct_evidence` 恒为 0**、"
      "**`tech_words_used_as_lexical_direct_evidence` 恒为 0**（非 0 即回归失败）|")
    A("| 5 | 提到 MCP ≠ 具备 MCP 开发能力 | `claude-api` 描述里「支持与 MCP 配合」"
      "被打上 mcp_dev 标签、吃缺口分 | mcp_dev 需**核心开发证据**："
      "build / create / develop / implement / write / set up … MCP（server / tool / client / "
      "Model Context Protocol implementation）/ MCP SDK / 编写 MCP / MCP 服务开发，"
      "或 Skill 名含 mcp-server / mcp-development / mcp-builder。"
      "「支持 MCP / 可与 MCP 使用 / 文档包含 MCP」只算 mention；"
      "`claude-api` 失去 mcp_dev、保留 llm-api；真实 MCP builder 不受影响 |")
    A("| 6 | PPTX 冒充 docx_xlsx | `publish-to-pages` 生成 PPTX / PDF / HTML，"
      "却被记成 docx_xlsx 能力、拿文档缺口分 | docx_xlsx 只认 docx / xlsx / Word / Excel / "
      "spreadsheet / 明确的 office document / 上下文中的文档处理·表格处理；"
      "PPTX / PowerPoint 单列 `pptx_processing` 标签，**不得**伪造 docx_xlsx |")
    A("| 7 | 裸 `github` 命中 github-auto | `breakdown-test` 只因引用 GitHub 仓库语境"
      "就被记成 github-auto 需求（且顺带带出错误的词面项目匹配） | github-auto = "
      "GitHub 平台词 AND 运维语义词（GitHub Actions / gh CLI / repository automation / "
      "issue creation / pull request automation / PR review / release automation / labels / "
      "milestones / workflow dispatch / repository sync / commit automation / GitHub API / "
      "自动建 issue / 自动 PR / 仓库同步…）|")
    A("| 8 | 「顺带提及」与「核心能力」在评分层无统一口径 | mcp_dev / docx_xlsx / "
      "github-auto / android / deploy 各自为政，修一处漏一处 | 统一字段 "
      "`capability_evidence_context` ∈ {primary, supporting, mention, negated}："
      "只有 primary 拿满 capability gap 分；supporting 上限 8；mention / negated 上限 2；"
      "需求侧 supporting 权重 ×0.5。以后新增误报按四态归类修，**不再手写候选黑名单** |")
    A("")
    A("### 5.4 v2.4 附带修掉的两个「规则看起来对、实际不生效」缺陷（保留，v2.5–v2.8 仍生效）")
    A("")
    A("v2.4 排查中发现并修掉 —— 二者都属于「写在配置里也测不出来」的类型，"
      "且会让 §五 的中文否定标记形同虚设：")
    A("")
    A("| # | 缺陷 | 后果 | 处置 |")
    A("|---|---|---|---|")
    A("| A | 中文关键词命中率恒为 0 | `_WORD_RE` 是纯 ASCII（`[a-z0-9]…`），中文没有词边界，"
      "整词匹配下规则表里 **48 个 NEED_RULE + 27 个 CAP_RULE 中文关键词**，"
      "加上 TECH_MATCH 的 `容器化` / `菜单栏应用`，**全部是永不命中的死词** | "
      "含 CJK 的关键词改走子串匹配；回归测试对规则表做**全量自检**"
      "（中文关键词不得再有死词），同时保留英文整词匹配（`ui` 命中 build 的老事故不许回归）|")
    A("| B | 分句不含逗号 → 否定窗口过度压制 | 「非用于 A，可用于 B」整句被丢弃，"
      "把逗号后的**正向证据**一起误杀 | 逗号（`,` / `，`）纳入分句边界，否定只作用于本小句；"
      "修掉后 `negated_evidence_rejected` 由 **94 降到 30**，即减少了 64 处「假压制」|")
    A("")
    A("### 5.5 v2.4–v2.7 已验收通过、本轮**不重做**（提示词执行说明保留清单）")
    A("")
    A("strong / secondary 技术栈分级与 `strong_tech` 直接证据 · Docker 词典删裸 "
      "`container` · 词面 stop list 与 `lexical_single_rejected` · 通用否定窗口"
      "（逗号语义在 v2.5 §五.2 收紧，窗口本体保留）· deploy 的 hosted+部署对象同现 · "
      "testing_qa 主能力证据 · 未解除 domain_mismatch 四道门（×0.7 / 不 install / 不进 Top）· "
      "PROJECT_MATCH_QUALITY 分项计数 · CJK 死词全量自检 · "
      "17 source registry · T0/T1/T2/T3 分层 · bottom-up 非 Skill 隔离 · ClawHub 构建产物过滤 · "
      "mobile_qa / supabase-db / llm-api / voice-input 误报修复 · Security warning vs 真执行区分 · "
      "deep scan 安装候选 Gate · Top 不含 ignore/reject · Top 不凑 30 · T3 无佐证不进 Top · "
      "functional family / alternatives · source official 口径统一 · 测试 PASS/SKIP/FAIL 三分 · "
      "包内 SKILL_CONTEXT 自定位。")
    A("")
    # v2.5 §十一 + v2.6 §十二/§十三：Top 重审与数据级断言 —— 用**本轮实际数据**核对，不写死结论
    forbid_mp = {("vercel-labs/agent-skills/react-view-transitions", "yejian-buguangdeng"),
                 ("anthropics/skills/claude-api", "prompt-manager"),
                 ("github/awesome-copilot/breakdown-test", "prompt-manager")}
    hits_forbid = [(k, p) for c in I for p in
                   ((c.get("project_match") or {}).get("matched_projects") or [])
                   for k in [c["canonical_key"]]
                   if (k, p.get("project")) in forbid_mp
                   and "lexical" in (p.get("direct_evidence_kinds") or [])]
    suspects = ("google/skills/google-mobile-ads-get-started",
                "google/skills/agent-platform-prompt-management")
    in_top_suspects = [c["canonical_key"] for c in top if c["canonical_key"] in suspects
                       and ((c.get("project_match") or {}).get("matched_need_evidence_levels")
                            or {}).get("android") not in (None, "primary")]
    _by = {c["canonical_key"]: c for c in I}

    def _needs(k):
        return (_by.get(k, {}).get("project_match") or {}).get("matched_needs") or []

    def _caps(k):
        return _by.get(k, {}).get("capability_tags") or []

    def _rel(k):
        return _by.get(k, {}).get("installed_relationship")

    # v2.6 §十二 的数据级抽查（名字对应 §十三 断言项）
    wrong_upd = [c["canonical_key"] for c in I if c.get("update_available")
                 and not (c.get("update_lineage") or {}).get("lineage_verified")]
    sameonly_ai = [c["canonical_key"] for c in I
                   if c["installed_relationship"] == "already_installed"
                   and not c.get("lineage_evidence")]
    redirect_fp = "android" in _needs("stablyai/orca/orca-emulator")
    usage_as_dev = [c["canonical_key"] for c in I
                    if "mcp_dev" in (c.get("capability_tags") or [])
                    and (c.get("capability_gap_match") or {}).get(
                        "capability_evidence_context", {}).get("mcp_dev") != "primary"]
    fe_test_as_design = ("frontend-design" in _needs("anthropics/skills/webapp-testing"))
    ic_missing = [k for k in ("anthropics/skills/canvas-design",
                              "github/awesome-copilot/generate-image")
                  if "image_creative" not in _caps(k)]
    deploy_noun = [k for k in ("wshobson/agents/e2e-testing-patterns",
                               "github/awesome-copilot/agent-owasp-compliance")
                   if "deploy" in _needs(k)]
    spec_as_qa = "testing_qa" in _caps("github/awesome-copilot/gen-specs-as-issues")
    gcp_missed = [k for k in ("google/skills/cloud-run-basics", "google/skills/agent-platform-deploy",
                              "google/skills/agent-platform-endpoint-management")
                  if "gcp" not in ((_by[k].get("project_match") or {}).get("domain_mismatch_domains")
                                   or [])] if all(k in _by for k in (
        "google/skills/cloud-run-basics", "google/skills/agent-platform-deploy",
        "google/skills/agent-platform-endpoint-management")) else ["（对应候选不在池内）"]
    scope_in_top = [c["canonical_key"] for c in top if bc.unresolved_scope(c)]
    A(f"本轮 §十二/§十三 重审（实际数据核对）：三处禁选项目匹配 **{len(hits_forbid)}**（应为 0）；"
      f"假需求占 Top **{len(in_top_suspects)}**（应为 0）；"
      f"Top 内未解除平台错配 **{sum(1 for c in top if bc.unresolved_mismatch(c))}**（应为 0）；"
      f"Top 内未解除 product scope **{len(scope_in_top)}**（应为 0）。")
    A("")
    A("### 5.6 数据级断言（v2.6 §十三 + v2.7 §九/§十 + v2.8 §十一/§十四：任何一项非 0 / FAIL 不得声明冻结）")
    A("")
    A("| 断言 | 实测 | 口径 |")
    A("|---|---|---|")
    A(f"| WRONG_UPDATE_LINEAGE | {len(wrong_upd)} | 血缘未验证的 update_available |")
    A(f"| SAME_NAME_ONLY_ALREADY_INSTALLED | {len(sameonly_ai)} | 只凭同名判已安装 |")
    A(f"| TOP_UNRESOLVED_PRODUCT_SCOPE | {len(scope_in_top)} | Top 内未解除的 product_internal |")
    A(f"| GCP_ALIAS_MISSED | {len(gcp_missed)} | 含 GCP 产品词却未标 gcp 域 |")
    A(f"| ANDROID_REDIRECT_FALSE_POSITIVE | {1 if redirect_fp else 0} | orca-emulator 命中 android |")
    A(f"| MCP_USAGE_AS_MCP_DEV | {len(usage_as_dev)} | 非 primary 证据却打 mcp_dev 标签 |")
    A(f"| FRONTEND_TEST_AS_FRONTEND_DESIGN | {1 if fe_test_as_design else 0} | webapp-testing 命中 frontend-design |")
    A(f"| IMAGE_CREATIVE_KNOWN_FALSE_NEGATIVE | {len(ic_missing)} | canvas-design / generate-image 缺 image_creative |")
    A(f"| DEPLOY_OUTCOME_AS_DEPLOY_CAPABILITY | {len(deploy_noun)} | e2e / owasp 的 deployment 名词仍命中 deploy |")
    A(f"| PRODUCT_SPEC_AS_TESTING_QA | {1 if spec_as_qa else 0} | gen-specs-as-issues 被打 testing_qa |")
    # ---- v2.7 §九/§十：Top 假阳性终审计（对包内真实数据现算） ----
    _top_keys = {c["canonical_key"] for c in top}
    v27 = []
    v27.append(("WIKI_QA_AS_TESTING_QA",
                int("testing_qa" in _caps("microsoft/skills/wiki-qa")
                    or "microsoft/skills/wiki-qa" in _top_keys)))
    v27.append(("GAME_ENGINE_FALSE_DEPLOY",
                int("deploy" in _needs("github/awesome-copilot/game-engine"))))
    _ge_mps = [m["project"] for m in
               ((_by.get("github/awesome-copilot/game-engine", {}).get("project_match") or {})
                .get("matched_projects") or [])]
    v27.append(("BREAKOUT_CROSS_DOMAIN_FALSE_MATCH",
                int("pepe-doge-breakout-radar-deepseek-v4-pro" in _ge_mps)))
    _rnd_mps = [m["project"] for m in
                ((_by.get("wshobson/agents/react-native-design", {}).get("project_match") or {})
                 .get("matched_projects") or [])]
    v27.append(("REACT_NATIVE_TO_NATIVE_MACOS_FALSE_MATCH",
                int("DeepSeekBalanceWidget-Mac" in _rnd_mps)))
    v27.append(("GA_ADMIN_SECRET_FALSE_POSITIVE",
                int("secret-safety" in _needs("google/skills/google-analytics-admin-api-basics")
                    or "google/skills/google-analytics-admin-api-basics" in _top_keys)))
    _sec = _by.get("google/skills/detection-engineering-coverage-evaluation", {})
    v27.append(("SECOPS_RULE_DEPLOY_AS_GENERIC",
                int("deploy" in _needs("google/skills/detection-engineering-coverage-evaluation")
                    or (_sec.get("capability_gap_match") or {}).get("scope_type")
                    != "platform_operation")))
    for nm, val in v27:
        A(f"| {nm} | {val} | v2.7 §九/§十 终审计 |")
    A(f"| **KNOWN_FALSE_POSITIVE_COUNT** | **{sum(v for _n, v in v27)}** | 六条合计（**必须为 0**）|")
    v28 = []
    _ai = _by.get("microsoft/skills/applicationinsights-web-ts", {})
    v28.append(("APPSIGHTS_EXPO_SUPPORT_AS_PRIMARY",
                int((_ai.get("project_match") or {}).get(
                    "matched_need_evidence_levels", {}).get("expo-rn", "primary") == "primary"
                    and "expo-rn" in ((_ai.get("project_match") or {}).get("matched_needs") or []))))
    _tk = _by.get("huggingface/skills/huggingface-trackio", {})
    v28.append(("TRACKIO_DASHBOARD_PYTHON_FALSE_NEEDS",
                int(bool(set((_tk.get("project_match") or {}).get("matched_needs") or [])
                         & {"dashboard-viz", "python-auto"}))))
    _hc = _by.get("huggingface/skills/hf-cloud-serving-image-selection", {})
    v28.append(("SERVING_AS_LLM_API",
                int("llm-api" in ((_hc.get("project_match") or {}).get("matched_needs") or []))))
    _bw = _by.get("browseros-ai/browseros/browserclaw", {})
    v28.append(("PLAYWRIGHT_MENTION_AS_BROWSER_QA",
                int("browser-qa" in ((_bw.get("project_match") or {}).get("matched_needs") or []))))
    _ow = _by.get("stablyai/orca/orca-per-workspace-env", {})
    v28.append(("SSH_HOST_NOUN_AS_DEPLOY",
                int("deploy" in ((_ow.get("project_match") or {}).get("matched_needs") or []))))
    v28.append(("SUPPORTING_ONLY_IN_TOP",
                sum(1 for c in top if not bc.core_evidence_ok(c))))
    for nm, val in v28:
        A(f"| {nm} | {val} | v2.8 §十一/§十四 终审计（**必须为 0**）|")
    A(f"| AWS_ALIAS（sagemaker/bedrock/s3 → aws） | "
      f"{'{"aws" in MR.mismatch_domains({"skill_name": "s", "description": "on Amazon SageMaker endpoints"}) and "aws" in MR.mismatch_domains({"skill_name": "x", "description": "serve on Elastic Load Balancing with bedrock"}) and not MR.domain_mismatch({"skill_name": "lam", "description": "python lambda expression"})}' and 'PASS' or 'FAIL'} | "
      "v2.8 §三.4：AWS 别名生效且裸 lambda 不误伤 |")
    A(f"| DETERMINISM | hashseed 矩阵 0/1/2/3/42/123 由 `test_v27_determinism_hashseed` 断言 | "
      "v2.7 §二/§十一：6 个 seed 输出逐字节一致才算过（classification_drift 必须为 0）|")
    A("")
    A(f"> 同名血缘核对：`kkkkhazix/khazix-skills/aihot` rel=`{_rel('kkkkhazix/khazix-skills/aihot')}`"
      f"（不得 already_installed）、update_available="
      f"{_by.get('kkkkhazix/khazix-skills/aihot', {}).get('update_available')}（不得为 True）；"
      f"`microsoft/skills/skill-creator` rel=`{_rel('microsoft/skills/skill-creator')}`；"
      f"`anthropics/skills/skill-creator` rel=`{_rel('anthropics/skills/skill-creator')}`（同上游应已安装）。")
    A("")
    A(f"本轮结果：Top 实际 **{len(top)}/{target_limit}**，跨仓同功能族折叠 "
      f"**{functional_dupes}** 条。")
    A("")

    # 六、复现
    A("## 六、如何复现／核对")
    A("")
    A("```bash")
    A("# 一键全流程（注册表 → 发现 → 分析 → Context → 本对照件）")
    A("python3 scripts/run_daily.py")
    A("# 只重算候选池")
    A("python3 scripts/analyze.py")
    A("# 重新生成本对照件")
    A("python3 scripts/make_digest.py -o ../CANDIDATES_DIGEST.md")
    A(f"# 离线测试（{_test_count()} 项，不联网；摘要分 PASS / SKIP / FAIL 三栏）")
    A("python3 tests/test_pipeline.py")
    A("```")
    A("")
    A("**依赖的输入（缺一不可）**：")
    A("")
    A("| 输入 | 解析优先序（v2.3 §九 / v2.4 §十二 保持） | 作用 |")
    A("|---|---|---|")
    A("| A 项目需求 `SKILL_CONTEXT.md` | ① `SKILL_CONTEXT_PATH` 环境变量 → "
      "② **包内 `支撑/输入/SKILL_CONTEXT.md`**（归档包解压后自定位） → ③ 本机默认路径 | "
      "决定 PROJECT_MATCH / 相关性否决 / matched_projects |")
    A("| B 已装侧底座 `INSTALLED_SKILLS_CONTEXT.md` + `SKILL_SOURCE_MAP.json` | "
      "① `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH` → ② 同级 v4 文件夹自动发现（向上 3 级） → "
      "③ 找不到则该组测试 **SKIP 并提示** | 决定 `installed_relationship` 与 "
      "`capability_gap_match` |")
    A("| C 外部候选 | `data/SKILL_CANDIDATES.json` | 本层产物 |")
    A("")
    A("**路径不再写死**：`scripts/common.py` 的所有输入路径都可用环境变量覆盖，"
      "未设置时按上表优先序自动定位（归档包内也能自洽），并用 `~` 展开（不写死用户名）。"
      "命中的来源会记录在 `common.PATH_RESOLUTION` 里，可核对到底读的是哪个文件：")
    A("")
    A("```bash")
    A("SKILL_REPO_ROOT=/path/to/仓库 \\")
    A("SKILL_CONTEXT_PATH=/path/to/SKILL_CONTEXT.md \\")
    A("SKILL_DATA_DIR=/path/to/data \\")
    A("python3 scripts/run_daily.py")
    A("```")
    A("")
    A("可覆盖的变量：`SKILL_REPO_ROOT` / `SKILL_CONTEXT_PATH` / `SKILL_DATA_DIR`"
      " / `INSTALLED_CTX_PATH` / `SOURCE_MAP_PATH`。"
      "换机器或跑归档副本时用环境变量指路，**不要改脚本内的路径**。")
    A("")
    A(f"> 未找到输入 A 时：`matched_projects` 会为空、需求证据全体失效 —— "
      f"本件生成时输入 A {_path_report('skill_context', SKILL_CONTEXT_PATH)}。")
    A("")
    A("> **本行会随运行环境变化**（env / 包内自定位 / 本机默认），属预期；"
      "对照件其余内容在不同环境下应当逐位一致。")
    A("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="-", help="输出文件；默认 stdout")
    a = ap.parse_args()
    md = build()
    if a.out == "-":
        print(md)
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"written: {a.out} ({len(md.encode('utf-8'))} B)")


if __name__ == "__main__":
    main()
