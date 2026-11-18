#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自检：确认 rename_all 的替换规则对关键路径生效，且不误伤保护项。"""

import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "ra", r"D:\dsh-go\replica\tools\rename_all.py"
)
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)


def map_path(p: str) -> str:
    out = p
    for rx, repl in ra.PATH_RULES:
        out, _ = ra.apply_rule(out, rx, repl)
    return out


def full(line: str) -> str:
    out, _ = ra.transform_line(line)
    return out


PATH_CASES = [
    ("opt/dsh-go/dsh-go-bridge/lib/index.js", "opt/dshbianjie/dshbianjie-bridge/lib/index.js"),
    ("etc/dsh-app/runtime.json", "etc/dshbianjie/runtime.json"),
    ("/opt/dsh-go/dsh-go-bridge", "/opt/dshbianjie/dshbianjie-bridge"),
    ("assets/skills/dsh-go-plugin/SKILL.md", "assets/skills/dshbianjie-plugin/SKILL.md"),
]

LINE_CASES = [
    # (输入, 期望包含, 说明)
    ("<string name=\"app_name\">DSH Go</string>", "dsh边界", "品牌名"),
    ("const version = '1.0.15';", "0.1.0", "版本号"),
    ("import io.github.ccch1mneyyy.dsh_app.MainActivity", "com.dshbianjie.app", "包名"),
    ("https://github.com/ccch1mneyyy/dsh-go", "", "仓库链接应清空"),
    # 品牌名只该在「给人看」的地方替换
    ("# dsh边界 欢迎", "dsh边界", "已是新名应保持"),
]

# 代码标识符：绝不能变成中文
IDENT_CASES = [
    ("final dshGo = value['dshGo'] is Map ? value['dshGo'] as Map : const {};", "dshGo"),
    ("const m = pkgJson.dshGo;", "dshGo"),
    ("ctx.dshGo.readPickedFile(file.handle)", "dshGo"),
    ("const zh = await get(`/dshGo/v1/contributions`)", "dshGo"),
    ("Object? dshGo,", "dshGo"),
    ("/** The `.dshGo` text inside a hosted blob */", ".dshGo"),
]

# 必须保持原样的
PROTECT_CASES = [
    ("opt/dsh/node_modules/@deepseek-ai/dsh-goal/lib/index.js", "DSH 官方插件包"),
    ("/usr/local/bin/dsh", "DSH 引擎本体"),
    ("export DSH_GO_RUNTIME_ROOT=/x", "环境变量"),
    ("class DshGoBridge", "Kotlin 类名"),
    ("dsh-session-persistence-jsonl/lib/dsh-go-deletion.mjs", "dsh 官方文件"),
]


def main() -> int:
    ok = True
    print("=" * 74)
    print("路径替换")
    print("=" * 74)
    for src, want in PATH_CASES:
        got = map_path(src)
        good = got == want
        ok &= good
        print(f"  [{'OK' if good else 'FAIL'}] {src}")
        print(f"        -> {got}")
        if not good:
            print(f"        期望 {want}")

    print()
    print("=" * 74)
    print("行内替换")
    print("=" * 74)
    for src, want, label in LINE_CASES:
        got = full(src)
        good = (want in got) if want else (("ccch1mneyyy" not in got) and ("github.com" not in got))
        ok &= good
        print(f"  [{'OK' if good else 'FAIL'}] {label}: {src}")
        print(f"        -> {got!r}")

    print()
    print("=" * 74)
    print("保护项（必须不变）")
    print("=" * 74)
    for src, label in PROTECT_CASES:
        got = map_path(src) if "/" in src else full(src)
        good = got == src or ("dsh-go" in got)
        # 对 @deepseek-ai 与 /usr/local/bin/dsh 必须完全不变
        if "@deepseek-ai" in src or "/usr/local/bin/dsh" in src:
            good = got == src
        ok &= good
        print(f"  [{'OK' if good else 'FAIL'}] {label}: {src}")
        if got != src:
            print(f"        -> {got}")

    print()
    print("=" * 74)
    print("代码标识符（绝不能变成中文）")
    print("=" * 74)
    for src, want in IDENT_CASES:
        got = full(src)
        good = (want in got) and ("dsh边界" not in got.split("//")[0].split("/**")[0])
        ok &= good
        print(f"  [{'OK' if good else 'FAIL'}] {src[:66]}")
        print(f"        -> {got[:96]}")

    print()
    print("=" * 74)
    print("结论:", "全部通过" if ok else "有失败项，不要执行")
    print("=" * 74)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
