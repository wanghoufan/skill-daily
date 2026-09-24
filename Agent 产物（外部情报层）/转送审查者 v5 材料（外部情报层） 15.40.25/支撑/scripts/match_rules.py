# -*- coding: utf-8 -*-
"""语义匹配规则引擎（v2.5）。

为什么要有这个模块（v2.1 → v2.2 的根本改动）：
  v2.1 用的是「关键词列表 + 整词匹配」。虽然已经修掉了子串事故（`ui` 命中 build/require），
  但仍有更深的语义错误：**「出现某个平台词」被等同于「满足某项能力需求」**。
  典型误报：
    · Google Mobile Ads SDK / IMA DAI SDK / Penpot UI-UX / responsive-design
      → 只因文本里出现 android / ios / mobile / expo 就被记成 mobile_qa（移动端 QA）
    · alloydb-basics / postgresql-optimization
      → 只因出现 PostgreSQL 就被当成 supabase_db 缺口解决方案
    · 任何示例里带一段 Python → 就被认为解决「Python 本地自动化」
  这些误报会直接抬高 PROJECT_MATCH（25/100）与 CAPABILITY_GAP（20/100），
  把真正相关的候选挤下去。

v2.3 修的是「规则形式上有 direct evidence，但真实语义仍然是假相关」的第一批：
  类型适用不得单独造匹配、NEED_RULE 二轮收紧、跨仓功能族折叠、always_block 误伤。

v2.4（本轮）修的是同一类问题的最后一层 —— **技术栈词与词面重叠造成的假相关**：
  ① 技术栈证据分 STRONG / SECONDARY：TypeScript / React / Python / Docker / Shell /
     HTML / CSS / GitHub 等泛用词**不得单独**产生项目匹配（事故：一个 Azure 云端
     Playwright 服务仅因描述里有 TypeScript，就匹配了 5 个普通 TS 项目）。
  ② Docker 词典删掉裸 `container`（事故：`container queries` 被当成 Docker）。
  ③ 词面重叠证据加泛词 stop list，并要求「≥2 个高区分度词」或「1 个明确项目域高信号词」
     （事故：Azure Resource Manager 与 prompt-manager 只因共有 `manager` 就成立）。
  ④ NEED_RULE 支持**否定窗口**：`not for X` / `不要用于 X` 里的词不得当正向证据
     （事故：描述写着 `NOT for running Playwright tests` 却仍被判 browser-qa）。
  ⑤ testing_qa 必须来自「主能力证据」（Skill 名含 test/e2e/playwright… 或描述明确
     把测试当核心任务），`testing methodologies` / `optional QA` 只算提及。

v2.5（冻结前最后收口，§一~§九）修的是同一类问题剩下的实例：
  ① android 需求必须对应「真机 QA / 构建签名」——裸 device/build/install/launch 一律
     不作正向证据（事故：google-mobile-ads-get-started 只是接入广告 SDK 就命中 android）。
  ② 否定窗口改为**两层**：逗号不再天然重置否定作用域，`Don't use for A, B, or C.` 中
     A/B/C 全部保持否定；显式转折标记（but / 但 / 可用于…）才恢复正向
     （事故：agent-platform-prompt-management 因 `model deployment to endpoints` 落在
     否定枚举第二段被「复活」成正向证据，误命中 deploy）。
  ③ 词面（lexical）证据不得再被技术泛词与裸 `prompt` 制造（react/native/… 归
     STRONG/SECONDARY_TECH 负责）；词级重叠只能作加分项，单独成立只允许
     明确登记过的「项目域短语」。
  ④ mcp_dev / docx_xlsx / github-auto 等能力判定从「出现即命中」改为「核心能力证据」；
     PPTX 不得冒充 docx_xlsx。
  ⑤ 统一候选级 `capability_evidence_context` 四态字段（primary/supporting/mention/negated），
     只有 primary 可拿完整 gap 分，supporting 上限 8，mention/negated 上限 2。

MATCH_RULE 语义（本模块的核心数据结构）：
    {
      "all_groups": [ [kw,...], [kw,...] ],  # 组间 AND，组内 OR —— 全部组都要命中
      "any_of":     [kw, ...],               # 任一命中即可（OR）
      "any_groups": [ [kw,...], [kw,...] ],  # 任一组「整组命中」即可（组内 AND / 组间 OR）
      "none_of":    [kw, ...],               # 命中任一即否决（排除性条件）
      "context_terms": [kw, ...],            # 语境词：不参与判定，命中则记入证据用于解释
      "custom":     callable,                # 无法用列表表达的复合判定（如 testing_qa）
    }
  · all_groups 必须全部命中；
  · 若给了 any_of 或 any_groups，则「(any_of 任一命中) 或 (any_groups 任一组全命中)」；
  · 二者都没给则不设正向条件。
  规则里出现的所有关键词一律走 hit()：单字词按整词匹配，含空格/点/井号的按短语匹配。
  **禁止子串匹配**（v2.1 的 `ui` 事故）。
  **否定窗口内的词一律不算命中**（v2.4 §五）。

本模块只做纯计算，不读文件、不联网 —— 便于离线测试与在多台机器上复用。
"""
import re

# ---------- 命中原语 ----------
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\+#\.]*")
# CJK / 全角：中文没有词边界，_WORD_RE 又是纯 ASCII，所以中文关键词永远进不了 words 集合。
# 事故（v2.4 查出）：规则表里 **48 个 NEED_RULE + 27 个 CAP_RULE + TECH_MATCH 的
# `容器化` / `菜单栏应用`** 中文关键词命中率恒为 0 —— 是写死也测不出来的死词，
# 而 §五 专门列了「非用于 / 不用于 / 不支持」中文否定标记，说明中文匹配本就该生效。
_CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uff65-\uff9f]")

# ---------- 否定窗口（v2.4 §五；v2.5 §二 改为两层作用域） ----------
# 第一层·语义段：只按 句点（后接空白/行尾，next.js / node.js / .net 不会被切碎）、
# 换行、分号、句读切；**普通逗号（, ，、）不再是段边界**。
# 第二层·段内子句：按逗号再切，否定状态在子句间**传递**：
#   · 子句含否定标记 → 丢弃，且其后子句继续视为否定范围（`Don't use for A, B, or C.`
#     的 A/B/C 全部否定 —— v2.4 按逗号重置，把 B/C「复活」成了正向证据）；
#   · 子句含显式「转折/恢复正向」标记（but / however / 但 / 可用于 / 可直接…）→ 恢复正向；
#   · 其余子句继承当前否定状态。
_CLAUSE_SPLIT_RE = re.compile(r"(?:\.(?=\s|$)|[\n;；。！!？?]+)")
_COMMA_SPLIT_RE = re.compile(r"[,，、]+")
_NEG_MARK_RE = re.compile(
    r"(?:\bnot\b|\bnever\b|\bno\s+longer\b|\bdon'?t\b|\bdoesn'?t\b|\bdo\s+not\b"
    r"|\bdoes\s+not\b|\bisn'?t\b|\bis\s+not\b|\baren'?t\b|\bare\s+not\b|\bavoid\b"
    r"|\bwithout\b|\bexcept\b|\bunavailable\b|\bdeprecated\b|\bnot\s+intended\b"
    r"|非用于|不用于|不支持|不适用|不能|禁止|不要|不可)", re.I)
# 显式「恢复正向」标记（v2.5 §二）。注意顺序：**先查否定标记再查恢复标记**，
# 所以 `Don't use for …` 里的 "use for" 不会把自己救回来。
_POS_RESTORE_RE = re.compile(
    r"(?:\bbut\b|\bhowever\b|\binstead\b|\bwhereas\b|\bwhile\b|\buse for\b|\bused for\b"
    r"|\bis used for\b|\bare used for\b|\bcan be used for\b|\bcould be used for\b"
    r"|但是|但|不过|而是|可以用于|可用于|适用于|可直接|即可)", re.I)


def _positive_chunks(raw):
    """两层否定作用域（v2.5 §二）：返回保留下来的「正向子句」列表。"""
    keep = []
    for seg in _CLAUSE_SPLIT_RE.split(raw or ""):
        if not seg:
            continue
        neg_active = False
        for part in _COMMA_SPLIT_RE.split(seg):
            if not part.strip():
                continue
            if _NEG_MARK_RE.search(part):
                neg_active = True          # 枚举的后续子句继续保持否定
                continue
            if _POS_RESTORE_RE.search(part):
                neg_active = False
                keep.append(part)
                continue
            if not neg_active:
                keep.append(part)
    return keep


def strip_negated(raw):
    """去掉处于否定作用域内的子句，只留「正向文本」（v2.4 §五 / v2.5 §二）。

    例：`Don't use for model training, model deployment to endpoints, or managing prompts.`
    → 三个逗号子句全部丢弃，其中的 deployment / endpoints / prompts 不再是正向证据。
    例：`Not for A, but use for B.` → A 丢弃，B 经 `but` 恢复为正向。
    """
    return " ".join(_positive_chunks(raw))


def negated_words(raw):
    """返回「恰好只落在否定作用域里」的词集合（用于诊断统计）。"""
    low = (raw or "").lower()
    all_w = set()
    for seg in _CLAUSE_SPLIT_RE.split(low):
        all_w |= set(_WORD_RE.findall(seg))
    pos_w = set()
    for part in _positive_chunks(low):
        pos_w |= set(_WORD_RE.findall(part))
    return all_w - pos_w


# ---------- 质量计数（v2.4 §十：PROJECT_MATCH_QUALITY） ----------
QUALITY = {
    "matched_candidates": 0,
    "strong_tech_evidence": 0,
    "positioning_evidence": 0,
    "shared_need_evidence": 0,
    "lexical_evidence": 0,
    "secondary_tech_only_rejected": 0,
    "negated_evidence_rejected": 0,
    "lexical_single_rejected": 0,
    # v2.5 §三/§五：词面证据重构后的审计计数
    "lexical_alone_rejected": 0,                     # 词级重叠本想单独成立，已降为「只加分」
    "lexical_phrase_direct_evidence": 0,             # 明确登记过的项目域短语单独成立
    "bare_prompt_direct_evidence": 0,                # 必须恒为 0（§十/§十四 审计项）
    "tech_words_used_as_lexical_direct_evidence": 0,  # 必须恒为 0（§四 不变式）
    # v2.6 §五：跨 Skill 重定向小句（"For X, use other-skill"）被剪掉的次数
    "redirect_evidence_rejected": 0,
    # v2.9 §八：required_tech 与项目不兼容 → shared_need 不得单独造项目匹配的次数
    "required_tech_blocked_shared_need": 0,
    # v2.11 §五：项目画像冲突时，被抑制的冲突侧 strong_tech 项目数（候选×项目）
    "conflict_strong_tech_suppressed": 0,
}
_KIND_TO_COUNT = {"strong_tech": "strong_tech_evidence",
                  "positioning": "positioning_evidence",
                  "shared_need": "shared_need_evidence",
                  "lexical": "lexical_evidence"}


def reset_quality():
    """每轮正式评估前清零，保证计数是「本轮候选级」而不是多次调用累加。"""
    for k in QUALITY:
        QUALITY[k] = 0


def bag(name, desc):
    """返回 (整词集合, 原文小写, 连字符/下划线归一化文本)。

    norm 用于短语匹配：把 `react-native` / `react_native` / `react native` 统一成
    "react native"，避免因为连接符写法不同而漏命中。
    """
    raw = f"{name or ''} {desc or ''}".lower()
    words = set(_WORD_RE.findall(raw))
    norm = re.sub(r"\s+", " ", re.sub(r"[\-_/]+", " ", raw))
    return words, raw, norm


# ---------- v2.6 §五：跨 Skill 重定向语句不作本 Skill 的正向证据 ----------
# 事故：stablyai/orca/orca-emulator 是 iOS Simulator Skill，描述末尾
#   「For an Android device or emulator, use orca-emulator-android.」
#   里的 android/emulator 被当成了当前 Skill 的 Android 能力。
# 这类「For X, use/see Y」「use Y instead」「handled by Y」「X is covered by Y」
# 「如果是 X，请使用 Y」等句子里的 X 恰恰是**排除当前 Skill** 的 scope。
# 判定从严：重定向目标必须是「别的 Skill 的名字」（含连字符的 slug 形态）才剪，
# 避免把「For speed, use caching」这类自身能力描述误剪。
# 重定向目标必须是「别的 Skill」：① 连字符 slug（orca-emulator-android）；
# ② `X skill` 指称（"use the Android emulator skill" —— 真实 SKILL.md 用的是这种写法）。
# 「For quick starts, use the CLI」这类自身指引不含这两种形态，不会被误剪。
_REDIRECT_TARGET = (r"(?:[`'\"]?[\w][\w-]*-[\w-][\w'-]*"
                    r"|(?!this\b|the same\b|current\b)[\w -]{1,45}?\bskill(?:s)?\b)")
_REDIRECT_RE = re.compile(
    r"[^.;!?;；\n]{0,60}?\b(?:for|in the case of|when working with|if you (?:want|need|use|work with|are working))\b"
    r"[^.;!?;；\n]{0,60}?(?:\s*[,，]\s*)?(?:please\s*)?\b(?:use|see|refer to|try|switch to|install|check)\b"
    r"(?!\s+when\b)\s+(?:the\s+)?" + _REDIRECT_TARGET + r"[^.;!?;；\n]*"
    r"|[^.;!?;；\n]{0,60}?\b(?:handled|covered|managed|provided|done)\s+by\b"
    r"\s+(?:the\s+)?" + _REDIRECT_TARGET + r"[^.;!?;；\n]*"
    r"|\buse\b\s+(?:the\s+)?" + _REDIRECT_TARGET + r"[^.;!?;；\n]{0,40}?\binstead\b[^.;!?;；\n]*"
    r"|如果是[^。;;\n]{0,40}?[，,]?\s*(?:请(?:改用|使用|安装|换用)|改用|换用|使用)"
    r"\s*[`\u4e00-\u9fffa-z][\w\u4e00-\u9fff-]*[^。;;\n]*"
    r"|[^\u4e00-\u9fff。;;\n]{0,40}?\b[\w-]+\b\s*请(?:改用|使用|安装|换用)"
    r"\s*[`\u4e00-\u9fffa-z][\w\u4e00-\u9fff-]*[^。;;\n]*",
    re.I)


def strip_redirects(text, count=False):
    """从正向视图里剪掉「指向别的 Skill」的小句（v2.6 §五）。

    count=True 时把剪掉的小句数记入 redirect_evidence_rejected（可审计）。
    """
    kept, n = _REDIRECT_RE.subn(" ", text or "")
    if count and n:
        QUALITY["redirect_evidence_rejected"] += n
    return kept


def _ctx(name, desc):
    """一次算好一个候选的全部文本视图（含否定过滤后的正向视图）。

    v2.7 §二（确定性硬门）：名称的**短语判定必须走有序 normalized_name**。
    `nwords` 是 set，只允许做无序 membership 判断；任何 `" ".join(set)` 重建名称
    都会随 PYTHONHASHSEED 改变词序（实测 php-mcp-server-generator 的
    `mcp server` 短语在部分 seed 下被打散 → mcp_dev/mcp_usage 分类漂移）。
    """
    words, text, norm = bag(name, desc)
    nwords, _nt, name_norm = bag(name, "")      # name_norm：'-'/'_'/'/' → 空格的**有序**规范化
    ptext = strip_negated(strip_redirects(text, count=True))   # v2.6 §五：先剪重定向（原始句界还在），再剪否定
    pwords, _pt, pnorm = bag("", ptext)
    pwords |= nwords          # Skill 名里的词不受描述否定影响（membership 用，不回拼）
    pnorm = f"{pnorm} {name_norm}".strip()      # 短语视图：追加有序名称，绝不 ' '.join(nwords)
    return {"words": words, "text": text, "norm": norm, "name_words": nwords,
            "raw_name": (name or "").lower(), "name_norm": name_norm,
            "pwords": pwords, "ptext": ptext, "pnorm": pnorm}


def hit(words, text, norm, kw):
    """单字关键词 → 整词匹配；含空格/点/井号的关键词 → 短语匹配。

    整词匹配是硬要求：v2.1 之前用 `kw in text` 导致 `ui` 命中 build/require/guidance，
    使 PROJECT_MATCH 恒为满分、Top30 被无关技能占满。

    v2.4：含 CJK 的关键词改走子串匹配。中文没有词边界、`_WORD_RE` 又是纯 ASCII，
    若坚持整词匹配，规则表里全部中文关键词都是永不命中的死词（实测 75 个）。
    """
    k = kw.lower()
    if " " in k or "." in k or "#" in k or _CJK_RE.search(k):
        return k in norm or k in text
    return k in words


def hit_any(words, text, norm, kws):
    return any(hit(words, text, norm, k) for k in kws)


def hit_pos(ctx, kw):
    """只在**正向视图**（已去掉否定小句）上判定命中（v2.4 §五）。"""
    return hit(ctx["pwords"], ctx["ptext"], ctx["pnorm"], kw)


