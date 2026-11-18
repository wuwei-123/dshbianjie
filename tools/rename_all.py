#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量改名：包名 / 品牌 / 路径 / 署名 / 版本
==========================================

一次性做完，不分阶段。改完统一构建验证。

改名映射
--------
包名      io.github.ccch1mneyyy.dsh_app   ->  com.dshbianjie.app
品牌      DSH Go / DshGo / dshGo / DSHGO   ->  dsh边界
运行时    /opt/dsh-go                     ->  /opt/dshbianjie
          /etc/dsh-app                    ->  /etc/dshbianjie
          dsh-go-bridge                   ->  dshbianjie-bridge
          dsh-go-ui/plugin/guide/support/market -> dshbianjie-*
版本      1.0.15                          ->  0.1.0
署名      作者 / 社交 / 仓库链接            ->  删除

绝对不能动的
------------
  @deepseek-ai/dsh-goal         DSH 官方插件包，不是本品牌
  dsh-session-persistence-jsonl 里含 dsh-go 的文件名同理
  /opt/dsh 与 /usr/local/bin/dsh  DSH 引擎本体
  DSH_GO_* 环境变量 / DshGo* 类名  代码标识符

用法
----
  python tools/rename_all.py --dry-run
  python tools/rename_all.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = r"D:\dsh-go\replica"
ROOTFS_TAR = r"D:\dsh-go\_work\rootfs\rootfs-arm64-v8a.tar"

SKIP_DIRS = {
    "build", ".dart_tool", ".gradle", "node_modules", ".git",
    "pub-cache", ".idea", ".vscode", "_work", "_backup",
}

TEXT_EXTS = {
    ".kt", ".java", ".xml", ".dart", ".gradle", ".kts", ".properties",
    ".json", ".arb", ".yaml", ".yml", ".md", ".pro", ".txt", ".html",
    ".js", ".css", ".toml", ".cfg", ".ini", ".sh", ".mjs",
}

# ============================================================ 替换规则
# (优先级从高到低；先长后短，避免部分匹配)

# 1) 包名
PKG_RULES = [
    (re.compile(r"io\.github\.ccch1mneyyy\.dsh_app"), "com.dshbianjie.app"),
    (re.compile(r"io\.github\.ccch1mneyyy"), "com.dshbianjie"),
]

# 2) 运行时路径（必须在品牌替换之前，否则 dsh-go 会被品牌规则吃掉）
#
# 注意：这里**不包含** API 前缀 /dsh-go/v1 —— 那是 App 与 bridge 的通信协议，
# 改了两端对不上，插件/面板/伙伴全废。它由 PROTECT 保护。
PATH_RULES = [
    (re.compile(r"/opt/dsh-go(?=[/\s\"']|$)"), "/opt/dshbianjie"),
    (re.compile(r"(?<![\w/])opt/dsh-go(?=[/\s\"']|$)"), "opt/dshbianjie"),
    (re.compile(r"/etc/dsh-app(?=[/\s\"']|$)"), "/etc/dshbianjie"),
    (re.compile(r"(?<![\w/])etc/dsh-app(?=[/\s\"']|$)"), "etc/dshbianjie"),
    (re.compile(r"dsh-go-bridge"), "dshbianjie-bridge"),
    (re.compile(r"dsh-go-plugin"), "dshbianjie-plugin"),
    (re.compile(r"dsh-go-guide"), "dshbianjie-guide"),
    (re.compile(r"dsh-go-support"), "dshbianjie-support"),
    (re.compile(r"dsh-go-ui"), "dshbianjie-ui"),
    (re.compile(r"dsh-go-market"), "dshbianjie-market"),
    (re.compile(r"dsh-go-deletion"), "dshbianjie-deletion"),
]

# 3) 版本
VERSION_RULES = [
    (re.compile(r"\b1\.0\.15\b"), "0.1.0"),
]

