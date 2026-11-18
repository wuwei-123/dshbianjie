#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 brand_glyph.g.dart（单路径版）
===================================

原生成器假设品牌标记是「尾巴 + 鳍 + 腹 + 气泡」四个分层路径（鲸鱼）。
新标记（无限符号）是单个路径，没有分层，所以这里生成一套简化结构：

    box / aspect / centroid   同样的测量语义，brand_mark.dart 的居中对齐照旧
    body                      唯一的形状（含内孔，evenodd 填充）
    tile + tileFill           启动页/关于页的方图标
    inkLight / inkDark        浅色与深色页面用的渐变

只改生成物，不改品牌语义：外面的 BrandMark 仍然按 box/centroid 对齐。
"""

from __future__ import annotations

import os
import re
import sys

APP = r"D:\dsh-go\replica\app"
BRAND = os.path.join(APP, "assets", "brand")
OUT = os.path.join(APP, "lib", "ui", "shell", "brand_glyph.g.dart")


def read(name: str) -> str:
    with open(os.path.join(BRAND, name), encoding="utf-8") as f:
        return f.read()


def paths(svg: str) -> dict[str, str]:
    """抽出 id -> d 的映射。"""
    out = {}
    for m in re.finditer(r'<path[^>]*\bid="([^"]+)"[^>]*\bd="([^"]+)"', svg):
        out[m.group(1)] = m.group(2)
    # 属性顺序可能反
    for m in re.finditer(r'<path[^>]*\bd="([^"]+)"[^>]*\bid="([^"]+)"', svg):
        out.setdefault(m.group(2), m.group(1))
    return out


def gradients(svg: str) -> dict[str, dict]:
    """抽出 linearGradient -> {x1,y1,x2,y2,stops}。"""
    out = {}
    for m in re.finditer(
        r'<linearGradient[^>]*\bid="([^"]+)"[^>]*>(.*?)</linearGradient>', svg, re.S
    ):
        gid, body = m.group(1), m.group(2)
        nums = {}
        for attr in ("x1", "y1", "x2", "y2"):
            am = re.search(attr + r'="([-\d.]+)"', m.group(0))
            nums[attr] = float(am.group(1)) if am else 0.0
        stops, cols = [], []
        for sm in re.finditer(
            r'<stop[^>]*offset="([\d.]+)"[^>]*stop-color="(#[0-9A-Fa-f]{6})"', body
        ):
            stops.append(float(sm.group(1)))
            cols.append(sm.group(2))
        if not stops:
            continue
        out[gid] = {**nums, "stops": stops, "colors": cols}
    return out


def parse_path(d: str) -> list[tuple[str, list[float]]]:
    """把 SVG path 拆成 (命令, 参数列表)，只支持 M/L/Z。"""
    ops = []
    for m in re.finditer(r"([MLZ])([^MLZ]*)", d):
        cmd = m.group(1)
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", m.group(2))]
        ops.append((cmd, nums))
    return ops


def dart_path(d: str) -> str:
    """生成 Dart Path 构造表达式。"""
    ops = parse_path(d)
    if not ops:
        return "Path()"
    lines = ["Path()"]
    for cmd, nums in ops:
        if cmd == "M" and len(nums) >= 2:
            lines.append(f"    ..moveTo({nums[0]:.3f}, {nums[1]:.3f})")
        elif cmd == "L" and len(nums) >= 2:
            lines.append(f"    ..lineTo({nums[0]:.3f}, {nums[1]:.3f})")
        elif cmd == "Z":
            lines.append("    ..close()")
    return "\n  ".join(lines)


def flatten_polys(d: str) -> list[list[tuple[float, float]]]:
    """把 path 展平成多边形，用于算 ink box 与重心。"""
    polys, cur = [], []
    for cmd, nums in parse_path(d):
        if cmd == "M" and len(nums) >= 2:
            if len(cur) >= 3:
                polys.append(cur)
            cur = [(nums[0], nums[1])]
        elif cmd == "L" and len(nums) >= 2:
            cur.append((nums[0], nums[1]))
        elif cmd == "Z":
            if len(cur) >= 3:
                polys.append(cur)
            cur = []
    if len(cur) >= 3:
        polys.append(cur)
    return polys


def area_centroid(poly) -> tuple[float, float, float]:
    a = cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-9:
        return 0.0, 0.0, 0.0
    return a, cx / (6 * a), cy / (6 * a)


def dart_gradient(g: dict) -> str:
    cols = ", ".join(f"Color(0xFF{c[1:]})" for c in g["colors"])
    stops = ", ".join(f"{s:.3f}" for s in g["stops"])
    return (
        "ui.Gradient.linear("
        f"Offset({g['x1']:.2f}, {g['y1']:.2f}), "
        f"Offset({g['x2']:.2f}, {g['y2']:.2f}), "
        f"const [{cols}], const [{stops}])"
    )


def main() -> int:
    light = read("glyph-light.svg")
    dark = read("glyph-dark.svg")
    tile = read("tile.svg")

    p = paths(light)
    pt = paths(tile)
    gl, gd, gt = gradients(light), gradients(dark), gradients(tile)

    if "body" not in p:
        sys.exit('glyph-light.svg: path id="body" missing')
    if "tile" not in pt:
        sys.exit('tile.svg: path id="tile" missing')

    ink = flatten_polys(p["body"])
    xs = [x for poly in ink for x, _ in poly]
    ys = [y for poly in ink for _, y in poly]
    box = (min(xs), min(ys), max(xs), max(ys))

    tot = cx = cy = 0.0
    for poly in ink:
        a, x, y = area_centroid(poly)
        tot += a
        cx += a * x
        cy += a * y
    if abs(tot) > 1e-9:
        cx, cy = cx / tot, cy / tot
    else:
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

    w, h = box[2] - box[0], box[3] - box[1]

    grad_light = gl.get("g") or next(iter(gl.values()))
    grad_dark = gd.get("g") or next(iter(gd.values()))
    grad_tile = gt.get("g") or grad_dark
    grad_bg = gt.get("bg")

    out = f'''// GENERATED by tool/make_brand_mark.py from assets/brand/glyph-light.svg,
// glyph-dark.svg and tile.svg. Do not edit; change the masters and run the tool.
//
// The dsh boundary glyph (infinity) in the launcher's 108 grid:
// the same placement as the themed launcher layer.

// dart format off
import 'dart:ui' as ui;
import 'dart:ui' show Color, Offset, Path, Rect, Shader;

/// Paths, gradients and measurements of the brand glyph (see `brand_mark.dart`).
abstract final class BrandGlyph {{
  /// The glyph's ink box.
  static const box = Rect.fromLTRB({box[0]:.3f}, {box[1]:.3f}, {box[2]:.3f}, {box[3]:.3f});

  /// Width / height of [box].
  static const aspect = {w / h:.6f};

  /// Visual centre: the area centroid of the ink, in the grid.
  static const centroid = Offset({cx:.4f}, {cy:.4f});

  /// The tile: the 72-unit visible square of the launcher icon.
  static const tileBox = Rect.fromLTWH(18, 18, 72, 72);

  /// The one shape: the infinity glyph (rings are holes, filled even-odd).
  static final Path body = {dart_path(p['body'])};

  /// The tile's rounded square.
  static final Path tile = {dart_path(pt['tile'])};

  static final Shader tileFill = {dart_gradient(grad_bg) if grad_bg else dart_gradient(grad_tile)};

  /// The glyph on light backgrounds, and on dark ones.
  static final Shader inkLight = {dart_gradient(grad_light)};
  static final Shader inkDark = {dart_gradient(grad_dark)};
  static final Shader inkTile = {dart_gradient(grad_tile)};

  /// Kept for callers written against the four-layer glyph (tail/fin/belly/bubble):
  /// this mark is one piece, so they all resolve to the same shape.
  static Path get fin => body;
  static Path get belly => body;
  static Path get bubble => body;
  static Shader get tailLight => inkLight;
  static Shader get tailDark => inkDark;
  static Shader get finLight => inkLight;
  static Shader get finDark => inkDark;
  static Shader get bellyLight => inkLight;
  static Shader get bellyDark => inkDark;
  static Shader get bubbleLight => inkLight;
  static Shader get bubbleDark => inkDark;
}}
'''

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(out)

    print(
        f"wrote {os.path.relpath(OUT, APP)}: box {box}, aspect {w / h:.4f}, "
        f"centroid ({cx:.3f}, {cy:.3f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
