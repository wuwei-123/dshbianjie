#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清掉宠物设置页的残余引用
=======================

home_shell / web_home 各监听一个「桌宠请求打开设置页」的流。
桌宠已禁用，这个流永远不会来消息，监听是死代码，删掉最干净。
settings_screen 只是 import 没有调用，去掉 import。
"""

from __future__ import annotations

import os

LIB = r"D:\dsh-go\replica\app\lib"


def rw(path: str) -> str:
    p = os.path.join(LIB, path)
    return open(p, encoding="utf-8", newline="").read()


def ww(path: str, text: str) -> None:
    p = os.path.join(LIB, path)
    open(p, "w", encoding="utf-8", newline="").write(text)


def edit(path: str, pairs, label: str) -> bool:
    raw = rw(path)
    orig = raw
    ok = True
    for old, new in pairs:
        if old not in raw:
            print(f"  [未匹配] {label}: {old.splitlines()[0][:66] if old else ''}")
            ok = False
            continue
        raw = raw.replace(old, new, 1)
    if raw != orig:
        ww(path, raw)
    if ok:
        print(f"  [已改] {label}")
    return ok


def main() -> int:
    print("1. home_shell：去掉桌宠设置请求监听")
    edit(
        "ui/shell/home_shell.dart",
        [
            ("import '../pets/pet_settings_page.dart';\n", ""),
            (
                """      _petSettings = ref.read(petOverlayChannelProvider).settingsRequests.listen((_) {
        if (mounted) unawaited(PetSettingsPage.open(context));
      });
""",
                """      // The floating pet is removed in this build, so nothing asks for its
      // settings page any more.
""",
            ),
        ],
        "home_shell",
    )

    print()
    print("2. web_home：同样处理")
    edit(
        "ui/web/web_home.dart",
        [
            ("import '../pets/pet_settings_page.dart';\n", ""),
            (
                """      _settings = ref.read(petOverlayChannelProvider).settingsRequests.listen((_) {
        if (mounted) unawaited(PetSettingsPage.open(context));
      });
""",
                """      // The floating pet is removed in this build.
""",
            ),
        ],
        "web_home",
    )

    print()
    print("3. settings_screen：去掉未使用的 import")
    edit(
        "ui/settings/settings_screen.dart",
        [("import '../pets/pet_settings_page.dart';\n", "")],
        "settings_screen",
    )

    print()
    print("4. 恢复 Spots.pet* 定义（pet_settings_page 仍在引用）")
    P = "ui/settings/index/spots.dart"
    raw = rw(P)
    if "static final petSize" not in raw:
        anchor = "    // 界面."
        add = """    // 宠物（本版已隐藏入口，定义保留以免残留引用报错）.
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
        if anchor in raw:
            raw = raw.replace(anchor, add + anchor, 1)
            ww(P, raw)
            print("  [已改] 恢复 4 个 SettingSpot")
        else:
            print("  [未找到锚点]")
    else:
        print("  [已存在]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
