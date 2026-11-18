#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定位宠物/伙伴的用户可见入口
==========================

彻底删除代价太大（2369 个连锁错误），改为切断入口：
代码留着，用户看不到、用不到，构建体积也基本不变但功能消失。

需要找的是：
  1. 路由 / 页面注册（PageLinks、home_shell）
  2. 设置项（设置页里的宠物/伙伴条目）
  3. 聊天页的桌宠浮层（pet_stage / PetPerch）
  4. 原生悬浮窗服务（PetOverlayService 在 Manifest 注册）
  5. 无障碍/权限里的桌宠条目
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

APP = r"D:\dsh-go\replica\app"
LIB = os.path.join(APP, "lib")
KF = os.path.join(APP, "android", "app", "src", "main", "kotlin", "com", "dshbianjie", "app")

PATTERNS = [
    (r"PetStage|PetPerch|pet_stage|pet_perch", "聊天页桌宠浮层"),
    (r"PetOverlayService|PetOverlayPlugin|pet_overlay", "原生悬浮窗"),
    (r"CompanionPage|companion_page", "伙伴小屋页面"),
    (r"petSettingsPage|PetSettingsPage|pet_settings", "宠物设置页"),
    (r"pet_picker|PetPicker", "宠物选择器"),
    (r"overlay_settings_tile|OverlaySettingsTile", "悬浮窗设置项"),
    (r"petPrefsProvider|PetPrefs", "宠物偏好"),
]


def main() -> int:
    hits = defaultdict(list)

    for dp, dn, filenames in os.walk(LIB):
        dn[:] = [d for d in dn if d not in {"build", ".dart_tool", "pets", "companion"}]
        if "ui" in dp and ("pets" in dp or "companion" in dp):
            continue
        for f in filenames:
            if not f.endswith(".dart"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, LIB).replace("\\", "/")
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if s.startswith(("//", "///", "*")):
                    continue
                for rx, label in PATTERNS:
                    if re.search(rx, line):
                        hits[label].append((rel, i, s[:105]))

    for _, label in PATTERNS:
        rows = hits.get(label, [])
        if not rows:
            continue
        print("=" * 78)
        print(f"{label}  —— {len(rows)} 处")
        print("=" * 78)
        for rel, i, s in rows[:20]:
            print(f"  {rel}:{i}")
            print(f"     {s}")
        if len(rows) > 20:
            print(f"  ... 另有 {len(rows)-20} 处")
        print()

    # Manifest 里的声明
    print("=" * 78)
    print("AndroidManifest 里的宠物条目")
    print("=" * 78)
    mf = os.path.join(APP, "android", "app", "src", "main", "AndroidManifest.xml")
    for i, line in enumerate(open(mf, encoding="utf-8").read().splitlines(), 1):
        if re.search(r"[Pp]et|companion", line):
            print(f"  L{i}: {line.strip()[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