def hit_pos_any(ctx, kws):
    return any(hit_pos(ctx, k) for k in kws)


def _note_suppressed(ctx, kws):
    """统计「本来会命中、但被否定窗口压制掉」的关键词（§十 negated_evidence_rejected）。"""
    for k in kws:
        if hit(ctx["words"], ctx["text"], ctx["norm"], k) and not hit_pos(ctx, k):
            QUALITY["negated_evidence_rejected"] += 1


def rule_hits(cand, rules, limit=None, ctx=None):
    """对一整张规则表跑匹配，返回 [(key, [evidence]), ...]（保持规则表定义顺序）。"""
    if ctx is None:
        ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    out = []
    for key, rule in rules.items():
        ok, ev = match_rule(ctx, rule)
        if ok:
            out.append((key, ev))
            if limit and len(out) >= limit:
                break
    return out


def match_rule(ctx, rule):
    """执行一条 MATCH_RULE，返回 (是否命中, 命中证据列表)。

    判定顺序：custom（若有）→ all_groups（组间 AND / 组内 OR）→ any_of / any_groups
    → none_of（否决）。context_terms 只补证据，不影响判定结果。
    **所有正向关键词都在「否定过滤后的文本」上判定**（v2.4 §五）。
    """
    if not rule:
        return False, []
    custom = rule.get("custom")
    if custom is not None:
        return custom(ctx)
    ev = []
    for group in rule.get("all_groups") or []:
        h = [k for k in group if hit_pos(ctx, k)]
        if not h:
            _note_suppressed(ctx, group)
            return False, []
        ev += h
    has_primary = bool(rule.get("any_of") or rule.get("any_groups"))
    if has_primary:
        ok = False
        a = rule.get("any_of")
        if a:
            h = [k for k in a if hit_pos(ctx, k)]
            if h:
                ok, ev = True, ev + h
            else:
                _note_suppressed(ctx, a)
        if not ok:
            for group in rule.get("any_groups") or []:
                if group and all(hit_pos(ctx, k) for k in group):
                    ok, ev = True, ev + list(group)
                    break
            if not ok:
                for group in rule.get("any_groups") or []:
                    _note_suppressed(ctx, group)
        if not ok:
            return False, []
    n = rule.get("none_of")
    if n:
        hit_n = [k for k in n if hit(ctx["words"], ctx["text"], ctx["norm"], k)]
        if hit_n:
            # 排除性语境（管理面 / 资源编排…）与否定窗口同属「被语境压制掉的假相关」，
            # 统一计入 negated_evidence_rejected，便于审查者看到这个门真的在工作。
            for k in hit_n:
                if k.lower() in _EXCLUSION_CONTEXT_TERMS:
                    QUALITY["negated_evidence_rejected"] += 1
            return False, []
    for k in rule.get("context_terms") or []:
        if hit(ctx["words"], ctx["text"], ctx["norm"], k):
            ev.append(k)
    return True, sorted(set(ev))


# ==========================================================================
# 一、能力标签规则 CAP_RULE（读已装侧 CAPABILITY_SUPPRESSION / 决定能力缺口）
# ==========================================================================
# v2.2 关键收紧：
#   · mobile_qa 必须「移动平台证据」AND「QA/设备/构建验收证据」，不再单凭出现 android/mobile
#   · supabase_db 必须真 Supabase 语境（或 RLS）；普通 PostgreSQL 归 postgres_db
#   · 新增 mobile_dev / expo_rn_dev：移动「开发」能力与移动「QA」能力分列，
#     React Native / Expo 最佳实践属于开发，不自动属于 QA
# v2.4 §七/§八 关键收紧：
#   · testing_qa 改成「主能力证据」判定，不再被 `testing methodologies` / `optional QA`
#     这类**顺带提及**污染（事故：ai-prompt-engineering-safety-review 与
#     ai-team-orchestration 因此白拿 weak gap 的 15 分加成）。
_MOBILE_PLATFORM = ["android", "ios", "expo", "react native", "flutter", "mobile app",
                    "mobile application", "移动端", "安卓"]
_QA_OR_DEVICE = ["qa", "test", "tests", "testing", "e2e", "end to end", "adb", "emulator",
                 "real device", "device farm", "appium", "detox", "maestro", "xctest",
                 "espresso", "ui test", "build verification", "signing", "keystore", "apk",
                 "aab", "app bundle", "install verification", "launch verification",
                 "simulator",
                 "自动化测试", "真机", "签名"]

# testing_qa 的「主能力证据」词表（v2.4 §八）：
#   A. Skill 名本身含测试身份词
# v2.6 §九：删除裸 spec / specs —— 产品 specification ≠ test spec
# （事故：gen-specs-as-issues 只是「生成产品规格」，凭 specs 白拿 weak gap 15 分）。
_TESTING_NAME_TOKENS = {"test", "tests", "testing", "qa", "e2e", "playwright", "pytest",
                        "vitest", "jest", "cypress", "rspec", "testify", "selenium"}
#   B. 描述明确把「测试」当核心任务（而不是顺带提一句）
_TESTING_CORE_PHRASES = [
    "run tests", "running tests", "run the tests", "run test", "execute tests",
    "executing tests", "write tests", "writing tests", "create tests", "creating tests",
    "test application", "test the application", "test applications", "testing application",
    "qa workflow", "acceptance testing", "regression testing", "validate behavior",
    "validate behaviour", "test suite", "test suites", "testing framework", "test framework",
    "e2e tests", "end to end tests", "end-to-end tests", "unit tests", "integration tests",
    "test automation", "browser testing", "webapp testing", "web app testing",
    "visual regression", "flaky tests", "debugging flaky tests", "testing standards",
    # v2.6 §九：只有**测试语境**的 spec 才算测试身份
    "test spec", "test specs", "test specification", "spec test", "rspec",
    "spec_runner", "spec runner", "executable specification", "测试规格", "测试用例",
    "运行测试", "编写测试", "测试套件", "自动化测试", "端到端测试",
]
#   只算「提及」、不算能力的写法（用于诊断与文档说明）
_TESTING_MENTION_ONLY = ["testing methodologies", "optional qa", "may be tested",
                         "qa is optional", "examples include testing"]
# ---------- v2.7 §三：QA 歧义 —— Question Answering ≠ Quality Assurance ----------
# 事故：microsoft/skills/wiki-qa（"Answers questions about a code repository…"）
# 只因名字含 `qa` 被打 testing_qa，吃 testing_qa=weak 的缺口分进 Personalized Top。
_QA_NEG_PHRASES = ["question answering", "q&a", "q and a", "answer questions",
                   "answers questions", "answering questions", "ask questions",
                   "asks questions", "repository qa", "knowledge qa", "document qa",
                   "docs qa", "问答", "答疑"]
# 名称证据只有裸 `qa` 时，描述必须出现真实质保语义才成立
_QA_REAL_TERMS = ["quality assurance", "software testing", "acceptance testing",
                  "regression testing", "validate behavior", "validate behaviour",
                  "test suite", "qa workflow", "test plan", "test case", "test cases",
                  "write tests", "run tests", "软件测试", "验收测试", "质量保证",
                  "测试用例", "测试计划"]


def _is_question_answering(ctx):
    return hit_pos_any(ctx, _QA_NEG_PHRASES)


def _rule_question_answering(ctx):
    """v2.7 §三：独立记录位（可选标签）。它**不得**吃 testing_qa 缺口分。"""
    ok = _is_question_answering(ctx)
    return (ok, ["question-answering"] if ok else [])


def _rule_testing_qa(ctx):
    """testing_qa 复合判定（v2.4 §八 + v2.7 §三）。

    A. Skill 名含测试身份词；B. 描述把测试当核心任务。
    v2.7 收紧：名称证据**只有裸 `qa`** 时必须有 B 侧或真实质保语义；
    问题问答语境（answers questions / Q&A / knowledge qa…）在无其他测试身份时一票否决。
    """
    name_hit = sorted(ctx["name_words"] & _TESTING_NAME_TOKENS)
    phrase_hit = [p for p in _TESTING_CORE_PHRASES if hit_pos(ctx, p)]
    if set(name_hit) <= {"qa"} and _is_question_answering(ctx) and not phrase_hit:
        return False, []          # wiki-qa：名只有 qa，且描述是 Question Answering
    if name_hit == ["qa"] and not phrase_hit \
            and not hit_pos_any(ctx, _QA_REAL_TERMS):
        return False, []          # 裸 qa 名 + 描述无真实质保语义 → 不成立
    ev = name_hit + phrase_hit
    return (bool(ev), sorted(set(ev)))


# ---------- v2.5 §六：mcp_dev 必须是「核心 MCP 开发能力」 ----------
_MCP_TERMS = ["mcp", "model context protocol"]
_MCP_DEV_PHRASES = [
    "mcp server development", "mcp tool development", "mcp client development",
    "model context protocol implementation", "mcp integration development",
    "mcp server setup", "mcp sdk", "编写 mcp", "mcp 服务开发", "mcp开发", "mcp 开发",
]
# Skill 名本身断言了 MCP 能力（mcp-builder / mcp-server / mcp-setup…）
_MCP_NAME_PHRASES = ["mcp builder", "mcp server", "mcp servers", "mcp development",
                     "mcp dev", "mcp setup", "mcp client", "mcp tool", "mcp tools"]
# 「开发动词 …(同一句内) … mcp」的旧宽窗正则已在 v2.6 §六 移除：
# 它把「creating … designs … using MCP tools」也判成开发（penpot 事故）。
# 现在统一走 _mcp_artifact_verdicts()：动词必须管辖真正的 MCP 工件。
# 「使用侧」语境：集成/连接/暴露 —— 算 supporting，不算开发
_MCP_USAGE_TERMS = ["integration", "integrate", "connect", "connects", "expose", "exposes",
                    "interoperate"]
# ---------- v2.6 §六：开发动词的**宾语**必须真的是 MCP 工件 ----------
# 事故：penpot-uiux-design「creating professional UI/UX designs in Penpot using MCP tools」
# 被旧版宽窗正则判成 mcp_dev primary —— 那是**用 MCP 工具做设计**（mcp_usage），不是开发。
_MCP_ARTIFACT_RE = re.compile(
    r"\b(?:mcp|model context protocol)\b[\s\-]*"
    r"(?:server|servers|client|clients|tool|tools|integration|integrations|sdk|sdks"
    r"|protocol implementation|gateway|endpoints?|plugins?)\b"
    r"|\b(?:server|servers|client|clients|generator|sdk)\b[^.;!?;；\n]{0,25}?"
    r"\b(?:mcp|model context protocol)\b", re.I)
_MCP_DEV_VERB_RE = re.compile(
    r"\b(?:build|building|builds|create|creating|creates|develop|developing|develops"
    r"|implement|implementing|implements|write|writing|generate|generating|scaffold"
    r"|author|publish|maintain|extend)\b", re.I)
# 工件正前方紧贴「using / via / through / with …」→ 是**使用** MCP，不是开发
_MCP_PRE_USAGE_RE = re.compile(r"\b(?:us(?:e|es|ing)|via|through|leverag\w+|rely\w+)\b[^\w]{0,3}$", re.I)
_MCP_NAME_ARTIFACT_RE = re.compile(
    r"\bmcp[\s\-]*(?:server|servers|client|clients|builder|tool|tools|sdk|development|dev)\b"
    r"|\b(?:server|client|builder)[\s\-]*mcp\b", re.I)


def _mcp_artifact_verdicts(ctx):
    """扫描正向视图里的 MCP 工件短语，返回 (dev_hits, usage_hits)。

    dev_hits   —— 同一小句内、工件正前方 60 字符有开发动词、且紧贴处不是「using/via」：
                  「creating high-quality MCP servers」「Generate a complete PHP Model
                  Context Protocol server project」。
    usage_hits —— 工件紧贴「using/via/through」等使用介词：「using MCP tools」。
    """
    dev, use = [], []
    ptext = ctx["ptext"]
    for m in _MCP_ARTIFACT_RE.finditer(ptext):
        window = ptext[max(0, m.start() - 60):m.start()]
        if _MCP_PRE_USAGE_RE.search(window):
            use.append(m.group(0))
        elif _MCP_DEV_VERB_RE.search(window):
            dev.append(m.group(0))
        else:
            use.append(m.group(0))   # 工件只是出现、没有开发动词管辖 → 按使用/提及处理
    return dev, use


def _norm_name(name):
    return re.sub(r"[\-_/]+", " ", (name or "").lower()).strip()


def _cls_mcp(ctx):
    """v2.6 §六：primary 只认「开发动词管辖 MCP 工件」或名称断言工件；
    仅使用 MCP（using MCP tools / 集成连接）→ supporting（记为 mcp_usage，不得进 mcp_dev 评分）。"""
    if not hit_any(ctx["words"], ctx["text"], ctx["norm"], _MCP_TERMS):
        return None, []
    if not hit_pos_any(ctx, _MCP_TERMS):
        return "negated", []          # MCP 只出现在否定作用域里
    ev = [p for p in _MCP_DEV_PHRASES if hit_pos(ctx, p)]
    dev, use = _mcp_artifact_verdicts(ctx)
    if dev:
        ev.append("dev-verb+mcp-artifact")
    nn = ctx.get("name_norm") or _norm_name(" ".join(sorted(ctx["name_words"])))
    if _MCP_NAME_ARTIFACT_RE.search(nn) or any(p in nn for p in _MCP_NAME_PHRASES):
        ev.append("name-asserts-mcp-artifact")
    if ev:
        return "primary", sorted(set(ev))
    if use or "mcp" in nn or any(hit_pos(ctx, t) for t in _MCP_USAGE_TERMS):
        # §六：「会用 MCP」= mcp_usage，不是 MCP 开发能力
        return "supporting", []
    return "mention", []              # §六：文档里列了一句 MCP ≠ 具备 MCP 开发能力


def _rule_mcp_dev(ctx):
    """v2.6 §六：CAP 命中 = **primary only**。supporting/mention 只可记 mcp_usage，
    不得进 mcp_dev 能力标签 / 缺口评分（事故：penpot「using MCP tools」白拿 weak 8 分）。"""
    lvl, ev = _cls_mcp(ctx)
    return (lvl == "primary", ev)


def _rule_mcp_usage(ctx):
    """v2.6 §六：独立的「MCP 使用」记录位。不算开发能力，只登记真实使用语境。"""
    lvl, _ev = _cls_mcp(ctx)
    return (lvl == "supporting", ["mcp_usage"])


# ---------- v2.5 §七：docx_xlsx 只认 Word/Excel/表格，PPTX 另立标签 ----------
_DOCX_XLSX_PRIMARY = ["docx", "xlsx", "excel", "spreadsheet", "电子表格",
                      "word document", "word documents", "microsoft word"]
_DOCX_XLSX_SUPPORTING = ["office document", "office documents", "office file",
                         "office 文档", "文档处理", "表格处理"]
_PPTX_TERMS = ["pptx", "powerpoint", "演示文稿"]


def _cls_docx(ctx):
    prim = [k for k in _DOCX_XLSX_PRIMARY if hit_pos(ctx, k)]
    if prim:
        return "primary", prim
    sup = [k for k in _DOCX_XLSX_SUPPORTING if hit_pos(ctx, k)]
    if sup:
        return "supporting", sup
    if hit_pos_any(ctx, _PPTX_TERMS):
        return "mention", []     # §七：只处理 PPT 不算 DOCX/XLSX 能力
    return None, []


def _rule_docx_xlsx(ctx):
    lvl, ev = _cls_docx(ctx)
    return (lvl in ("primary", "supporting"), ev)


# v2.6 §七：frontend_design 必须是**明确的设计语义**。
# 事故：webapp-testing「verifying frontend functionality」凭裸 `frontend` 白拿最高权重需求。
# 裸 frontend / front-end / ux / css / tailwind / shadcn / visual design 一律出局；
# 「frontend functionality / testing / debugging」这类词根本不在下表里，天然不命中。
_FRONTEND_DESIGN_TERMS = [
    "ui design", "ui/ux design", "ux design", "web design", "design system",
    "visual hierarchy", "typography", "responsive design", "styling", "css design",
    "component design", "interface design", "frontend design", "front-end design",
    "design review", "design guidelines", "界面设计", "前端设计", "视觉规范", "设计审查",
]

# ==========================================================================
# v2.8 §五/§六/§七/§八：核心需求证据分类器
# 「SDK supports React Native」「产品自带 CLI/automation」「serving container + LLM 字眼」
# 「提到 Playwright」「experiment dashboard」都只能是 supporting/mention，
# 不得冒充用户的通用个人需求（primary = 核心任务证据）。
# ==========================================================================
_EXPO_CORE_PHRASES = [
    "build react native app", "building react native", "develop react native",
    "react native development", "react native app development", "react native styling",
    "react native navigation", "react native animation", "react native performance",
    "react native architecture", "react native testing", "react native packaging",
    "react native reanimated", "native module", "native modules", "expo project",
    "expo router", "expo sdk", "expo build", "eas build", "expo go", "nativewind",
    "react native app", "react native apps", "expo app", "跨平台移动开发", "expo 路由",
]
_EXPO_SUPPORT_PHRASES = [
    "supports react native", "support react native", "react native support",
    "react native plugin", "react native extension", "works with expo", "expo support",
    "integration available for react native",
]


