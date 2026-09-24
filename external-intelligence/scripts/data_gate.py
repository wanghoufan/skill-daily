# -*- coding: utf-8 -*-
"""数据质量 Gate（v2.2）：在候选进入正式池之前，先判断「这是不是一个 Skill」。

背景（§一.1）：v2.1 的 ClawHub HTML 容错解析会把前端构建产物当成 Skill 收录，
约 50 条形如 `assets/design-system-xxxx.css`、`index-xxxx.js`、`styles-xxxx.css`。
它们的 `skill_name` 其实是文件名，不是 Skill。

原则：
  · 这类条目**允许留在 raw discovery 里作为抓取证据**（不删原始数据），
    但**不得进入 SKILL_CANDIDATES.json 正式候选池**。
  · Skill 名必须符合合理 slug / skill directory 规则。

本模块只做纯判断，不读文件、不联网。
"""
import os
import re

# 静态资源扩展名（出现即不是 Skill）
ARTIFACT_EXTS = {".css", ".js", ".mjs", ".cjs", ".map", ".png", ".jpg", ".jpeg", ".svg",
                 ".webp", ".gif", ".ico", ".bmp", ".avif", ".woff", ".woff2", ".ttf", ".otf",
                 ".eot", ".scss", ".less", ".sass", ".mp4", ".webm", ".mov", ".pdf", ".zip",
                 ".tar", ".gz", ".7z", ".wasm", ".lock", ".log"}

# 明显的构建/静态资源目录（路径首段命中即不是 Skill）
ARTIFACT_DIRS = {"assets", "static", "build", "dist", "public", "_next", "node_modules",
                 ".git", "coverage", "out", "vendor", "chunks", "fonts", "images", "img",
                 ".cache", "tmp", "temp"}

# 打包器生成的 hash 文件名：index-a1b2c3d4、vendor.9f8e7d6c、chunk-abc123
_HASH_NAME_RE = re.compile(r"^(index|main|chunk|vendor|runtime|polyfills|app|styles|bundle)"
                           r"[.\-][0-9a-f]{6,}", re.I)
_LEGAL_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def is_artifact_entry(name):
    """是否是「构建产物 / 静态资源」而非 Skill。"""
    n = (name or "").strip().lower()
    if not n:
        return True
    if "/" in n or "\\" in n:
        parts = [p for p in re.split(r"[/\\]", n) if p]
        if parts and parts[0] in ARTIFACT_DIRS:
            return True
        n = parts[-1] if parts else n
    if os.path.splitext(n)[1] in ARTIFACT_EXTS:
        return True
    if _HASH_NAME_RE.match(n):
        return True
    return False


def is_valid_skill_name(name):
    """Skill 名必须是合理 slug / skill directory 名。"""
    n = (name or "").strip()
    if not n or len(n) > 80:
        return False
    if "/" in n or "\\" in n or n in (".", ".."):
        return False
    if is_artifact_entry(n):
        return False
    if not _LEGAL_SLUG_RE.match(n):
        return False
    # 去掉分隔符后至少 2 个字符（排除 "a"、"x-1" 这类残渣）
    if len(re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "", n)) < 2:
        return False
    return True


def has_min_fm(text):
    """frontmatter / Agent Skills 基本结构是否可解析。"""
    if not text:
        return False
    head = text[:4000]
    if not re.match(r"^\s*---\s*\n", head):
        return False
    return bool(re.search(r"^name\s*:\s*\S", head, re.M)) or \
        bool(re.search(r"^description\s*:", head, re.M))
