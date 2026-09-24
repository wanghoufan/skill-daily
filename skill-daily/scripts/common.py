#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill-daily 公共层：输入定位、配置、反馈存储、日期工具。

边界（§二十四 / 执行说明）：
* 冻结底座（SKILL_CONTEXT / INSTALLED_* / EXTERNAL_* / SKILL_CANDIDATES 与 v2.11 规则）
  **只读**；本引擎绝不写入 external-intelligence 目录。
* 不安装 / 不删除 / 不升级任何 Skill（§十四：auto_install 恒为 false）。
* 确定性优先（§二十二）：Delta / 动作分类 / 排序 / 冷却 / 去重 / 机器 JSON 全部用代码。
"""
import json
import os
import re
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)                       # skill-daily/

# ---------- 冻结输入定位（只读；V1.4 §三：集中式 root resolver，验证文件而非目录存在） ----------
TRANSFER_DIR_NAME = "转送审查者 v5 材料（外部情报层）"
LEGACY_NESTED = ("Agent 产物（外部情报层）", TRANSFER_DIR_NAME)


def _valid_external_root(root):
    """§三：候选必须真实含 SKILL_CANDIDATES.json（或 data/ 下）+ build_context.py
    （或 支撑/scripts/ 下），不能只看目录存在。返回 (candidates_path, scripts_dir) 或 None。"""
    if not root or not os.path.isdir(root):
        return None
    cand = _first_existing(os.path.join(root, "SKILL_CANDIDATES.json"),
                           os.path.join(root, "data", "SKILL_CANDIDATES.json"))
    if not os.path.exists(cand):
        return None
    scripts = _first_existing(os.path.join(root, "scripts", "build_context.py"),
                              os.path.join(root, "支撑", "scripts", "build_context.py"))
    if not os.path.exists(scripts):
        return None
    return cand, os.path.dirname(scripts)


def resolve_external_root():
    """§三 优先级：1 环境变量；2 同级 external-intelligence（开发仓）；
    3 同级转送包（用户最常用复现布局）；4 旧版 Agent 产物嵌套（继续兼容）。
    找不到时给友好错误，绝不让用户看到 ModuleNotFoundError。"""
    parent = os.path.dirname(BASE)
    env = os.environ.get("EXTERNAL_INTELLIGENCE_ROOT")
    tried = []
    if env:
        v = _valid_external_root(env)
        if v:
            return env, "env_override", v
        raise SystemExit(
            f"EXTERNAL_INTELLIGENCE_ROOT 指向的目录不是有效的 External v2.11 包：{env}\n"
            "需要包含 SKILL_CANDIDATES.json（或 data/ 下）与 "
            "scripts/build_context.py（或 支撑/scripts/ 下）。")
    for cand_root, mode in (
            (os.path.join(parent, "external-intelligence"), "development_repo"),
            (os.path.join(parent, TRANSFER_DIR_NAME), "sibling_transfer_package"),
            (os.path.join(parent, *LEGACY_NESTED), "legacy_nested")):
        v = _valid_external_root(cand_root)
        if v:
            return cand_root, mode, v
        tried.append(cand_root)
    raise SystemExit(
        "找不到 External Skill Intelligence v2.11。\n"
        f"请将“{TRANSFER_DIR_NAME}”与 skill-daily 放在同级，\n"
        "或设置 EXTERNAL_INTELLIGENCE_ROOT 指向其目录。\n"
        "已尝试：\n  " + "\n  ".join(tried))


def _first_existing(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]


EXTERNAL_ROOT, EXTERNAL_RESOLUTION_MODE, _resolved = resolve_external_root()
CANDIDATES_PATH = _resolved[0]
EXTERNAL_SCRIPTS_DIR = _resolved[1]
EXTERNAL_CONTEXT_PATH = _first_existing(
    os.path.join(EXTERNAL_ROOT, "EXTERNAL_SKILLS_CONTEXT.md"),
    os.path.join(EXTERNAL_ROOT, "EXTERNAL_SKILLS_CONTEXT.md"))
EXTERNAL_SNAPSHOT_PATH = _first_existing(
    os.path.join(EXTERNAL_ROOT, "data", "state", "last_snapshot.json"),
    os.path.join(EXTERNAL_ROOT, "state", "last_snapshot.json"))
REGISTRY_PATH = _first_existing(
    os.path.join(EXTERNAL_ROOT, "SKILL_SOURCE_REGISTRY.json"),
    os.path.join(EXTERNAL_ROOT, "data", "SKILL_SOURCE_REGISTRY.json"))
# v2.11 冻结语义复用：classify_delta / snap_key（只 import，不修改对方代码）
sys.path.insert(0, EXTERNAL_SCRIPTS_DIR)

# ---------- 本引擎自有状态 ----------
CONFIG_PATH = os.path.join(BASE, "config", "daily.json")
FEEDBACK_PATH = os.path.join(BASE, "data", "SKILL_FEEDBACK.json")
FEEDBACK_HISTORY_PATH = os.path.join(BASE, "data", "SKILL_FEEDBACK_HISTORY.jsonl")
DAILY_SNAPSHOT_PATH = os.path.join(BASE, "data", "state", "daily_snapshot.json")
CONTEXT_OUT_PATH = os.path.join(BASE, "DAILY_REPORT_CONTEXT.json")
REPORTS_DIR = os.path.join(BASE, "reports")

FEEDBACK_STATUSES = ("installed", "tried", "useful", "poor", "ignored", "removed", "deferred")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")


def load_config():
    cfg = load_json(CONFIG_PATH, {}) or {}
    cfg.setdefault("max_daily_items", 10)
    cfg.setdefault("min_daily_items", 0)
    cfg.setdefault("watch_repeat_days", 7)
    cfg.setdefault("ignored_repeat_days", 7)
    cfg.setdefault("deferred_repeat_days", 7)
    cfg.setdefault("removed_cooldown_days", 30)
    # v2.11 整改 §二/§八：全动作冷却 + 展示族配额（全部配置化）
    cfg.setdefault("install_repeat_days", 7)
    cfg.setdefault("update_repeat_days", 7)
    cfg.setdefault("restore_repeat_days", 3)
    cfg.setdefault("max_install_per_capability_family", 2)
    cfg.setdefault("max_watch_per_capability_family", 1)
    # V1.2 整改 §七：tombstone 有限保留期（消失通知台账）
    cfg.setdefault("tombstone_retention_days", 30)
    cfg.setdefault("show_internal_system_events", False)
    cfg["auto_install"] = False          # §十四：无论配置怎么写，V1 恒为 False
    cfg.setdefault("language", "zh-CN")
    return cfg


# ---------- 反馈层（§一 D / §八 / §九） ----------
def load_feedback():
    return load_json(FEEDBACK_PATH, {}) or {}


def init_feedback_files():
    """首次运行时初始化空反馈文件（验收块 feedback: initialized 的来源）。"""
    if not os.path.exists(FEEDBACK_PATH):
        save_json({}, FEEDBACK_PATH)
        return True
    return False


def record_feedback(canonical_key, status, note="", on_date=None):
    """写最新状态 + 一行一条的历史。机器读取只依赖最新状态文件。"""
    if status not in FEEDBACK_STATUSES:
        raise ValueError(f"status 必须是 {FEEDBACK_STATUSES} 之一，收到 {status!r}")
    d = (on_date or datetime.now().date()).isoformat()
    fb = load_feedback()
    fb[canonical_key] = {"canonical_key": canonical_key, "status": status,
                         "user_note": note, "updated_at": d}
    save_json(fb, FEEDBACK_PATH)
    os.makedirs(os.path.dirname(FEEDBACK_HISTORY_PATH), exist_ok=True)
    with open(FEEDBACK_HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"canonical_key": canonical_key, "status": status,
                            "user_note": note, "updated_at": d},
                           ensure_ascii=False) + "\n")
    return fb[canonical_key]


# ---------- 日期工具（冷却计算全部显式传参，保证可测 / 确定性） ----------
def parse_date(s):
    return date.fromisoformat((s or "")[:10]) if s else None


def days_between(a, b):
    return (b - a).days if (a and b) else None


def clean_desc(desc, limit=88):
    """小白讲解第一层用：取描述第一句，压缩空白，截断。"""
    d = re.split(r"(?<=[。；;!?])\s*", (desc or "").strip())[0]
    d = re.sub(r"\s+", " ", d)
    if len(d) > limit:
        d = d[:limit].rstrip(" ,;:，；：") + "…"
    return d
