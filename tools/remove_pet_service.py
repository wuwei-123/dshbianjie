#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Manifest 移除桌宠悬浮窗服务
============================

PetOverlayService 是桌宠的原生前台服务。移除注册后：
  - 系统不会再为桌宠拉起进程
  - 悬浮窗不会出现
  - 代码仍在，回滚只需加回声明

同时保留 PetOverlayPlugin 等被 Dart 侧引用的类（避免编译错误）。
"""

from __future__ import annotations

import os
import re

P = r"D:\dsh-go\replica\app\android\app\src\main\AndroidManifest.xml"

# 精确匹配整个 service 块（含注释与 property）
BLOCK = re.compile(
    r"\n\s*<!-- Keeps the floating pet's process up[^>]*-->\s*"
    r"<service\s+android:name=\"\.pet\.PetOverlayService\"[\s\S]*?</service>\n",
    re.S,
)


def main() -> int:
    raw = open(P, encoding="utf-8").read()
    m = BLOCK.search(raw)
    if not m:
        print("未匹配到 PetOverlayService 块")
        # 退化：按行删除
        lines = raw.splitlines(keepends=True)
        out = []
        skip = 0
        for i, line in enumerate(lines):
            if ".pet.PetOverlayService" in line:
                # 往回找到 <service 开头
                j = len(out) - 1
                while j >= 0 and "<service" not in out[j]:
                    j -= 1
                if j >= 0:
                    del out[j:]
                skip = 1
                continue
            if skip:
                if "</service>" in line:
                    skip = 0
                continue
            out.append(line)
        raw = "".join(out)
        open(P, "w", encoding="utf-8").write(raw)
        print("已用逐行方式移除")
        return 0

    raw = raw[: m.start()] + "\n" + raw[m.end() :]
    open(P, "w", encoding="utf-8").write(raw)
    print("已移除 PetOverlayService 声明")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
