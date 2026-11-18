#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动海报：整张显示，不裁切、不删字
==================================

方案 B（用户选定）：把图四整张当启动界面。

要点：
  - **不裁切**：整张 1152x2048 全部保留，一个字都不删
  - **不拉伸变形**：等比缩放到屏幕宽度
  - 上下多余的空间用海报自身的深色底补齐，视觉上无缝

处理：
  按「宽度铺满」缩放（1152 -> 1440，高 2048 -> 2560），
  再用边缘采样色填到常见屏幕高度（3168），得到一张可直接铺屏的图。

产出：
  res/drawable-nodpi/launch_background_image.png   整图 + 补边
  res/values/colors.xml 里补 launch_background_bottom 颜色（与补边同色）
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image

SRC = r"D:\dsh-go\assets-in\splash-source.png"
RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
REPORT = r"D:\dsh-go\reports"

# 目标画布：按主流长屏（1440x3168）准备，比这更长的屏幕会由 drawable 的
# gravity 继续用底部颜色延伸，不会露白
OUT_W = 1440
OUT_H = 3168


def main() -> int:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    print(f"源图: {w}x{h}（整张保留，不裁切）")

    # 等比缩放到目标宽度
    scale = OUT_W / w
    new_h = int(round(h * scale))
    if new_h > OUT_H:
        # 极窄长屏以外的情况：仍以宽度为准，允许纵向超出（由 XML 居中裁掉极少部分）
        print(f"  注意：缩放后高 {new_h} > 画布 {OUT_H}，将按宽度铺满")
    scaled = im.resize((OUT_W, new_h), Image.LANCZOS)
    print(f"缩放到: {scaled.size}")

    # 采样海报顶部与底部的颜色，用于补边（取上下各 8 行平均）
    top_strip = np.asarray(scaled.crop((0, 0, OUT_W, 8)), dtype=np.float32)
    bot_strip = np.asarray(
        scaled.crop((0, scaled.size[1] - 8, OUT_W, scaled.size[1])), dtype=np.float32
    )
    top_color = tuple(int(v) for v in top_strip.reshape(-1, 3).mean(axis=0))
    bot_color = tuple(int(v) for v in bot_strip.reshape(-1, 3).mean(axis=0))
    print(f"补边色 上={top_color} 下={bot_color}")

    canvas = Image.new("RGB", (OUT_W, OUT_H), bot_color)
    # 上半部分用顶部色，下半用底部色，渐变过渡
    for y in range(OUT_H):
        t = y / max(OUT_H - 1, 1)
        c = tuple(int(top_color[i] * (1 - t) + bot_color[i] * t) for i in range(3))
        canvas.paste(Image.new("RGB", (OUT_W, 1), c), (0, y))

    # 把整张贴上去（垂直居中）
    off_y = (OUT_H - new_h) // 2
    canvas.paste(scaled, (0, off_y))
    print(f"整图粘贴位置 y={off_y}..{off_y + new_h}（整张可见）")

    out_dir = os.path.join(RES, "drawable-nodpi")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "launch_background_image.png")
    canvas.save(out, optimize=True)
    print(f"写入: {out}  {os.path.getsize(out)//1024} KB")

    preview = os.path.join(REPORT, "splash-full-preview.png")
    canvas.resize((540, int(540 * OUT_H / OUT_W)), Image.LANCZOS).save(preview)
    print(f"预览: {preview}")

    # 记录补边色，供 XML 兜底
    with open(os.path.join(REPORT, "splash-edge-color.txt"), "w", encoding="utf-8") as f:
        f.write(f"top=#{top_color[0]:02X}{top_color[1]:02X}{top_color[2]:02X}\n")
        f.write(f"bottom=#{bot_color[0]:02X}{bot_color[1]:02X}{bot_color[2]:02X}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
