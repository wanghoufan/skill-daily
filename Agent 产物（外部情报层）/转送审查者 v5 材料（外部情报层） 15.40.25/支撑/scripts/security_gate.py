# -*- coding: utf-8 -*-
"""Security Gate v2 + install 候选两阶段深度静态审查（v2.2）。

v2.1 的问题：静态扫描只要文本里出现 `.env` / `GITHUB_TOKEN` / `eval` / `sudo`，
就把 risk 判成 high → reject。结果是**误伤**：正常部署 Skill 合法引用 token、
安全审计 Skill 讲解 `eval` 的危害、文档里讨论 `.env` 规范，统统被判高危。

v2.2 的核心区分：**「提到危险行为」≠「真的要求执行危险行为」**
  · 每条 finding 增加 confidence（high/medium/low）与
    behavior_context（mention / instruction / executable / remote_execution）
  · verdict 取值：pass / review_required / block / unscanned
  · block 只留给高置信、真会被执行的危险行为（远程 pipe shell、rm -rf ~/、
    凭据外泄、混淆 payload 执行等）
  · 文档讨论 sudo、示例读取 GITHUB_TOKEN → review_required，交人工判断

另有 PASS 2 深度静态审查：带 scripts/ 的候选不能只打一个 `bundled_scripts=low` 就
放行安装候选。对「有希望进 install_candidate」的候选，会列出该 Skill 目录下的
.py/.sh/.js/.ts/.mjs/.cjs/.ps1 以及 package.json 的 postinstall/preinstall，
逐个静态读取并套用同一套规则。

v2.3 §四 再修一处误伤：`always_block` 规则原先**命中即 block**，完全忽略
behavior_context —— 导致「安全审查 Skill 在文档里举 `rm -rf /` 反例」也被 reject。
现在：block 仅限 remote_execution / executable / 明确祈使 instruction；
mention / warning（never / do not / 禁止 / 不要 / 举反例 / 安全审计）一律只
review_required，交人工判断。

⚠️ 本模块**只做静态读取，任何情况下都不执行被抓取的脚本**。
"""
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fetch_cached, gh_api_cached, github_token, CACHE

