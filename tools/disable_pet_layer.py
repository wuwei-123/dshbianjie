#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
让 PetStage 不再渲染宠物（去掉 PetLayer）
========================================

chat_screen 用 PetStage 包住整个聊天页。它内部是：

    PetPerchScope -> Listener -> NotificationListener -> Stack[
        _FocusReporter(child: 页面内容),      <- 必须保留
        PetLayer(...)                        <- 宠物本体，去掉
    ]

只去掉 PetLayer，布局与交互链完全不变，宠物不再出现。

同时把 onPointerDown 里对宠物交互的调用去掉（没有宠物了，摸不到东西）。
"""

from __future__ import annotations

import os

APP = r"D:\dsh-go\replica\app"
LIB = os.path.join(APP, "lib")

P = os.path.join(LIB, "ui", "pets", "pet_stage.dart")

OLD = """            child: Stack(
              fit: StackFit.expand,
              children: [
                _FocusReporter(
                  sessionId: widget.sessionId,
                  child: KeyedSubtree(key: _content, child: widget.child),
                ),
                Positioned.fill(
                  child: PetLayer(registry: _registry, aside: widget.aside, scrolling: _scrolling, onReveal: _reveal),
                ),
              ],
            ),"""

NEW = """            child: Stack(
              fit: StackFit.expand,
              children: [
                _FocusReporter(
                  sessionId: widget.sessionId,
                  child: KeyedSubtree(key: _content, child: widget.child),
                ),
                // Pets are removed in this build: the stage keeps its layout
                // (perches, focus reporting) but paints nothing over the page.
              ],
            ),"""


def main() -> int:
    if not os.path.isfile(P):
        print("找不到", P)
        return 2
    raw = open(P, encoding="utf-8").read()
    if OLD not in raw:
        print("未匹配到 Stack 结构，检查文件")
        # 打印 Stack 附近内容帮助定位
        i = raw.find("PetLayer(")
        if i > 0:
            print("  PetLayer 出现位置上下文：")
            print(raw[max(0, i - 500) : i + 200])
        return 1

    raw = raw.replace(OLD, NEW, 1)

    # 去掉指针事件里的触摸调用（没有宠物可摸）
    touch = "onPointerDown: (_) => ref.read(petInteractionProvider.notifier).touch(),"
    if touch in raw:
        raw = raw.replace(touch, "onPointerDown: (_) {},", 1)
        print("  已去掉宠物触摸响应")

    open(P, "w", encoding="utf-8").write(raw)
    print("已去掉 PetLayer（宠物不再渲染）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
