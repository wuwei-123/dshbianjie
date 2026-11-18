#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
协议摸底：/dsh-go/v1 与 dshGo 的全部位置
========================================

这两类是「协议」，改必须两端同步：
  客户端 packages/dsh_client/lib/src/*.dart  +  app/lib/**
  服务端 runtime/bridge/dshbianjie-bridge/lib/*.js

只读取，不修改。
"""

import collections
import os
import re

ROOT = r"D:\dsh-go\replica"
SKIP = {"build", ".dart_tool", ".gradle", "node_modules", ".git",
        "pub-cache", ".idea", ".vscode", "_work", "_backup"}

EXTS = {".dart", ".js", ".mjs", ".kt", ".json", ".md", ".yaml", ".yml", ".sh"}

# 协议相关模式
PATTERNS = [
    (r"/dsh-go/v1", "API 路径 /dsh-go/v1"),
    (r"/dsh-go-guard-canary", "canary 路径"),
    (r"/dsh-go-guard", "guard 路径"),
    (r"dsh-go\.guarded", "Symbol 键"),
    (r"/dsh-go/plugins", "插件目录路径"),
    (r"\.dsh-go-l2s-", "L2S 临时前缀"),
    (r"\bdshGo\b", "dshGo 标识符/JSON 字段"),
    (r"\bDshGo\b", "DshGo 类名/类型"),
    (r"\bdsh-go\b", "dsh-go 独立词"),
    (r"\bdsh-Go\b", "dsh-Go 变体"),
]


def layer_of(rel: str) -> str:
    if rel.startswith("packages/dsh_client"):
        return "客户端库 dsh_client"
    if rel.startswith("packages/"):
        return "其他 package"
    if rel.startswith("runtime/bridge"):
        return "服务端 bridge"
    if rel.startswith("app/lib"):
        return "App Dart"
    if rel.startswith("app/android"):
        return "App Kotlin"
    if rel.startswith("app/assets"):
        return "App 资产/技能"
    if rel.startswith(("app/test", "runtime/tests", "sdk/")):
        return "测试/SDK"
    return "其他"


def main() -> int:
    hits = collections.defaultdict(list)   # pattern -> [(layer, rel, line, text)]
    by_layer = collections.Counter()
    file_set = collections.defaultdict(set)

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in EXTS:
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            layer = layer_of(rel)
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
            for i, line in enumerate(lines, 1):
                for pat, label in PATTERNS:
                    if re.search(pat, line):
                        hits[label].append((layer, rel, i, line.strip()[:120]))
                        file_set[label].add(rel)

    print("=" * 86)
    print("协议类引用统计")
    print("=" * 86)
    for _, label in PATTERNS:
        rows = hits[label]
        if not rows:
            continue
        print(f"\n【{label}】{len(rows)} 行 / {len(file_set[label])} 文件")
        layers = collections.Counter(r[0] for r in rows)
        for lay, n in layers.most_common():
            print(f"    {lay:<22} {n:>4} 行")

    print()
    print("=" * 86)
    print("服务端（bridge）里需要改的协议点")
    print("=" * 86)
    for _, label in PATTERNS:
        rows = [r for r in hits[label] if r[0] == "服务端 bridge"]
        if not rows:
            continue
        print(f"\n【{label}】{len(rows)} 行")
        for layer, rel, ln, text in rows[:12]:
            print(f"    {rel}:{ln}")
            print(f"       {text}")

    print()
    print("=" * 86)
    print("客户端库里需要改的协议点")
    print("=" * 86)
    for _, label in PATTERNS:
        rows = [r for r in hits[label] if r[0] == "客户端库 dsh_client"]
        if not rows:
            continue
        print(f"\n【{label}】{len(rows)} 行")
        for layer, rel, ln, text in rows[:12]:
            print(f"    {rel}:{ln}")
            print(f"       {text}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