# 4) 品牌名（放在路径之后）
#
# 关键约束：dshGo / DshGo 在本项目里是 **代码 API 标识符**，不是品牌名：
#   value['dshGo']            market 清单字段
#   ctx.dshGo.readPickedFile  插件 SDK 命名空间
#   /dshGo/v1/contributions   桥接 API 路径
#   .dshGo                    文件扩展名
#   pkgJson.dshGo             插件包清单字段
# 这些一律不能改，否则编译失败或运行时功能全废。
#
# 安全的品牌替换只针对：
#   带空格的 "DSH Go" / "Dsh Go"
#   全大写 "DSHGO" / "DSH-GO"
#   独立单词 "dsh-go"（前后不是字母数字、斜杠、连字符、点）
BRAND_RULES = [
    (re.compile(r"DSH\s+Go"), "dsh边界"),
    (re.compile(r"Dsh\s+Go"), "dsh边界"),
    (re.compile(r"\bDSHGO\b"), "dsh边界"),
    (re.compile(r"\bDSH-GO\b"), "dsh边界"),
    (re.compile(r"\bDsh-Go\b"), "dsh边界"),
    # 仅当 dsh-go 是独立词（前后无 / _ - . 字母数字）才替换
    (re.compile(r"(?<![\w/\-.])(dsh-go)(?![\w/\-.])"), "dsh边界"),
]

# 5) 署名（最后做，清得最狠）
ATTR_RULES = [
    (re.compile(r"https?://github\.com/ccch1mneyyy[\w\-/#?=&.]*"), ""),
    (re.compile(r"https?://ccch1mneyyy\.github\.io[\w\-/#?=&.]*"), ""),
    (re.compile(r"https?://x\.com/cccch1mneyyyy"), ""),
    (re.compile(r"https?://b23\.tv/\w+"), ""),
    (re.compile(r"https?://qm\.qq\.com/[\w/?=&.]*"), ""),
    (re.compile(r"https?://forum\.dshtui\.com[\w/?=&.]*"), ""),
    (re.compile(r"https?://go\.dshtui\.com[\w/?=&.]*"), ""),
    (re.compile(r"@cccch1mneyyyy"), ""),
    (re.compile(r"ccchimneyyy"), ""),
    (re.compile(r"ccch1mneyyy(?:/dsh-go(?:-market)?)?"), ""),
]

# ============================================================ 保护规则

# 这些 token 出现的位置不能动
PROTECT = [
    # DSH 官方包与引擎本体
    re.compile(r"@deepseek-ai/[\w@/.-]*"),
    re.compile(r"dsh-session-persistence-jsonl[\w/.-]*"),
    re.compile(r"/opt/dsh(?!bianjie)(?!-go)/(?!dsh-go)"),
    re.compile(r"/usr/local/bin/dsh\b"),
    re.compile(r"\bDSH_GO_[A-Z0-9_]+\b"),
    re.compile(r"\bDshGo[A-Z][A-Za-z0-9_]*\b"),
    re.compile(r"\bDshGoBridge\b"),
    re.compile(r"\bDSH_GO\b"),
    # 代码 API 标识符：本项目的插件 SDK 命名空间，不是品牌名
    re.compile(r"\bdshGo\b"),
    re.compile(r"\bDshGo\b"),
    re.compile(r"['\"]dshGo['\"]"),
    re.compile(r"\.dshGo\b"),
    re.compile(r"/dshGo/"),
    re.compile(r"pkgJson\.dshGo"),
    re.compile(r"ctx\.dshGo"),
    re.compile(r"\bdshGo\s*[:=]"),
    # 通信协议路径：App 与 bridge 的 wire format，改了两端对不上
    re.compile(r"/dsh-go/v1"),
    re.compile(r"/dsh-go-guard-canary"),
    re.compile(r"/dsh-go-guard"),
    re.compile(r"dsh-go\.guarded"),
    re.compile(r"/dsh-go/plugins"),
    re.compile(r"\.dsh-go-l2s-"),
]


def protected_spans(line: str) -> list[tuple[int, int]]:
    spans = []
    for rx in PROTECT:
        for m in rx.finditer(line):
            spans.append((m.start(), m.end()))
    return spans


def overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(not (span[1] <= s or span[0] >= e) for s, e in spans)