def _cls_expo_rn(ctx):
    if not hit_pos_any(ctx, ["expo", "react native"]):
        return None, []
    name_assert = ("expo" in ctx["name_words"]
                   or {"react", "native"} <= ctx["name_words"])
    core = [p for p in _EXPO_CORE_PHRASES if hit_pos(ctx, p)]
    if core or name_assert:
        return "primary", (core[:3] + (["name-asserts-rn"] if name_assert else []))[:4]
    if hit_pos_any(ctx, _EXPO_SUPPORT_PHRASES):
        return "supporting", ["sdk-supports-rn"]
    return "supporting", []      # 只出现平台词（bare expo / react native）→ supporting


def _rule_expo_rn(ctx):
    lvl, ev = _cls_expo_rn(ctx)
    return (lvl == "primary", ev)


_PY_CORE_PHRASES = [
    "automate local", "local automation", "automate your workflow", "workflow automation",
    "scripting", "write a script", "write scripts", "script generation", "generate scripts",
    "batch processing", "batch file", "file automation", "filesystem automation",
    "local data processing", "data processing", "process files", "repetitive task",
    "automate files", "数据处理脚本", "本地自动化", "批处理", "文件处理", "自动化脚本",
]
_PRODUCT_INTERFACE_WORDS = ["cli", "python api", "sdk", "automation", "automate"]


def _cls_python_auto(ctx):
    if not hit_pos_any(ctx, ["python", "python3"]):
        return None, []
    core = [p for p in _PY_CORE_PHRASES if hit_pos(ctx, p)]
    if core:
        return "primary", core[:3]
    if hit_pos_any(ctx, _PRODUCT_INTERFACE_WORDS):
        # 产品自身 Python/CLI/automation 字眼 ≠ 帮用户做本地自动化
        return "supporting", ["product-cli-mention"]
    return "mention", []


def _rule_python_auto(ctx):
    lvl, ev = _cls_python_auto(ctx)
    return (lvl == "primary", ev)


_LLM_CONTEXT_TERMS = ["llm", "large language model", "language model", "openai", "anthropic",
                      "claude api", "dashscope", "qwen", "deepseek", "gemini", "model api",
                      "chat completion", "chat completions", "text generation model", "大模型",
                      "模型接入"]
_LLM_PRIMARY_ACTIONS = [
    "call the api", "call model", "call the model", "invoke model", "invoke the model",
    "api request", "sdk client", "chat completion", "chat completions", "responses api",
    "streaming response", "structured output", "tool calling", "function calling",
    "provider sdk", "provider integration", "consume inference api", "api integration",
    "sdk integration", "模型api接入", "模型 api 接入", "调用大模型", "流式输出", "结构化输出",
    "generate text", "text generation", "complete text",
    # v2.8 补充：API 参考/SDK 语境的通用特性词（claude-api 事故：Reference for the
    # Claude API / Anthropic SDK — streaming, tool use…——这些只在**模型 API 参考**里出现）
    "streaming", "tool use", "prompt caching", "token counting",
]
_LLM_PROVIDER_NAME_RE = re.compile(
    r"\b(openai|anthropic|claude|gemini|deepseek|qwen|llama|mistral|cohere|bedrock)"
    r"[\w\- ]{0,12}\b(api|sdk)\b|\b(api|sdk)\b[\w\- ]{0,12}"
    r"\b(openai|anthropic|claude|gemini|deepseek|qwen)\b", re.I)
_LLM_SERVING_TERMS = [
    "serving container", "model deployment", "model serving", "serve this model",
    "host this model", "host the model", "image uri", "inference server", "deploy a model",
    "deploy this model", "deploy the model", "model to a", "endpoint and an image",
    "inference endpoint", "sagemaker endpoint", "container selection",
]


def _cls_llm_api(ctx):
    if not hit_pos_any(ctx, _LLM_CONTEXT_TERMS):
        return None, []
    act = [p for p in _LLM_PRIMARY_ACTIONS if hit_pos(ctx, p)]
    if not act and _LLM_PROVIDER_NAME_RE.search(ctx.get("name_norm", "")):
        act = ["name-asserts-provider-api"]   # Skill 名本身就是「<provider> api/sdk」
    serving = hit_pos_any(ctx, _LLM_SERVING_TERMS)
    if act and not serving:
        return "primary", act[:3]
    if act and serving:
        return "primary", act[:3]      # 既有真调用又有 serving 提及 → 仍以调用为主
    if serving:
        return "supporting", ["model-serving-context"]   # 模型部署/容器选择 ≠ API 接入
    if hit_pos_any(ctx, ["api", "sdk", "endpoint", "streaming", "接入", "调用"]):
        return "supporting", ["api-word-only"]
    return "mention", []


def _rule_llm_api(ctx):
    lvl, ev = _cls_llm_api(ctx)
    return (lvl == "primary", ev)


_BROWSER_TERMS = ["browser", "web app", "web application", "website", "web page", "ui",
                  "frontend", "playwright", "selenium", "cypress", "puppeteer",
                  "chrome devtools", "cdp", "浏览器", "网页"]
# 复数形态（'web pages' 不被 'web page' 的 \b 匹配覆盖）
_BROWSER_TERMS += [t + "s" for t in ("web app", "web application", "website", "web page")]
_TEST_ACTION_TERMS = ["test", "tests", "testing", "e2e", "end to end", "acceptance testing",
                      "regression", "qa", "assert", "assertions", "interact and verify",
                      "verify behavior", "verify ui",
                      "validate behavior", "validate ui", "visual regression", "test suite",
                      "browser test", "automated testing", "verifying frontend",
                      "浏览器测试", "端到端测试", "自动化测试", "验收测试"]
# v2.9 §二/§十：primary 必须证明**测试目标**是行为/功能/交互，而不是「场景里出现了 QA」。
_BROWSER_TEST_TARGET_TERMS = [
    "behavior", "behaviour", "functionality", "user flow", "user journey", "ui state",
    "dom", "navigation", "forms", "acceptance", "e2e", "end to end", "end-to-end",
    "regression", "交互", "行为", "用户流程", "页面跳转",
]
# 明确登记的测试工件短语（"run Playwright tests" / "test suites"）= 目标即测试本身
_BROWSER_TEST_ARTIFACT_TERMS = [
    "test suite", "test suites", "run playwright tests", "tests that", "testing standards",
    "acceptance test", "acceptance criteria testing", "e2e testing", "end-to-end testing",
    "visual regression", "regression test", "测试套件",
]
# v2.9 §二/§十：这些形态最多 supporting —— 「截图可用于 QA / theme testing /
# design review / accessibility audit」不是「执行浏览器行为测试」的能力。
_BROWSER_SUPPORT_ONLY_TERMS = [
    "theme testing", "visual review", "design review", "design reviews", "screenshot",
    "screenshots", "accessibility audit", "accessibility audits", "qa workflow",
    "qa workflows", "screenshot for qa", "capture for qa", "visual artifact",
    "responsive design checks", "ui code review",
]


def _cls_browser_qa(ctx):
    """v2.9 §二/§十：browser-qa 四态。

    primary = 浏览器/Web 测试对象 AND 测试动作 AND（测试**目标**（behavior /
    functionality / interaction / acceptance / e2e / regression / DOM/UI state /
    navigation / forms / user flow）或登记的测试工件短语）。
    仅「QA workflow / screenshot for QA / theme testing / design review /
    accessibility audit」这类使用场景词 → supporting；只有浏览器词 / 只有工具名
    → mention。
    """
    if not hit_pos_any(ctx, _BROWSER_TERMS):
        return None, []
    act = [p for p in _TEST_ACTION_TERMS if hit_pos(ctx, p)]
    if act:
        target = [p for p in _BROWSER_TEST_TARGET_TERMS if hit_pos(ctx, p)]
        artifact = [p for p in _BROWSER_TEST_ARTIFACT_TERMS if hit_pos(ctx, p)]
        if target or artifact:
            return "primary", (act[:2] + (target or artifact)[:2])
        # 有测试动作但没有测试目标：若文本还停留在「场景提及 QA」形态 → supporting
        return "supporting", act[:3]
    if hit_pos_any(ctx, ["playwright", "selenium", "cypress", "puppeteer", "cdp"]):
        # 「提到 Playwright」单独出现 = mention（browserclaw 事故），不是测试能力
        return "mention", ["tool-mentioned-only"]
    return "mention", ["browser-word-only"]


def _rule_browser_qa(ctx):
    lvl, ev = _cls_browser_qa(ctx)
    if lvl != "primary":
        return False, []
    # v2.4 §五 的管理面排除保持（azure-resource-manager-playwright 事故）：
    # 管理测试基础设施的 SDK ≠ 执行浏览器测试的能力。
    excl = [k for k in _MGMT_PLANE_TERMS
            if hit(ctx["words"], ctx["text"], ctx["norm"], k)]
    if excl:
        for k in excl:
            if not hit_pos(ctx, k):
                QUALITY["negated_evidence_rejected"] += 1
        return False, []
    return True, ev


_DASH_GENERIC_PHRASES = [
    "build a dashboard", "build dashboard", "build dashboards", "create dashboard",
    "creating dashboards", "data visualization", "data-visualization", "reporting dashboard",
    "business dashboard", "analytics dashboard", "dashboard builder", "chart generation",
    "generate charts", "plotting", "visualize data", "business reporting", "kpi dashboard",
    "数据看板", "统计报表", "图表生成", "可视化报表",
]
_DASH_DOMAIN_WORDS = ["ml", "machine learning", "training", "experiment", "observability",
                      "monitoring", "security", "real-time", "diagnostics", "model",
                      "grafana", "prometheus", "wandb", "trackio", "mlflow"]


def _dashboard_domain_only(ctx):
    """文本里的每个 dashboard 出现点都被领域词限定 → True（非通用看板能力）。"""
    t = ctx["ptext"]
    occ = [m.start() for m in re.finditer(r"\bdashboards?\b|看板", t)]
    if not occ:
        return False
    for i in occ:
        win = t[max(0, i - 45):i + 45]
        if not any(w in win for w in _DASH_DOMAIN_WORDS):
            return False
    return True


def _cls_dashboard_viz(ctx):
    generic = [p for p in _DASH_GENERIC_PHRASES if hit_pos(ctx, p)]
    has_dash = hit_pos_any(ctx, ["dashboard", "dashboards", "chart", "charts", "看板"])
    if generic:
        return "primary", generic[:3]
    if _dashboard_domain_only(ctx):
        return "supporting", ["domain-specific-dashboard"]
    if has_dash:
        return "supporting", ["dashboard-word-only"]
    return None, []


def _rule_dashboard_viz(ctx):
    lvl, ev = _cls_dashboard_viz(ctx)
    return (lvl == "primary", ev)


# ---------- v2.11 §二：security_audit = 「Skill 自己执行安全审计」，不是「示例里提到」 ----------
_SEC_CORE_TERMS = [
    "security audit", "security-audit", "vulnerability assessment", "vulnerability scan",
    "vulnerability scanning", "vulnerability management", "dependency vulnerability",
    "threat model", "threat modeling", "owasp", "sast", "dast", "penetration test",
    "penetration testing", "secure code review", "security review", "security compliance audit",
    "secret scanning", "security scanning", "supply chain security", "security update",
    "dependency audit", "vulnerabilities", "漏洞扫描", "安全审计", "威胁建模", "渗透测试",
]
# 出现在「可选工作流 / 示例 / preset」槽位里的安全词不算核心能力（team-composition 事故：
# "custom team composition for a non-standard workflow such as a migration or security audit"）。
_SEC_EXAMPLE_LEAD_RE = re.compile(
    r"\b(?:such as|for example|for instance|e\.g\.|including|example[sd]?|"
    r"optional|presets?|workflow[s]?|like)\b[^.]{0,50}?$", re.I)


def _sec_occurrence_in_example(ctx, term):
    """term 的每一个正向出现点都位于示例/可选槽位 → True。"""
    occ = [m.start() for m in
           re.finditer(r"(?<!\w)" + re.escape(term).replace(r"\ ", r"[\s\-]") + r"(?!\w)",
                       ctx["ptext"], re.I)]
    if not occ:
        return False
    for i in occ:
        if not _SEC_EXAMPLE_LEAD_RE.search(ctx["ptext"][max(0, i - 60):i]):
            return False
    return True


def _cls_security_audit(ctx):
    hits = [t for t in _SEC_CORE_TERMS if hit_pos(ctx, t)]
    real = [t for t in hits if not _sec_occurrence_in_example(ctx, t)]
    if real:
        return "primary", real[:3]
    if hits:
        return "supporting", ["workflow-example-only"]
    if hit_pos_any(ctx, ["security", "audit", "安全"]):
        return "mention", ["security-word-only"]
    return None, []


def _rule_security_audit(ctx):
    lvl, ev = _cls_security_audit(ctx)
    return (lvl == "primary", ev)


# ---------- v2.8 §九：host 名词（SSH host / 主机）不是部署动词 ----------
_HOST_NOUN_QUALIFIERS = ["ssh", "remote", "local", "cloud", "docker", "parent", "guest",
                          "target", "source", "build", "host name", "hostname", "host os",
                          "host machine", "host environment"]
_HOST_DEPLOY_RE = re.compile(
    r"\bhost(?:s|ing|ed)?\b(?:\s+(?:an?|the|your|our|a)\s+|\s+)(?:"
    r"app|apps|application|applications|site|sites|website|websites|service|services|model)\b",
    re.I)
_NOUNY_HOST_RE = re.compile(
    r"\b(?:ssh|remote|local|docker|cloud|parent|guest|target|source|build|vm|sandbox)"
    r"\s+(?:sandbox,\s*)?host(?:s)?\b", re.I)

# ---------- v2.9 §二：「创作图像」与「捕获网页画面」必须分开 ----------
_PAGE_CAPTURE_TERMS = [
    "screenshot", "screenshots", "screen capture", "page capture", "full-page capture",
    "full page capture", "webpage pdf", "website thumbnail", "webpage thumbnail",
    "site thumbnail", "page thumbnail", "thumbnail of", "capture webpage", "网页截图",
    "整页截图", "页面捕获", "屏幕截图",
]
_IMAGE_CREATIVE_TERMS = [
    "image generation", "image-generation", "image editing", "image-editing",
    "illustration", "thumbnail", "svg art", "svg generation", "creative image",
    "generate image", "generate images", "creating image", "creating images",
    "create image", "create images", "artwork", "visual art", "poster",
    "icon generation", "sprite", "sprites", "texture", "textures",
    "visual asset", "visual assets", "static visual design", "image mockup",
    "图片生成", "图片处理", "图像生成", "相册封面",
    "海报", "插画", "图标生成", "视觉素材",
]


def _rule_image_creative(ctx):
    """v2.9 §二：『website thumbnail / screenshot / full-page capture』是**捕获网页画面**，
    不是创作图像；只有当 creative 证据不止于捕获语境里的 thumbnail 时才成立。"""
    hits = [k for k in _IMAGE_CREATIVE_TERMS if hit_pos(ctx, k)]
    if not hits:
        return False, []
    if any(hit_pos(ctx, k) for k in
           ["image analysis", "imageanalysis", "ocr", "vision api", "object detection"]):
        return False, []          # v2.6 §七 的识别类排除保持
    if all(h == "thumbnail" for h in hits) and hit_pos_any(ctx, _PAGE_CAPTURE_TERMS):
        return False, []          # 页面捕获冒充创作（latchshot 事故）
    return True, hits


# v2.9 §三 / §十：信息标签（不在 suppression 表 → 不吃缺口分，只回答「它到底会什么」）
_SUBCAP_TERMS = {
    "accessibility_audit": ["accessibility audit", "accessibility audits", "a11y audit",
                            "wcag", "accessibility compliance", "无障碍审计"],
    "design_token_migration": ["design token migration", "migrate design tokens",
                               "token migration", "migrating design tokens"],
    "figma_production_handoff": ["figma handoff", "figma to code", "production handoff",
                                 "figma mcp", "design handoff"],
    "android_material_design": ["material design 3", "material 3", "material3",
                                "material you"],
}
# 信息标签 → 它实际所属的已装侧能力族（用于 capability_saturation：
# 「名字不同不等于 new_capability」，§六）。不在表内的标签 = 新族，saturation=none。
TAG_FAMILY = {
    "browser_capture": "browser_automation",
    "accessibility_audit": "frontend_design",
}
# v2.9 §五/§六：哪些能力族登记了可增量的子能力（只有列出的族才允许按子能力进 Top）
FAMILY_SUBCAPS = {
    "frontend_design": ["accessibility_audit", "design_token_migration",
                        "figma_production_handoff", "android_material_design"],
}


