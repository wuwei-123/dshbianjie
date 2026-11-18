#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极版：极简几何无限符号（通知图标 + 主题图标）
==============================================

24dp 状态栏图标必须极简。用两条对称贝塞尔弧画 8 字，线宽固定。

关键尺寸（24 网格）：
  占地 2.5 .. 21.5   —— 留 2.5 边距，不会顶到状态栏边缘
  线宽 2.2           —— 24dp 下约 2px，清晰但不糊
  环高比 1:2.6       —— 压扁一些，更像 ∞ 而不是「8」

同时生成 108dp 版给 Android 13+ 主题图标。
"""

from __future__ import annotations

import os

import cairosvg

RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
REPORT = r"D:\dsh-go\reports"

GRID = 24.0
PAD = 2.5
STROKE = 2.2


def build(g: float, pad: float) -> str:
    """在 g×g 网格里画一个 ∞。"""
    cx, cy = g / 2, g / 2
    left = pad
    right = g - pad
    mid = g / 2

    # 环的纵向半高：略小于半宽，得到扁一点的 8 字
    half_w = (right - left) / 2
    half_h = half_w / 1.55

    top = cy - half_h
    bot = cy + half_h

    # 控制点：让弧线鼓出，形成饱满的环
    k = half_w * 0.62

    d = (
        f"M {left:.3f},{cy:.3f} "
        # 左环上弧 -> 中心
        f"C {left:.3f},{top:.3f} {left + k:.3f},{top:.3f} {mid:.3f},{cy:.3f} "
        # 中心 -> 右环上弧
        f"C {right - k:.3f},{top:.3f} {right:.3f},{top:.3f} {right:.3f},{cy:.3f} "
        # 右环下弧 -> 中心
        f"C {right:.3f},{bot:.3f} {right - k:.3f},{bot:.3f} {mid:.3f},{cy:.3f} "
        # 中心 -> 左环下弧
        f"C {left + k:.3f},{bot:.3f} {left:.3f},{bot:.3f} {left:.3f},{cy:.3f}"
    )
    return d


def write_vector(path: str, size: int, d: str, stroke: float, comment: str) -> None:
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- {comment} -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{size}dp"
    android:height="{size}dp"
    android:viewportWidth="{size}"
    android:viewportHeight="{size}">
    <path
        android:strokeColor="#FFFFFFFF"
        android:strokeWidth="{stroke}"
        android:strokeLineCap="round"
        android:strokeLineJoin="round"
        android:fillColor="#00000000"
        android:pathData="{d}" />
</vector>
'''
    open(path, "w", encoding="utf-8").write(xml)
    print(f"  写入 {os.path.basename(path)}  {size}dp  stroke={stroke}")


def preview(d: str, g: float, stroke: float, out: str, px: int = 192) -> None:
    # 同时渲一个 24px 的真实尺寸，模拟状态栏观感
    for size, suffix in ((px, "big"), (24, "actual")):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {g:g} {g:g}">'
            f'<path fill="none" stroke="#ffffff" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-linejoin="round" d="{d}"/></svg>'
        )
        png = cairosvg.svg2png(
            bytestring=svg.encode(),
            output_width=size, output_height=size,
            background_color="#101318",
        )
        p = out.replace(".png", f"-{suffix}.png")
        open(p, "wb").write(png)
        print(f"  预览 {p}")


def main() -> int:
    d = build(GRID, PAD)
    print("路径:", d[:100], "...")

    write_vector(
        os.path.join(RES, "drawable", "ic_stat_dsh.xml"),
        24, d, STROKE,
        "Status-bar icon for all notifications: the infinity mark. "
        "Small icons are drawn from alpha only.",
    )

    # 108dp 主题层：同一路径按比例放大，线宽也放大，保持视觉一致
    d108 = build(108.0, PAD * 108.0 / 24.0)
    write_vector(
        os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"),
        108, d108, STROKE * 108.0 / 24.0,
        "Themed-icon (Android 13+) layer: the infinity mark silhouette.",
    )

    preview(d, GRID, STROKE, os.path.join(REPORT, "stat-icon-v3.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
