#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语境分类：把 dsh-go 的每一处按「能不能改」分清楚
================================================

为什么需要：dsh-go 在这份代码里有三种身份，混在一起就会改坏。

  1. 品牌名        README 标题、"关于 DSH Go"、窗口标题     -> 要改成 dsh边界
  2. 文件/目录路径  /opt/dsh-go/direct/preload.mjs          -> 改了 App 起不来
                   assets/skills/dsh-go-plugin/
  3. 代码标识符     DshGoBridge、dshGoApi、DSH_GO_*          -> 改了编译不过

本脚本只读取、只分类、只报告，不动任何文件。
"""

import collections
import os
import re

ROOT = r"D:\dsh-go\replica"

SKIP_DIRS = {
    "build", ".dart_tool", ".gradle", "node_modules", ".git",
    "pub-cache", ".idea", ".vscode",
}

CODE_EXTS = {
    ".kt", ".java", ".dart", ".js", ".py", ".sh", ".yml", ".yaml",
    ".json", ".gradle", ".kts", ".properties", ".xml", ".arb",
}

# ---- 判定规则：命中即「不能改」 ----

# 真实文件系统路径 / 模块名 / 已安装目录
PATH_LIKE = re.compile(
    r"(/opt/dsh-go|/etc/dsh-app|assets/skills/dsh-go-|dsh-go-bridge|"
    r"dsh-go-plugin|dsh-go-guide|dsh-go-support|dsh-go-ui|dsh-go-market)"
)

# 代码标识符（驼峰/下划线/全大写常量）
IDENT_LIKE = re.compile(
    r"\b(DshGo|dshGo|DSH_GO|DshGo[A-Z]\w*|dshGo[A-Z]\w*|DSH_GO_[A-Z_]+)\b"
)

# 系统对接标识：包名/action/域名里的 dshgo
SYSTEM_LIKE = re.compile(
    r"(com\.dshbianjie\.app\.\w*dshgo|dshgo://|dshgo\.app|dshgo\.com|\.dshgo\b)"
)

# 品牌文案：带这些上下文才认为是给人看的名字
BRAND_CONTEXT = re.compile(
    r"(关于|欢迎|设置|标题|版本|简介|作者|https?://|README|DSH\s+Go)"
)


def classify(line: str) -> str:
    """给一行里的 dsh-go 归类。"""
    if PATH_LIKE.search(line):
        return "路径/模块名（不能改）"
    if SYSTEM_LIKE.search(line):
        return "系统对接标识（要单独定）"
    if IDENT_LIKE.search(line):
        return "代码标识符（不能改）"
    return "待定（可能是品牌名）"


def main() -> int:
    buckets = collections.defaultdict(list)
    counts = collections.Counter()

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext not in CODE_EXTS:
                continue
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            for i, line in enumerate(lines, 1):
                if not re.search(r"dsh[-_ ]?go|DshGo|dshGo|DSH_GO", line, re.I):
                    continue
                kind = classify(line)
                counts[kind] += 1
                buckets[kind].append((rel, i, line.strip()[:130]))

    print("=" * 84)
    print("dsh-go 语境分类")
    print("=" * 84)
    for kind, n in counts.most_common():
        print(f"  {kind:<26} {n:>5} 行")
    print()

    for kind in ("路径/模块名（不能改）", "代码标识符（不能改）", "系统对接标识（要单独定）"):
        rows = buckets.get(kind, [])
        if not rows:
            continue
        print("=" * 84)
        print(f"{kind}  —— 共 {len(rows)} 行，抽样 15 条")
        print("=" * 84)
        seen = set()
        shown = 0
        for rel, ln, text in rows:
            key = text[:70]
            if key in seen:
                continue
            seen.add(key)
            print(f"  {rel}:{ln}")
            print(f"      {text}")
            shown += 1
            if shown >= 15:
                break
        print()

    rows = buckets.get("待定（可能是品牌名）", [])
    print("=" * 84)
    print(f"待定 —— 共 {len(rows)} 行（这些才是品牌名替换的候选）")
    print("=" * 84)
    by_file = collections.Counter(r[0] for r in rows)
    print("  涉及文件数:", len(by_file))
    print("  命中最多：")
    for f, n in by_file.most_common(20):
        print(f"      {n:>4}  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