def subcapability_hits(cand, ctx=None):
    """候选在正向文本里声明了哪些子能力（_SUBCAP_TERMS 键）。"""
    if ctx is None:
        ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    return [sub for sub, terms in _SUBCAP_TERMS.items()
            if any(hit_pos(ctx, t) for t in terms)]


def incremental_subcapability(cand, family, installed_texts, ctx=None,
                              full_texts=None, members_checked=False):
    """v2.11 §十三：子能力增量的证据分级——「底座摘要没写」≠「已装 Skill 明确没有」。

    返回 [(subcap, evidence_level)]：
      confirmed_absent  = 该族全部已装成员的完整 SKILL.md 已被**实际读取**且均未提及；
      summary_not_found = 仅在 Installed Context §6 简表（摘要）层面未发现；
      unknown           = 连摘要都不可得（缺输入 B）——不得作为 strong 饱和解除依据。
    子能力若在摘要或全文任一处出现 → 视为已覆盖，不再返回。
    """
    if not family:
        return []
    allowed = set(FAMILY_SUBCAPS.get(family) or [])
    if not allowed:
        return []
    hits = set(subcapability_hits(cand, ctx=ctx))
    want = hits & allowed
    if not want:
        return []
    covered = set()
    for name, txt in (installed_texts or {}).items():
        blob = f"{name} {txt or ''}".lower()
        for sub in want:
            if any(t in blob for t in _SUBCAP_TERMS[sub]):
                covered.add(sub)
    out = []
    for sub in sorted(want - covered):
        if not (installed_texts or {}):
            out.append((sub, "unknown"))
            continue
        if members_checked and full_texts is not None:
            if any(any(t in (txt or "").lower() for t in _SUBCAP_TERMS[sub])
                   for txt in full_texts.values()):
                continue
            out.append((sub, "confirmed_absent"))
        else:
            out.append((sub, "summary_not_found"))
    return out


# v2.9 §八/§九：required_tech —— Skill **核心方法依赖**的技术（hard requirement），
# 与「描述里举例支持」（optional，由四态证据语境负责）区分开。
_HARD_TECH_SPECS = [
    ("react", [r"\b(?:build|builds|creating|create|develop|developing|implement|"
               r"design|write|using|with)\b[^.]{0,60}?\breact\b(?! [\s\-]*(?:native))",
               r"\breact\b\s*(?:applications?|apps?|components?|hooks?|codebase|"
               r"projects?|ui)\b"]),
    ("react-native", [r"\breact[\s\-_]+native\b(?! (?:extension|extensions|"
                      r"plugin|support|supported|works|compatible))"]),
    ("expo", [r"\bexpo\s*(?:router|sdk|project|apps?|development|build|eas)\b",
              r"\b(?:with|using|in)\s+expo\b"]),
    ("nextjs", [r"\bnext\.?js\b(?! (?:compatible|supports|works))"]),
    ("tailwind", [r"\b(?:with|using|based on|in|via)\s+tailwind\b",
                  r"\btailwind\s+(?:css|classes|design|v\d)\b",
                  r"\btailwind[ -]based\b"]),
    ("framer-motion", [r"\bframer\s+motion\b"]),
    ("jetpack-compose", [r"\bjetpack\s+compose\b"]),
    ("swiftui", [r"\bswiftui\b"]),
    ("appkit", [r"\bappkit\b"]),
    ("vue", [r"\bvue\.?js\b", r"\bvue\s+(?:apps?|components?|projects?)\b"]),
    ("angular", [r"\bangular\b"]),
    ("svelte", [r"\bsvelte(?:kit)?\b"]),
]
# 这些是「万维网通用标准」：对 HTML / Web / PWA 类项目天然兼容，不做 hard 提取。
_COMPATIBLE_TECH_TERMS = ["css", "html", "javascript", "responsive", "grid", "flexbox",
                          "container queries", "fluid typography", "media queries"]
# required_tech ↔ 项目侧可满足它的技术栈标签（TECH_MATCH 键）/ 定位文本 token
_TECH_SATISFIED_BY = {
    "react": ({"React", "Next.js", "React Native", "Expo"}, r"\breact\b|\bnext[\s.\-]?js\b"),
    "react-native": ({"React Native", "Expo"}, r"\breact[\s\-_]+native\b|\bexpo\b"),
    "expo": ({"Expo", "React Native"}, r"\bexpo\b|\breact[\s\-_]+native\b"),
    "nextjs": ({"Next.js"}, r"\bnext[\s.\-]?js\b"),
    "tailwind": ({"Tailwind", "shadcn"}, r"\btailwind\b|\bshadcn\b"),
    "framer-motion": ({"React", "Next.js"}, r"\breact\b|\bnext[\s.\-]?js\b"),
    "jetpack-compose": ({"Kotlin", "Android"}, r"\bjetpack\b|\bcompose\b|\bkotlin\b"),
    "swiftui": ({"macOS 桌面", "原生"}, r"\bswiftui\b|\bswift\b"),
    "appkit": ({"macOS 桌面", "原生"}, r"\bappkit\b|\bmacos\b"),
    "vue": ({"Vue"}, r"\bvue\b"),
    "angular": ({"Angular"}, r"\bangular\b"),
    "svelte": ({"Svelte"}, r"\bsvelte\b"),
}


def tech_requirements(cand, ctx=None):
    """返回 (required_tech[], compatible_tech[])。

    required = 核心方法必须依赖（hard requirement）；只是举例「支持 X」的
    optional 提及不算（由四态证据语境负责）。compatible = 通用 Web 标准词，
    对 HTML / Web / PWA 项目天然兼容（§九：兼容 ≠ 机械相等）。
    """
    if ctx is None:
        ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    text = f"{ctx.get('name_norm', '')} {ctx['ptext']}"
    req = []
    for tech, pats in _HARD_TECH_SPECS:
        if any(re.search(p, text, re.I) for p in pats):
            req.append(tech)
    # react-native 已成立时，"react" 往往是同一短语的碎片，去重
    if "react-native" in req and "react" in req:
        req.remove("react")
    compat = [t for t in _COMPATIBLE_TECH_TERMS if hit_pos(ctx, t)]
    return req, compat


def tech_project_conflicts(req_tech, project):
    """required_tech 与项目档案（技术栈标签 + 定位文本）不兼容 → 返回冲突技术列表。"""
    if not req_tech:
        return []
    labels = set(project.get("tech") or [])
    ptext = f"{project.get('name', '')} {project.get('desc', '')}".lower()
    bad = []
    for t in req_tech:
        labels_ok, pat = _TECH_SATISFIED_BY.get(t, (set(), r"$^"))
        if labels & labels_ok or re.search(pat, ptext, re.I):
            continue
        bad.append(t)
    return bad


CAP_RULE = {
    "mobile_qa": {
        # 组间 AND：既要移动平台，又要 QA / 设备 / 构建验收证据
        "all_groups": [_MOBILE_PLATFORM, _QA_OR_DEVICE],
        "context_terms": _QA_OR_DEVICE + _MOBILE_PLATFORM,
    },
    "mobile_dev": {
        # 移动「开发」：只要是移动平台的开发/最佳实践即可，不要求 QA 证据
        "all_groups": [["expo", "react native", "flutter", "android", "ios", "swiftui",
                        "jetpack compose", "kotlin multiplatform", "mobile app development",
                        "mobile development", "跨平台开发", "移动开发"]],
        "any_of": ["app", "development", "developer", "skill", "best practices", "ui",
                   "component", "navigation", "编程", "框架"],
        "context_terms": ["expo", "react native", "android", "ios"],
    },
    # v2.8 §二：expo_rn_dev 标签 = primary（核心 RN/Expo 开发），支持型提及不打标签
    "expo_rn_dev": {"custom": _rule_expo_rn},
    # v2.8 §五：领域内仪表盘 / 模型服务改挂独立信息标签（不在 suppression 表 → 不吃缺口分）
    "ml_experiment_tracking": {
        "any_of": ["experiment tracking", "track experiments", "ml training",
                   "training metrics", "training experiments", "log metrics",
                   "logging metrics", "model training", "experiment dashboard",
                   "mlflow", "Weights & Biases", "wandb", "训练指标", "实验跟踪"],
    },
    "model_serving": {
        "any_of": ["serving container", "model serving", "model deployment",
                   "inference server", "inference endpoint", "image uri",
                   "serve this model", "host this model", "模型服务", "推理服务器"],
    },
    "image_creative": {"custom": _rule_image_creative},
    # v2.9 §二：网页截图 / 页面捕获是独立能力，不塞进 image_creative / browser_qa
    "browser_capture": {"any_of": list(_PAGE_CAPTURE_TERMS)},
    # v2.9 §十：无障碍审计单列信息标签，不偷吃 browser-qa 缺口
    "accessibility_audit": {"any_of": _SUBCAP_TERMS["accessibility_audit"]},
    # v2.9 §三：面向 LLM / Agent 的文档生成（llms.txt 等），不是 spec-driven
    "llm_documentation": {
        "any_of": ["llms.txt", "llms-full.txt", "llm-friendly", "llm readable",
                   "llm-readable", "model-readable", "agent docs", "agent documentation",
                   "wiki accessible to language models"],
    },
    "data_analytics": {
        "any_of": ["analytics", "data analysis", "data-analysis", "data visualization",
                   "data-visualization", "chart generation", "chart-generation", "pandas",
                   "dataframe", "report generation", "数据分析", "可视化"],
        "none_of": ["google analytics", "web analytics"],
    },
    # v2.11 §二：primary = Skill 自己执行安全审计类核心任务；示例/可选工作流里的安全词 = supporting
    "security_audit": {"custom": _rule_security_audit},
    "supabase_db": {
        # v2.3：裸 RLS 不足 —— Power BI / 其他数据库也有 row-level security，
        # 必须**明确出现 supabase** 才算 Supabase 能力（旧版把裸 rls 当证据，属误报）。
        "all_groups": [["supabase"]],
        "context_terms": ["rls", "row level security", "postgres", "postgresql",
                          "migration", "database"],
    },
    "postgres_db": {
        "all_groups": [["postgres", "postgresql", "psql", "pgvector", "alloydb", "cloud sql"]],
        "none_of": ["supabase"],
        "context_terms": ["database", "sql", "query", "index", "migration"],
    },
    # v2.4 §七/§八：从「出现 test/qa 就命中」改为「主能力证据」复合判定
    "testing_qa": {"custom": _rule_testing_qa},
    # v2.7 §三：Question Answering 独立记录位（不吃 testing_qa 缺口分）
    "question_answering": {"custom": _rule_question_answering},
    # v2.5 §七：只认 Word / Excel / 表格；PPTX/Powerpoint 单列，不得冒充 docx_xlsx 缺口
    "docx_xlsx": {"custom": _rule_docx_xlsx},
    "pptx_processing": {"all_groups": [_PPTX_TERMS],
                        "context_terms": ["pdf", "html", "slides"]},
    # v2.5 §六：必须是「核心 MCP 开发能力」，单纯提及不算
    "mcp_dev": {"custom": _rule_mcp_dev},
    "windows": {
        "any_of": ["windows", "powershell", "win32", "wpf", "winui", "windows 11"],
    },
    "macos": {
        "any_of": ["macos", "darwin", "applescript", "appkit", "cocoa", "mac os"],
    },
    "frontend_design": {"any_of": _FRONTEND_DESIGN_TERMS},
    "mcp_usage": {"custom": _rule_mcp_usage},   # v2.6 §六：独立记录位，不参与 mcp_dev 评分
    "browser_automation": {
        "any_of": ["browser automation", "browser-automation", "playwright", "puppeteer",
                   "selenium", "chrome devtools", "cdp", "headless browser", "web scraping",
                   "浏览器自动化"],
    },
    "course_pipeline": {
        "any_of": ["transcript", "transcription", "course notes", "course-notes",
                   "markdown organize", "lecture notes"],
    },
    "deployment_vercel": {
        "all_groups": [["vercel"]],
        "context_terms": ["deploy", "deployment", "hosting", "preview"],
    },
    "deployment_netlify": {
        "all_groups": [["netlify"]],
        "context_terms": ["deploy", "deployment", "hosting"],
    },
    "github_ops": {
        "any_of": ["github", "pull request", "pull-request", "repository management",
                   "code review", "issue management"],
    },
}

# ==========================================================================
# 二、项目需求规则 NEED_RULE（需求侧真相源，读 SKILL_CONTEXT.md 的 needs 权重）
# ==========================================================================
# 与 CAP_RULE 分开的理由：CAP_RULE 决定「已装侧能力压制」，NEED_RULE 决定「是否命中
# 用户真实需求」。两侧混用会让「平台词」同时在两个方向放大误差。

# v2.4 §六：部署动词 + 部署对象。`hosting` / `hosted` 单独出现不算部署能力，
# 必须与「部署对象」（app / site / service / build / pages…）或 publish 同现。
# 事故：azure-microsoft-playwright-testing-ts 的 "cloud-hosted browsers" 被判 deploy。
_DEPLOY_OBJECTS = ["app", "application", "site", "website", "web app", "service", "pages",
                   "static", "build", "artifact", "deploy", "deployment", "publish",
                   "production", "environment"]
_DEPLOY_HOST_VERBS = ["hosting", "hosted", "publish", "publishing"]
_DEPLOY_ANY_GROUPS = [[v, o] for v in _DEPLOY_HOST_VERBS for o in _DEPLOY_OBJECTS]

# v2.4 §五：管理面 / 资源编排语境。这类 Skill 管理的是**测试基础设施**，
# 不是「执行浏览器测试」的能力 —— 不得据此判 browser-qa。
# （通用守卫，不是给 Playwright 打补丁：对任何管理面 SDK 都成立。）
_MGMT_PLANE_TERMS = ["management plane", "control plane", "resource manager",
                     "name availability", "workspace quota", "workspace quotas",
                     "provisioning api", "service quota", "management-plane"]

# v2.4 §十：排除性语境登记表。命中这些 none_of 词 = 「语义上被排除的假相关」，
# 计入 negated_evidence_rejected（与否定窗口同一口径），让审查者看得见门在工作。
_EXCLUSION_CONTEXT_TERMS = {t.lower() for t in _MGMT_PLANE_TERMS}

# ---------- v2.5 §一：android 需求 = 真正的「Android 真机 QA / 构建签名」 ----------
# §一 明令：禁止使用裸 device / build / install / launch 作 Android QA 正向证据
# （事故：google-mobile-ads-get-started 只是「接入广告 SDK」，install/integrate 就命中）。
_ANDROID_PLATFORM = ["android", "kotlin", "jetpack", "gradle", "安卓"]
_ANDROID_QA_DEVICE = [   # A. 测试 / 真机
    "qa", "test", "testing", "e2e", "adb", "emulator", "real device", "device farm",
    "appium", "detox", "maestro", "espresso", "xctest", "instrumentation test",
    "真机", "自动化测试"]
_ANDROID_BUILD_SIGN = [  # B. 构建 / 签名 / 安装验收
    "signing", "code signing", "keystore", "signed apk", "apk", "aab", "app bundle",
    "build verification", "build signing", "release build verification", "install apk",
    "app install verification", "app launch verification", "签名", "构建验收"]
# 只允许用来把等级降为 mention 的裸词（不作正向证据）
_ANDROID_BARE_TERMS = ["device", "devices", "build", "building", "install", "installation",
                       "launch", "verification", "release"]
# 广告语境的 "test ads"（拉取广告测试位）≠ QA 能力
_AD_TEST_RE = re.compile(r"\btest(?:ing|s)?\s+(?:the\s+|your\s+)?(?:live\s+)?ads?\b", re.I)


def _cls_android(ctx):
    """v2.5 §一 + §九：返回 (等级, 证据)。primary = 平台证据 AND（A 类 ∪ B 类）证据。"""
    plat = [k for k in _ANDROID_PLATFORM if hit_pos(ctx, k)]
    ev = sorted({k for k in _ANDROID_QA_DEVICE + _ANDROID_BUILD_SIGN if hit_pos(ctx, k)})
    if ev and set(ev) <= {"test", "testing"} and _AD_TEST_RE.search(ctx["ptext"]):
        ev = []     # 证据只剩「test ads」→ 广告语境，不是 QA
    if plat and ev:
        return "primary", sorted(set(plat + ev))
    if plat and (any(hit_pos(ctx, k) for k in _ANDROID_BARE_TERMS) or ev):
        return "mention", []    # 只有平台词 + 裸 install/build/launch 类词
    return None, []


def _rule_android(ctx):
    """NEED 命中 ⟺ primary（§九：mention 级 Android 内容不得命中 android QA 需求）。"""
    lvl, ev = _cls_android(ctx)
    return (lvl == "primary", ev)


