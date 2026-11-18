#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
停用上游更新检查（二开专用）
============================

为什么必须做：
  App 的自动更新指向上游（dl.dshtui.com 镜像 + GitHub + 多个加速器）。
  它们发布的是官方 DSH Go。用户点「立即更新」会装回官方包，
  把二开版本覆盖掉 —— 包名不同时更糟：两个 App 并存，用户分不清哪个是自己的。

处理：
  1. updateDownloadOrigin 清空 -> 镜像源被跳过
  2. GitHub 仓库已是空串 -> API/页面/资源 URL 都拼不出有效地址
  3. 加速器列表清空 -> 不再尝试任何镜像
  4. beta 通道清空

结果：检查更新时找不到任何源，界面不弹「发现新版本」。
要在自己仓库发布时，把 UPDATE_* 换成自己的地址即可。
"""

import os
import re

P = r"D:\dsh-go\replica\app\lib\update\update_config.dart"

raw = open(P, encoding="utf-8").read()
orig = raw

# 1) 下载镜像源
raw = raw.replace(
    "const updateDownloadOrigin = 'https://dl.dshtui.com';",
    "const updateDownloadOrigin = '';",
)

# 2) 分享/镜像 origin
raw = raw.replace("const updateMirrorOrigin = '';", "const updateMirrorOrigin = '';")

# 3) 加速器列表：清空，避免回落到上游 release
raw = re.sub(
    r"(const updateMirrors = <UpdateMirror>\[).*?(\];)",
    r"\1\2",
    raw,
    flags=re.S,
)

if raw == orig:
    print("没有匹配到，检查常量名")
else:
    open(P, "w", encoding="utf-8").write(raw)
    print("已停用更新源")

print()
print("当前 update_config.dart 里的外链：")
for i, line in enumerate(open(P, encoding="utf-8").read().splitlines(), 1):
    s = line.strip()
    if s.startswith("//") or s.startswith("///") or s.startswith("*"):
        continue
    if "https://" in line or "http://" in line:
        print(f"  L{i}: {s}")
