#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宠物残留清理（按行处理，兼容 CRLF）。"""

from __future__ import annotations

import os

LIB = r"D:\dsh-go\replica\app\lib"


def read(path: str) -> list[str]:
    return open(os.path.join(LIB, path), encoding="utf-8", newline="").read().splitlines(keepends=True)


def write(path: str, lines: list[str]) -> None:
    open(os.path.join(LIB, path), "w", encoding="utf-8", newline="").write("".join(lines))


def drop_listener(path: str, var: str, label: str) -> None:
    """删掉 `_x = ref.read(petOverlayChannelProvider).settingsRequests.listen(...)` 整块。"""
    lines = read(path)
    out = []
    i = 0
    removed = 0
    while i < len(lines):
        if f"{var} = ref.read(petOverlayChannelProvider).settingsRequests.listen(" in lines[i]:
            depth = 0
            j = i
            while j < len(lines):
                depth += lines[j].count("(") - lines[j].count(")")
                if depth <= 0:
                    break
                j += 1
            removed += 1
            i = j + 1
            continue
        if "import '../pets/pet_settings_page.dart';" in lines[i]:
            removed += 1
            i += 1
            continue
        out.append(lines[i])
        i += 1
    if removed:
        write(path, out)
        print(f"  [已改] {label}（{removed} 处）")
    else:
        print(f"  [无改动] {label}")


def restore_spots() -> None:
    path = "ui/settings/index/spots.dart"
    lines = read(path)
    if any("static final petSize" in l for l in lines):
        print("  [已存在] Spots.pet*")
        return

    anchor = None
    for i, l in enumerate(lines):
        if l.strip().startswith("// ") and "鐣岄潰" in l:  # 「界面.」
            anchor = i
            break
    if anchor is None:
        for i, l in enumerate(lines):
            if "static final uiMode = SettingSpot(" in l:
                anchor = i
                break
    if anchor is None:
        print("  [未找到锚点] Spots.pet*")
        return

    block = """    // 宠物设置点：本版已隐藏入口，定义保留（残留页面仍在引用）.
    static final petSize = SettingSpot(
      'pet-size',
      page: SettingsPageId.pets,
      title: (l) => l.botsPetSize,
      keywords: (l) => l.searchKwPetSize,
    );
    static final petQuiet = SettingSpot(
      'pet-quiet',
      page: SettingsPageId.pets,
      title: (l) => l.botsPetQuiet,
      keywords: (l) => l.searchKwPetQuiet,
    );
    static final petOutsideApp = SettingSpot(
      'pet-outside-app',
      page: SettingsPageId.pets,
      title: (l) => l.botsPetOutsideApp,
      keywords: (l) => l.searchKwPetOutside,
    );
    static final petDisplayWhen = SettingSpot(
      'pet-display-when',
      page: SettingsPageId.pets,
      title: (l) => l.botsPetDisplayWhen,
      keywords: (l) => l.searchKwPetDisplayWhen,
    );

"""
    lines.insert(anchor, block)
    write(path, lines)
    print("  [已改] 恢复 4 个 SettingSpot")


print("1. home_shell")
drop_listener("ui/shell/home_shell.dart", "_petSettings", "home_shell")
print("2. web_home")
drop_listener("ui/web/web_home.dart", "_settings", "web_home")
print("3. spots.dart")
restore_spots()