# ---------- 规则表 ----------
# always_block=True  → 高置信危险行为，命中即 block（无论文本语境）
# 其余规则 → 产生 review_required；severity 由「行为语境」决定：
#     mention（文档提及/解释）        → 降一档
#     instruction / executable / remote_execution → 保持原档
RULES = [
    dict(rule="pipe_to_shell", always_block=True,
         pattern=r"(curl|wget)[^\n;]*\|\s*(sudo\s+)?(ba|z|k)?sh\b",
         label="把远程内容直接管道进 shell"),
    dict(rule="remote_fetch_exec", always_block=True,
         pattern=r"(curl|wget)[^\n;]*\|[^\n;]*\b(eval|exec|source|python|node|perl)\b",
         label="远程抓取内容后直接执行"),
    # v2.3 收窄：`/` 只匹配**根目录本身**（后面跟空白或行尾），不再吞掉 /tmp/... 这类普通绝对路径 ——
    # 旧写法 `(~|/|\$HOME|\*)` 会把 `rm -rf /tmp/build`（常规清理）也判成破坏性命令。
    dict(rule="destructive_rm_root", always_block=True,
         pattern=r"rm\s+(?:-[a-zA-Z]+\s+)*(?:-rf|-fr|-r\s+-f)\s+"
                 r"(?:\$HOME(?:/\S*)?|~(?:/\S*)?|/(?=\s|$)|\*)",
         label="删除家目录/根目录等破坏性命令"),
    dict(rule="credential_exfil", always_block=True,
         pattern=(r"(\.ssh/id_|\.aws/credentials|\.env\b|GITHUB_TOKEN|AWS_SECRET|API_KEY)"
                  r"[^\n]{0,200}(curl|wget|requests\.post|fetch\(|nc\s|ncat|scp\s)"),
         label="读取凭据后向外部网络发送"),
    dict(rule="obfuscated_payload_exec", always_block=True,
         pattern=r"(base64\s+-d|xxd\s+-r|openssl\s+enc\s+-d)[^\n]{0,80}\|\s*\S*(sh|bash|eval|exec)",
         label="混淆/解码后的 payload 直接执行"),
    dict(rule="pipe_to_interpreter", always_block=True,
         pattern=r"(curl|wget)[^\n;]*\|\s*(python|python3|node|perl|ruby)\b",
         label="把远程内容直接管道进解释器"),
    # ---- 以下为需要人工复核的敏感项（review_required） ----
    dict(rule="sudo", pattern=r"\bsudo\b", severity="medium",
         label="提权命令 sudo"),
    dict(rule="dynamic_code", pattern=r"\b(eval|exec)\s*\(|\$\(\s*(curl|wget)",
         severity="medium", label="动态代码执行（eval/exec）"),
    dict(rule="ssh_keys", pattern=r"\.ssh/id_|authorized_keys|id_rsa|id_ed25519",
         severity="medium", label="访问 SSH 私钥/授权文件"),
    dict(rule="credential_files", pattern=r"\.env\b|\.aws/credentials|keychain|GITHUB_TOKEN|AWS_SECRET|API_KEY|OPENAI_API_KEY",
         severity="medium", label="涉及凭据文件/密钥环境变量"),
    dict(rule="git_push_auto", pattern=r"\bgit\s+push\b",
         severity="low", label="自动 git push"),
    dict(rule="auto_deploy", pattern=r"vercel\s+--prod\b|netlify\s+deploy\s+--prod\b|\bwrangler\s+deploy\b",
         severity="low", label="直接推生产环境部署"),
    dict(rule="telemetry_exfil", pattern=r"(paste\.rs|ngrok|requestbin|webhook\.site|hastebin|transfer\.sh)",
         severity="medium", label="向第三方中转/回传服务发送数据"),
    dict(rule="postinstall_hook", pattern=r"\b(postinstall|preinstall)\b",
         severity="medium", label="npm 安装期钩子（postinstall/preinstall）"),
    dict(rule="obfuscation", pattern=r"[A-Za-z0-9+/]{200,}={0,2}",
         severity="low", label="疑似混淆/长 base64 块"),
    dict(rule="broad_fs", pattern=r"find\s+/\s|chmod\s+-R\s+777|chown\s+-R\s+root",
         severity="medium", label="大范围文件系统操作"),
    dict(rule="network_generic", pattern=r"\b(curl|wget|fetch)\b",
         severity="low", label="网络访问"),
]

# 规则 → 行为布尔标志（安全 Gate 的行为画像，供日报与人工复核直读）
RULE_FLAGS = {
    "shell_exec":               {"pipe_to_shell", "pipe_to_interpreter", "dynamic_code", "sudo"},
    "destructive_commands":     {"destructive_rm_root", "broad_fs"},
    "secret_access":            {"ssh_keys", "credential_files", "credential_exfil"},
    "network_access":           {"network_generic", "remote_fetch_exec", "telemetry_exfil"},
    "filesystem_write":         {"broad_fs", "destructive_rm_root"},
    "remote_instruction_fetch": {"remote_fetch_exec", "pipe_to_shell", "pipe_to_interpreter"},
    "external_dependencies":    {"postinstall_hook"},
}
FLAG_KEYS = ["shell_exec", "network_access", "filesystem_write", "destructive_commands",
             "secret_access", "remote_instruction_fetch", "external_dependencies"]

# 执行语境的强信号：命令行提示符 / 代码块里的可执行行 / 祈使指令
_EXEC_HINTS = re.compile(r"^\s*[$#>]\s+\S|```(?:ba|z|k)?sh\b|^\s{0,4}(?:run|execute|invoke)\b",
                         re.I | re.M)
