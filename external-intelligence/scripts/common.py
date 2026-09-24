# -*- coding: utf-8 -*-
"""External Skill Intelligence — 共享工具。"""
import json, os, re, hashlib, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CONFIG = os.path.join(BASE, "config")

# 数据目录解析：环境变量 > 默认 data/ > 归档副本的同级目录。
# 归档场景：转送审查者 v5 材料（外部情报层）/支撑/scripts/ 下的副本，
# 其数据文件（SKILL_CANDIDATES.json 等）放在 支撑/ 的上一级（即 v5 根目录）。
if os.environ.get("SKILL_DATA_DIR"):
    DATA = os.path.abspath(os.path.expanduser(os.environ["SKILL_DATA_DIR"]))
elif not os.path.isdir(DATA):
    _up = os.path.dirname(BASE)
    if os.path.exists(os.path.join(_up, "SKILL_CANDIDATES.json")):
        DATA = _up

RAW = os.path.join(DATA, "raw")
STATE = os.path.join(DATA, "state")
REPO_ROOT = os.path.dirname(BASE)

# 输入真相源（只读）。路径解析顺序：环境变量 > 默认相对位置。
# 为什么要环境变量：本层不是自包含的——「已装侧底座」在 v4 转送文件夹、「项目需求」在本机另一个
# 项目档案目录。把脚本归档副本（转送审查者 v5 材料/支撑/scripts）单独交付时，按 __file__ 推出的
# 相对路径会失效（实测报 FileNotFoundError）。用环境变量可以不改一行代码就指向真实位置：
#   SKILL_REPO_ROOT=/path/to/60\ Skill\ 仓库 \
#   SKILL_CONTEXT_PATH=/path/to/SKILL_CONTEXT.md \
#   python3 scripts/run_daily.py
_ENV_ROOT = os.environ.get("SKILL_REPO_ROOT")
if _ENV_ROOT:
    REPO_ROOT = os.path.abspath(os.path.expanduser(_ENV_ROOT))

_V4_NAME = "转送审查者 v4 材料（Canonical 模型）"

# 记录解析来源，便于测试与人工诊断「到底是哪一级命中的」
PATH_RESOLUTION = {"skill_context": None, "installed_ctx": None, "source_map": None,
                   "v4_dir": None}

# ---------- 输入 B：已装侧底座（v4） ----------
# v2.3 解析顺序（§九）；v2.6 起本仓库的转送材料统一收进
# `Agent 产物（外部情报层）/` 子文件夹（用户指令：不得污染仓库根目录）：
#   ① INSTALLED_CTX_PATH / SOURCE_MAP_PATH 环境变量（显式指路，最高优先）
#   ② 同级 v4 文件夹自动发现 —— REPO_ROOT 下（根目录或 Agent 产物 子目录），
#      以及自当前位置向上逐级查找（归档副本场景：v5 包与 v4 包同级摆放）
#   ③ 都找不到 → 调用方 SKIP 并明确提示（绝不假装读到）
_ARTIFACT_SUBDIR = "Agent 产物（外部情报层）"

def _v4_candidates(base):
    return [os.path.join(base, _V4_NAME),
            os.path.join(base, _ARTIFACT_SUBDIR, _V4_NAME)]

V4_DIR = None
for _cand in _v4_candidates(REPO_ROOT):
    if os.path.isdir(_cand):
        V4_DIR = _cand
        PATH_RESOLUTION["v4_dir"] = "repo_root"
        break
if V4_DIR is None:
    _cur = REPO_ROOT
    for _ in range(3):
        _parent = os.path.dirname(_cur)
        if _parent == _cur:
            break
        _cur = _parent
        hit = next((c for c in _v4_candidates(_cur) if os.path.isdir(c)), None)
        if hit:
            V4_DIR = hit
            PATH_RESOLUTION["v4_dir"] = "auto_discover_up"
            break
if V4_DIR is None:
    V4_DIR = os.path.join(REPO_ROOT, _V4_NAME)   # 保持旧行为：不存在的路径，由下游 SKIP 提示

SOURCE_MAP_PATH = os.path.join(V4_DIR, "SKILL_SOURCE_MAP.json")
INSTALLED_CTX_PATH = os.path.join(V4_DIR, "INSTALLED_SKILLS_CONTEXT.md")

# 归档副本可自定位：若上述默认位置都不对，允许直接指向已装侧文件
if os.environ.get("INSTALLED_CTX_PATH"):
    INSTALLED_CTX_PATH = os.path.abspath(os.path.expanduser(os.environ["INSTALLED_CTX_PATH"]))
    PATH_RESOLUTION["installed_ctx"] = "env"
elif os.path.exists(INSTALLED_CTX_PATH):
    PATH_RESOLUTION["installed_ctx"] = "v4_dir:" + str(PATH_RESOLUTION["v4_dir"])
if os.environ.get("SOURCE_MAP_PATH"):
    SOURCE_MAP_PATH = os.path.abspath(os.path.expanduser(os.environ["SOURCE_MAP_PATH"]))
    PATH_RESOLUTION["source_map"] = "env"
