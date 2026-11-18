#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除宠物 / 伙伴功能（第一阶段：删文件）
=====================================

策略：先删干净，再让编译器告诉我哪些地方还引用着。
比静态分析可靠——Dart 的类型系统会把每个漏网之处都指出来。

删除：
  lib/pets/          桌宠核心（状态、包、精灵图、悬浮桥）
  lib/companion/     伙伴小屋（Live2D、语音、信号）
  lib/ui/pets/       桌宠界面
  lib/ui/companion/  伙伴小屋界面
  lib/dev/pet_*.dart 调试入口
  lib/plugins/seams/adapters/pet_adapter.dart
  kotlin/.../pet/    原生悬浮窗
  assets/pets /companion /whale
"""

from __future__ import annotations

import os
import shutil
import sys

APP = r"D:\dsh-go\replica\app"
LIB = os.path.join(APP, "lib")
KT = os.path.join(APP, "android", "app", "src", "main", "kotlin", "com", "dshbianjie", "app")

DIRS = [
    os.path.join(LIB, "pets"),
    os.path.join(LIB, "companion"),
    os.path.join(LIB, "ui", "pets"),
    os.path.join(LIB, "ui", "companion"),
    os.path.join(KT, "pet"),
    os.path.join(APP, "assets", "pets"),
    os.path.join(APP, "assets", "companion"),
    os.path.join(APP, "assets", "whale"),
]

FILES = [
    os.path.join(LIB, "dev", "pet_actions_probe_main.dart"),
    os.path.join(LIB, "dev", "pet_probe_support.dart"),
    os.path.join(LIB, "plugins", "seams", "adapters", "pet_adapter.dart"),
    os.path.join(LIB, "ui", "pets", "overlay_settings_tile.dart"),
]


def main() -> int:
    dry = "--dry-run" in sys.argv
    removed_dirs = 0
    removed_files = 0
    freed = 0

    for d in DIRS:
        if not os.path.isdir(d):
            continue
        n = sum(len(f) for _, _, f in os.walk(d))
        size = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fn in os.walk(d)
            for f in fn
        )
        print(f"  [DIR ] {os.path.relpath(d, APP)}  {n} 个文件  {size/1024/1024:.2f} MB")
        if not dry:
            shutil.rmtree(d, ignore_errors=True)
        removed_dirs += 1
        freed += size

    for f in FILES:
        if not os.path.isfile(f):
            continue
        size = os.path.getsize(f)
        print(f"  [FILE] {os.path.relpath(f, APP)}  {size/1024:.0f} KB")
        if not dry:
            os.remove(f)
        removed_files += 1
        freed += size

    print()
    print(f"{'将删' if dry else '已删'}: {removed_dirs} 个目录 + {removed_files} 个文件")
    print(f"释放空间: {freed/1024/1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