def apply_rule(line: str, rx: re.Pattern, repl: str) -> tuple[str, int]:
    """替换一行。

    repl 可能含 \\1 反向引用（复合标识符规则用到），必须用 m.expand(repl)。
    直接拼 repl 会把字面量 "\\1" 写进源码，把代码写坏。
    """
    spans = protected_spans(line)
    out = []
    last = 0
    n = 0
    for m in rx.finditer(line):
        if overlaps((m.start(), m.end()), spans):
            continue
        out.append(line[last:m.start()])
        out.append(m.expand(repl))
        last = m.end()
        n += 1
    if n == 0:
        return line, 0
    out.append(line[last:])
    return "".join(out), n


def transform_line(line: str) -> tuple[str, dict]:
    stats = {"pkg": 0, "path": 0, "version": 0, "brand": 0, "attr": 0}
    for rx, repl in PKG_RULES:
        line, n = apply_rule(line, rx, repl); stats["pkg"] += n
    for rx, repl in PATH_RULES:
        line, n = apply_rule(line, rx, repl); stats["path"] += n
    for rx, repl in VERSION_RULES:
        line, n = apply_rule(line, rx, repl); stats["version"] += n
    for rx, repl in BRAND_RULES:
        line, n = apply_rule(line, rx, repl); stats["brand"] += n
    for rx, repl in ATTR_RULES:
        line, n = apply_rule(line, rx, repl); stats["attr"] += n
    return line, stats


# ============================================================ 文件处理

def iter_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in TEXT_EXTS:
                yield os.path.join(dirpath, fn)


def rename_source_tree(root: str, dry: bool) -> dict:
    totals = {"files": 0, "pkg": 0, "path": 0, "version": 0, "brand": 0, "attr": 0}
    touched = []
    for p in iter_files(root):
        rel = os.path.relpath(p, root).replace("\\", "/")
        if "changelog" in rel.lower():
            continue
        try:
            raw = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, PermissionError):
            continue
        out = []
        local = {"pkg": 0, "path": 0, "version": 0, "brand": 0, "attr": 0}
        for line in raw.splitlines(keepends=True):
            nl, st = transform_line(line)
            out.append(nl)
            for k, v in st.items():
                local[k] += v
        s = sum(local.values())
        if s == 0:
            continue
        totals["files"] += 1
        for k, v in local.items():
            totals[k] += v
        touched.append((rel, s, local))
        if not dry:
            open(p, "w", encoding="utf-8").write("".join(out))
    return {"totals": totals, "touched": touched}


# ============================================================ rootfs

