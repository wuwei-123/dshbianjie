#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宠物/伙伴功能引用链分析
======================

彻底删除前必须知道谁引用了谁，否则删完编译不过、再逐个补会非常被动。

输出：
  1. 待删文件清单（Dart / Kotlin / 资源）
  2. 每个待删文件被哪些「外部」文件引用
  3. 外部引用点（这些才是真正要改的地方）
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

ROOT = r"D:\dsh-go\replica"
APP = os.path.join(ROOT, "app")
LIB = os.path.join(APP, "lib")
KT = os.path.join(APP, "android", "app", "src", "main", "kotlin", "com", "dshbianjie", "app")

# 要删除的目录/前缀
DART_DELETE_DIRS = [
    os.path.join(LIB, "pets"),
    os.path.join(LIB, "companion"),
    os.path.join(LIB, "ui", "pets"),
    os.path.join(LIB, "ui", "companion"),
]
DART_DELETE_FILES = [
    os.path.join(LIB, "dev", "pet_actions_probe_main.dart"),
    os.path.join(LIB, "dev", "pet_probe_support.dart"),
    os.path.join(LIB, "plugins", "seams", "adapters", "pet_adapter.dart"),
]

KT_DELETE_DIRS = [os.path.join(KT, "pet")]
ASSET_DELETE_DIRS = [
    os.path.join(APP, "assets", "pets"),
    os.path.join(APP, "assets", "companion"),
    os.path.join(APP, "assets", "whale"),
]


def collect(paths, dirs, exts):
    out = set()
    for d in dirs:
        if os.path.isdir(d):
            for dp, _, fn in os.walk(d):
                for f in fn:
                    if os.path.splitext(f)[1].lower() in exts:
                        out.add(os.path.join(dp, f))
    for p in paths:
        if os.path.exists(p):
            out.add(p)
    return out


def main() -> int:
    dart_del = collect(DART_DELETE_FILES, DART_DELETE_DIRS, {".dart"})
    kt_del = collect([], KT_DELETE_DIRS, {".kt"})

    print("=" * 78)
    print(f"待删 Dart 文件: {len(dart_del)}")
    print(f"待删 Kotlin 文件: {len(kt_del)}")
    for d in ASSET_DELETE_DIRS:
        if os.path.isdir(d):
            n = sum(len(f) for _, _, f in os.walk(d))
            print(f"待删资源目录: {os.path.relpath(d, APP)}  ({n} 个文件)")
    print()

    # 所有 dart 文件
    all_dart = []
    for dp, dn, fn in os.walk(LIB):
        dn[:] = [x for x in dn if x not in {"build", ".dart_tool"}]
        for f in fn:
            if f.endswith(".dart"):
                all_dart.append(os.path.join(dp, f))

    # 外部文件（不在待删集合里）
    external = [p for p in all_dart if p not in dart_del]

    # 建立：待删文件的模块名 -> 路径
    del_modules = {}
    for p in dart_del:
        rel = os.path.relpath(p, LIB).replace("\\", "/")
        mod = rel[:-5]  # 去掉 .dart
        del_modules[mod] = p

    # 扫描外部文件的 import
    refs = defaultdict(list)   # 外部文件 -> [引用的待删模块]
    for p in external:
        try:
            txt = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, PermissionError):
            continue
        hits = []
        for m in re.finditer(r"^(?:import|export)\s+'([^']+)'", txt, re.M):
            uri = m.group(1)
            if uri.startswith("dart:"):
                continue
            target = None
            if uri.startswith("package:dshbianjie_app/"):
                target = uri[len("package:dshbianjie_app/") :]
            elif not uri.startswith("package:"):
                # 相对路径，按当前文件所在目录解析
                base = os.path.dirname(os.path.relpath(p, LIB)).replace("\\", "/")
                target = os.path.normpath(os.path.join(base, uri)).replace("\\", "/")
            if target and target in del_modules:
                hits.append(target)
        if hits:
            refs[p] = sorted(set(hits))

    print("=" * 78)
    print(f"外部引用点: {len(refs)} 个文件")
    print("=" * 78)
    by_dir = defaultdict(int)
    for p in refs:
        d = os.path.dirname(os.path.relpath(p, LIB)).replace("\\", "/") or "."
        by_dir[d] += 1
    for d, n in sorted(by_dir.items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  lib/{d}/")

    print()
    print("=" * 78)
    print("逐文件明细（外部 -> 引用的宠物模块）")
    print("=" * 78)
    for p in sorted(refs):
        rel = os.path.relpath(p, LIB).replace("\\", "/")
        print(f"  lib/{rel}")
        for t in refs[p]:
            print(f"      <- {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
