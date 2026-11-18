#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从新图标提取无限符号，产出品牌 SVG 母版
=========================================

品牌标记是矢量路径（assets/brand/*.svg -> tool/make_brand_mark.py
-> lib/ui/shell/brand_glyph.g.dart）。换标记必须换 SVG 母版，
直接塞位图会让侧栏/关于页的小尺寸发糊。

流程：
  1. 裁出无限符号区域
  2. 用感知亮度算 alpha（亮线条不透明，深色底透明）
  3. skimage.measure.find_contours 提有序闭合轮廓（不是散乱线段）
  4. Douglas-Peucker 简化到几百点
  5. 输出 108 网格的 SVG

产出：
  assets/brand/glyph-light.svg   浅色页面
  assets/brand/glyph-dark.svg    深色页面
  assets/brand/glyph-mono.svg    单色
  assets/brand/tile.svg          带底板的方图标
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image
from skimage import measure

SRC = r"D:\dsh-go\assets-in\icon-final.png"
BRAND = r"D:\dsh-go\replica\app\assets\brand"
REPORT = r"D:\dsh-go\reports"

# 无限符号在源图中的范围（占边长比例）
BOX = (0.20, 0.22, 0.80, 0.74)

GRID = 108.0        # launcher 网格
GLYPH_SPAN = 46.0   # 符号在 108 网格里的宽度
# 轮廓提取的工作分辨率
WORK = 512
# 简化容差（工作像素）
EPS = 1.2


def extract_rgb_alpha(src: Image.Image) -> Image.Image:
    """把「深色底 + 亮线条」的图标转成可矢量化的形状。

    注意极性：源图里**亮**的是无限符号，**暗**的是底板。
    所以 alpha = 亮度，亮度高 -> 不透明。搞反了就会得到一张负形。
    """
    w, h = src.size
    x0, y0, x1, y1 = BOX
    crop = src.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1))).convert("RGB")
    crop = crop.resize((WORK, WORK), Image.LANCZOS)
    arr = np.asarray(crop, dtype=np.float32) / 255.0

    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]

    # 实测：底板亮度 ~0.05-0.12，符号线条 ~0.45-1.0
    lo, hi = 0.22, 0.55
    t = np.clip((lum - lo) / (hi - lo), 0.0, 1.0)

    blue = np.array([0.40, 0.62, 1.00], dtype=np.float32)
    white = np.array([1.00, 1.00, 1.00], dtype=np.float32)
    rgb = blue * (1 - t[..., None]) + white * t[..., None]

    out = np.zeros((WORK, WORK, 4), dtype=np.uint8)
    out[:, :, :3] = (rgb * 255).astype(np.uint8)
    out[:, :, 3] = (np.clip(t ** 0.9, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def trace_path(mask: np.ndarray, span: float) -> tuple[str, int, float]:
    """找轮廓 -> 简化 -> 变成 SVG path。

    无限符号是「环形线条」：每个环都是外圈 + 内孔。
    所以必须保留多层轮廓，并用 evenodd 填充规则 —— 外圈填实、内圈挖空。
    只取外轮廓会得到实心块（丢掉环形的质感）。
    """
    padded = np.pad(mask.astype(np.uint8), 2, mode="constant")
    contours = measure.find_contours(padded, 0.5)

    if not contours:
        return "", 0, 1.0

    def bbox(c):
        return (c[:, 0].min(), c[:, 1].min(), c[:, 0].max(), c[:, 1].max())

    def area_of(c):
        y0, x0, y1, x1 = bbox(c)
        return (y1 - y0) * (x1 - x0)

    # 丢掉极小的噪点（小于整体 0.15% 的包围盒）
    big = max(area_of(c) for c in contours)
    contours = [c for c in contours if area_of(c) > big * 0.0015]
    contours = sorted(contours, key=area_of, reverse=True)

    # 全局外接框（取最大的那条的外框，保证居中稳定）
    ymin, xmin, ymax, xmax = bbox(contours[0])
    w = max(xmax - xmin, 1)
    h = max(ymax - ymin, 1)

    scale = span / max(w, h)
    off_x = (GRID - w * scale) / 2
    off_y = (GRID - h * scale) / 2

    parts = []
    total_pts = 0
    for c in contours:
        simp = measure.approximate_polygon(c, tolerance=EPS)
        if len(simp) < 4:
            continue
        total_pts += len(simp)
        pts = [((p[1] - xmin) * scale + off_x, (p[0] - ymin) * scale + off_y) for p in simp]
        seg = [f"M{pts[0][0]:.2f} {pts[0][1]:.2f}"]
        for px, py in pts[1:]:
            seg.append(f"L{px:.2f} {py:.2f}")
        seg.append("Z")
        parts.append(" ".join(seg))

    return " ".join(parts), total_pts, w / h


def main() -> int:
    if not os.path.exists(SRC):
        print("找不到源图:", SRC)
        return 2

    src = Image.open(SRC).convert("RGB")
    rgba = extract_rgb_alpha(src)
    rgba.save(os.path.join(REPORT, "glyph-extracted.png"))
    print("抠图:", rgba.size, "->", os.path.join(REPORT, "glyph-extracted.png"))

    alpha = np.asarray(rgba)[:, :, 3].astype(np.float32) / 255.0
    mask = alpha > 0.35

    d, npts, ar = trace_path(mask, GLYPH_SPAN)
    if not d:
        print("轮廓提取失败")
        return 1
    print(f"轮廓点数: {npts}  宽高比: {ar:.3f}")
    print(f"path 长度: {len(d)} 字符")

    def wrap(stops: str, body: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID:g} {GRID:g}">\n'
            f"<defs>{stops}</defs>\n"
            f'<path id="body" fill="url(#g)" fill-rule="evenodd" d="{body}"/>\n'
            "</svg>\n"
        )

    grad = (
        '<linearGradient id="g" gradientUnits="userSpaceOnUse" '
        'x1="24" y1="42" x2="84" y2="66">'
        '<stop offset="0" stop-color="#5C8BFF"/>'
        '<stop offset="0.45" stop-color="#9FC0FF"/>'
        '<stop offset="1" stop-color="#F2F7FF"/></linearGradient>'
    )
    mono = (
        '<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#000000"/>'
        '<stop offset="1" stop-color="#000000"/></linearGradient>'
    )

    os.makedirs(BRAND, exist_ok=True)
    for name in ("glyph-light.svg", "glyph-dark.svg"):
        p = os.path.join(BRAND, name)
        open(p, "w", encoding="utf-8").write(wrap(grad, d))
        print("写入", p)

    p = os.path.join(BRAND, "glyph-mono.svg")
    open(p, "w", encoding="utf-8").write(wrap(mono, d))
    print("写入", p)

    # tile.svg：符号叠在深色圆角底板上（108 网格里取 18..90 的 72 单位可见区）
    tile_grad = (
        '<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="24" y1="42" x2="84" y2="66">'
        '<stop offset="0" stop-color="#7FA6FF"/>'
        '<stop offset="0.45" stop-color="#C0D6FF"/>'
        '<stop offset="1" stop-color="#FFFFFF"/></linearGradient>'
        '<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="18" y1="18" x2="90" y2="90">'
        '<stop offset="0" stop-color="#171C27"/>'
        '<stop offset="1" stop-color="#0A0D13"/></linearGradient>'
    )
    squircle = (
        "M34.58 18C31.39 18.13 29.27 18.57 27.14 19.54C23.87 21.03 21.03 23.87 19.54 27.14"
        "C18.57 29.27 18.13 31.39 18 34.58L18 73.42C18.13 76.61 18.57 78.73 19.54 80.86"
        "C21.03 84.13 23.87 86.97 27.14 88.46C29.27 89.43 31.39 89.87 34.58 90"
        "L73.42 90C76.61 89.87 78.73 89.43 80.86 88.46C84.13 86.97 86.97 84.13 88.46 80.86"
        "C89.43 78.73 89.87 76.61 90 73.42L90 34.58C89.87 31.39 89.43 29.27 88.46 27.14"
        "C86.97 23.87 84.13 21.03 80.86 19.54C78.73 18.57 76.61 18.13 73.42 18Z"
    )
    tile = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="18 18 72 72">\n'
        f"<defs>{tile_grad}</defs>\n"
        f'<path id="tile" fill="url(#bg)" d="{squircle}"/>\n'
        f'<path id="body" fill="url(#g)" fill-rule="evenodd" d="{d}"/>\n'
        "</svg>\n"
    )
    p = os.path.join(BRAND, "tile.svg")
    open(p, "w", encoding="utf-8").write(tile)
    print("写入", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
