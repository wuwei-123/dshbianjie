#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段一改名：品牌名 + 署名清理 + 版本号
======================================

只处理「可安全替换」的部分，不碰运行时路径和代码标识符。
路径改名（/opt/dsh-go 等）需要重建 rootfs，单独在阶段二做。

替换内容：
  1. 品牌名：DSH Go / DshGo / dshGo / DSHGO …  ->  dsh边界
     （只替换「给人看的」字符串，代码标识符 DSH_GO_* / DshGoIsland 不动）
  2. 署名清理：作者名、微博/B站/X/GitHub 链接、仓库地址、社区群
  3. 版本号：1.0.15 -> 0.1.0
  4. 只保留一句「基于 DSH Go 二开」

用法：
  python tools/rename_brand.py --dry-run
  python tools/rename_brand.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = r"D:\dsh-go\replica"

SKIP_DIRS = {
    "build", ".dart_tool", ".gradle", "node_modules", ".git",
    "pub-cache", ".idea", ".vscode",
}

TEXT_EXTS = {
    ".kt", ".java", ".xml", ".dart", ".gradle", ".kts", ".properties",
    ".json", ".arb", ".yaml", ".yml", ".md", ".pro", ".txt", ".html",
    ".js", ".css", ".toml", ".cfg", ".ini",
}

# ---- 必须保护：路径与模块名，改了 App 起不来 ----
PATH_GUARDS = (
    "/opt/dsh-go", "opt/dsh-go", "/etc/dsh-app", "dsh-go-bridge",
    "dsh-go-plugin", "dsh-go-guide", "dsh-go-support", "dsh-go-ui",
    "dsh-go-market", "/usr/local/bin/dsh", "assets/skills/dsh-go-",
)

# ---- 必须保护：代码标识符 ----
IDENT_PATTERNS = [
    re.compile(r"\bDSH_GO_[A-Z0-9_]+\b"),
    re.compile(r"\bDshGo[A-Za-z0-9_]*\b"),
    re.compile(r"\bdshGo[A-Za-z0-9_]*\b"),
    re.compile(r"\bDSH_GO\b"),
]

# ---- 品牌名替换规则（顺序重要：先长后短）----
BRAND_RULES = [
    (re.compile(r"DSH\s+Go"), "dsh边界"),
    (re.compile(r"Dsh\s+Go"), "dsh边界"),
    (re.compile(r"DSH-GO"), "dsh边界"),
    (re.compile(r"Dsh-Go"), "dsh边界"),
    (re.compile(r"DSHGO"), "dsh边界"),
    (re.compile(r"\bDshGo\b"), "dsh边界"),
    (re.compile(r"\bdshGo\b"), "dsh边界"),
    (re.compile(r"\bdshgo\b"), "dsh边界"),
]

# ---- 署名/链接清理 ----
ATTRIBUTION_RULES = [
    # GitHub 仓库与主页
    (re.compile(r"https?://github\.com/ccch1mneyyy(?:/dsh-go)?(?:/[\w\-#?=&.]*)?"), ""),
    (re.compile(r"https?://ccch1mneyyy\.github\.io(?:/[\w\-#?=&.]*)?"), ""),
    (re.compile(r"ccch1mneyyy/dsh-go-market"), ""),
    (re.compile(r"ccch1mneyyy/dsh-go"), ""),
    # 社交账号
    (re.compile(r"https?://x\.com/cccch1mneyyyy"), ""),
    (re.compile(r"https?://b23\.tv/[\w]+"), ""),
    (re.compile(r"@cccch1mneyyyy"), ""),
    (re.compile(r"ccchimneyyy"), ""),
    (re.compile(r"ccch1mneyyy"), ""),
    # 社区
    (re.compile(r"https?://qm\.qq\.com/[\w/?=&.]*"), ""),
    (re.compile(r"https?://forum\.dshtui\.com[/\w?=&.]*"), ""),
    (re.compile(r"https?://go\.dshtui\.com[/\w?=&.]*"), ""),
]

# 版本号
VERSION_RULES = [
    (re.compile(r"\b1\.0\.15\b"), "0.1.0"),
]

# 允许保留的唯一声明
BASED_ON = "基于 DSH Go 二开"


def protected_spans(line: str) -> list[tuple[int, int]]:
    """返回该行中不能动的区间（路径 / 标识符）。"""
    spans = []
    for tok in PATH_GUARDS:
        start = 0
        while True:
            i = line.find(tok, start)
            if i < 0:
                break
            spans.append((i, i + len(tok)))
            start = i + len(tok)
    for rx in IDENT_PATTERNS:
        for m in rx.finditer(line):
            spans.append((m.start(), m.end()))
    return spans


def overlaps(a: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(not (a[1] <= s or a[0] >= e) for s, e in spans)


def apply_rules(line: str) -> tuple[str, int]:
    """对单行应用全部规则，跳过受保护区间。返回 (新行, 改动数)。"""
    n = 0
    for rules in (VERSION_RULES, BRAND_RULES, ATTRIBUTION_RULES):
        for rx, repl in rules:
            spans = protected_spans(line)
            out = []
            last = 0
            changed = False
            for m in rx.finditer(line):
                if overlaps((m.start(), m.end()), spans):
                    continue
                out.append(line[last:m.start()])
                out.append(repl)
                last = m.end()
                changed = True
            if changed:
                out.append(line[last:])
                line = "".join(out)
                n += 1
    return line, n


def iter_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in TEXT_EXTS:
                yield os.path.join(dirpath, fn)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=ROOT)
    args = ap.parse_args(argv)

    root = args.root
    print(f"工程根: {root}")
    print(f"模式  : {'DRY-RUN' if args.dry_run else '执行'}")
    print()

    total_files = 0
    total_hits = 0
    touched = []
    # changelog 是上游历史，不改
    for p in iter_files(root):
        rel = os.path.relpath(p, root).replace("\\", "/")
        if "changelog" in rel.lower():
            continue
        try:
            raw = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, PermissionError):
            continue

        lines = raw.splitlines(keepends=True)
        new_lines = []
        local = 0
        for line in lines:
            nl, n = apply_rules(line)
            new_lines.append(nl)
            local += n
        if local == 0:
            continue

        total_files += 1
        total_hits += local
        touched.append((rel, local))
        if not args.dry_run:
            open(p, "w", encoding="utf-8").write("".join(new_lines))

    print(f"涉及文件: {total_files}")
    print(f"改    动: {total_hits} 处")
    print()
    print("改动最多的 15 个文件：")
    for rel, n in sorted(touched, key=lambda x: -x[1])[:15]:
        print(f"  {n:>4}  {rel}")
    print()
    if args.dry_run:
        print("DRY-RUN 结束，未改动。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