_CMD_HINTS = re.compile(r"\b(run|execute|invoke|install and run|you must|please run|"
                        r"执行|运行|请先|记得运行)\b", re.I)

# 否定 / 警示语境（v2.3 §四）：安全审计文档举反例、明确劝阻 —— **一律不得 block**。
# 触发场景：安全审查 Skill 在文档里写「never run `rm -rf /`」被旧实现直接 reject。
_NEGATION_RE = re.compile(
    r"\b(never|do not|don't|must not|should not|avoid|prohibited|forbidden|"
    r"warning|caution|unsafe|insecure|dangerous|malicious|"
    r"anti[- ]?pattern|bad practice|bad example|not recommended|red flag|"
    r"security review|security audit|secure coding|threat model|"
    r"禁止|不要|切勿|严禁|避免|反例|警示|不安全)\b", re.I)

# §四：block 仅限这 6 类高危行为，且必须处在「真要求执行」的语境里
BLOCK_ELIGIBLE_RULES = {"pipe_to_shell", "remote_fetch_exec", "destructive_rm_root",
                        "credential_exfil", "obfuscated_payload_exec", "pipe_to_interpreter"}
BLOCKING_CONTEXTS = {"remote_execution", "executable", "instruction"}
# 只降级、不阻断的语境
NON_BLOCKING_CONTEXTS = {"mention", "warning"}


def _should_block(rule, ctx):
    """§四 核心判定：高危规则命中时，**只有明确的否定/警示语境才降级**。

    warning（never / do not / 禁止 / 不要 / 举反例 / 安全审计文档）→ 只 review_required；
    其余（裸命令 mention、祈使 instruction、可执行 executable、远程执行）一律 block。

    为什么 mention 也 block：对 `rm -rf ~/`、`curl … | bash` 这类**无可辩解的高危命令**，
    「被提及」与「被要求执行」在静态审查里无法可靠区分，按 fail-closed 处理。
    真正的安全文档在讨论这类命令时必然带否定/警示词 → 会落到 warning。
    """
    return rule in BLOCK_ELIGIBLE_RULES and ctx != "warning"


def behavior_context(text, start, end):
    """判断命中片段的「行为语境」——v2.2 区分『提到』与『执行』，v2.3 增加『警示』。

    remote_execution > executable > instruction > warning > mention
    （warning 优先级最高：只要窗口里出现否定/警示表述，就不再当它要求执行）
    """
    window = text[max(0, start - 220): min(len(text), end + 220)]
    # §四：否定 / 警示语境优先 —— 「never run rm -rf /」不是真的要求执行
    if _NEGATION_RE.search(window):
        return "warning"
    if re.search(r"(curl|wget)[^\n;|]*\|[^\n;]*(sh|bash|eval|exec|source|python|node|perl|ruby)",
                 window, re.I):
        return "remote_execution"
    if _EXEC_HINTS.search(window):
        return "executable"
    if re.search(r"^```", window, re.M) and re.search(r"^\s{0,4}\S+\s+(-|--)\w", window, re.M):
        return "executable"
    if _CMD_HINTS.search(window):
        return "instruction"
    return "mention"


def _severity_for(base_severity, ctx):
    """语境降档：mention / warning → 降一档；真被执行语境 → 保持原档。"""
    order = ["low", "medium", "high"]
    if ctx in NON_BLOCKING_CONTEXTS:
        return order[max(0, order.index(base_severity) - 1)]
    return base_severity


def _confidence_for(rule, ctx, severity):
    if ctx in NON_BLOCKING_CONTEXTS:
        return "medium" if severity in ("medium", "high") else "low"
    if rule.get("always_block"):
        return "high"
    if severity == "high" and ctx in ("executable", "remote_execution", "instruction"):
        return "high"
    if severity == "medium":
        return "medium"
    return "low"


