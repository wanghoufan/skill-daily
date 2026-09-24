#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户反馈录入（§一 D / §八 / §九）。

用法：
    python3 scripts/feedback.py <canonical_key> <status> [备注]
    status ∈ installed | tried | useful | poor | ignored | removed | deferred
    python3 scripts/feedback.py --list          # 查看最新状态

反馈只影响明确可解释的维度（能力族 / 同一来源仓），每条调整都会在日报里给出
feedback_reason；引擎不猜「你可能不喜欢什么」（§九）。本工具不安装/删除/升级任何 Skill。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                    # noqa: E402


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--list":
        fb = C.load_feedback()
        if not fb:
            print("（暂无反馈记录）")
        for k, v in sorted(fb.items()):
            print(f"{v.get('updated_at')}  {v.get('status'):9s}  {k}"
                  + (f"  备注：{v.get('user_note')}" if v.get("user_note") else ""))
        return 0
    if len(argv) < 2:
        print("需要 <canonical_key> <status>", file=sys.stderr)
        return 2
    key, status = argv[0], argv[1]
    note = argv[2] if len(argv) > 2 else ""
    try:
        entry = C.record_feedback(key, status, note)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    C.init_feedback_files()
    print(f"已记录反馈：{key} → {entry['status']}（{entry['updated_at']}）")
    print("下一次 build_daily.py 生效：可解释的调整只作用于同能力族 / 同来源仓的展示优先级与冷却。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
