#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 brand_mark.dart 的注释头换成新品牌描述（鲸鱼 -> 无限符号）。"""

import re

P = r"D:\dsh-go\replica\app\lib\ui\shell\brand_mark.dart"

NEW_DOC = """/// The dsh boundary mark: the infinity glyph (boundless possibilities).
///
/// Vector paths generated from the brand masters in `assets/brand/`
/// (`brand_glyph.g.dart`, by `tool/make_brand_mark.py`), in the launcher icon's
/// 108 grid, so the mark and the themed launcher layer never drift apart.
///
/// - By default the colour glyph: blue-to-white gradient, one tuning for light
///   pages and one for dark, picked by the theme.
/// - [color]: one flat tint (a quiet footer, white on the poster card).
/// - [tile]: the launcher tile, the glyph on the icon's dark rounded square.
class BrandMark extends StatelessWidget {"""

raw = open(P, encoding="utf-8").read()
# 从第一处 /// 注释块开始，到 class BrandMark 行
m = re.search(r"^///.*?^class BrandMark extends StatelessWidget \{", raw, re.S | re.M)
if not m:
    raise SystemExit("未匹配到注释块")

out = raw[: m.start()] + NEW_DOC + raw[m.end() :]
open(P, "w", encoding="utf-8").write(out)
print("已更新注释头")