def scan_text(text, extra_findings=None):
    """对一段文本做规则扫描，返回 (findings, blocking_rules, review_rules)。

    v2.3 §四：`always_block` 规则**不再命中即 block** —— 必须先看 behavior_context。
    只有 remote_execution / executable / 明确祈使 instruction 才是 block；
    mention / warning（含 never / do not / 禁止 / 不要 / 举反例）归 review_required。
    """
    findings, blocking, review = [], [], []
    if text:
        for r in RULES:
            m = re.search(r["pattern"], text, re.I | re.M)
            if not m:
                continue
            ev = re.sub(r"\s+", " ", m.group(0))[:90]
            ctx = behavior_context(text, m.start(), m.end())
            if r.get("always_block") and _should_block(r["rule"], ctx):
                findings.append({"rule": r["rule"], "severity": "high", "confidence": "high",
                                 "behavior_context": ctx,
                                 "label": r["label"], "evidence": ev, "level": "block"})
                blocking.append(r["rule"])
            else:
                base = "high" if r.get("always_block") else r.get("severity", "low")
                sev = _severity_for(base, ctx)
                findings.append({"rule": r["rule"], "severity": sev,
                                 "confidence": _confidence_for(r, ctx, sev),
                                 "behavior_context": ctx, "label": r["label"], "evidence": ev,
                                 "level": "review"})
                review.append(r["rule"])
    for f in (extra_findings or []):
        findings.append(f)
    return findings, blocking, review


def _flags_from(findings):
    hit = {f["rule"] for f in findings}
    return {k: bool(hit & v) for k, v in RULE_FLAGS.items()}


def _verdict_of(findings, blocking):
    """block 优先；其次 review_required；都没有则 pass。"""
    if blocking:
        return "block"
    if findings:
        return "review_required"
    return "pass"


def _risk_level_of(verdict, findings):
    """向后兼容的 risk_level（下游日报/表格仍在用）。"""
    if verdict == "block":
        return "high"
    if verdict == "review_required":
        return "medium"
    if verdict == "pass":
        return "low"
    return "unknown"


def _install_blocked(findings):
    """决定候选是否被安全因素挡在 install_candidate 之外。

    规则（对应「提到风险 ≠ 执行风险」，且**只有高置信危险行为才挡**）：
      · 任一 block 级 finding → 挡（远程 pipe shell、rm -rf ~/、凭据外发、混淆执行）
      · 任一 high severity 且 behavior_context 非 mention（真在指令/可执行语境）→ 挡
      · medium/low 级一律不挡 —— 只标注「需人工复核」。

    为什么 medium 不挡：v2.2 首次实现时按「medium 且非 mention → 挡」，
    实测直接把 28 个 install 候选全部降级为 watch（脚本里出现
    `process.env.TOKEN` / `fetch(...)` 这类语句太常见，语境天然是 executable）。
    那等于把「静态审查」变回「一见敏感词就否」，违背本次整改目标。
    """
    for f in findings:
        if f.get("level") == "block":
            return True
        if f.get("severity") == "high" and f.get("behavior_context") not in NON_BLOCKING_CONTEXTS:
            return True
    return False


def security_scan(text, has_scripts=False):
    """PASS 1：对 SKILL.md 文本做静态审查。text=None 表示未扫描（不得当低风险）。"""
    if text is None:
        flags = {k: None for k in FLAG_KEYS}
        return {"status": "unscanned", "verdict": "unscanned", "risk_level": "unknown",
                "findings": [], "blocking_rules": [], "review_rules": [],
                "install_blocked": True, "max_severity": None,
                **flags, "scanned_at": None,
                "note": "未做静态审查（超出本轮抓取预算）——不得推荐安装"}
    findings, blocking, review = scan_text(text)
    # SKILL.md 里提到 scripts/ 目录 → 只作提示，真正的结论由 PASS 2 深度扫描给出
    if has_scripts and not any(f["rule"] == "bundled_scripts" for f in findings):
        findings.append({"rule": "bundled_scripts", "severity": "low", "confidence": "medium",
                         "behavior_context": "mention", "level": "review",
                         "label": "含 scripts/ 目录（需 PASS 2 深度静态审查）",
                         "evidence": "SKILL.md 引用 scripts/（脚本未逐一静态审查）"})
        review.append("bundled_scripts")
    verdict = _verdict_of(findings, blocking)
    return {"status": "scanned", "verdict": verdict,
            "risk_level": _risk_level_of(verdict, findings),
            "findings": findings, "blocking_rules": sorted(set(blocking)),
            "review_rules": sorted(set(review)),
            "install_blocked": _install_blocked(findings),
            "max_severity": ("high" if blocking else
                             "medium" if any(f["severity"] == "medium" for f in findings) else
                             "low" if findings else "none"),
            **_flags_from(findings),
            "scanned_at": None,   # 由调用方填 TODAY
            "note": "静态审查=只读匹配不执行；官方来源不豁免本 Gate"}


