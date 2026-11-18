#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清掉设置索引里的宠物条目（精确文本匹配，不用括号推断）。"""

from __future__ import annotations

import os

P = r"D:\dsh-go\replica\app\lib\ui\settings\index\spots.dart"

# 整块精确文本
BLOCKS = [
    # 设置索引里的宠物页
    """    SettingsPageMeta(
      SettingsPageId.pets,
      title: (l) => l.botsPets,
      group: _look,
      keywords: (l) => l.searchKwPets,
      freq: Freq.medium,
      links: const ['pets'],
    ),
""",
]


def main() -> int:
    raw = open(P, encoding="utf-8").read()
    n = 0
    for b in BLOCKS:
        if b in raw:
            raw = raw.replace(b, "")
            n += 1
            print(f"  已删宠物页索引条目")
        else:
            print("  未匹配宠物页索引条目")

    # 4 个 SettingSpot：用正则整块删
    import re

    for name in ("petSize", "petQuiet", "petOutsideApp", "petDisplayWhen"):
        pat = re.compile(
            r"\n    static final " + name + r" = SettingSpot\(\n(?:.*\n)*?    \);\n",
        )
        new_raw, cnt = pat.subn("\n", raw)
        if cnt:
            raw = new_raw
            n += 1
            print(f"  已删 SettingSpot({name})")
        else:
            print(f"  未匹配 SettingSpot({name})")

    # 删掉留下的空注释行
    raw = raw.replace("    // 瀹犵墿.\n", "")

    if n:
        open(P, "w", encoding="utf-8").write(raw)
    print()
    print(f"共改动 {n} 处")

    # 验证
    left = raw.count("SettingsPageId.pets")
    print(f"剩余 SettingsPageId.pets 引用: {left}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