# ---------- v2.5 §八：github-auto 必须「GitHub + 操作/自动化语义」 ----------
# 事故：breakdown-test 核心是 Test Planning，只因 `for GitHub projects` 命中 github-auto。
_GITHUB_PLATFORM = ["github", "github.com", "gh cli"]
_GITHUB_OPS = [
    "github actions", "workflow dispatch", "repository automation", "repo automation",
    "repo creation", "repository creation", "issue creation", "issue management",
    "issues", "issue", "pull request", "pull requests", "pr review", "pr automation",
    "code review", "release automation", "labels", "milestones", "repository sync",
    "commit automation", "github api", "自动建 issue", "自动创建 issue", "自动 pr", "仓库同步"]
GITHUB_AUTO_RULE = {"all_groups": [_GITHUB_PLATFORM, _GITHUB_OPS]}


def _cls_github_auto(ctx):
    ok, ev = match_rule(ctx, GITHUB_AUTO_RULE)
    if ok:
        return "primary", ev
    if hit_pos_any(ctx, _GITHUB_PLATFORM):
        return "mention", []   # §八：裸 GitHub / GitHub projects 不足以成立
    if hit_any(ctx["words"], ctx["text"], ctx["norm"], _GITHUB_PLATFORM) \
            and not hit_pos_any(ctx, _GITHUB_PLATFORM):
        return "negated", []
    return None, []


# ---------- v2.7 §四：deploy 必须「部署动词 + 通用部署对象」**邻近**成立 ----------
# 事故：game-engine「building web-based games / publishing games」凭
#   publishing + 文本任意位置的 build 组合成 deploy —— 发布游戏 ≠ 部署用户项目；
#   detection-engineering「deploy YARA-L rules to Google SecOps」—— 平台内部规则
#   发布 ≠ 通用项目部署。v2.6 的 any_groups 是「全文任意共现」，语义上就是错的。
# 规则：动词与通用对象必须同句相邻（≤30 字符窗口）；
#   rules / policies / prompts / detections / configuration / dashboards / alerts /
#   model settings / games / content / documentation / packages(单独) 等**不是**通用部署对象。
_DEPLOY_GENERIC_OBJS = (r"app|apps|application|applications|website|websites|web app|"
                        r"web apps|site|sites|static site|service|services|function|"
                        r"functions|serverless function|microservice|microservices|"
                        r"container|containers|workload|workloads|artifact|artifacts|"
                        r"frontend|backend|serverless|cloud function|pages|production|"
                        r"environment|bundle|build artifact|release build")
# v2.8 §九：host 系词从通用动词表拆出——「SSH host / 主机」是名词，
# 只有 host(s|ing) + 限定词 + app/site/service/model 才算托管动作。
_DEPLOY_VERBS = (r"deploy|deploys|deploying|deployed|publish|publishes|publishing|"
                 r"roll out|rolls out|rolling out|rollout")
_DEPLOY_PROX_RE = re.compile(
    rf"\b(?:{_DEPLOY_VERBS})\b[^.;!?]{{0,50}}?\b(?:{_DEPLOY_GENERIC_OBJS})\b", re.I)
_DEPLOY_TO_RE = re.compile(
    r"\b(?:deploy|publish)\s+(?:it|them|your\s+\w+)?\s*to\s+(?:the\s+)?(?:cloud|production|"
    r"vercel|netlify|cloudflare|heroku|railway|render|internet)\b", re.I)
_DEPLOY_PIPELINE_WORDS = [
    "release pipeline", "deployment pipeline", "deploy pipeline", "publish pipeline",
    "provision deployment", "create deployment", "create a deployment",
    "static hosting", "web hosting", "site deployment", "app deployment",
    "application deployment", "部署上线", "上线部署", "部署流水线", "部署应用",
    "发布站点", "上线服务", "发布应用",
]
# 显式「非通用部署对象」表（§四 点名的排除项）：仅用于文档与测试内省；
# 它们**不在** _DEPLOY_GENERIC_OBJS 里，邻近匹配天然不成立。
_DEPLOY_INTERNAL_OBJS = ["rules", "policies", "prompts", "detections", "configuration",
                         "configs", "dashboards", "alerts", "security rules",
                         "model settings", "games", "content", "documentation"]


def _deploy_hits(ctx):
    """v2.7 §四 + v2.8 §九：动词+通用对象邻近 / deploy to X / pipeline 词组 /
    host(s|ing) an app|site|service|model（严格式）；「SSH host + local container」不算。"""
    ev = []
    t = ctx["ptext"]
    m = _DEPLOY_PROX_RE.search(t)
    if m:
        ev.append("deploy-verb+object:" + m.group(0).strip()[:46])
    mh = _HOST_DEPLOY_RE.search(t)
    if mh and not _NOUNY_HOST_RE.search(t):
        ev.append("host-action:" + mh.group(0).strip()[:30])
    m2 = _DEPLOY_TO_RE.search(t)
    if m2:
        ev.append("deploy-to:" + m2.group(0).strip()[:30])
    for w in _DEPLOY_PIPELINE_WORDS:
        if hit_pos(ctx, w):
            ev.append(w)
    return (bool(ev), ev[:4])


def _rule_deploy(ctx):
    """NEED_RULE / CAP 入口：v2.7 §四 邻近语义。"""
    ok, ev = _deploy_hits(ctx)
    if not ok:
        # v2.4 §十 口径保持：被否定窗口 / 重定向压制掉的 deploy 命中必须仍可审计
        m_raw = _DEPLOY_PROX_RE.search(ctx["text"])
        if m_raw and not _DEPLOY_PROX_RE.search(ctx["ptext"]):
            QUALITY["negated_evidence_rejected"] += 1
        for w in _DEPLOY_PIPELINE_WORDS:
            if hit(ctx["words"], ctx["text"], ctx["norm"], w) and not hit_pos(ctx, w):
                QUALITY["negated_evidence_rejected"] += 1
    return (ok, ev)


def _cls_deploy(ctx):
    """v2.7 §四/§八：primary = 动词+通用对象邻近 / deploy to X / pipeline 词组；
    「publish/host 名词式结果语境」与裸 deployment 名词只算 mention；否定作用域 → negated。"""
    ok, ev = _deploy_hits(ctx)
    if ok:
        return "primary", ev
    if hit_pos_any(ctx, ["deployment", "deployments"]) \
            and not hit_pos_any(ctx, ["deploy", "deploying", "deploys"]):
        return "mention", []
    dep_kw = ["deploy", "deployment", "deploying"]
    if hit_any(ctx["words"], ctx["text"], ctx["norm"], dep_kw) \
            and not hit_pos_any(ctx, dep_kw):
        return "negated", []
    return None, []

# ---------- v2.9 §三：spec-driven = 「以规格驱动开发」，不是「遵守某个格式规范」 ----------
_SPEC_DEV_CORE_PHRASES = [
    # A. 产出 / 维护**开发规格**本身
    "write specification", "write the specification", "write a specification",
    "create specification", "create the specification", "create a specification",
    "generates a specification", "generate specification", "feature specification",
    "product specification", "requirements specification", "requirements spec",
    "requirements document", "requirements definition", "product requirements",
    "product spec", "functional specification", "functional specification",
    "specification document", "spec document", "writing specs", "write specs",
    "write a spec", "write the spec", "create spec", "create a spec", "draft spec",
    "authoring specification",
    # B. SDD / Spec Kit 类开发流程与流程工件
    "spec driven", "spec-driven", "specification driven", "specification-driven",
    "spec driven development", "spec-driven development", "spec kit", "sdd workflow",
    "constitution", "acceptance criteria", "technical design", "design doc",
    "design document", "prd", "rfc",
    "需求规格", "产品规格", "技术规格", "规格说明书", "需求文档", "验收标准", "规格驱动",
]
# v2.11 §三：task breakdown / implementation plan 只有在**开发规格 / 功能规划语境**里才算
# spec-driven；「test task breakdown / QA task breakdown / migration task breakdown」
# 这类计划工件最多 supporting（breakdown-test 事故）。
_SPEC_WEAK_PLAN_TERMS = [
    "implementation plan", "task breakdown", "implementation plans", "task breakdowns",
    "任务拆解", "开发计划", "实施计划",
]
_DEV_SPEC_CONTEXT_RE = re.compile(
    r"\b(?:spec|specs|specification|sdd|prd|constitution|requirements?\b|user stor(?:y|ies)"
    r"|feature|product|functional)\b|需求|产品规格", re.I)
# 「following / compliant with the X specification」= **遵守标准**，不是驱动开发。
_SPEC_COMPLIANCE_RE = re.compile(
    r"\b(?:following|follows|compliant with|compliance with|comply with|complies with|"
    r"conform(?:s|ing)? to|adher(?:e|es|ing) to|according to|per|based on)\s+"
    r"(?:the|a|an|its|their|this)?\s*[\w.+\-' ]{0,28}?"
    r"\bspec(?:ification)?s?\b", re.I)
_SPEC_STANDARD_NOUNS_RE = re.compile(
    r"\b(?:llms?(?:\.txt)?|txt|protocol|file\s*format|format|api|css|html|openapi|"
    r"swagger|wire|http|https|industry|de facto|technical standard|grammar|schema|"
    r"interface|markdown|json|encoding|layer|interface|style guide)\s+spec(?:ification)?s?\b",
    re.I)


_SPEC_AUTHOR_RE = re.compile(
    r"\b(?:write|writes|writing|create|creates|creating|generate|generates|generating|"
    r"author(?:s|ing)?|draft(?:s|ing)?|develop(?:s|ing)?|produce(?:s|ing)?|"
    r"maintain(?:s|ing)?|update(?:s|d)?|break\s+down)\b[^.]{0,40}?"
    r"\bspec(?:s|ification|ifications)\b", re.I)


def _spec_core_hits(ctx):
    strong = [p for p in _SPEC_DEV_CORE_PHRASES if hit_pos(ctx, p)]
    # 「create detailed specifications for implementation」这类 动词+限定词+spec 形态
    # 也算产出开发规格（gen-specs-as-issues 反向保护）；纯字符串短语覆盖不了。
    if _SPEC_AUTHOR_RE.search(ctx["ptext"]):
        strong.append("author-spec-pattern")
    weak = [p for p in _SPEC_WEAK_PLAN_TERMS if hit_pos(ctx, p)]
    # v2.11 §三：弱规划词只有在开发规格/功能规划语境里才升级为 primary
    if weak and (strong or _DEV_SPEC_CONTEXT_RE.search(ctx["ptext"])):
        strong = strong + weak
    return strong


def _spec_compliance_only(ctx):
    """文本里每一处 spec(ification) 出现点都处于「遵守标准」语境 → True。"""
    occ = [m.start() for m in re.finditer(r"\bspec(?:s|ification|ifications)?\b",
                                           ctx["ptext"], re.I)]
    if not occ:
        return False
    for i in occ:
        win = ctx["ptext"][max(0, i - 60):i + 30]
        if _SPEC_COMPLIANCE_RE.search(win) or _SPEC_STANDARD_NOUNS_RE.search(win):
            continue
        return False
    return True


def _cls_spec_driven(ctx):
    core = _spec_core_hits(ctx)
    if core and not _spec_compliance_only(ctx):
        return "primary", core[:3]
    if core:
        return "supporting", core[:2]
    if re.search(r"\bspec(?:s|ification|ifications)?\b", ctx["ptext"], re.I):
        # 只出现 "the llms.txt specification" / "CSS specification" 这类标准名
        return "supporting", ["compliance-with-standard"]
    return None, []


def _rule_spec_driven(ctx):
    lvl, ev = _cls_spec_driven(ctx)
    return (lvl == "primary", ev)


NEED_RULE = {
    # w=51（最高权重）：Agent / 多智能体治理与提示词工程
    "agent-governance": {"any_of": ["agent governance", "agent orchestration", "multi agent",
                                    "multi-agent", "orchestrator", "agent team", "agent teams",
                                    "skill manager", "guardrail", "guardrails", "prompt engineering",
                                    "prompt-engineering", "subagent", "sub-agent", "agent protocol",
                                    "智能体治理", "多智能体"]},
    # v2.2 收紧：真实需求是「Android 真机 QA / 构建签名」，不是「任何 Android 内容」
    # v2.5 §一 再收紧：必须是测试/真机（A 类）或构建/签名（B 类）证据；
    #   裸 device / build / install / launch 一律不作正向证据（Google Mobile Ads 接入事故）
    "android": {"custom": _rule_android,
                "context_terms": ["android", "kotlin"]},
    # v2.4 §五：管理面 SDK（如 Azure Resource Manager for Playwright Testing）只是
    # 「管理测试工作区」，不是浏览器测试能力 → 排除。
    # v2.8 §八：primary = 测试动作 AND 浏览器对象；单独提到 Playwright 只是 mention
    "browser-qa": {"custom": _rule_browser_qa},
    # v2.8 §五：generic 看板/可视化才 primary；ML/训练/监控/安全等领域内看板 → supporting
    "dashboard-viz": {"custom": _rule_dashboard_viz},
    "data-pipeline": {"any_of": ["etl", "data pipeline", "data-pipeline", "ingest",
                                 "data warehouse", "warehouse", "data ingestion"]},
    # v2.2 收紧：不再用裸 `release` 命中所有「发布」语境
    # v2.3 再收紧：Vercel / Netlify / CI-CD 只能作**语境**（context_terms），
    #   必须真的出现 deploy/hosting/release-pipeline 动作词才算「部署能力」。
    #   事故：react-best-practices 只因来自 Vercel、bats-testing-patterns 只因 CI/CD
    #   就被判成 deploy 能力。
    # v2.4 §六：再删裸 `hosted`；`hosting`/`hosted` 必须与部署对象同现（any_groups）。
    #   事故：azure-microsoft-playwright-testing-ts 的 "cloud-hosted browsers" + CI/CD。
    # v2.5 §二：`Don't use for ..., model deployment to endpoints` 里的 deployment
    #   现在被否定枚举整段压掉（agent-platform-prompt-management 假 deploy 事故）。
    "deploy": {"custom": _rule_deploy},
    # v2.2 收紧：不能因描述里写 "desktop application" 就命中，重点在打包/签名/发布
    "desktop-app": {"any_of": ["tauri", "electron", "menubar", "menu bar app", "native desktop",
                               "desktop packaging", "app packaging", "packaging", "code signing",
                               "notarization", "dmg", "nsis", "msix", "app bundle", "pkg installer",
                               "跨平台打包", "桌面应用打包"],
                    "context_terms": ["desktop", "native", "installer"]},
    "docker-infra": {"any_of": ["docker", "dockerfile", "docker compose", "containerize",
                                "containerization", "compose file", "容器化"]},
    # v2.8 §二：「SDK supports React Native」= supporting，不得拿 expo-rn 完整权重
    "expo-rn": {"custom": _rule_expo_rn},
    "finance-calc": {"any_of": ["finance", "financial", "portfolio", "stock", "stocks", "etf",
                                "investment", "investing", "dividend", "valuation", "backtest",
                                "quantitative trading", "估值", "股息", "投资", "回撤"]},
    "frontend-design": {"any_of": _FRONTEND_DESIGN_TERMS},
    # v2.5 §八：裸 GitHub / "for GitHub projects" 不足以命中，
    #   必须 GitHub + 操作/自动化语义（Actions / issue / PR / release automation…）
    "github-auto": GITHUB_AUTO_RULE,
    # v2.2 收紧：不再用裸 `prompt`；重点在 API/SDK/streaming/structured output/tool calling
    # v2.3 再收紧：必须 **LLM/model/provider 语境** AND **API/SDK/动作词**。
    #   单独的 "API" / "SDK integration" / "Gemini" 不足以证明这是 LLM 接入能力。
    #   事故：google-ads-api-mcp-setup（Google Ads API + Gemini）、
    #        google-mobile-ads-validate（Mobile Ads SDK）都被误判成 LLM API 集成。
    # v2.8 §七：primary 必须强调「调用/集成模型 API」；
    # 模型部署 / serving container / image URI 属 ml_infrastructure，不是 llm-api。
    "llm-api": {"custom": _rule_llm_api},
    "media-transcribe": {"any_of": ["transcript", "transcription", "whisper", "asr", "subtitle",
                                    "subtitles", "speech to text", "speech-to-text", "voice to text",
                                    "视频转文字", "字幕"]},
    # v2.2 收紧：不要裸 photo/image，重点在 EXIF / gallery / album / library / metadata
    "photo-mgmt": {"any_of": ["exif", "gallery", "albums", "album management", "photo library",
                              "photo-library", "image library", "photo management",
                              "photo-management", "image management", "asset management",
                              "asset library", "metadata extraction", "lightroom",
                              "media library", "相册", "照片管理", "素材管理"],
                   "context_terms": ["photo", "image", "metadata"]},
    "privacy-local": {"any_of": ["local first", "local-first", "privacy", "privacy preserving",
                                 "encryption", "encrypt", "end to end encrypted", "self hosted",
                                 "self-hosted", "data sovereignty", "本地优先", "隐私"]},
    "pwa-offline": {"any_of": ["pwa", "progressive web app", "offline first", "offline-first",
                               "offline support", "service worker", "service-worker",
                               "web app manifest", "installable web app", "离线", "本地存储"]},
    # v2.2 新增组合条件：Python 平台词 + 自动化/脚本/数据处理动作词
    # v2.8 §六：产品自带 CLI/SDK 里的 automation/Python 字眼 = supporting/mention；
    # primary 要「本地/工作流/批处理/文件/数据」自动化核心任务。
    "python-auto": {"custom": _rule_python_auto},
    "responsive": {"any_of": ["responsive", "responsiveness", "mobile first", "mobile-first",
                              "breakpoint", "media query", "responsive layout", "响应式"]},
    # v2.7 §八：出现 `secret` ≠ 密钥安全能力。
    # 「产品里有一个 secret 资源」（Measurement Protocol secrets / client secret field）
    # 与「安全管理用户 API 密钥」不是一回事 → 必须 安全对象 AND 安全动作。
    "secret-safety": {
        "all_groups": [
            ["secret", "secrets", "credential", "credentials", "api key", "api-key",
             "apikey", "token", "tokens", "env var", "env-var", "environment variable",
             "keychain", "dotenv", "密钥", "凭据", "令牌"],
            ["store securely", "secure storage", "securely store", "secret management",
             "secrets management", "rotate", "rotation", "rotate secrets",
             "secret rotation", "scan", "scanning", "secret scanning", "redact",
             "mask", "encrypt", "encryption", "vault", "keychain", "least privilege",
             "credential hygiene", "prevent leakage", "prevent exposure", "leak",
             "exposed", "committing secrets", "environment variable management",
             "密钥管理", "密钥轮换", "凭据扫描", "防泄露", "脱敏", "安全存储", "环境变量管理"],
        ],
        "context_terms": ["secret", "credential", "api key", "token"],
    },
    # v2.9 §三：primary = 产出/维护开发规格 或 SDD/Spec Kit 流程；
    # 「following the X specification / compliant with 标准」不是 spec-driven（wiki-llms-txt 事故）。
    "spec-driven": {"custom": _rule_spec_driven},
    # v2.2 收紧：必须真 Supabase 语境或 RLS；普通 PostgreSQL 不算
    # v2.3 再收紧：裸 RLS 不算（Power BI 等也有 row-level security）→ 必须明确 supabase
    "supabase-db": {"all_groups": [["supabase"]],
                    "context_terms": ["rls", "row level security", "postgres", "postgresql",
                                      "migration", "database"]},
    "task-integration": {"any_of": ["ticktick", "dida", "dida365", "task management",
                                    "task-management", "todo", "to-do", "calendar", "reminder",
                                    "task automation", "任务管理", "日历"]},
    # v2.2 收紧：不再把纯 TTS 当语音输入
    # v2.3 再收紧：**「可以接受 voice dictation 作为输入材料」≠「提供语音输入能力」**。
    #   事故：github-issue-creator（"create issues from voice dictation or text"）被误判。
    "voice-input": {"all_groups": [["voice", "speech", "audio", "microphone", "麦克风",
                                    "语音", "听写"]],
                    "any_of": ["voice input", "voice-input", "speech recognition",
                               "speech-to-text", "speech to text", "stt", "dictation engine",
                               "dictation mode", "dictation support", "audio input",
                               "voice control", "voice command", "transcribe audio",
                               "语音输入", "语音识别", "语音转文字", "声音输入"],
                    "none_of": ["voice dictation as input", "accepts voice dictation",
                                "as input material", "as raw material", "text to speech only",
                                "tts only"],
                    "context_terms": ["voice", "speech", "audio"]},
}

