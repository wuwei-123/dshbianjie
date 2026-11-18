#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改名第 2 步：真实目录与文件名
=============================

文本替换改不到目录名和文件名本身。这里处理它们。

注意顺序：先深后浅，否则父目录一改名，子路径就失效。
"""

import os
import sys

ROOT = r"D:\dsh-go\replica"
SKIP = {"build", ".dart_tool", ".gradle", "node_modules", ".git",
        "pub-cache", ".idea", ".vscode", "_work", "_backup"}

# 目录/文件名映射
RENAMES = [
    ("dsh-go-example-", "dshbianjie-example-"),
    ("dsh-go-bridge", "dshbianjie-bridge"),
    ("dsh-go-guide", "dshbianjie-guide"),
    ("dsh-go-plugin", "dshbianjie-plugin"),
    ("dsh-go-support", "dshbianjie-support"),
    ("dsh-go-ui", "dshbianjie-ui"),
    ("dsh-go-pop.svg", "dshbianjie-pop.svg"),
    ("dsh-go.svg", "dshbianjie.svg"),
    ("dsh-go.json", "dshbianjie.json"),
]


def new_name(name: str) -> str:
    for old, new in RENAMES:
        if name == old:
            return new
        if old.endswith("-") and name.startswith(old):
            return new + name[len(old):]
        if name.startswith(old):
            return name.replace(old, new, 1)
    return name


def main() -> int:
    dry = "--dry-run" in sys.argv
    print(f"工程根: {ROOT}")
    print(f"模式  : {'DRY-RUN' if dry else '执行'}")
    print()

    # 收集所有待改名的条目（目录+文件），按路径深度倒序
    targets = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for d in dirnames:
            if dsh_ok := (d != new_name(d)):
                targets.append((os.path.join(dirpath, d), d, new_name(d), True))
        for f in filenames:
            if f != new_name(f):
                targets.append((os.path.join(dirpath, f), f, new_name(f), False))

    # 深的先处理
    targets.sort(key=lambda t: t[0].count(os.sep), reverse=True)

    print(f"待改名条目: {len(targets)}")
    done = 0
    for path, old, new, is_dir in targets:
        dst = os.path.join(os.path.dirname(path), new)
        mark = "DIR " if is_dir else "FILE"
        if os.path.exists(dst):
            print(f"  [跳过-已存在] {mark} {old} -> {new}")
            continue
        print(f"  [{mark}] {old} -> {new}")
        if not dry:
            os.rename(path, dst)
        done += 1

    print()
    print(f"{'将改' if dry else '已改'}: {done} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