def rename_rootfs(tar_path: str, dry: bool) -> dict:
    """在 tar 内改名：条目路径 + 符号链接目标 + 文本文件内容。

    只改内容的原因：opt/dsh-go/dsh-go-bridge/lib/index.js 里硬编码了
    '/opt/dsh-go/dsh-go-bridge/...' 这样的自引用路径。只改目录名不改内容，
    运行时 require 会找不到模块，App 启动即崩。
    """
    import tarfile

    if not os.path.exists(tar_path):
        return {"error": f"找不到 {tar_path}"}

    out_path = tar_path + ".new"
    stats = {
        "total": 0,
        "renamed_entries": 0,
        "renamed_links": 0,
        "content_files": 0,
        "content_refs": 0,
    }
    sample = []
    content_sample = []

    def map_name(name: str) -> str:
        for rx, repl in PATH_RULES:
            name, _ = apply_rule(name, rx, repl)
        return name

    def map_content(data: bytes) -> tuple[bytes, int]:
        """对文件内容做同样的路径替换；二进制内容原样返回。"""
        if b"\x00" in data[:4096]:
            return data, 0
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return data, 0
        n = 0
        for rx, repl in PATH_RULES:
            text, k = apply_rule(text, rx, repl)
            n += k
        if n == 0:
            return data, 0
        return text.encode("utf-8"), n

    if dry:
        with tarfile.open(tar_path, "r:") as tf:
            for m in tf:
                stats["total"] += 1
                new = map_name(m.name)
                if new != m.name:
                    stats["renamed_entries"] += 1
                    if len(sample) < 8:
                        sample.append((m.name, new))
                if m.isreg() and m.name.startswith(("opt/dsh-go", "etc/dsh-app")):
                    f = tf.extractfile(m)
                    if f:
                        _, k = map_content(f.read())
                        if k:
                            stats["content_files"] += 1
                            stats["content_refs"] += k
                            if len(content_sample) < 8:
                                content_sample.append((m.name, k))
        return {**stats, "sample": sample, "content_sample": content_sample, "dry": True}

    with tarfile.open(tar_path, "r:") as src, tarfile.open(out_path, "w") as dst:
        for m in src:
            stats["total"] += 1

            # 用改名前的原始路径判断要不要改内容
            orig_name = m.name
            needs_content_fix = orig_name.startswith(("opt/dsh-go", "etc/dsh-app"))

            new_name = map_name(orig_name)
            if new_name != orig_name:
                stats["renamed_entries"] += 1
                if len(sample) < 8:
                    sample.append((orig_name, new_name))
            m.name = new_name

            if m.issym():
                new_link = map_name(m.linkname)
                if new_link != m.linkname:
                    stats["renamed_links"] += 1
                m.linkname = new_link

            # 数据只取一次：要么读进内存处理后重建条目，要么原样流转发
            if m.isreg():
                fileobj = src.extractfile(m)
                if fileobj is None:
                    dst.addfile(m)
                    continue
                if needs_content_fix:
                    new_raw, k = map_content(fileobj.read())
                    if k:
                        stats["content_files"] += 1
                        stats["content_refs"] += k
                        if len(content_sample) < 8:
                            content_sample.append((m.name, k))
                        # 重建条目：改 m.size 会与内部 offset_data 不一致，
                        # addfile 仍按旧长度读取，导致 unexpected end of data。
                        import copy, io
                        fresh = copy.copy(m)
                        fresh.size = len(new_raw)
                        fresh.offset_data = 0
                        fresh.pax_headers = {}
                        dst.addfile(fresh, io.BytesIO(new_raw))
                        continue
                    import io
                    dst.addfile(m, io.BytesIO(new_raw))
                    continue
                dst.addfile(m, fileobj)
                continue

            dst.addfile(m)

    return {
        **stats,
        "sample": sample,
        "content_sample": content_sample,
        "out": out_path,
    }


# ============================================================ main

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--tar", default=ROOTFS_TAR)
    ap.add_argument("--skip-rootfs", action="store_true")
    args = ap.parse_args(argv)

    dry = args.dry_run
    print(f"工程根: {args.root}")
    print(f"模式  : {'DRY-RUN' if dry else '执行'}")
    print()

    print("=" * 70)
    print("1. 源码文本改名")
    print("=" * 70)
    res = rename_source_tree(args.root, dry)
    t = res["totals"]
    print(f"  涉及文件  : {t['files']}")
    print(f"  包名      : {t['pkg']}")
    print(f"  运行时路径: {t['path']}")
    print(f"  版本号    : {t['version']}")
    print(f"  品牌名    : {t['brand']}")
    print(f"  署名清理  : {t['attr']}")
    print()
    print("  改动最多的 12 个文件：")
    for rel, n, loc in sorted(res["touched"], key=lambda x: -x[1])[:12]:
        print(f"    {n:>5}  {rel}")
    print()

    if not args.skip_rootfs:
        print("=" * 70)
        print("2. rootfs 内路径改名")
        print("=" * 70)
        r = rename_rootfs(args.tar, dry)
        if "error" in r:
            print(f"  {r['error']}")
        else:
            print(f"  总条目      : {r['total']}")
            print(f"  改名条目    : {r['renamed_entries']}")
            print(f"  改名链接目标: {r.get('renamed_links', 0)}")
            print(f"  改名内容文件: {r.get('content_files', 0)}"
                  f"  （引用 {r.get('content_refs', 0)} 处）")
            if r.get("sample"):
                print("  路径样例：")
                for a, b in r["sample"]:
                    print(f"    {a}")
                    print(f"      -> {b}")
            if r.get("content_sample"):
                print("  内容改动样例：")
                for name, n in r["content_sample"]:
                    print(f"    {n:>4} 处  {name}")
            if not dry:
                print(f"  写出: {r['out']}")
        print()

    if dry:
        print("DRY-RUN 结束，未改动任何文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