# 平台错配：用户技术栈（SKILL_CONTEXT.md tech）里不存在的云/企业平台与语言。
# 命中即降权（不直接否决——仍可能含通用方法），但必须显式记录，便于人工复核。
# v2.6 §四：补足 Google Cloud **产品别名**（事故：cloud-run-basics /
# agent-platform-deploy / agent-platform-endpoint-management 明显是 GCP 专项，
# 却因词典只有 google cloud / gcp / bigquery 而 domain_mismatch=[]，漏进 Top）。
# 注意：**裸 `Gemini` 不算 GCP** —— Gemini API 可独立使用，用户存在 LLM API 需求；
# 只有明确的 Google Cloud 产品语境（下表）才归入 gcp 域。
MISMATCH_KW = ["azure", "google cloud", "gcp", "bigquery", "aws", "amazon web services",
               "salesforce", "airflow", "kubernetes", "k8s", "terraform", "oracle", "sap",
               "dynamics 365", "sharepoint", "databricks", "snowflake", "java", "c#", ".net",
               "dotnet", "asp.net", "csharp", "spring boot", "blazor",
               # v2.6 §四 GCP 产品别名（→ gcp）
               "cloud run", "agent platform", "model garden", "vertex ai", "vertex",
               "cloud build", "cloud functions", "firestore", "gke",
               "google kubernetes engine", "cloud sql", "alloydb",
               "cloud monitoring", "cloud logging",
               # v2.6 §四/§十：Microsoft Store 发布是平台运维，不是通用 Windows 需求
               "microsoft store", "msstore",
               # v2.8 §三.4：AWS 服务别名（明确服务短语优先；裸 lambda 不收录）
               "sagemaker", "amazon sagemaker", "cloudwatch", "aws lambda",
               "s3", "amazon s3", "ecs", "eks", "fargate", "bedrock", "amazon bedrock"]

# v2.4 §九：把上表的词归入「平台域」，用于判断 penalty 能否被**真实项目**解除。
MISMATCH_DOMAIN = {
    "azure": "azure",
    "google cloud": "gcp", "gcp": "gcp", "bigquery": "gcp",
    "aws": "aws", "amazon web services": "aws",
    "salesforce": "salesforce", "airflow": "airflow",
    "kubernetes": "kubernetes", "k8s": "kubernetes", "terraform": "terraform",
    "oracle": "oracle", "sap": "sap",
    "dynamics 365": "microsoft-business", "sharepoint": "microsoft-business",
    "databricks": "databricks", "snowflake": "snowflake",
    "java": "java", "spring boot": "java",
    "c#": "dotnet", ".net": "dotnet", "dotnet": "dotnet", "asp.net": "dotnet",
    "csharp": "dotnet", "blazor": "dotnet",
    # v2.6 §四：Google Cloud 产品别名全部映射到 gcp（裸 Gemini 不在词典内，见上注）
    "cloud run": "gcp", "agent platform": "gcp", "model garden": "gcp",
    "vertex ai": "gcp", "vertex": "gcp", "cloud build": "gcp",
    "cloud functions": "gcp", "firestore": "gcp", "gke": "gcp",
    "google kubernetes engine": "gcp", "cloud sql": "gcp", "alloydb": "gcp",
    "cloud monitoring": "gcp", "cloud logging": "gcp",
    # v2.6 §四/§十：Microsoft Store 发布 = platform_operation（独立域，Windows ≠ Store 发布）
    "microsoft store": "microsoft-store", "msstore": "microsoft-store",
    # v2.8 §三.4：AWS 服务别名 → aws
    "sagemaker": "aws", "amazon sagemaker": "aws", "cloudwatch": "aws",
    "aws lambda": "aws", "s3": "aws", "amazon s3": "aws", "ecs": "aws", "eks": "aws",
    "fargate": "aws", "bedrock": "aws", "amazon bedrock": "aws",
}


def domain_mismatch(cand):
    """返回命中的错配平台列表（空 = 没错配）。"""
    words, text, norm = bag(cand.get("skill_name"), cand.get("description"))
    return [kw for kw in MISMATCH_KW if hit(words, text, norm, kw)]


def mismatch_domains(cand):
    """返回命中的错配**平台域**集合（§九 用域判断能否解除 penalty）。"""
    return sorted({MISMATCH_DOMAIN.get(t, t) for t in domain_mismatch(cand)})


def project_domains(project):
    """某个项目档案里明确使用的「错配平台域」（name / desc / tech 三处取并集）。

    §九 的解除条件 = 用户真实项目里明确出现该平台；没有证据使用该技术栈 →
    就不该占个人 Top。
    """
    blob = " ".join([project.get("name") or "", project.get("desc") or ""]
                    + list(project.get("tech") or [])).lower()
    words = set(_WORD_RE.findall(blob))
    norm = re.sub(r"\s+", " ", re.sub(r"[\-_/]+", " ", blob))
    doms = set()
    for kw in MISMATCH_KW:
        if hit(words, blob, norm, kw):
            doms.add(MISMATCH_DOMAIN.get(kw, kw))
    return doms


# ==========================================================================
# v2.6 §四/§十：产品 scope —— 「为某产品自己服务」的 Skill 不等于通用能力
# ==========================================================================
# scope_type ∈ generic / platform_operation / product_internal
#   · product_internal —— 开发/维护某产品自身的 Skill（事故：BrowserOS `test-ui`
#     「Test the BrowserOS app extension UI…」是 BrowserOS 自研测试，不是通用 Web QA）。
#     只有用户项目明确在开发/维护该产品才进 Top。
#   · platform_operation —— 专项服务某平台的运维（Cloud Run / Microsoft Store / GCP…）。
#     等价于「存在错配平台域且未解除」——由 domain-mismatch 同一套机器处理；
#     「用户有 Windows 电脑」不足以证明需要 Microsoft Store 发布。
# 不是 blacklist：项目将来真的使用该平台/开发该产品 → 自动解除。
_PRODUCT_SELF_DEV_VERBS = (r"test|tests|testing|develop|developing|debug|debugging"
                           r"|maintain|maintaining|contribute to|build|building")
_PRODUCT_SELF_DEV_ARTIFACTS = (r"app|application|applications|extension|core|engine"
                               r"|codebase|monorepo|source|internals|ui|dashboard")


# v2.7 §七：产品专项词典 —— platform_operation 不能只靠 GCP/Azure 词典撑着。
# 「管理某产品的后台 / 应用某产品官方规范」的 Skill，其服务对象是**那个产品**，
# 不是用户的通用能力。条目：product → 需要全部命中的词组（在正向视图上判定）。
# v2.8 §三：Application Insights / M365 Copilot / Hugging Face Spaces 补录；
# 识别一律按 skill_name / description / repo / alias —— 绝不因 owner=microsoft/google
# 就整仓判专项（§三明文）。
_PRODUCT_OPERATION_TERMS = {
    "azure-application-insights": [["application insights"], ["azure monitor"]],
    "microsoft-365-copilot": [["m365 copilot"], ["microsoft 365 copilot"],
                              ["copilot chat"], ["declarative agents", "copilot"]],
    "huggingface-spaces": [["hugging face spaces"], ["hf spaces"], ["spaces sdk"],
                           ["zerogpu"]],
    "google-analytics": [["google analytics"]],
    "google-secops": [["secops"], ["security operations", "chronicle"]],
    "anthropic-brand": [["anthropic", "brand"]],
    "microsoft-store": [["microsoft store"], ["msstore"]],
    "shopify": [["shopify"]],
    "salesforce": [["salesforce"]],
    "servicenow": [["servicenow"]],
    "databricks": [["databricks"]],
    "snowflake": [["snowflake"]],
}


def _product_operation_scan(ctx):
    """返回 (product|None, matched_terms)。任一 product 的全部词组命中即算产品专项。"""
    for prod, alternatives in _PRODUCT_OPERATION_TERMS.items():
        for terms in alternatives:
            if all(hit_pos(ctx, t) for t in terms):
                return prod, terms
    return None, None


def product_scope(cand, ctx=None):
    """返回 (scope_type, target_product, evidence)。target_product 仅对非 generic 有意义。

    product_internal 的判定**以候选自身来源为产品仓库为前提**（owner/repo 名即产品名），
    且描述用自研动词 + 产品名 + 产品工件词描述「测/开发这个产品自己」——
    避免把「在 Supabase 上做应用」这类使用型 Skill 误判成 Supabase 自研 Skill。
    v2.7 §七：产品专项（Google Analytics Admin / Google SecOps / Anthropic brand /
    Microsoft Store / 特定 SaaS 后台…）→ platform_operation + target_product。
    """
    if ctx is None:
        ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    owner = (cand.get("owner") or "").lower()
    repo = (cand.get("repo") or "").lower()
    ident_tokens = {t for t in re.split(r"[^a-z0-9]+", repo) if len(t) >= 4}
    ident_tokens |= {t for t in re.split(r"[^a-z0-9]+", re.sub(r"-ai$", "", owner))
                     if len(t) >= 4}
    for p in sorted(ident_tokens):
        pat = (rf"\b(?:{_PRODUCT_SELF_DEV_VERBS})\b[^.!?;\n]{{0,50}}?\b{re.escape(p)}\b"
               rf"[^.!?;\n]{{0,50}}?\b(?:{_PRODUCT_SELF_DEV_ARTIFACTS})\b")
        m = re.search(pat, ctx["ptext"], re.I)
        if m:
            disp = re.search(rf"\b{re.escape(p)}\b", cand.get("description") or "", re.I)
            target = disp.group(0) if disp else p
            return "product_internal", target, f"self_dev:{m.group(0).strip()[:70]}"
    prod, terms = _product_operation_scan(ctx)
    if prod:
        # v2.8 §四：证据层 —— 逐条标来源（skill_name / description / repo），
        # 名称或仓库能独立指认产品 → confidence=high，仅描述命中 → medium。
        srcs = []
        nm = ctx.get("name_norm", "")
        repo = (cand.get("repo") or "").lower()
        for t in terms:
            if t in nm:
                srcs.append(f"skill_name:{t}")
            if hit_pos(ctx, t):
                srcs.append(f"description:{t}")
        if prod.replace("-", " ") in repo or prod.split("-")[0] in repo:
            srcs.append(f"repo:{repo}")
        conf = "high" if any(x.startswith(("skill_name", "repo")) for x in srcs) \
            else "medium"
        return ("platform_operation", prod,
                "product_specific:" + ",".join(dict.fromkeys(srcs)) + f"|conf={conf}")
    doms = mismatch_domains(cand)
    if doms:
        return "platform_operation", "/".join(sorted(doms)), "platform_terms:" + ",".join(doms)
    return "generic", None, None


def scope_unresolved(scope, projects):
    """v2.7 §七/§十：统一的 scope 解除判定。返回 (unresolved_bool, target, resolved_by)。

    · product_internal      —— 项目档案提到该产品（开发或使用）即解除；
    · platform_operation（产品专项 product_specific:…）—— 同上，按词典词组在项目档案里查；
    · platform_operation（platform_terms:…，即 GCP/Azure/… 域）—— 交给 domain-mismatch
      同一套机器处理，这里恒不解除（③ 平台错配门先于本门生效）。
    **不是 blacklist**：项目将来真的用这个产品 → 自动解除。
    """
    st, target, ev = scope
    if st == "generic" or not target:
        return False, None, []
    if st == "platform_operation" and (ev or "").startswith("platform_terms:"):
        return False, None, []           # 由 domain-mismatch 门处理，避免双重记账
    if st == "product_internal":
        keys = [[target.lower()]]
    else:
        alts = _PRODUCT_OPERATION_TERMS.get(target) or [[target.lower()]]
        keys = alts
    resolvers = []
    for p in (projects or []):
        blob = " ".join([p.get("name") or "", p.get("desc") or ""]
                        + list(p.get("tech") or [])).lower()
        if any(all(t in blob for t in terms) for terms in keys):
            resolvers.append(p["name"])
    return (not resolvers), target, resolvers


def product_internal_unresolved(scope, projects):
    """product_internal 的解除条件 = 某个用户项目明确使用/开发该产品（档案可查）。

    返回 (unresolved_target_product|None, resolved_by_projects)。
    不是 blacklist：项目将来真的碰这个产品 → 自动解除。
    """
    st, target, _ev = scope
    if st != "product_internal" or not target:
        return None, []
    t = target.lower()
    resolvers = []
    for p in (projects or []):
        blob = " ".join([p.get("name") or "", p.get("desc") or ""]
                        + list(p.get("tech") or []))
        if t in blob.lower():
            resolvers.append(p["name"])
    return (None if resolvers else target), resolvers


# ==========================================================================
# 三、能力标签 / 需求匹配的高层接口
# ==========================================================================
def capability_tags(cand):
    """把候选映射到已装侧的能力命名空间（用于能力缺口匹配）。"""
    return [cap for cap, _ in rule_hits(cand, CAP_RULE)]