elif os.path.exists(SOURCE_MAP_PATH):
    PATH_RESOLUTION["source_map"] = "v4_dir:" + str(PATH_RESOLUTION["v4_dir"])

# ---------- 输入 A：项目需求 SKILL_CONTEXT.md ----------
# v2.3 解析顺序（§九）：
#   ① SKILL_CONTEXT_PATH 环境变量
#   ② **归档包内自带件** 支撑/输入/SKILL_CONTEXT.md（转送包已随附 → 解压即可跑）
#   ③ 本机默认项目档案路径（用 ~ 而非写死用户名 → 换账号/换机器仍可用）
_LOCAL_DEFAULT_CTX = "~/Developer/coding/1.Active/000-alw-github 档案/SKILL_CONTEXT.md"


def _resolve_skill_context():
    """按 §九 规定的优先序解析输入 A，并把命中来源记入 PATH_RESOLUTION。"""
    env = os.environ.get("SKILL_CONTEXT_PATH")
    if env:
        PATH_RESOLUTION["skill_context"] = "env"
        return os.path.abspath(os.path.expanduser(env))
    # ② 包内自带（归档副本里 BASE 就是 支撑/，主仓里则是 external-intelligence/）
    for cand in (os.path.join(BASE, "输入", "SKILL_CONTEXT.md"),
                 os.path.join(os.path.dirname(BASE), "支撑", "输入", "SKILL_CONTEXT.md")):
        if os.path.exists(cand):
            PATH_RESOLUTION["skill_context"] = "package:" + os.path.normpath(cand)
            return os.path.abspath(cand)
    PATH_RESOLUTION["skill_context"] = "local_default"
    return os.path.abspath(os.path.expanduser(_LOCAL_DEFAULT_CTX))


SKILL_CONTEXT_PATH = _resolve_skill_context()

REGISTRY_PATH = os.path.join(DATA, "SKILL_SOURCE_REGISTRY.json")
CANDIDATES_PATH = os.path.join(DATA, "SKILL_CANDIDATES.json")
SNAPSHOT_PATH = os.path.join(STATE, "last_snapshot.json")
CONTEXT_OUT = os.path.join(BASE, "EXTERNAL_SKILLS_CONTEXT.md")
if not os.path.exists(CONTEXT_OUT) and os.path.exists(
        os.path.join(DATA, "EXTERNAL_SKILLS_CONTEXT.md")):
    # 归档副本场景：CONTEXT 与数据文件同级（v5 根目录），不在 支撑/ 下
    CONTEXT_OUT = os.path.join(DATA, "EXTERNAL_SKILLS_CONTEXT.md")

TODAY = datetime.date.today().isoformat()

def ensure_dirs():
    for d in (DATA, RAW, STATE): os.makedirs(d, exist_ok=True)

def load_json(path, default=None):
    try: return json.load(open(path, encoding="utf-8"))
    except Exception: return default

def save_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def load_config():
    return load_json(os.path.join(CONFIG, "scoring.json"), {})

def canonical_key(owner, repo, skill_name):
    """去重主键：owner/repo/skill（小写）——不能只按 skill 名称。"""
    return f"{(owner or '').lower()}/{(repo or '').lower()}/{(skill_name or '').lower()}"

def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]

_TOKEN_CACHE = {}


def github_token():
    """取 GitHub token：环境变量优先，其次本机 gh CLI 登录态。

    v2.2 新增。原因：未认证配额只有 60 次/小时，一次全量跑就要几百次调用，
    很容易半途耗尽并把整批候选打成 deep_scan=failed（fail-closed → 安装候选全灭）。
    token 只从**运行环境**取，不写死在代码里（迁移到别的电脑同样适用）：
      1) GITHUB_TOKEN / GH_TOKEN 环境变量
      2) `gh auth token`（本机已 gh auth login 即可，无需额外配置）
    取不到就退回匿名请求（仍可用，只是配额低）。
    """
    if "v" in _TOKEN_CACHE:
        return _TOKEN_CACHE["v"]
    tok = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not tok:
        try:
            import subprocess
            r = subprocess.run(["gh", "auth", "token"], capture_output=True,
                               text=True, timeout=10)
            if r.returncode == 0:
                tok = (r.stdout or "").strip()
        except Exception:
            tok = ""
    _TOKEN_CACHE["v"] = tok or None
    return _TOKEN_CACHE["v"]


def _gh_headers():
    h = {"Accept": "application/vnd.github+json",
         "User-Agent": "external-skill-intelligence"}
    tok = github_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def gh_api(path, params=""):
    """GitHub API GET，返回 dict/list 或 None（有 token 就用，没有就匿名）。"""
    import urllib.request
    url = f"https://api.github.com{path}" + (f"?{params}" if params else "")
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception:
        return None


