#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏通知图标：专门做极简版
============================

问题：从图标位图描出来的无限符号有 500+ 个点。
24dp 的状态栏里只占约 24x24 物理像素，这么复杂的图形缩小后是一团黑影。

状态栏小图标（Notification small icon）的规范：
  - 单一 alpha 通道，系统只取透明度上色
  - 内容要极简：一根线、一个符号，2-3px 线宽
  - 四周留白，图形占 24dp 里约 18-20dp

做法：不用描出来的复杂路径，直接**几何绘制**一个干净的无限符号
（两条贝塞尔曲线组成的 8 字），线宽固定，缩到 24dp 依然清晰。
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw

RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
REPORT = r"D:\dsh-go\reports"

# 用 24 网格画，便于直接写 vector pathData
GRID = 24.0
STROKE = 2.0
# 留白：图形占 24 里的 3..21
PAD = 3.0


def build_path() -> str:
    """两条对称的外部弧组成 8 字，用矩形描边 -> 转成填充路径。

    直接描边（stroke）在 Android VectorDrawable 里可以用 strokeWidth，
    但通知图标更稳的是「填充路径」，所以这里用 stroke 属性写：
    VectorDrawable 支持 strokeColor / strokeWidth / strokeLineCap，
    小图标也能正确渲染。
    """
    # 8 字的四个控制点（左右两个环）
    # 用两段三次贝塞尔：从左上 -> 交叉点 -> 右下，再镜像回来
    cx, cy = GRID / 2, GRID / 2
    w = (GRID - PAD * 2) / 2      # 每个环的宽
    h = (GRID - PAD * 2) / 2.4    # 环的高（压扁一点更像无限符号）

    left_x = PAD
    right_x = GRID - PAD
    top_y = cy - h / 2
    bot_y = cy + h / 2

    # 一条连续路径：左环上半 -> 中间交叉 -> 右环上半 -> 右环下半 -> 交叉 -> 左环下半
    d = (
        f"M {left_x:.2f},{cy:.2f} "
        # 左环到中点（上弧）
        f"C {left_x:.2f},{top_y:.2f} "
        f"{(left_x + right_x) / 2:.2f},{top_y:.2f} "
        f"{cx:.2f},{cy:.2f} "
        # 中点到右环（上弧）
        f"C {(cx + right_x) / 2:.2f},{top_y:.2f} "
        f"{right_x:.2f},{top_y:.2f} "
        f"{right_x:.2f},{cy:.2f} "
        # 右环回来（下弧）
        f"C {right_x:.2f},{bot_y:.2f} "
        f"{(cx + right_x) / 2:.2f},{bot_y:.2f} "
        f"{cx:.2f},{cy:.2f} "
        # 中点回左环（下弧）
        f"C {(left_x + right_x) / 2 - (right_x - left_x) / 4:.2f},{bot_y:.2f} "
        f"{left_x:.2f},{bot_y:.2f} "
        f"{left_x:.2f},{cy:.2f} Z"
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
    print(f"  写入 {os.path.basename(path)}  ({size}dp, stroke {stroke})")


def render_preview(d: str, stroke: float, out: str, px: int = 128) -> None:
    """用 PIL 近似渲染，确认形状。"""
    scale = px / GRID
    im = Image.new("RGBA", (px, px), (32, 32, 32, 255))
    dr = ImageDraw.Draw(im)

    # 解析 M / C / Z
    import re
    cur = None
    pts = []
    for m in re.finditer(r"([MCZ])([^MCZ]*)", d):
        cmd, body = m.group(1), m.group(2)
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", body)]
        if cmd == "M":
            cur = (nums[0] * scale, nums[1] * scale)
            pts.append(cur)
        elif cmd == "C":
            # 三次贝塞尔采样
            p1 = (nums[0] * scale, nums[1] * scale)
            p2 = (nums[2] * scale, nums[3] * scale)
            p3 = (nums[4] * scale, nums[5] * scale)
            for i in range(1, 13):
                t = i / 12
                mt = 1 - t
                x = mt**3 * cur[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
                y = mt**3 * cur[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
                pts.append((x, y))
            cur = p3

    if len(pts) > 1:
        dr.line(pts, fill=(255, 255, 255, 255), width=max(1, int(stroke * scale)), joint="curve")
    im.resize((px * 2, px * 2), Image.LANCZOS).save(out)
    print(f"  预览 {out}")


def main() -> int:
    d = build_path()
    print("生成路径:", d[:90], "...")

    # 1) 24dp 状态栏图标
    write_vector(
        os.path.join(RES, "drawable", "ic_stat_dsh.xml"),
        24, d, STROKE,
        "Status-bar icon for all notifications: the infinity glyph, stroked so it "
        "stays legible at 24dp. Small icons are drawn from alpha only.",
    )

    # 2) 108dp 主题图标（放大也行，但主题层要实心，用粗 stroke 近似）
    write_vector(
        os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"),
        108, d, STROKE,
        "Themed-icon (Android 13+) layer: the infinity glyph silhouette.",
    )

    render_preview(d, STROKE, os.path.join(REPORT, "stat-icon-simple.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