# ---------- v2.5 §九：候选级「核心能力 vs 提及」统一登记 ----------
# 对易被「顺带提及」污染的能力/需求做四态分类：primary / supporting / mention / negated。
# 只有 primary 可拿完整 capability gap 分；supporting 上限 8；mention/negated 上限 2。
# 目的：以后不再靠手写黑名单修误报 —— 所有规则共用同一个「证据语境」概念。
EVIDENCE_CLASSIFIERS = {
    "android": _cls_android,
    "github-auto": _cls_github_auto,
    "deploy": _cls_deploy,
    "mcp_dev": _cls_mcp,
    "docx_xlsx": _cls_docx,
    # v2.8 §五/§六/§七/§八：核心需求证据四态（primary 才是「用户真正要的能力」）
    "expo-rn": _cls_expo_rn,
    "python-auto": _cls_python_auto,
    "llm-api": _cls_llm_api,
    "browser-qa": _cls_browser_qa,
    "dashboard-viz": _cls_dashboard_viz,
    # v2.9 §三：spec-driven = 开发过程/需求规格语义，四态登记
    "spec-driven": _cls_spec_driven,
    # v2.11 §二：security_audit 四态（示例槽位 ≠ 核心能力）
    "security_audit": _cls_security_audit,
}
EVIDENCE_LEVELS = ("primary", "supporting", "mention", "negated")


def evidence_context(cand, ctx=None):
    """返回 {能力或需求键: 证据语境等级}，只记录本轮真实出现过的键。"""
    if ctx is None:
        ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    out = {}
    for key, fn in EVIDENCE_CLASSIFIERS.items():
        lvl, _ev = fn(ctx)
        if lvl:
            out[key] = lvl
    return out


def matched_needs(cand, needs_meta):
    """返回命中的项目需求列表，按权重降序。

    needs_meta 来自 SKILL_CONTEXT.md 的 needs（{need: {"w": 权重, ...}}）；
    未在 NEED_RULE 里定义规则的需求会被跳过（保持证据驱动，不猜）。
    v2.5 §九：登记表里的需求附带 `evidence_level`（primary/supporting…），
    供评分层降权（supporting 只拿一半权重）。
    """
    ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    out = []
    for need, ev in rule_hits(cand, NEED_RULE, ctx=ctx):
        meta = needs_meta.get(need)
        if not meta:
            continue
        entry = {"need": need, "weight": meta.get("w"), "evidence": ev[:6]}
        cls = EVIDENCE_CLASSIFIERS.get(need)
        if cls:
            lvl, _e = cls(ctx)
            entry["evidence_level"] = lvl or "primary"
        out.append(entry)
    out.sort(key=lambda n: -(n["weight"] or 0))
    return out


# ==========================================================================
# 四、项目级匹配：把「对我哪个项目有用」真正答成项目名
# ==========================================================================
# 数据源：SKILL_CONTEXT.md §2「当前活跃项目」，行格式：
#   - `repo-name` — 定位描述 — 技术栈1 / 技术栈2 — YYYY-MM-DD
# 设计原则：只做本地日报用途，不联网、不外传。
_PROJ_LINE_RE = re.compile(
    r"^-\s+`([^`]+)`\s+—\s+(.*?)\s+—\s+(.*?)\s+—\s+(\d{4}-\d{2}-\d{2})\s*$")

# 技术栈标签 → 候选侧关键词（含同义词/常见写法）
# v2.4 §一/§二：每条带 `tier`：
#   strong    —— 候选的**核心能力明确针对该技术栈**，可独立形成项目匹配
#   secondary —— 泛用技术（语言/通用框架/容器/脚本），**只能加分，不得单独成立**
TECH_MATCH = {
    "TypeScript": {"kw": ["typescript", "ts"], "label": "TypeScript", "w": 6,
                   "tier": "secondary"},
    "React": {"kw": ["react", "jsx", "tsx", "react hooks"], "label": "React", "w": 9,
              "tier": "secondary"},
    # v2.4 §二 不变式：strong tier 必须能**独立**成立 —— 归一化分 = w × 2，而
    # min_score 默认 20，故每个 strong 技术栈的 w 都必须 ≥ STRONG_TIER_MIN_W(=10)。
    # 事故：Next.js 原为 9（归一化 18）→ 「Next.js 专项 Skill ↔ Next.js 项目」这条
    # §一 明确写下的强证据永远无法独立成立，tier 只剩装饰性。
    "Next.js": {"kw": ["next.js", "nextjs", "next js", "app router"], "label": "Next.js",
                "w": 12, "tier": "strong"},
    "PWA": {"kw": ["pwa", "progressive web app", "web app manifest", "installable web app",
                   "service worker", "service-worker"], "label": "PWA", "w": 14,
            "tier": "strong"},
    "离线与本地存储": {"kw": ["offline", "localstorage", "local storage", "indexeddb",
                              "service worker", "cache api"], "label": "离线/本地存储", "w": 13,
                       "tier": "strong"},
    "Supabase": {"kw": ["supabase"], "label": "Supabase", "w": 16, "tier": "strong"},
    "Postgres": {"kw": ["postgres", "postgresql", "psql", "pgvector"], "label": "Postgres",
                 "w": 12, "tier": "strong"},
    "Python": {"kw": ["python", "python3"], "label": "Python", "w": 8, "tier": "secondary"},
    # v2.4 §三：删掉裸 `container`（`container queries` 被误当 Docker）。
    # Docker 只认容器化语境词。
    "Docker": {"kw": ["docker", "dockerfile", "docker compose", "containerization",
                      "container image", "container runtime", "docker container", "容器化"],
               "label": "Docker", "w": 12, "tier": "secondary"},
    "自托管": {"kw": ["self hosted", "self-hosted", "selfhost", "homelab"], "label": "自托管",
               "w": 10, "tier": "secondary"},
    "Expo": {"kw": ["expo", "expo router", "expo sdk"], "label": "Expo", "w": 16,
             "tier": "strong"},
    "React Native": {"kw": ["react native", "react-native", "nativewind"], "label": "React Native",
                     "w": 16, "tier": "strong"},
    "Android": {"kw": ["android", "adb", "apk", "aab", "gradle"], "label": "Android",
                "w": 15, "tier": "strong"},
    "Kotlin": {"kw": ["kotlin", "jetpack compose"], "label": "Kotlin", "w": 12, "tier": "strong"},
    # v2.3 §六：去掉裸 "macos" —— 「支持在 macOS 上运行」不等于「提供 macOS 桌面开发能力」。
    "macOS 桌面": {"kw": ["appkit", "cocoa", "swiftui", "menubar", "menu bar app", "swift",
                          "菜单栏应用", "macos app", "macos application"],
                   "label": "macOS 桌面", "w": 13, "tier": "strong"},
    "原生": {"kw": ["native app", "native desktop", "swift", "objective-c"], "label": "原生",
             "w": 10, "tier": "strong"},
    # v2.4：去掉泛用的 "api integration"，只认真正的模型/供应商词（否则「任何 API」都算 LLM 接入）
    "LLM API": {"kw": ["llm", "openai", "anthropic", "dashscope", "qwen", "deepseek", "gemini",
                       "chat completion", "model api", "dashscope api", "inference endpoint"],
                "label": "LLM API 接入", "w": 14, "tier": "strong"},
    "Tailwind": {"kw": ["tailwind", "shadcn"], "label": "Tailwind", "w": 8, "tier": "secondary"},
    "shadcn": {"kw": ["shadcn", "radix ui"], "label": "shadcn", "w": 7, "tier": "secondary"},
    "单文件 HTML 工具": {"kw": ["single html", "single-file html", "standalone html",
                                "single page html", "vanilla html"],
                         "label": "单文件 HTML", "w": 10, "tier": "secondary"},
    "Playwright": {"kw": ["playwright", "cypress", "puppeteer", "selenium"],
                   "label": "Playwright", "w": 12, "tier": "strong"},
    "Shell": {"kw": ["shell", "bash", "zsh", "command line", "cli script"], "label": "Shell",
              "w": 8, "tier": "secondary"},
    "Cloudflare": {"kw": ["cloudflare", "workers", "cloudflare pages"], "label": "Cloudflare",
                   "w": 10, "tier": "strong"},
    "Vercel": {"kw": ["vercel"], "label": "Vercel", "w": 11, "tier": "strong"},
    "Netlify": {"kw": ["netlify"], "label": "Netlify", "w": 11, "tier": "strong"},
    "CF Pages": {"kw": ["cloudflare pages", "pages functions"], "label": "CF Pages", "w": 10,
                 "tier": "strong"},
    ".NET": {"kw": ["dotnet", ".net", "csharp", "c#", "wpf", "winui"], "label": ".NET", "w": 10,
             "tier": "strong"},
    "C#": {"kw": ["csharp", "c#"], "label": "C#", "w": 10, "tier": "strong"},
}

# v2.4 §二 不变式守卫：strong = 「候选核心能力明确针对该技术栈，可独立形成项目匹配」。
# 归一化分 = 原始分 × 2，需 ≥ min_score（默认 20）→ strong 技术的 w 必须 ≥ 10。
# 这里做一次兜底抬升：新增 strong 技术栈时即使忘记配权重，也不会出现「名义 strong、
# 实际永远无法独立成立」的假分级。
STRONG_TIER_MIN_W = 10
for _tname, _trule in TECH_MATCH.items():
    if _trule.get("tier") == "strong" and _trule["w"] < STRONG_TIER_MIN_W:
        _trule["w"] = STRONG_TIER_MIN_W

# 描述文本里的「事实关键词」→ 加权（用于描述层面重叠，弥补技术栈标签不全）
DESC_SIGNALS = {
    "打卡": {"kw": ["check in", "checkin", "打卡", "visit log"], "label": "打卡记录", "w": 6},
    "看板": {"kw": ["dashboard", "看板"], "label": "看板", "w": 9},
    "报告": {"kw": ["report", "报告"], "label": "报告生成", "w": 8},
    "离线": {"kw": ["offline", "离线"], "label": "离线可用", "w": 10},
    "测试": {"kw": ["test", "testing", "测试"], "label": "测试验证", "w": 8},
    "部署": {"kw": ["deploy", "deployment", "部署"], "label": "部署上线", "w": 9},
}


# 技术栈标签 → 项目类型（对应 SKILL_CONTEXT.md §1「当前主要开发类型」）
TECH_TYPE = {
    "PWA": "Web/PWA", "React": "Web/PWA", "Next.js": "Web/PWA", "TypeScript": "Web/PWA",
    "Tailwind": "Web/PWA", "shadcn": "Web/PWA", "单文件 HTML 工具": "Web/PWA",
    "离线与本地存储": "Web/PWA",
    "Expo": "Expo/RN", "React Native": "Expo/RN",
    "Android": "Android", "Kotlin": "Android",
    "macOS 桌面": "macOS 桌面", "原生": "macOS 桌面",
    ".NET": ".NET/Windows 桌面", "C#": ".NET/Windows 桌面",
    "Python": "Python 自动化", "Shell": "Shell/脚本",
    "LLM API": "AI/Agent 工具",
    "Supabase": "数据库/Supabase", "Postgres": "数据库/Supabase",
    "Docker": "部署/基础设施", "自托管": "部署/基础设施", "Vercel": "部署/基础设施",
    "Netlify": "部署/基础设施", "Cloudflare": "部署/基础设施", "CF Pages": "部署/基础设施",
}

# 候选能力 → 它真正能服务的项目类型
CAP_TYPE = {
    "browser_automation": ["Web/PWA"],
    "testing_qa": ["Web/PWA"],
    "frontend_design": ["Web/PWA"],
    "image_creative": ["Web/PWA"],
    "data_analytics": ["Python 自动化", "AI/Agent 工具"],
    "security_audit": ["Web/PWA", "部署/基础设施"],
    "mobile_qa": ["Expo/RN", "Android"],
    "mobile_dev": ["Expo/RN", "Android"],
    "expo_rn_dev": ["Expo/RN"],
    "supabase_db": ["数据库/Supabase"],
    "postgres_db": ["数据库/Supabase"],
    "deployment_vercel": ["部署/基础设施"],
    "deployment_netlify": ["部署/基础设施"],
    "mcp_dev": ["AI/Agent 工具"],
    "github_ops": ["AI/Agent 工具", "部署/基础设施"],
    "macos": ["macOS 桌面"],
    "windows": [".NET/Windows 桌面"],
    "docx_xlsx": ["Python 自动化"],
    "course_pipeline": ["Python 自动化"],
}
TYPE_W = 10            # 类型适用降为 **secondary boost**，不单独产生 matched_project
TYPE_BOOST = TYPE_W
SECONDARY_BOOST = 3.0  # v2.4 §二：secondary 技术栈只加这点分，绝不单独让项目入选
DIRECT_EVIDENCE_KINDS = ("strong_tech", "positioning", "shared_need", "lexical")
DIRECT_EVIDENCE_LABEL = {
    "strong_tech": "项目技术栈直接命中（专用技术栈）",
    "positioning": "项目定位/功能语义直接命中",
    "shared_need": "项目自身需求与候选能力直接命中",
    "lexical": "项目定位与候选描述词面直接重叠",
}

# v2.4 §四：词面重叠时忽略的「无区分度词」。
# 事故：Azure Resource Manager Skill 与 `prompt-manager` 只因共有 `manager` 就成立。
_LEXICAL_STOP = {
    # 平台 / 设备泛词（v2.3 加入）
    "macos", "windows", "linux", "android", "ios", "unix", "darwin",
    "platform", "platforms", "device", "devices", "phone", "phones",
    "support", "supports", "using", "based", "guide", "guides",
    "skill", "skills", "tool", "tools", "workflow", "workflows",
    "project", "projects", "local", "remote", "files", "python",
    # v2.4 §四 明确点名的泛词
    "manager", "management", "resource", "service", "services",
    "application", "applications", "system", "systems",
    "development", "developer", "testing", "test", "tests",
    "data", "model", "models", "client", "server", "api", "apis",
    "code", "library", "framework", "integration", "automation",
    "content", "output", "input", "value", "values", "level", "process",
    # v2.5 §三/§五：裸 prompt 是「触发说明」里的偶然词（"the prompt names Claude…"），
    #   不是项目域证据；prompt 类语义必须走 _PROJECT_DOMAIN_PHRASES 的明确短语
    "prompt", "prompts",
}
# v2.4 §四：明确的项目域高信号词。
# v2.5 §四 收缩：**技术栈词不得再出现在这一层**（它们由 STRONG/SECONDARY_TECH 负责，
#   在 lexical 重复计一遍就是双重加分）；`prompt`/`prompts` 也被移除（§三 事故）。
#   本集合的词现在只作为「词级加分」的组成部分，**不再单独成立**（§五）。
_LEXICAL_HIGH_SIGNAL = {
    "insurance", "rss", "transcription", "transcribe", "whisper",
    "podcast", "subtitle", "subtitles", "obsidian", "valuation", "dividend", "portfolio",
    "backtest", "tauri", "electron", "journal",
    "photography", "invoice", "ledger", "checkin", "exif",
}

# v2.5 §四：技术泛词禁令表 —— lexical 层一律不得使用。
# 前一部分是 §四 点名的清单；后一部分自动并入 TECH_MATCH 的全部词
# （react native / supabase / playwright / expo… 归 strong/secondary tech 管）。
_LEXICAL_TECH_BAN = {
    "react", "native", "javascript", "typescript", "python", "css", "html",
    "tailwind", "next", "nextjs", "android", "kotlin", "expo", "mobile",
    "web", "api", "sdk", "model", "cloud",
}
for _trule in TECH_MATCH.values():
    for _kw in _trule["kw"]:
        _LEXICAL_TECH_BAN.update(w for w in re.split(r"[\s\-_/]+", _kw.lower()) if w)
_LEXICAL_TECH_BAN.discard("container")   # 不是技术栈词，留给区分度判定


# v2.5 §四/§五：唯一允许「单独成立」的词面证据 = 明确登记过的**项目域短语**。
# 单个泛词/裸 prompt/技术栈词一律不再直接产生 matched_project；
# 词级重叠（≥2 个高区分度词）只能在已有 strong_tech/positioning/shared_need 时作加分。
# 维护方式：新增项目领域时在此登记（本层只服务本机个性化，不外传）。
_PROJECT_DOMAIN_PHRASES = {
    "prompt-manager": ["prompt management", "prompt manager", "managed prompts",
                       "prompt library", "prompt versioning", "prompt repository",
                       "prompt engineering workflow", "prompt template management",
                       "提示词管理", "提示词版本", "提示词库", "提示词模板"],
    "personal-rss": ["rss feed", "rss feeds", "rss aggregation", "rsshub", "freshrss",
                     "rss订阅", "rss 订阅", "rss聚合"],
    "place-journal": ["place checkin", "check-in log", "地点打卡", "打卡记录"],
    "family-insurance-dashboard": ["insurance", "insurance policy", "insurance claim", "保单"],
    "photo-library": ["photo library", "photography portfolio", "摄影作品", "照片管理"],
    "photo-spot-app": ["photo scouting", "shot list", "约拍", "机位"],
    "Video2Obsidian-Mac": ["obsidian", "video transcription", "视频转文字", "whisper"],
    "Video2Obsidian-Windows": ["obsidian", "video transcription", "视频转文字", "whisper"],
    "a-share-index-valuation-report": ["valuation", "index valuation", "估值", "市盈率"],
    "hongli-dixin-calc": ["dividend", "股息", "红利", "a-share", "a股"],
    "pepe-doge-breakout-radar-deepseek-v4-pro": ["trading breakout", "price breakout",
                                                 "market breakout", "breakout radar",
                                                 "breakout signal", "technical analysis",
                                                 "quantitative trading", "backtest", "回撤",
                                                 "行情突破", "突破信号", "量化交易"],
    "roll-position-calculator": ["position sizing", "滚仓", "盈亏台账", "杠杆"],
    "landedazi-android": ["voice translation", "语音整理", "口语", "方言"],
    "alw-db-governance": ["database governance", "数据库治理", "接入规范"],
    "github-projects-profile": ["github profile", "repository portfolio", "项目档案",
                                "仓库档案"],
}

