#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改名脚本：包名 + 软件名
=======================

把 io.github.ccch1mneyyy.dsh_app  ->  com.dshbianjie.app
把 DSH Go                        ->  dsh边界

为什么要写脚本而不是手工改：涉及 538 个 Kotlin 文件、1181 处包名引用、
几百处界面文案、Kotlin 源码目录迁移、XML 全限定名、以及 Dart 侧常量。
手工必然漏。

替换边界（重要）：
  改   io.github.ccch1mneyyy.dsh_app    —— 包名，Android/Kotlin/Dart 全量
  改   DSH Go                          —— 品牌名，用户可见文案
  保留 https://github.com/ccch1mneyyy  —— 上游仓库地址，是事实信息
  保留 author / authorXHandle 等       —— 作者署名，AGPL 要求保留出处

用法：
    python tools/rename_app.py --dry-run     # 只看会改什么
    python tools/rename_app.py               # 实际执行
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------- 改名定义

OLD_PKG = "io.github.ccch1mneyyy.dsh_app"
NEW_PKG = "com.dshbianjie.app"

OLD_PKG_PATH = "io/github/ccch1mneyyy/dsh_app"   # 目录结构
NEW_PKG_PATH = "com/dshbianjie/app"

OLD_NAME = "DSH Go"
NEW_NAME = "dsh边界"

# 这些字符串里出现的 ccch1mneyyy 是上游仓库/作者，不是包名，不能动
PROTECTED_PATTERNS = (
    "github.com/ccch1mneyyy",
    "ccch1mneyyy.github.io",
    "ccch1mneyyy/dsh-go",
    "authorXHandle",
    "authorBilibiliName",
)

# 要处理的文件类型
TEXT_EXTS = {
    ".kt", ".java", ".xml", ".dart", ".gradle", ".kts", ".properties",
    ".json", ".arb", ".yaml", ".yml", ".md", ".pro", ".txt", ".html",
    ".js", ".css", ".toml", ".cfg", ".ini",
}

# 跳过的目录（构建产物 / 缓存 / 依赖）
SKIP_DIRS = {
    "build", ".dart_tool", ".gradle", "node_modules", ".git",
    "pub-cache", ".idea", ".vscode",
}

# 只做「软件名」替换、不做包名替换的路径前缀。
# docs/ 是上游的历史文档，改掉会伪造上游记录；改名只影响 App 本身。
NAME_ONLY_PREFIXES = ("docs", "site", "infra", "services", "market", "sdk", "examples")


# ---------------------------------------------------------------- 工具

