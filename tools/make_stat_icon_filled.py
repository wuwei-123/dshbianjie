#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏图标最终版：实心填充（不用描边）
======================================

排查结论：
  - APK 里 ic_stat_dsh 路径正确
  - 桌面图标显示正确（新无限符号）
  - 但状态栏仍显示旧应用图标

原因：部分 ROM（含 vivo Funtouch）在渲染 Notification smallIcon 时，
对 VectorDrawable 的 **stroke（描边）** 支持不好 —— 描边不填充的路径
会被当作「无内容」，于是系统回退到应用图标。

修复：把无限符号改成**实心填充路径**（fill 而不是 stroke）。
用一个带宽度的闭合轮廓表达线条，任何 ROM 都能正确渲染。

做法：在 24 网格里，用「外轮廓 - 内轮廓」的环形路径（evenOdd 挖空），
线宽 2.2，与之前视觉一致但是填充而非描边。
"""

from __future__ import annotations

import math
import os

import cairosvg

RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
REPORT = r"D:\dsh-go\reports"

GRID = 24.0
PAD = 2.5
STROKE = 2.2
SEG = 96      # 每环采样点数


def ring(cx: float, cy: float, rx: float, ry: float, n: int = SEG):
    """椭圆采样。"""
    return [
        (cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


def path_from_poly(pts, close=True) -> str:
    d = [f"M {pts[0][0]:.3f},{pts[0][1]:.3f}"]
    for x, y in pts[1:]:
        d.append(f"L {x:.3f},{y:.3f}")
    if close:
        d.append("Z")
    return " ".join(d)


def build_filled_infinity(g: float, pad: float, stroke: float) -> str:
    """用两条『胶囊形』的环拼成 ∞，实心填充。

    无限符号 = 左右两个环 + 中间的交叉。用实心环形表达：
      外环（外椭圆）、内环（内椭圆，方向相反 -> evenOdd 挖空）
    左侧环与右侧环在中心相接，形成 8 字。
    """
    cx, cy = g / 2, g / 2
    half_w = (g - pad * 2) / 2
    rx = half_w * 0.92
    ry = half_w * 0.62
    t = stroke / 2          # 线宽的一半

    left_cx = cx - half_w * 0.52
    right_cx = cx + half_w * 0.52

    parts = []
    for lcx in (left_cx, right_cx):
        # 外轮廓（顺时针）
        outer = ring(lcx, cy, rx, ry)
        parts.append(path_from_poly(outer))
        # 内轮廓（逆时针，evenOdd 下挖空）
        inner = ring(lcx, cy, rx - t * 1.35, ry - t * 1.35)
        inner.reverse()
        parts.append(path_from_poly(inner))
    return " ".join(parts)


def write_vector(path: str, size: int, d: str, comment: str) -> None:
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- {comment} -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{size}dp"
    android:height="{size}dp"
    android:viewportWidth="{size}"
    android:viewportHeight="{size}">
    <path
        android:fillColor="#FFFFFFFF"
        android:fillType="evenOdd"
        android:pathData="{d}" />
</vector>
'''
    open(path, "w", encoding="utf-8").write(xml)
    print(f"  写入 {os.path.basename(path)}  {size}dp  path {len(d)} 字符")


def preview(d: str, g: float, out: str, px: int = 192) -> None:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {g:g} {g:g}">'
        f'<path fill="#ffffff" fill-rule="evenodd" d="{d}"/></svg>'
    )
    for size, tag in ((px, "big"), (24, "actual")):
        png = cairosvg.svg2png(
            bytestring=svg.encode(), output_width=size, output_height=size,
            background_color="#101318",
        )
        p = out.replace(".png", f"-{tag}.png")
        open(p, "wb").write(png)
    print(f"  预览 {out.replace('.png', '-big.png')}")


def main() -> int:
    d = build_filled_infinity(GRID, PAD, STROKE)
    write_vector(
        os.path.join(RES, "drawable", "ic_stat_dsh.xml"),
        24, d,
        "Status-bar icon for all notifications: the infinity mark, filled (not stroked) "
        "so every ROM renders it. Small icons use alpha only.",
    )

    d108 = build_filled_infinity(108.0, PAD * 108.0 / 24.0, STROKE * 108.0 / 24.0)
    write_vector(
        os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"),
        108, d108,
        "Themed-icon (Android 13+) layer: the infinity mark silhouette.",
    )

    preview(d, GRID, os.path.join(REPORT, "stat-filled.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
