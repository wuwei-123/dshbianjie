#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试：捕获组展开 / 标识符完整性
====================================

之前踩过的坑：
  1. m.expand 没做，repl 里的 \\1 被当成字面量写进源码
     -> `dshbianjie\\1` 出现在几百个文件里，代码全废
  2. 品牌名规则误伤代码标识符
     -> `dshGo` 变成中文，编译不过
  3. 协议路径与客户端不同步
     -> App 连不上 bridge

本测试锁死这三类。
"""

import importlib.util
import sys

BASE = r"D:\dsh-go\replica\tools"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rp = load("rp", BASE + r"\rename_protocol.py")
ra = load("ra", BASE + r"\rename_all.py")

FAILS = []


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILS.append(label)
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"        got : {got!r}")
        print(f"        want: {want!r}")


def check_in(label, got, needle):
    ok = needle in got
    if not ok:
        FAILS.append(label)
    print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"        got: {got!r}")
        print(f"        需包含: {needle!r}")


def main() -> int:
    print("=" * 78)
    print("1. 捕获组必须展开（不能出现字面量 \\1）")
    print("=" * 78)
    cases = [
        # 复合标识符：dshGoPanel -> dshbianjiePanel
        ("final x = Slots.dshGoPanel;", "dshbianjiePanel"),
        ("window.__dshGoIsland.init(cfg)", "__dshbianjieIsland"),
        ("class DshGoContributions {}", "DshbianjieContributions"),
        ("final DshGoScope scope;", "DshbianjieScope"),
    ]
    for src, want in cases:
        got, _ = rp.transform(src)
        check_in(f"展开 {src[:40]}", got, want)
        if "\\1" in got:
            FAILS.append("字面量 \\1 泄漏: " + src)
            print("        !! 出现字面量 \\1")

    print()
    print("=" * 78)
    print("2. 协议路径两端一致")
    print("=" * 78)
    proto = [
        ('const PREFIX = "/dsh-go";', 'const PREFIX = "/dshbianjie";'),
        ('const path = "/dsh-go/v1/inventory";', '"/dshbianjie/v1/inventory"'),
        ("const CANARY = '/dsh-go-guard-canary';", "'/dshbianjie-guard-canary'"),
        ("const STREAM_PATH = '/dsh-go/v1/stream';", "'/dshbianjie/v1/stream'"),
        ('Symbol.for("dsh-go.guarded")', '"dshbianjie.guarded"'),
        ("const ptr = `/dshGo/capabilities`", "/dshbianjie/capabilities"),
    ]
    for src, want in proto:
        got, _ = rp.transform(src)
        check_in(f"协议 {src[:44]}", got, want)

    print()
    print("=" * 78)
    print("3. 不能动的（DSH 官方 / 引擎本体）")
    print("=" * 78)
    keep = [
        "import '@deepseek-ai/dsh-goal';",
        "opt/dsh/node_modules/@deepseek-ai/dsh-app-boot",
        "exec /usr/local/bin/dsh web",
        "const PROOT = '/opt/dsh/direct/preload.mjs';",
        "dsh-session-persistence-jsonl/lib/x.mjs",
    ]
    for src in keep:
        got, _ = rp.transform(src)
        check(f"保留 {src[:44]}", got, src)

    print()
    print("=" * 78)
    print("4. Dart 包名同步")
    print("=" * 78)
    got, _ = rp.transform("import 'package:dsh_app/ui/theme/theme.dart';")
    check_in("package:dsh_app -> dshbianjie_app", got, "package:dshbianjie_app/")

    got, _ = rp.transform("name: dsh_app")
    check("pubspec name", got, "name: dshbianjie_app")

    print()
    print("=" * 78)
    print("结论:", "全部通过" if not FAILS else f"{len(FAILS)} 项失败")
    print("=" * 78)
    for f in FAILS:
        print("  FAIL:", f)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
