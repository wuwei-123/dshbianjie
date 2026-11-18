#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
切断宠物/伙伴入口（精确版）
==========================

按实际文件内容逐条改。每次改完都会打印结果，便于核对。
"""

from __future__ import annotations

import os
import re

APP = r"D:\dsh-go\replica\app"
LIB = os.path.join(APP, "lib")

EDITS = [
    # ---- 1. 聊天页：去掉 PetStage 包装，child 直通 ----
    (
        "ui/chat/chat_screen.dart",
        [
            (
                """              child: PetStage(
                sessionId: sessionId,
                aside: typing,
                child: CustomMultiChildLayout(
                  delegate: _ChatLayout(_veilHeight),
                  children: [""",
                """              child: CustomMultiChildLayout(
                  delegate: _ChatLayout(_veilHeight),
                  children: [""",
            ),
        ],
        "聊天页：PetStage 直通",
    ),
    # ---- 2. 伙伴小屋：路由返回 null ----
    (
        "links/page_links.dart",
        [
            ("import '../ui/companion/companion_page.dart';\n", ""),
            (
                "if (id == companionPageLink) return const CompanionPage();",
                "// Companion (Live2D) is removed in this build; the link stays\n"
                "  // declared so old shortcuts fail softly instead of crashing.\n"
                "  if (id == companionPageLink) return null;",
            ),
        ],
        "伙伴小屋：去掉路由",
    ),
    # ---- 3. 设置：宠物页换成空 ----
    (
        "ui/settings/index/settings_pages.dart",
        [
            ("import '../../pets/pet_settings_page.dart';\n", ""),
            (
                "SettingsPageId.pets => const PetSettingsPage(),",
                "// Removed in this build (no pets).\n"
                "      SettingsPageId.pets => const SizedBox.shrink(),",
            ),
        ],
        "设置：宠物页置空",
    ),
]


def main() -> int:
    ok = 0
    fail = 0
    for rel, pairs, label in EDITS:
        p = os.path.join(LIB, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            print(f"[跳过] {label}: {rel} 不存在")
            fail += 1
            continue
        raw = open(p, encoding="utf-8").read()
        orig = raw
        local_ok = True
        for old, new in pairs:
            if old not in raw:
                print(f"[未匹配] {label}: {old.splitlines()[0][:70]}")
                local_ok = False
                continue
            raw = raw.replace(old, new, 1)
        if raw != orig:
            open(p, "w", encoding="utf-8").write(raw)
        if local_ok:
            print(f"[已改] {label}")
            ok += 1
        else:
            fail += 1

    print()
    print(f"完成 {ok} 项，未完全匹配 {fail} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
