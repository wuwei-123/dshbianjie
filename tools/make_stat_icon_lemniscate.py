#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏图标：用双纽线生成实心 ∞
==============================

前一版用两个相交椭圆，形状不对（成了两个圆环）。
这次用**双纽线**（lemniscate of Bernoulli）的等距带，得到真正的 8 字。

做法：
  取曲线 x = a·cos t / (1 + sin²t), y = a·sin t·cos t / (1 + sin²t)
  沿法向偏移 ±w/2 得到带宽度的闭合轮廓，再填充（不用 stroke）。

这样是**纯填充路径**，任何 ROM 都能渲染。
"""

from __future__ import annotations

import math
import os

import cairosvg

RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
REPORT = r"D:\dsh-go\reports"

GRID = 24.0
PAD = 2.5
STROKE = 2.0
N = 180   # 采样点数


def lemniscate(t: float) -> tuple[float, float]:
    """双纽线，t ∈ [0, 2π)，返回单位尺度坐标。"""
    s = math.sin(t)
    c = math.cos(t)
    d = 1 + s * s
    return (c / d, s * c / d)


def build(g: float, pad: float, w: float) -> str:
    """构造带宽度的双纽线轮廓（外圈 + 内圈，evenOdd 挖空）。"""
    # 采样曲线
    pts = [lemniscate(2 * math.pi * i / N) for i in range(N)]

    # 缩放：曲线 x 范围约 [-1,1]，y 约 [-0.354, 0.354]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx0 = (max(xs) + min(xs)) / 2
    cy0 = (max(ys) + min(ys)) / 2
    span = max(max(xs) - min(xs), (max(ys) - min(ys)) * 1.9)
    scale = (g - pad * 2) / span

    def to_canvas(p):
        return (g / 2 + (p[0] - cx0) * scale, g / 2 + (p[1] - cy0) * scale)

    centre = [to_canvas(p) for p in pts]
    hw = w / 2

    # 法向（用相邻点差分）
    def normal(i):
        a = centre[(i - 1) % N]
        b = centre[(i + 1) % N]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        return (-dy / ln, dx / ln)

    outer = []
    inner = []
    for i in range(N):
        nx, ny = normal(i)
        px, py = centre[i]
        outer.append((px + nx * hw, py + ny * hw))
        inner.append((px - nx * hw, py - ny * hw))

    def path(pts_list):
        d = [f"M {pts_list[0][0]:.3f},{pts_list[0][1]:.3f}"]
        for x, y in pts_list[1:]:
            d.append(f"L {x:.3f},{y:.3f}")
        d.append("Z")
        return " ".join(d)

    # evenOdd：外轮廓 + 反向内轮廓 = 环带
    inner.reverse()
    return path(outer) + " " + path(inner)


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
        open(out.replace(".png", f"-{tag}.png"), "wb").write(png)
    print(f"  预览 {out.replace('.png', '-big.png')}")


def main() -> int:
    d = build(GRID, PAD, STROKE)
    write_vector(
        os.path.join(RES, "drawable", "ic_stat_dsh.xml"),
        24, d,
        "Status-bar icon for all notifications: the infinity mark as a filled band "
        "(no stroke) so every ROM renders it. Small icons use alpha only.",
    )

    d108 = build(108.0, PAD * 108.0 / 24.0, STROKE * 108.0 / 24.0)
    write_vector(
        os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"),
        108, d108,
        "Themed-icon (Android 13+) layer: the infinity mark silhouette.",
    )

    preview(d, GRID, os.path.join(REPORT, "stat-lemniscate.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
