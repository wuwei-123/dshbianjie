#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
协议改名：/dsh-go/v1 -> /dshbianjie/v1，dshGo -> dshbianjie
==========================================================

二开要求把所有 dsh-go 标识换成自己的。协议也在内，所以客户端与服务端
必须同步改，改完必须两端一致，否则 App 连不上 bridge。

映射
----
  /dsh-go/v1              ->  /dshbianjie/v1         （HTTP/WS 路径）
  /dsh-go                ->  /dshbianjie            （PREFIX）
  /dsh-go-guard-canary   ->  /dshbianjie-guard-canary
  dsh-go.guarded         ->  dshbianjie.guarded     （Symbol.for 键）
  /dsh-go/plugins        ->  /dshbianjie/plugins
  .dsh-go-l2s-           ->  .dshbianjie-l2s-
  dsh-go-bridge          ->  dshbianjie-bridge
  dshGo                  ->  dshbianjie             （JSON 字段 / 服务名 / JSON Pointer）
  DshGo                  ->  Dshbianjie             （类名/类型名）
  dsh-go（独立词）        ->  dshbianjie

不动
----
  @deepseek-ai/*                     DSH 官方包
  /opt/dsh, /usr/local/bin/dsh       DSH 引擎本体

用法
----
  python tools/rename_protocol.py --dry-run
  python tools/rename_protocol.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = r"D:\dsh-go\replica"

SKIP_DIRS = {
    "build", ".dart_tool", ".gradle", "node_modules", ".git",
    "pub-cache", ".idea", ".vscode", "_work", "_backup",
}

TEXT_EXTS = {
    ".dart", ".js", ".mjs", ".kt", ".java", ".json", ".md",
    ".yaml", ".yml", ".sh", ".xml", ".arb", ".kts", ".gradle",
    ".properties", ".txt", ".html", ".css", ".toml",
}

# 顺序：先长后短
RULES = [
    # 0) Dart 包名（package:dsh_app/... / pubspec name）
    #    逐行处理，所以这里不能用 re.M 与 $ —— 它们会吃掉行尾换行，
    #    把 "name: dsh_app\n" 变成 "name: dshbianjie_app"，与下一行粘连。
    (re.compile(r"\bpackage:dsh_app/"), "package:dshbianjie_app/"),
    (re.compile(r"^(name:\s*)dsh_app(?=\s*$)"), r"\1dshbianjie_app"),
    # 1) 带 /v1 的路径（最具体）
    (re.compile(r"/dsh-go/v1"), "/dshbianjie/v1"),
    (re.compile(r"/dsh-go-guard-canary"), "/dshbianjie-guard-canary"),
    (re.compile(r"/dsh-go-guard"), "/dshbianjie-guard"),
    (re.compile(r"dsh-go\.guarded"), "dshbianjie.guarded"),
    (re.compile(r"/dsh-go/plugins"), "/dshbianjie/plugins"),
    (re.compile(r"\.dsh-go-l2s-"), ".dshbianjie-l2s-"),
    (re.compile(r"\.dsh-go-tmp"), ".dshbianjie-tmp"),
    (re.compile(r"\.dsh-go-direct-path-alias"), ".dshbianjie-direct-path-alias"),
    # 2) JSON Pointer 前缀 /dshGo/
    (re.compile(r"/dshGo(?=/)"), "/dshbianjie"),
    # 3) 模块/包名（含 examples 目录引用）
    (re.compile(r"dsh-go-bridge"), "dshbianjie-bridge"),
    (re.compile(r"dsh-go-plugin"), "dshbianjie-plugin"),
    (re.compile(r"dsh-go-guide"), "dshbianjie-guide"),
    (re.compile(r"dsh-go-support"), "dshbianjie-support"),
    (re.compile(r"dsh-go-ui"), "dshbianjie-ui"),
    (re.compile(r"dsh-go-market"), "dshbianjie-market"),
    (re.compile(r"dsh-go-example-"), "dshbianjie-example-"),
    (re.compile(r"dsh-go-deletion"), "dshbianjie-deletion"),
    (re.compile(r"dsh-go-pr-gate"), "dshbianjie-pr-gate"),
    (re.compile(r"dsh-go/phone-caller"), "dshbianjie/phone-caller"),
    # 4) 复合标识符：captured group 保留后缀
    (re.compile(r"\b__dshGo(\w+)"), r"__dshbianjie\1"),
    (re.compile(r"\bdshGo([A-Z]\w*)"), r"dshbianjie\1"),
    (re.compile(r"\bDshGo([A-Z]\w*)"), r"Dshbianjie\1"),
    (re.compile(r"\bdshGo(\b)"), r"dshbianjie\1"),
    (re.compile(r"\bDshGo(\b)"), r"Dshbianjie\1"),
    # 5) 裸 PREFIX "/dsh-go"（引号内，不含 /v1）
    (re.compile(r"""["']/dsh-go["']"""), '"/dshbianjie"'),
    # 6) 剩余独立词 dsh-go
    (re.compile(r"(?<![\w/\-.])(dsh-go)(?![\w/\-.])"), "dshbianjie"),
]

# 绝对不能动
PROTECT = [
    re.compile(r"@deepseek-ai/[\w@/.\-]*"),
    re.compile(r"/opt/dsh(?!bianjie)"),
    re.compile(r"/usr/local/bin/dsh\b"),
    re.compile(r"dsh-session-persistence-jsonl[\w/.\-]*"),
]


def spans_of(line: str):
    out = []
    for rx in PROTECT:
        for m in rx.finditer(line):
            out.append((m.start(), m.end()))
    return out


def overlaps(a, spans) -> bool:
    return any(not (a[1] <= s or a[0] >= e) for s, e in spans)


def apply(line: str, rx, repl: str) -> tuple[str, int]:
    """替换一行。

    关键：repl 里有 \\1 这类反向引用，必须用 m.expand(repl) 展开。
    直接 parts.append(repl) 会把字面量 "\\1" 写进文件，把代码写坏。
    """
    spans = spans_of(line)
    parts, last, n = [], 0, 0
    for m in rx.finditer(line):
        if overlaps((m.start(), m.end()), spans):
            continue
        parts.append(line[last:m.start()])
        parts.append(m.expand(repl))
        last = m.end()
        n += 1
    if not n:
        return line, 0
    parts.append(line[last:])
    return "".join(parts), n


def transform(line: str) -> tuple[str, int]:
    n = 0
    for rx, repl in RULES:
        line, k = apply(line, rx, repl)
        n += k
    return line, n


def iter_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in TEXT_EXTS:
                yield os.path.join(dirpath, fn)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    dry = args.dry_run

    print(f"工程根: {ROOT}")
    print(f"模式  : {'DRY-RUN' if dry else '执行'}")
    print()

    files, total = 0, 0
    touched = []
    for p in iter_files():
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if "changelog" in rel.lower():
            continue
        try:
            raw = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, PermissionError):
            continue
        out, local = [], 0
        for line in raw.splitlines(keepends=True):
            nl, n = transform(line)
            out.append(nl)
            local += n
        if not local:
            continue
        files += 1
        total += local
        touched.append((rel, local))
        if not dry:
            open(p, "w", encoding="utf-8").write("".join(out))

    print(f"涉及文件: {files}")
    print(f"改动    : {total} 处")
    print()
    print("改动最多的 15 个文件：")
    for rel, n in sorted(touched, key=lambda x: -x[1])[:15]:
        print(f"  {n:>5}  {rel}")
    print()
    if dry:
        print("DRY-RUN 结束，未改动。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
