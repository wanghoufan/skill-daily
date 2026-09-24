# -*- coding: utf-8 -*-
"""每日运行入口：注册表校验 → 双向发现 → 分析评分 → 轻量 Context + delta → 精简对照件。"""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
PY = sys.executable
DIGEST_OUT = os.path.join(BASE, "CANDIDATES_DIGEST.md")
STEPS = [
    ("build_registry.py", []),
    ("discover.py", []),
    ("analyze.py", []),
    ("build_context.py", []),
    ("make_digest.py", ["-o", DIGEST_OUT]),
]

def main():
    for s, args in STEPS:
        print(f"\n===== {s} {' '.join(args)} =====")
        r = subprocess.run([PY, os.path.join(HERE, s)] + args)
        if r.returncode != 0:
            print(f"STEP FAILED: {s}"); return r.returncode
    print("\nDONE. 输出：data/SKILL_SOURCE_REGISTRY.json, data/SKILL_CANDIDATES.json, "
          "EXTERNAL_SKILLS_CONTEXT.md, CANDIDATES_DIGEST.md")
    return 0

if __name__ == "__main__":
    sys.exit(main())
