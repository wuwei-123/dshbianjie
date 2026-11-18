#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把新图标铺到所有密度与主题变体
==============================

源图：D:\\dsh-go\\assets-in\\icon-final.png（1536x1536，深色底 + 无限符号）

Android 图标规范：
  ic_launcher.png            48/72/96/144/192   （mdpi..xxxhdpi）
  ic_launcher_round.png      同上，圆形裁切
  ic_launcher_foreground.png 108/162/216/324/432 = launcher × 2.25
                             （adaptive icon 的 108dp 画布，内容必须在中央 72dp 安全区内）

源图本身已经是一个「带圆角深色底 + 描边的完整 app 图标」。
两种处理：
  A. 直接缩放整张图  -> 桌面显示再套一层系统圆角，会变成「图标里还有图标」
  B. 只取中央图形内容 -> 更像原生图标

这里用 B + 适度留白：源图四周有约 8% 的暗色边距，先裁掉，
再按密度缩放，避免双重边框。
"""

from __future__ import annotations

import os
import shutil

from PIL import Image, ImageDraw

SRC_ICON = r"D:\dsh-go\assets-in\icon-final.png"
RES = r"D:\dsh-go\replica\app\android\app\src\main\res"

# 密度 -> (launcher 边长, foreground 边长)
DENSITIES = {
    "mipmap-mdpi": (48, 108),
    "mipmap-hdpi": (72, 162),
    "mipmap-xhdpi": (96, 216),
    "mipmap-xxhdpi": (144, 324),
    "mipmap-xxxhdpi": (192, 432),
}

# 裁掉源图外圈的比例（上下左右各 7%），去掉自带的圆角描边
CROP_MARGIN = 0.07


def load_square() -> Image.Image:
    im = Image.open(SRC_ICON).convert("RGBA")
    w, h = im.size
    side = min(w, h)
    # 先居中裁成正方形
    left = (w - side) // 2
    top = (h - side) // 2
    im = im.crop((left, top, left + side, top + side))
    # 再裁掉外圈
    m = int(side * CROP_MARGIN)
    im = im.crop((m, m, side - m, side - m))
    return im


def rounded_mask(size: int, radius_ratio: float = 0.225) -> Image.Image:
    """圆角矩形蒙版（Android/iOS 图标通用的 squircle 近似）。"""
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    r = int(size * radius_ratio)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=255)
    return mask


def circle_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


def make_launcher(src: Image.Image, size: int, rounded: bool) -> Image.Image:
    out = src.resize((size, size), Image.LANCZOS)
    mask = rounded_mask(size) if rounded else None
    if mask is not None:
        out.putalpha(mask)
    return out


def make_foreground(src: Image.Image, size: int) -> Image.Image:
    """Deprecated: an adaptive icon's foreground must be the glyph alone.

    This used to paste the whole finished icon - dark rounded tile, border and
    glyph - into the foreground layer. An adaptive icon is two layers: the
    background gradient (res/drawable/ic_launcher_<theme>_background.xml) and
    a foreground that is the glyph on transparency. Pasting the tile covered
    the gradient, and copying it onto frost/ink/night gave all four themes the
    same dark picture - the glyph vanished on the two dark backgrounds.

    The foregrounds are produced by tools/make_icon_foregrounds.py instead.
    This function is kept so older callers still import, and returns an empty
    transparent layer so a stray call cannot paint over the gradient again.
    """
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def main() -> int:
    if not os.path.exists(SRC_ICON):
        print(f"找不到源图: {SRC_ICON}")
        return 2

    src = load_square()
    print(f"源图裁切后: {src.size[0]}x{src.size[1]}")
    print()

    total = 0
    for dens, (l_size, f_size) in DENSITIES.items():
        d = os.path.join(RES, dens)
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

        # 1) 方形图标
        p = os.path.join(d, "ic_launcher.png")
        make_launcher(src, l_size, rounded=False).save(p, optimize=True)
        total += 1
        print(f"  {dens:<16} ic_launcher.png            {l_size}x{l_size}")

        # 2) 圆形图标
        p = os.path.join(d, "ic_launcher_round.png")
        make_launcher(src, l_size, rounded=True).save(p, optimize=True)
        total += 1
        print(f"  {dens:<16} ic_launcher_round.png      {l_size}x{l_size}")

        # 3) adaptive 前景: not this script's job any more.
        #
        # The foreground must be the glyph alone on transparency, tinted to read
        # on each theme's background gradient. This script pasted the finished
        # tile into it, which covered the gradient; tools/make_icon_foregrounds.py
        # writes the foregrounds now.
        print(f"  {dens:<16} ic_launcher_foreground.png  -> tools/make_icon_foregrounds.py")

    print()
    print(f"已替换 {total} 个图标文件")

    # 主题变体：先前的品牌方案只保留一份方形图标。
    # The *foreground* is deliberately not copied between themes any more: ink
    # and night have dark background gradients, so a shared dark foreground made
    # the glyph invisible. tools/make_icon_foregrounds.py tints each theme.
    print()
    print("主题变体同步（frost/ink/night 方形+圆形 -> 同一份）:")
    for dens, (l_size, f_size) in DENSITIES.items():
        d = os.path.join(RES, dens)
        base = os.path.join(d, "ic_launcher.png")
        base_round = os.path.join(d, "ic_launcher_round.png")
        for theme in ("frost", "ink", "night"):
            for target, source in (
                (f"ic_launcher_{theme}.png", base),
                (f"ic_launcher_{theme}_round.png", base_round),
            ):
                tp = os.path.join(d, target)
                if os.path.exists(tp):
                    shutil.copyfile(source, tp)
                    total += 1
        print(f"  {dens:<16} 三套主题已同步（前景另见 make_icon_foregrounds.py）")
    print()
    print(f"合计写入 {total} 个文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
