#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用浅底线稿生成状态栏通知图标
============================

新源图特点：**白底 + 深色细线条**，正好是通知小图标需要的形态
（通知图标只取 alpha，深色线条在浅底上抠出来就是清晰的细线）。

与之前深底图标相反，这次 alpha 要按「越暗越不透明」来算。
"""

from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image
from skimage import measure

RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
REPORT = r"D:\dsh-go\reports"
OBJ = os.path.expanduser(r"~\.dsh\attachments\v1\objects")

# 新图标 sha256
SHA = "2bef00ed908d7abbecb46c4f52f5f4e39fa50fe58b5ee7d1cfc013408a4ff078"
SRC = os.path.join(OBJ, SHA[:2], SHA)

GRID = 24.0      # 通知图标 24dp
WORK = 480       # 描摹工作分辨率
EPS = 0.6


def load_line_art() -> Image.Image:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    # 居中裁成正方形
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2, (w - side) // 2 + side, (h - side) // 2 + side))
    im = im.resize((WORK, WORK), Image.LANCZOS)
    return im


def to_alpha(im: Image.Image) -> np.ndarray:
    """白底深线 -> alpha：越暗越不透明。"""
    arr = np.asarray(im, dtype=np.float32) / 255.0
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    # 白底 ~0.95+，线条 ~0.0-0.4
    a = np.clip((0.80 - lum) / (0.80 - 0.25), 0.0, 1.0)
    return a


def trace(alpha: np.ndarray, target: float, pad: float, min_frac: float) -> str:
    mask = alpha > 0.45
    padded = np.pad(mask.astype(np.uint8), 2, mode="constant")
    contours = measure.find_contours(padded, 0.5)
    if not contours:
        return ""

    def bbox_area(c):
        return (c[:, 0].max() - c[:, 0].min()) * (c[:, 1].max() - c[:, 1].min())

    big = max(bbox_area(c) for c in contours)
    contours = [c for c in contours if bbox_area(c) > big * min_frac]
    contours = sorted(contours, key=bbox_area, reverse=True)

    ys = np.concatenate([c[:, 0] for c in contours])
    xs = np.concatenate([c[:, 1] for c in contours])
    ymin, ymax = ys.min(), ys.max()
    xmin, xmax = xs.min(), xs.max()
    w = max(xmax - xmin, 1)
    h = max(ymax - ymin, 1)

    avail = target - pad * 2
    scale = avail / max(w, h)
    off_x = (target - w * scale) / 2
    off_y = (target - h * scale) / 2

    parts = []
    for c in contours:
        simp = measure.approximate_polygon(c, tolerance=EPS)
        if len(simp) < 4:
            continue
        pts = [
            ((p[1] - xmin) * scale + off_x, (p[0] - ymin) * scale + off_y)
            for p in simp
        ]
        seg = [f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"]
        for px, py in pts[1:]:
            seg.append(f"L {px:.2f},{py:.2f}")
        seg.append("Z")
        parts.append(" ".join(seg))
    return " ".join(parts)


def write_vector(path: str, size: float, d: str, comment: str) -> None:
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- {comment} -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{int(size)}dp"
    android:height="{int(size)}dp"
    android:viewportWidth="{size:g}"
    android:viewportHeight="{size:g}">
    <path
        android:fillColor="#FFFFFFFF"
        android:fillType="evenOdd"
        android:pathData="{d}" />
</vector>
'''
    open(path, "w", encoding="utf-8").write(xml)
    print(f"  写入 {os.path.basename(path)}  ({int(size)}dp, path {len(d)} 字符)")


def preview(d: str, size: float, out: str, px: int = 192) -> None:
    import cairosvg

    scale = px / size
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size:g} {size:g}">'
        f'<path fill="#ffffff" fill-rule="evenodd" d="{d}"/></svg>'
    )
    png = cairosvg.svg2png(
        bytestring=svg.encode(), output_width=px, output_height=px,
        background_color="#1b1f27",
    )
    open(out, "wb").write(png)
    print(f"  预览 {out}")


def main() -> int:
    if not os.path.exists(SRC):
        print("找不到源图:", SRC)
        return 2

    im = load_line_art()
    alpha = to_alpha(im)
    print(f"线条像素占比: {(alpha > 0.45).mean() * 100:.1f}%")

    # 通知图标：24dp，留 2dp 边
    d24 = trace(alpha, GRID, 2.0, 0.0008)
    if not d24:
        print("描摹失败")
        return 1
    write_vector(
        os.path.join(RES, "drawable", "ic_stat_dsh.xml"),
        GRID, d24,
        "Status-bar icon for all notifications: the infinity mark. "
        "Small icons are drawn from alpha only.",
    )
    preview(d24, GRID, os.path.join(REPORT, "stat-icon-final.png"))

    # 主题图标层：108dp，构图留白更大
    d108 = trace(alpha, 108.0, 18.0, 0.0008)
    if d108:
        write_vector(
            os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"),
            108.0, d108,
            "Themed-icon (Android 13+) layer: the infinity mark silhouette.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