def iter_text_files(root: Path):
    """遍历工程里的文本文件，跳过构建产物和依赖。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in TEXT_EXTS:
                yield p


def is_protected(line: str) -> bool:
    """这一行是否含有不该动的上游作者/仓库引用。"""
    return any(pat in line for pat in PROTECTED_PATTERNS)


def replace_in_text(text: str, old: str, new: str) -> tuple[str, int]:
    """逐行替换，跳过含受保护串的行。返回 (新文本, 替换次数)。"""
    out = []
    n = 0
    for line in text.splitlines(keepends=True):
        if old in line and not is_protected(line):
            out.append(line.replace(old, new))
            n += line.count(old)
        else:
            out.append(line)
    return "".join(out), n


# ---------------------------------------------------------------- 步骤

def step_move_sources(root: Path, dry: bool) -> list[str]:
    """迁移 Kotlin/Java 源码目录到新包路径。"""
    changed = []
    for lang in ("kotlin", "java"):
        for srcset in ("main", "test", "androidTest", "debug", "profile"):
            old_dir = root / "app" / "android" / "app" / "src" / srcset / lang / OLD_PKG_PATH
            new_dir = root / "app" / "android" / "app" / "src" / srcset / lang / NEW_PKG_PATH
            if not old_dir.is_dir():
                continue
            if dry:
                n = sum(1 for _ in old_dir.rglob("*") if _.is_file())
                print(f"  [dry] 迁移 {old_dir.relative_to(root)} -> {NEW_PKG_PATH}  ({n} 个文件)")
                changed.append(str(old_dir))
                continue

            new_dir.parent.mkdir(parents=True, exist_ok=True)
            if new_dir.exists():
                # 合并（通常不该发生，发生了说明之前跑过一半）
                for item in old_dir.iterdir():
                    shutil.move(str(item), str(new_dir / item.name))
                shutil.rmtree(old_dir, ignore_errors=True)
            else:
                shutil.move(str(old_dir), str(new_dir))
            # 清掉迁移后留下的空壳目录
            p = old_dir
            while p != root and p.is_dir() and not any(p.iterdir()):
                p.rmdir()
                p = p.parent
            print(f"  迁移 {srcset}/{lang}")
            changed.append(str(new_dir))
    return changed


def step_replace_text(root: Path, dry: bool) -> dict:
    """全量替换文本内容。

    docs/ 等外围目录只跳过「包名」替换（那些目录里不该出现 App 包名），
    「软件名」照常替换——它们是给这个 App 用的，但历史 changelog 保持原样。
    """
    stats = {"files": 0, "pkg": 0, "name": 0}
    touched = []
    for p in iter_text_files(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        in_periphery = any(rel.startswith(pre + "/") for pre in NAME_ONLY_PREFIXES)
        # changelog 是上游版本历史，不碰
        is_changelog = "changelog" in rel.lower()

        try:
            raw = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        new, n1 = (raw, 0)
        if not in_periphery:
            new, n1 = replace_in_text(raw, OLD_PKG, NEW_PKG)

        n2 = 0
        if not is_changelog:
            new, n2 = replace_in_text(new, OLD_NAME, NEW_NAME)

        if n1 == 0 and n2 == 0:
            continue
        stats["files"] += 1
        stats["pkg"] += n1
        stats["name"] += n2
        touched.append((rel, n1, n2))
        if not dry:
            p.write_text(new, encoding="utf-8")
    return {"stats": stats, "touched": touched}


def step_gradle(root: Path, dry: bool) -> list[str]:
    """build.gradle.kts 的 namespace / applicationId（已由上一步覆盖，这里做确认）。"""
    f = root / "app" / "android" / "app" / "build.gradle.kts"
    if not f.exists():
        return []
    txt = f.read_text(encoding="utf-8")
    hits = []
    for key in ("namespace", "applicationId"):
        for m in re.finditer(rf'{key}\s*=\s*"([^"]+)"', txt):
            hits.append(f"{key} = {m.group(1)}")
    return hits


def step_manifest(root: Path, dry: bool) -> list[str]:
    """Manifest 里的 label 与全限定名（已由文本替换覆盖，这里做确认）。"""
    f = root / "app" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if not f.exists():
        return []
    txt = f.read_text(encoding="utf-8")
    out = []
    m = re.search(r'android:label="([^"]+)"', txt)
    if m:
        out.append(f"label = {m.group(1)}")
    out.append(f"残留旧包名: {txt.count(OLD_PKG)} 处")
    return out


# ---------------------------------------------------------------- 主流程

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="改名：包名 + 软件名")
    ap.add_argument("--root", default=None, help="工程根，默认脚本上一级")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not (root / "app" / "pubspec.yaml").exists():
        print(f"不是工程根（找不到 app/pubspec.yaml）: {root}", file=sys.stderr)
        return 2

    print(f"工程根: {root}")
    print(f"包名  : {OLD_PKG} -> {NEW_PKG}")
    print(f"软件名: {OLD_NAME} -> {NEW_NAME}")
    print(f"模式  : {'DRY-RUN（不改文件）' if args.dry_run else '实际执行'}")
    print()

    # 1) 目录迁移要先做：否则替换后的 package 声明会和新路径对不上
    print("== 1. 迁移 Kotlin/Java 源码目录 ==")
    moved = step_move_sources(root, args.dry_run)
    if not moved:
        print("  （没有需要迁移的目录，可能已迁移过）")
    print()

    # 2) 文本替换
    print("== 2. 替换文本内容 ==")
    res = step_replace_text(root, args.dry_run)
    s = res["stats"]
    print(f"  涉及文件: {s['files']}")
    print(f"  包名替换: {s['pkg']} 处")
    print(f"  软件名替换: {s['name']} 处")
    print()
    if res["touched"]:
        print("  改动最多的 10 个文件：")
        for path, n1, n2 in sorted(res["touched"], key=lambda x: -(x[1] + x[2]))[:10]:
            print(f"    {n1:>4} 包名 + {n2:>3} 软件名  {path}")
    print()

    # 3) 确认关键文件
    print("== 3. 确认关键配置 ==")
    for line in step_gradle(root, args.dry_run):
        print(f"  gradle: {line}")
    for line in step_manifest(root, args.dry_run):
        print(f"  manifest: {line}")
    print()

    if args.dry_run:
        print("DRY-RUN 结束，未改动任何文件。")
        return 0

    print("改名完成。下一步：")
    print("  cd app && flutter clean")
    print("  python tools/build_replica.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
