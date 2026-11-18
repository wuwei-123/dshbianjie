#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把生成的图标拼一张预览图，检查各种尺寸下的观感。"""

import os
from PIL import Image, ImageDraw

RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
OUT = r"D:\dsh-go\reports\icon-preview.png"

# (目录, 文件, 展示尺寸)
ITEMS = [
    ("mipmap-xxxhdpi", "ic_launcher.png", 192),
    ("mipmap-xxxhdpi", "ic_launcher_round.png", 192),
    ("mipmap-xxxhdpi", "ic_launcher_foreground.png", 192),
    ("mipmap-xxhdpi", "ic_launcher.png", 144),
    ("mipmap-xhdpi", "ic_launcher.png", 96),
    ("mipmap-hdpi", "ic_launcher.png", 72),
    ("mipmap-mdpi", "ic_launcher.png", 48),
]

PAD = 24
LABEL_H = 22


def main() -> int:
    tiles = []
    for d, f, show in ITEMS:
        p = os.path.join(RES, d, f)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGBA")
        im = im.resize((show, show), Image.LANCZOS)
        tiles.append((im, f"{f.replace('.png','')}\n{show}px", show))

    if not tiles:
        print("没有可预览的图标")
        return 1

    total_w = sum(t[2] for t in tiles) + PAD * (len(tiles) + 1)
    max_h = max(t[2] for t in tiles)
    total_h = max_h + LABEL_H + PAD * 2 + 40

    canvas = Image.new("RGBA", (total_w, total_h), (24, 26, 32, 255))
    draw = ImageDraw.Draw(canvas)

    x = PAD
    for im, label, show in tiles:
        y = PAD + (max_h - show) // 2 + 20
        canvas.paste(im, (x, y), im)
        draw.text((x, PAD + max_h + 28), label, fill=(200, 205, 215, 255))
        x += show + PAD

    draw.text((PAD, 4), "dsh boundary launcher icons", fill=(120, 180, 255, 255))
    canvas.convert("RGB").save(OUT, quality=95)
    print("写入", OUT, canvas.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