# ==========================================================================
# PASS 2：install 候选的深度静态审查（只看文本，绝不执行）
# ==========================================================================
SCRIPT_EXT = {".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".ps1",
              ".rb", ".pl", ".php", ".bat", ".cmd"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv",
             "vendor", "coverage", ".next", "out"}
MAX_SCRIPT_FILES = 8          # 单个候选最多读多少个脚本文件
MAX_SCRIPT_BYTES = 24000      # 单文件读取上限（超出截断，仅作静态匹配）


_API_DIR = os.path.join(CACHE, "ghapi")
_api_mem = {}


def gh_api_json(path, timeout=20, ttl_hours=24):
    """GitHub API GET，带磁盘缓存 + 进程内缓存。

    **只在成功时落盘**（失败绝不写缓存）—— 这是与旧 `fetch_cached` 的关键差别：
    旧逻辑把失败也写成 MISS 并缓存 24h，一旦某轮把未认证配额（60 次/小时）跑爆，
    后续所有 tree API 都命中「失败缓存」，深度审查于是永久 failed
    （v2.2 实测踩过：32 个 install 候选全部 deep_scan=failed，install_candidate 归零）。

    认证：委托 common.github_token()，即 `GITHUB_TOKEN` / `GH_TOKEN` 环境变量，
    或本机已登录的 `gh auth token`（配额 60/小时 → 5000/小时）。取不到就匿名。
    具体缓存读写复用 common.gh_api_cached，保证全项目只有一套「成功才缓存」语义。
    """
    if path in _api_mem:
        return _api_mem[path]
    d = gh_api_cached(path, ttl_hours=ttl_hours)
    _api_mem[path] = d
    return d


_tree_cache = {}


