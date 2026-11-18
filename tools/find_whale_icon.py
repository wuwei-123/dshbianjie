#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 APK 里找疑似旧鲸鱼图标（蓝紫调 + 圆角透明）。"""

import io
import sys
import zipfile

import numpy as np
from PIL import Image

APK = r"D:\dsh-go\replica\app\build\app\outputs\flutter-apk\app-arm64-release.apk"

hits = []
with zipfile.ZipFile(APK) as z:
    for n in z.namelist():
        if not n.startswith("res/") or not n.endswith(".png"):
            continue
        try:
            im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
        except Exception:
            continue
        if im.size[0] < 40:
            continue
        a = np.asarray(im)
        rgb = a[:, :, :3].astype(float)
        alpha = a[:, :, 3]
        opaque = alpha > 200
        if opaque.sum() < 100:
            continue
        mean = rgb[opaque].mean(axis=0)
        corner = float(alpha[:4, :4].mean())
        # 蓝紫调：B 明显大于 R；且四角较透明（圆角/圆形图标）
        if mean[2] > mean[0] + 20 and corner < 80:
            hits.append((n, im.size, tuple(int(x) for x in mean), int(corner)))

print("疑似旧图标:", len(hits))
for h in hits[:15]:
    print(f"   {h[0]}  {h[1]}  mean={h[2]}  cornerAlpha={h[3]}")

# 同时列出所有 432x432 / 192x192 的，逐个看中心色
print()
print("192x192 与 432x432 图标清单（中心色）：")
with zipfile.ZipFile(APK) as z:
    for n in z.namelist():
        if not n.startswith("res/") or not n.endswith(".png"):
            continue
        try:
            im = Image.open(io.BytesIO(z.read(n))).convert("RGB")
        except Exception:
            continue
        if im.size in [(192, 192), (432, 432)]:
            w, h = im.size
            print(f"   {n} {im.size} 中心={im.getpixel((w//2, h//2))} 角={im.getpixel((2,2))}")