def gh_api_cached(path, params="", ttl_hours=24):
    """带磁盘缓存的 GitHub API GET —— **只在成功时写缓存**。

    v2.2 新增。旧逻辑（fetch_cached）会把失败（None）也缓存 24 小时，
    一次配额耗尽就会把后续所有重跑都污染成失败，属于不可恢复的假阴性。
    这里：成功 → 写缓存；失败 → 不写缓存（下次重跑会重试），保证可恢复。
    """
    import hashlib, time
    os.makedirs(CACHE, exist_ok=True)
    url = f"https://api.github.com{path}" + (f"?{params}" if params else "")
    key = "api_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    body_path = os.path.join(CACHE, key + ".json")
    meta_path = os.path.join(CACHE, key + ".jsonmeta")
    try:
        if os.path.exists(meta_path):
            age = time.time() - float(open(meta_path).read().strip() or 0)
            if age < ttl_hours * 3600:
                return json.load(open(body_path, encoding="utf-8"))
    except Exception:
        pass
    d = gh_api(path, params)
    if d is not None:
        try:
            with open(body_path, "w", encoding="utf-8") as f:
                json.dump(d, f)
            with open(meta_path, "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass
    return d

def fetch_text(url, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "external-skill-intelligence"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

CACHE = os.path.join(DATA, "cache")
def fetch_cached(url, timeout=10, ttl_hours=24, miss_ttl_hours=1):
    """带磁盘缓存的文本抓取：同一 URL 在 TTL 内复用，保证同日重跑结果稳定、也省流量。

    v2.2 修正：命中缓存的「失败」只用**短 TTL**（默认 1 小时）。
    旧逻辑把 MISS 缓存满 24 小时，一次网络抖动/配额耗尽会把整天后续重跑
    都锁死成失败（不可恢复的假阴性）。现在失败 1 小时后自动重试。
    """
    import hashlib, time
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    body_path, meta_path = os.path.join(CACHE, key + ".txt"), os.path.join(CACHE, key + ".meta")
    try:
        if os.path.exists(meta_path):
            age = time.time() - float(open(meta_path).read().strip() or 0)
            raw = open(body_path, encoding="utf-8").read()
            miss = (raw == "\x00MISS")
            if age < (miss_ttl_hours if miss else ttl_hours) * 3600:
                return None if miss else raw
    except Exception:
        pass
    txt = fetch_text(url, timeout=timeout)
    try:
        with open(body_path, "w", encoding="utf-8") as f:
            f.write(txt if txt is not None else "\x00MISS")
        with open(meta_path, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass
    return txt

# ---------- 已安装 Skill 真相源（v4 Canonical 模型） ----------
def load_installed():
    """返回 dict: installed={name: entry}, all_known={name: entry}, suppression={cap: level},
    availability={cap: {...}}, installed_texts={skill名: 用途简述}（v2.9 §六，只读）"""
    sm = load_json(SOURCE_MAP_PATH, {"skills": {}})
    skills = sm.get("skills", {})
    installed = {n: e for n, e in skills.items()
                 if e.get("canonical", {}).get("installed_canonical")}
    ctx = open(INSTALLED_CTX_PATH, encoding="utf-8").read() if os.path.exists(INSTALLED_CTX_PATH) else ""
    suppression, availability = {}, {}
    # v2.9 §六：已装侧「名称+用途简述」文本（只读冻结底座 §6 简表），
    # 供 incremental_subcapability 判定「已装 Skill 明确没有该子能力」。
    installed_texts = {}
    in_tbl = False
    for line in ctx.split("\n"):
        if line.startswith("## 6."):
            in_tbl = True
            continue
        if in_tbl and line.startswith("## "):
            break
        if not in_tbl or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 3 and cells[0] not in ("Canonical Skill", "") \
                and not set(cells[0]) <= {"-", " ", ":"}:
            installed_texts[cells[0]] = cells[2]
    m = re.search(r"CAPABILITY_SUPPRESSION:.*?(?=\n[A-Z_]{6,}:)", ctx, re.S)
    if m:
        for lv in ("strong", "medium", "weak", "none"):
            mm = re.search(rf"^\s*{lv}: (.+)$", m.group(0), re.M)
            if mm:
                for cap in [x.strip() for x in mm.group(1).split(",") if x.strip()]:
                    suppression[cap] = lv
    m = re.search(r"CAPABILITY_AVAILABILITY:.*?(?=\n[A-Z_]{6,}:)", ctx, re.S)
    if m:
        for cap_m in re.finditer(r"^\s{2}([\w]+):\n\s+coverage: (\w+)\n\s+availability: (\w+)", m.group(0), re.M):
            availability[cap_m.group(1)] = {"coverage": cap_m.group(2), "availability": cap_m.group(3)}
    return {"installed": installed, "all_known": skills,
            "suppression": suppression, "availability": availability,
            "installed_texts": installed_texts}

# ---------- 项目需求真相源（SKILL_CONTEXT.md） ----------
def load_project_needs():
    """解析 SKILL_CONTEXT.md 的机器状态（HTML 注释 JSON），返回 needs/tech/totals；失败返回空。"""
    if not os.path.exists(SKILL_CONTEXT_PATH): return {}
    txt = open(SKILL_CONTEXT_PATH, encoding="utf-8").read()
    m = re.search(r"<!--\s*SKILL_CONTEXT_STATE\s*(\{.*?\})\s*-->", txt, re.S)
    if not m: return {}
    try: return json.loads(m.group(1))
    except Exception: return {}