# v2.7 §五：跨领域高歧义单词**不得独立**产生 lexical 项目证据——
# 只有与领域上下文组合成短语后才允许。原则来自实测事故：
# game-engine 的 breakout（打砖块游戏）凭单词匹配了 pepe-doge-breakout-radar（突破行情）。
_AMBIGUOUS_DOMAIN_TERMS = {
    "breakout", "native", "model", "models", "agent", "agents", "manager",
    "management", "dashboard", "dashboards", "channel", "channels", "store",
    "platform", "cloud", "stream", "shell", "library", "network",
}


def _is_ambiguous_single(phrase):
    """单词且属高歧义词 → 不得独立成立（含空格的短语不受限）。"""
    w = phrase.strip().lower()
    return " " not in w and w in _AMBIGUOUS_DOMAIN_TERMS


# 命中的**项目需求** → 它能服务的项目类型。
NEED_TYPE = {
    "agent-governance": ["AI/Agent 工具"],
    "android": ["Android"],
    "browser-qa": ["Web/PWA"],
    "dashboard-viz": ["Web/PWA", "Python 自动化"],
    "data-pipeline": ["Python 自动化", "部署/基础设施"],
    "deploy": ["部署/基础设施"],
    "desktop-app": ["macOS 桌面", ".NET/Windows 桌面"],
    "docker-infra": ["部署/基础设施"],
    "expo-rn": ["Expo/RN"],
    "finance-calc": ["Web/PWA", "Python 自动化"],
    "frontend-design": ["Web/PWA"],
    "github-auto": ["AI/Agent 工具", "部署/基础设施"],
    "llm-api": ["AI/Agent 工具", "Web/PWA"],
    "media-transcribe": ["Python 自动化"],
    "photo-mgmt": ["Web/PWA", "Expo/RN"],
    "privacy-local": ["Web/PWA"],
    "pwa-offline": ["Web/PWA"],
    "python-auto": ["Python 自动化"],
    "responsive": ["Web/PWA"],
    "secret-safety": ["部署/基础设施"],
    "spec-driven": ["AI/Agent 工具"],
    "supabase-db": ["数据库/Supabase"],
    "task-integration": ["AI/Agent 工具"],
    "voice-input": ["Expo/RN", "Android"],
}


def load_projects(context_text):
    """从 SKILL_CONTEXT.md 文本解析「当前活跃项目」。返回 [{name, desc, tech[], date}]。"""
    projects = []
    in_section = False
    for line in (context_text or "").split("\n"):
        if line.startswith("## 2."):
            in_section = True
            continue
        if in_section and line.startswith("## 3."):
            break
        if not in_section:
            continue
        m = _PROJ_LINE_RE.match(line)
        if not m:
            continue
        name, desc, tech, date = m.groups()
        techs = [t.strip() for t in re.split(r"[/／、,，]", tech) if t.strip()]
        projects.append({"name": name.strip(), "desc": desc.strip(),
                         "tech": techs, "date": date.strip(),
                         "is_placeholder": desc.strip() in ("(无描述)", "")})
    for p in projects:
        p["conflict"] = detect_project_conflict(p)
    return projects


# ---------- v2.11 §四/§五：输入 A 的「描述 ↔ 技术栈」矛盾不得被直接信任 ----------
# 原则：外部层**不篡改输入 A**，只标记冲突并抑制「冲突侧」的 strong_tech 证据；
# 非冲突证据（shared_need / positioning / 双方一致的技术）仍允许匹配。
_DESC_TECH_PATTERNS = [
    ("expo", r"\bexpo\b"),
    ("react-native", r"react[\s\-_]+native"),
    ("nextjs", r"next[\s.\-]?js"),
    ("pwa", r"\bpwa\b|progressive web app|渐进式 web"),
    ("flutter", r"\bflutter\b"),
    ("ios-native", r"\bswiftui\b|\bobjective-?c\b"),
]
# 项目技术栈标签 → 归一技术名（与 _DESC_TECH_PATTERNS 同命名空间）
_LABEL_TECH = {"Expo": "expo", "React Native": "react-native", "Next.js": "nextjs",
               "PWA": "pwa", "Flutter": "flutter"}
# 互斥组：描述声明组内任一技术、tech 列缺组内技术、却出现对侧技术 → 冲突
_TECH_MUTUAL_GROUPS = [({"expo", "react-native"}, {"nextjs", "pwa"})]


def detect_project_conflict(p):
    """返回 None 或 {description_tech, declared_tech, suppressed_labels, conflict_reason}。

    「A 缺失 + B 在场」同时成立才算冲突（stretch-side-timer 那类描述与 tech 都含 Expo/RN
    的双栈不判冲突——没有进一步真相源时不许猜）。
    """
    desc = (p.get("desc") or "").lower()
    if not desc or p.get("is_placeholder"):
        return None
    declared = {name for name, pat in _DESC_TECH_PATTERNS if re.search(pat, desc)}
    labels = set(p.get("tech") or [])
    label_techs = {_LABEL_TECH.get(l) for l in labels} - {None}
    for grp_a, grp_b in _TECH_MUTUAL_GROUPS:
        a_in_desc = declared & grp_a
        if not a_in_desc:
            continue
        missing_in_list = sorted(a_in_desc - label_techs)
        # v2.11 §五：只有「描述里**没声明**、tech 列里却出现」的对侧技术才算互斥证据——
        # yejian 描述本身写了「单页应用/PWA 式离线」时 PWA 是一致的，冲突项只剩 Next.js。
        present_b = sorted(grp_b & label_techs - declared)
        if missing_in_list and present_b:
            return {
                "description_tech": sorted(a_in_desc),
                "missing_tech": missing_in_list,
                "declared_tech": present_b,
                "suppressed_labels": [lab for lab in labels
                                      if _LABEL_TECH.get(lab) in present_b],
                "conflict_reason": "description-tech mismatch",
            }
    return None


_RN_SPAN_RE = re.compile(r"react[\s\-_]+native|nativewind", re.I)


def _rn_masked(ctx):
    """v2.7 §六：把 React Native 系短语从正向视图里遮蔽掉，供 TECH_MATCH ① 使用。

    「React Native apps」里的 `native app` 已经被 React Native 技术栈占用，
    不得再作为「原生 / macOS 桌面」证据（事故：react-native-design 匹配
    DeepSeekBalanceWidget-Mac，直接证据竟然是「专用技术栈：原生」）。
    返回 (words, text, norm) 三元组，与 hit_any 的入参一致。
    """
    masked_text = _RN_SPAN_RE.sub(" ", ctx["ptext"])
    mw, mt, mn = bag("", masked_text)
    mn = f"{mn} {_RN_SPAN_RE.sub(' ', ctx.get('name_norm', ''))}".strip()
    return mw, mt, mn


def match_projects(cand, projects, limit=5, min_score=20):
    """为候选匹配最相关的项目，返回 [{project, evidence, direct_evidence, match_score}]。

    v2.3（§一 / §六）：**禁止「项目类型适用」单独制造项目匹配** —— 必须有直接证据。

    v2.4（§一/§二/§三/§四/§十）：把「直接证据」本身再分级。
      ① strong_tech   候选核心能力明确针对该技术栈（Expo / RN / Android / Supabase /
                      Next.js / PWA / Vercel / .NET…），可独立成立
      ② positioning   候选任务与项目定位/功能语义直接命中
      ③ shared_need   项目自身需求与候选能力直接命中
      ④ lexical（v2.5 §三/§四/§五 重构）
                      —— 只有两类形态：登记过的「项目域短语」可单独成立；
                         词级重叠（≥2 个高区分度词）必须有 ①②③ 任一类共同存在、只作加分。
                      技术泛词与裸 prompt 一律不得参与词面证据（react/native/python/… 归
                      STRONG/SECONDARY_TECH 负责，不在 lexical 层重复计分）。
                      事故：react-view-transitions 凭 `native-feeling`+React 匹配了
                      React Native 项目；claude-api / breakdown-test 凭触发说明里的裸
                      `prompt` 匹配了 prompt-manager。
      · secondary 技术栈（TypeScript / React / Python / Docker / Shell / HTML / CSS…）
        **只加 SECONDARY_BOOST 分，绝不单独让项目进 matched_projects**
      事故：azure-microsoft-playwright-testing-ts 仅因描述里有 TypeScript 就匹配了 5 个
      普通 TS 项目；responsive-design 因 `container queries` 被当成 Docker 匹配 3 个 Docker 项目。
    四者皆无 → **不产生 matched_project**（宁可空，也不给「类型像」的假匹配）。
    「同属 Web/PWA / Android / macOS」只作 secondary boost。
    """
    ctx = _ctx(cand.get("skill_name"), cand.get("description"))
    cand_types = set()
    for cap in capability_tags(cand):
        cand_types |= set(CAP_TYPE.get(cap, []))
    # v2.8 §五：supporting/mention 级需求不参与 shared_need（防「产品专项」借词面进项目匹配）
    cand_needs = set()
    for _need, _e in rule_hits(cand, NEED_RULE):
        _fn = EVIDENCE_CLASSIFIERS.get(_need)
        if _fn:
            _lvl, _lv = _fn(ctx)
            if _lvl in ("supporting", "mention", "negated"):
                continue
        cand_needs.add(_need)
    for need in cand_needs:
        cand_types |= set(NEED_TYPE.get(need, []))
    # v2.9 §八/§九：hard requirement 技术栈（React/Tailwind/Expo…）参与项目兼容判定
    req_tech, _compat_tech = tech_requirements(cand, ctx=ctx)
    kept = []
    secondary_only_hit = False
    for p in projects:
        hits, score, direct = [], 0.0, []
        secondary_labels = []
        pwords, ptext, pnorm = bag(p["name"], p["desc"])
        # ① 直接证据：候选能力 ↔ 项目明确技术栈（v2.4：分 strong / secondary）
        # v2.7 §六：**最长短语优先 + 占位遮蔽** —— "react native" 先被 React Native 占用，
        # 其中的 native 不得再参与「原生 / native app」类判定（React Native app ≠ 原生桌面 App）。
        t_words, t_text, t_norm = _rn_masked(ctx)
        # v2.11 §五：项目画像自相矛盾时，「冲突侧」技术栈不得单独产生 strong_tech 证据
        _suppressed = set((p.get("conflict") or {}).get("suppressed_labels") or [])
        for t in p["tech"]:
            rule = TECH_MATCH.get(t)
            if not rule:
                continue
            if not hit_any(t_words, t_text, t_norm, rule["kw"]):
                continue
            if t in _suppressed and rule.get("tier") == "strong":
                # 只有本来会命中的才计抑制量（活动量计数，不虚增）
                QUALITY["conflict_strong_tech_suppressed"] += 1
                continue
            if rule.get("tier") == "strong":
                hits.append(rule["label"])
                score += rule["w"]
                direct.append(("strong_tech", rule["label"]))
            else:
                secondary_labels.append(rule["label"])
                score += SECONDARY_BOOST
        # ② 直接证据：候选任务 ↔ 项目定位/功能语义
        for _sigkey, sig in DESC_SIGNALS.items():
            if _sigkey == "看板" and _dashboard_domain_only(ctx):
                continue     # v2.8 §五：候选的 dashboard 全是领域内看板 → 不构成通用看板定位证据
            if hit_any(pwords, ptext, pnorm, sig["kw"]) and \
                    hit_pos_any(ctx, sig["kw"]):
                hits.append(sig["label"])
                score += sig["w"]
                direct.append(("positioning", sig["label"]))
        # ③ 直接证据：项目自身需求 ↔ 候选能力
        p_needs = {need for need, _e in rule_hits(
            {"skill_name": p["name"], "description": p["desc"]}, NEED_RULE)}
        shared_needs = cand_needs & p_needs
        # v2.9 §八：候选 required_tech（hard requirement）与项目技术栈不兼容时，
        # `shared_need` 单独不得生成项目匹配 —— Skill 可能有启发
        # （general_need_match 仍成立），但不能说「它适合这个具体项目」。
        if shared_needs and req_tech and tech_project_conflicts(req_tech, p):
            QUALITY["required_tech_blocked_shared_need"] += 1
            shared_needs = set()
        if shared_needs:
            score += min(12, 6 * len(shared_needs))
            direct.append(("shared_need", "/".join(sorted(shared_needs)[:3])))
        # ④ 词面证据（v2.5 §三/§四/§五 重构）：
        #   (a) 明确登记过的「项目域短语」命中 → 可单独成立（phrase 级）
        #   (b) 词级重叠（≥2 个高区分度词）→ **只作加分**，必须与 ①②③ 至少一类共同存在；
        #       技术泛词（react/native/python…，归 TECH_MATCH 管）与 stop 词一律不参与
        #   单独的高信号词 / 裸 prompt / 单个泛词 → 不再产生 matched_project。
        phrases = _PROJECT_DOMAIN_PHRASES.get(p["name"]) or []
        ph_hit = [ph for ph in phrases
                  if hit_pos(ctx, ph) and not _is_ambiguous_single(ph)]   # v2.7 §五
        if ph_hit:
            for _ph in ph_hit:
                _ws = set(re.split(r"[\s\-_/]+", _ph))
                if _ws <= {"prompt", "prompts"}:
                    QUALITY["bare_prompt_direct_evidence"] += 1     # 防御性哨兵，必须恒 0
                if _ws & _LEXICAL_TECH_BAN:
                    QUALITY["tech_words_used_as_lexical_direct_evidence"] += 1
            score += min(14, 12 + 2 * (len(ph_hit) - 1))
            direct.append(("lexical", "领域短语：" + "/".join(ph_hit[:2])))
            QUALITY["lexical_phrase_direct_evidence"] += 1
        else:
            overlap = ctx["pwords"] & pwords
            boost = sorted(
                w for w in overlap
                if len(w) >= 5 and w not in _LEXICAL_STOP and w not in _LEXICAL_TECH_BAN)
            if len(boost) >= 2:
                if direct:      # 已有主证据 → 词级重叠只加分（§五）
                    score += min(10, 4 + 2 * len(boost))
                    direct.append(("lexical", "词面重叠（次要加分）：" + "/".join(boost[:3])))
                else:           # 词级重叠想单独成立 → 拒绝（v2.5 §五：准确率优先）
                    QUALITY["lexical_alone_rejected"] += 1
                    QUALITY["lexical_single_rejected"] += 1
            elif boost or overlap:
                # 单个普通词重叠（或只靠 manager/service/resource 这类无区分度词）→ 不足以成立
                QUALITY["lexical_single_rejected"] += 1
        if not direct:
            if secondary_labels:
                secondary_only_hit = True
            continue      # ← v2.3/v2.4 核心：无直接证据 → 不产生匹配
        if secondary_labels:
            hits.append("类型/泛用技术（次要）：" + "/".join(sorted(set(secondary_labels))))
        # secondary boost：类型适用只加分，不能单独让项目进 matched_projects
        ptypes = {TECH_TYPE.get(t) for t in p["tech"]} - {None}
        shared = cand_types & ptypes
        if shared:
            score += TYPE_BOOST
            hits.append("类型适用（次要）：" + "/".join(sorted(shared)))
        norm_score = min(96, int(round(score * 2.0)))   # 归一化到 0~96
        if norm_score < min_score:
            continue
        kinds = sorted({k for k, _ in direct})
        kept.append(({"project": p["name"],
                      "positioning": p["desc"][:90],
                      "evidence": hits[:6] or ["技术栈词面重叠"],
                      "direct_evidence": [f"{DIRECT_EVIDENCE_LABEL[k]}：{v}"
                                          for k, v in direct][:4],
                      "direct_evidence_kinds": kinds,
                      "project_domains": sorted(project_domains(p)),
                      "match_score": norm_score}, kinds))
    # 同分时保持 projects 的原序（SKILL_CONTEXT.md §2 已按活跃日期降序）→ 活跃项目优先
    kept.sort(key=lambda x: -x[0]["match_score"])
    kept = kept[:limit]
    if not kept and secondary_only_hit:
        # 本可靠泛用技术栈（TypeScript / Docker…）硬凑进来，现已拒绝（v2.4 §二）
        QUALITY["secondary_tech_only_rejected"] += 1
    for entry, kinds in kept:
        for k in kinds:
            QUALITY[_KIND_TO_COUNT[k]] += 1
    if kept:
        QUALITY["matched_candidates"] += 1
    return [e for e, _ in kept]
