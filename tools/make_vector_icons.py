#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把矢量图标（通知小图标 + 主题图标）换成无限符号
================================================

ic_stat_dsh.xml            24dp  状态栏/通知小图标，只取 alpha
ic_launcher_monochrome.xml 108dp Android 13+ 主题图标层

两者原本都是鲸鱼轮廓（尾巴 + 气泡）。新品牌是无限符号，
从 assets/brand/glyph-mono.svg 的路径重新生成，缩放到各自的 viewport。

注意：通知小图标是「单色 + 只看 alpha」的，
所以必须是实心填充路径，不能有渐变或描边。
"""

from __future__ import annotations

import os
import re

BRAND = r"D:\dsh-go\replica\app\assets\brand"
RES = r"D:\dsh-go\replica\app\android\app\src\main\res"


def read_svg_path(name: str) -> tuple[str, tuple[float, float, float, float]]:
    """从 glyph-mono.svg 取 path 与其包围盒。"""
    raw = open(os.path.join(BRAND, name), encoding="utf-8").read()
    m = re.search(r'<path[^>]*\bid="body"[^>]*\bd="([^"]+)"', raw)
    if not m:
        m = re.search(r'<path[^>]*\bd="([^"]+)"', raw)
    if not m:
        raise SystemExit(f"{name}: 找不到 path")
    d = m.group(1)

    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]
    xs, ys = nums[0::2], nums[1::2]
    return d, (min(xs), min(ys), max(xs), max(ys))


def transform_path(d: str, box, target: float, pad: float) -> str:
    """把路径平移缩放到 target x target 的画布，四周留 pad。

    源在 108 网格里，目标可能是 24dp 或 108dp。
    """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        raise SystemExit("包围盒无效")

    avail = target - pad * 2
    scale = avail / max(w, h)
    # 居中
    off_x = (target - w * scale) / 2 - x0 * scale
    off_y = (target - h * scale) / 2 - y0 * scale

    out = []
    for m in re.finditer(r"([MLZ])([^MLZ]*)", d):
        cmd, body = m.group(1), m.group(2)
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", body)]
        if cmd == "Z":
            out.append("Z")
            continue
        pairs = []
        for i in range(0, len(nums) - 1, 2):
            px = nums[i] * scale + off_x
            py = nums[i + 1] * scale + off_y
            pairs.append(f"{px:.3f},{py:.3f}")
        out.append(cmd + " ".join(pairs))
    return " ".join(out)


def write_vector(path: str, size: int, path_data: str, comment: str) -> None:
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
        android:pathData="{path_data}" />
</vector>
'''
    open(path, "w", encoding="utf-8").write(xml)
    print(f"  写入 {os.path.basename(path)}  ({size}dp, path {len(path_data)} 字符)")


def main() -> int:
    d, box = read_svg_path("glyph-mono.svg")
    print(f"源路径: {len(d)} 字符, 包围盒 {box}")

    # 1) 通知小图标：24dp，四周各留 1.6dp（状态栏图标要留白，否则顶到边）
    p24 = transform_path(d, box, 24.0, 1.6)
    write_vector(
        os.path.join(RES, "drawable", "ic_stat_dsh.xml"),
        24,
        p24,
        "Status-bar icon for all notifications: the infinity glyph. "
        "Small icons are drawn from alpha only.",
    )

    # 2) 主题图标层：108dp，安全区 72，四周留 18
    p108 = transform_path(d, box, 108.0, 20.0)
    write_vector(
        os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"),
        108,
        p108,
        "Themed-icon (Android 13+) layer: the infinity glyph silhouette, "
        "same placement as mipmap/ic_launcher_foreground.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