def repo_tree(owner, repo, branch):
    """仓库全量文件树（进程内缓存；同一仓库多个 Skill 只请求一次）。"""
    k = f"{owner}/{repo}@{branch}"
    if k in _tree_cache:
        return _tree_cache[k]
    d = gh_api_json(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    paths = [x["path"] for x in (d or {}).get("tree", []) if x.get("type") == "blob"] \
        if d and "tree" in d else None
    _tree_cache[k] = paths
    return paths


def deep_scan(owner, repo, skill_path, branch, max_files=MAX_SCRIPT_FILES, known_scripts=None):
    """PASS 2：列出 Skill 目录下的可执行/脚本文本并静态审查。

    known_scripts：discover 阶段已经拿到的该 Skill 目录下的脚本路径列表。
      传列表（可为空列表）→ **零额外 API 调用**，直接用；
      传 None → 回退到 tree API 现查（会用掉 GitHub 未认证配额）。

    返回 dict：
      deep_scan_status: complete（扫完或无脚本）/ failed（拿不到文件树）/ skipped（无 owner 或 path）
      scripts_scanned / script_files / package_hooks / tree_source
      findings / blocking_rules / deep_install_blocked
    """
    base = {"deep_scan_status": "skipped", "scripts_scanned": 0, "script_files": [],
            "package_hooks": [], "findings": [], "blocking_rules": [],
            "deep_install_blocked": False, "scanned_paths": [], "tree_source": None}
    if not (owner and repo and skill_path):
        base["deep_scan_status"] = "complete"   # 无目录可扫 → 不构成阻断
        base["note"] = "无 skill 目录信息，无可执行文件可查"
        return base
    if known_scripts is not None:
        pool = list(known_scripts)
        base["tree_source"] = "discover_tree"
    else:
        paths = repo_tree(owner, repo, branch)
        if paths is None:
            base["deep_scan_status"] = "failed"
            base["note"] = ("仓库文件树不可读（GitHub API 不可用或配额耗尽）"
                            "→ 无法完成深度审查（fail-closed，不当作安全）")
            return base
        prefix = skill_path.rstrip("/") + "/"
        pool = []
        for p in paths:
            if not p.startswith(prefix):
                continue
            rel = p[len(prefix):]
            if "/" in rel and rel.split("/")[0] in SKIP_DIRS:
                continue
            ext = os.path.splitext(p)[1].lower()
            if ext in SCRIPT_EXT or os.path.basename(p) == "package.json":
                pool.append(p)
        base["tree_source"] = "tree_api"
    # 再过滤一次（幂等）：跳过依赖/构建目录，只留可执行脚本与 package.json
    pool = [p for p in pool
            if not any(seg in SKIP_DIRS for seg in p.split("/")[:-1])
            and (os.path.splitext(p)[1].lower() in SCRIPT_EXT
                 or os.path.basename(p) == "package.json")]
    targets = sorted(pool, key=lambda p: (os.path.basename(p) != "package.json", p))[:max_files]
    findings, blocking, hooks = [], [], []
    for p in targets:
        txt = fetch_cached(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{p}",
                           timeout=12)
        if txt is None:
            continue
        txt = txt[:MAX_SCRIPT_BYTES]
        base["scanned_paths"].append(p)
        if os.path.basename(p) == "package.json":
            for h in ("postinstall", "preinstall"):
                m = re.search(rf'"{h}"\s*:\s*"([^"]{1,120})"', txt)
                if m:
                    hooks.append({"hook": h, "command": m.group(1)})
                    findings.append({"rule": "postinstall_hook", "severity": "medium",
                                     "confidence": "high", "behavior_context": "instruction",
                                     "level": "review",
                                     "label": f"package.json 的 {h} 钩子",
                                     "evidence": f'{h}: "{m.group(1)}"',
                                     "file": p})
            continue
        fs, bl, rv = scan_text(txt)
        for f in fs:
            f["file"] = p
            findings.append(f)
        blocking += [f"{r}@{os.path.basename(p)}" for r in bl]
    base["scripts_scanned"] = len([p for p in base["scanned_paths"]
                                   if os.path.basename(p) != "package.json"])
    base["script_files"] = base["scanned_paths"]
    base["package_hooks"] = hooks
    base["findings"] = findings
    base["blocking_rules"] = sorted(set(blocking))
    base["deep_scan_status"] = "complete"
    base["deep_install_blocked"] = _install_blocked(findings)
    base["note"] = ("深度静态审查：只读文本匹配，未执行任何脚本"
                    if targets else "该 Skill 目录下未发现脚本文件（无需深度审查）")
    return base


def deep_scan_summary(ds):
    """给日报用的一句话摘要。"""
    if not ds:
        return "未做深度审查"
    st = ds.get("deep_scan_status")
    if st == "complete":
        n = ds.get("scripts_scanned", 0)
        extra = f"，package 钩子 {len(ds.get('package_hooks') or [])} 个" if ds.get("package_hooks") else ""
        return f"complete（已静态读取 {n} 个脚本{extra}；未执行）"
    if st == "failed":
        return "failed（仓库文件树不可读，未能完成）"
    if st == "pending":
        return "pending（超出本轮预算未扫描，fail-closed）"
    if st == "not_required":
        return "not_required（未进入安装候选，未触发深度审查）"
    return "skipped（无可执行文件可查）"
