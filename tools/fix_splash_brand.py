#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动页改用新图标（tile 版）
==========================

原启动页画的是鲸鱼尾线条标记（size 60）。
新品牌的主视觉是「深色圆角方 + 无限符号」，也就是应用图标本身。
启动页把它按 tile 模式画出来，视觉与实际桌面图标一致。

改动：
  _mark 60 -> 96（图标要够大才像 app 图标）
  BrandMark(size: _mark) -> BrandMark(size: _mark, tile: true)
  glow 半径随尺寸放大
"""

import re

P = r"D:\dsh-go\replica\app\lib\ui\onboarding\welcome_page.dart"

raw = open(P, encoding="utf-8").read()
orig = raw

# 1) 尺寸：60 -> 96
raw = raw.replace("static const _mark = 60.0;", "static const _mark = 96.0;")
raw = raw.replace("static const _glow = 220.0;", "static const _glow = 300.0;")

# 2) 用 tile 模式绘制（方图标）
raw = raw.replace(
    "const BrandMark(size: _mark),",
    "const BrandMark(size: _mark, tile: true),",
)

# 3) tile 是正方形，layout 宽度不该再乘 aspect
raw = raw.replace(
    "      width: _mark * BrandMark.aspect,\n      height: _mark,",
    "      width: _mark,\n      height: _mark,",
)

# 4) tile 有自己的视觉中心（就是几何中心），不需要光学位移
raw = raw.replace(
    "                  offset: -BrandMark.opticalShift(_mark),",
    "                  offset: Offset.zero,",
)

# 5) 更新注释
raw = raw.replace(
    "/// The brand mark (the colour glyph) over a soft glow, easing in (fade + a slight\n"
    "/// grow) the first time the page shows. Still under reduced motion.",
    "/// The app icon (dark tile + infinity glyph) over a soft glow, easing in\n"
    "/// (fade + a slight grow) the first time the page shows. Still under reduced motion.",
)

if raw == orig:
    print("没有任何改动，检查匹配")
else:
    open(P, "w", encoding="utf-8").write(raw)
    print("已更新 welcome_page.dart")

# 显示关键行
for i, line in enumerate(open(P, encoding="utf-8").read().splitlines(), 1):
    if "_mark = " in line or "_glow = " in line or "BrandMark(size" in line or "width: _mark" in line:
        print(f"  L{i}: {line.strip()}")
