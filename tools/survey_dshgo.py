#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摸底：列出工程里所有 "DSH Go" 的变体写法
========================================

只读，不改任何文件。用于在批量替换前确认范围。

覆盖的变体：
  DSH Go / DSH  Go / dsh go / DSH-GO / dsh-go / dsh_go / DSH_GO / DshGo / dshGo / DSHGO ...
"""

import collections
import os
import re
import sys

ROOT = r"D:\dsh-go\replica"

SKIP_DIRS = {
    "build", ".dart_tool", ".gradle", "node_modules", ".git",
    "pub-cache", ".idea", ".vscode",
}

EXTS = {
    ".kt", ".java", ".xml", ".dart", ".gradle", ".kts", ".properties",
    ".json", ".arb", ".yaml", ".yml", ".md", ".pro", ".txt", ".html",
    ".js", ".css", ".toml", ".cfg", ".ini", ".sh", ".py",
}

# 每个变体一个正则；顺序影响归类，先精确后宽松
VARIANTS = [
    ("DSH Go",        re.compile(r"DSH\s+Go")),
    ("dsh go",        re.compile(r"dsh\s+go")),
    ("Dsh Go",        re.compile(r"Dsh\s+Go")),
    ("DSH-GO",        re.compile(r"DSH-GO")),
    ("dsh-go",        re.compile(r"dsh-go")),
    ("Dsh-Go",        re.compile(r"Dsh-Go")),
    ("DSH_GO",        re.compile(r"DSH_GO")),
    ("dsh_go",        re.compile(r"dsh_go")),
    ("DshGo",         re.compile(r"DshGo")),
    ("dshGo",         re.compile(r"dshGo")),
    ("DSHGO",         re.compile(r"DSHGO")),
    ("dshgo",         re.compile(r"\bdshgo\b", re.I)),
    ("dshgo.com 等域名", re.compile(r"dshgo\.(com|dev|app|cn)")),
    ("含 DSH Go 的中文串", re.compile(r"关于\s*DSH\s*Go|DSH\s*Go\s*二开")),
    ("dsh-go 仓库路径", re.compile(r"ccch1mneyyy/dsh-go")),
    ("dsh-go.github.io", re.compile(r"ccch1mneyyy\.github\.io")),
]


def main() -> int:
    counter = collections.Counter()
    by_ext = collections.Counter()
    files_hit = collections.defaultdict(set)
    repo_refs = collections.Counter()

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext not in EXTS:
                continue
            try:
                text = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, PermissionError):
                continue

            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            for label, rx in VARIANTS:
                n = len(rx.findall(text))
                if n:
                    counter[label] += n
                    by_ext[ext] += n
                    files_hit[label].add(rel)

    total = sum(counter.values())
    print("=" * 80)
    print(f"所有变体统计  （工程根 {ROOT}）")
    print("=" * 80)
    for label, _ in VARIANTS:
        n = counter[label]
        if n:
            print(f"  {label:<22} {n:>5} 处   涉及 {len(files_hit[label]):>3} 个文件")
    print(f"  {'合计':<22} {total:>5} 处")
    print()

    print("=" * 80)
    print("按文件类型")
    print("=" * 80)
    for ext, n in by_ext.most_common():
        print(f"  {ext:<10} {n:>5} 处")
    print()

    print("=" * 80)
    print("仓库/作者引用（这些是要清掉的）")
    print("=" * 80)
    for label in ("dsh-go 仓库路径", "dsh-go.github.io"):
        files = sorted(files_hit[label])
        print(f"  [{label}] {len(files)} 个文件")
        for f in files[:25]:
            print(f"      {f}")
        if len(files) > 25:
            print(f"      ... 另有 {len(files)-25} 个")
    print()

    print("=" * 80)
    print("各变体命中最多的文件（前 5）")
    print("=" * 80)
    for label, _ in VARIANTS:
        files = files_hit[label]
        if not files:
            continue
        print(f"  [{label}]")
        for f in sorted(files)[:5]:
            print(f"      {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
