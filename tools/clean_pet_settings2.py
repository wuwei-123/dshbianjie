#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清掉设置索引里的宠物条目（按行处理，兼容 CRLF/LF）
"""

from __future__ import annotations

P = r"D:\dsh-go\replica\app\lib\ui\settings\index\spots.dart"

raw = open(P, encoding="utf-8", newline="").read()
lines = raw.splitlines(keepends=True)

out = []
i = 0
removed = 0
while i < len(lines):
    line = lines[i]

    # 1) SettingsPageMeta( 后跟 SettingsPageId.pets
    if "SettingsPageMeta(" in line and i + 1 < len(lines) and "SettingsPageId.pets" in lines[i + 1]:
        # 找到配对的 "),"
        depth = 0
        j = i
        while j < len(lines):
            depth += lines[j].count("(") - lines[j].count(")")
            if depth <= 0:
                break
            j += 1
        removed += 1
        print(f"  删除 SettingsPageMeta(pets)：第 {i+1}-{j+1} 行")
        i = j + 1
        continue

    # 2) static final petXxx = SettingSpot(
    if "static final" in line and "SettingSpot(" in line:
        name = line.split("static final")[1].split("=")[0].strip()
        if name.startswith("pet"):
            depth = 0
            j = i
            while j < len(lines):
                depth += lines[j].count("(") - lines[j].count(")")
                if depth <= 0 and ")" in lines[j]:
                    break
                j += 1
            removed += 1
            print(f"  删除 SettingSpot({name})：第 {i+1}-{j+1} 行")
            i = j + 1
            continue

    out.append(line)
    i += 1

with open(P, "w", encoding="utf-8", newline="") as f:
    f.write("".join(out))

print(f"\n共删除 {removed} 块")
print("剩余 SettingsPageId.pets:", "".join(out).count("SettingsPageId.pets"))
