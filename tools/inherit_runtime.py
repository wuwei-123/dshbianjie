#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从原版 APK 精确继承 runtime 资产
================================

runtime/out/ 是 runtime/build-runtime.sh 的产物目录，不随源码分发。
它里面不是"要重新发明的代码"，而是随包分发的静态运行时资产：

    assets/runtime/manifest.json          启动模板 + 全部哈希声明
    assets/runtime/rootfs-<abi>.tar.xz    Ubuntu 24.04 + Node + dsh 的 rootfs
    assets/runtime/licenses/*.txt         三个上游许可
    lib/<abi>/libproot.so                 Termux proot
    lib/<abi>/libproot-loader.so
    lib/<abi>/libtalloc.so
    lib/<abi>/libandroid-shmem.so

复刻要 1:1，就必须用原版的字节：重建的 rootfs 即使内容等价，
tar 成员顺序/时间戳/xz 参数不同也会让 sha256 不一致，而 manifest.json
把哈希钉死了，App 启动时会校验。

因此本脚本从原版 APK 抽出这 9 个条目，放进 build.gradle.kts 期望的
目录结构，再用 manifest.json 声明的 sha256 逐个核验。

产出：
    runtime/out/<abi>/assets/runtime/...
    runtime/out/<abi>/jniLibs/<abi>/*.so
    runtime/out/<abi>/build-report.json    来源记录（替代 build-runtime.sh 的报告）
    runtime/out/manifest.json              已构建 ABI 索引

用法：
    python tools/inherit_runtime.py ORIGINAL.apk [--abi arm64-v8a] [--out runtime/out]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone

# ---------------------------------------------------------------- 常量

# build-runtime.sh 产出的 jniLibs 内容（见其注释第 21 行）
JNI_LIBS = (
    "libproot.so",
    "libproot-loader.so",
    "libtalloc.so",
    "libandroid-shmem.so",
)

LICENSES = (
    "proot-COPYING.txt",
    "libtalloc-notice.txt",
    "libandroid-shmem-copyright.txt",
)


# ---------------------------------------------------------------- 工具

def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.2f}{unit}"
        n /= 1024.0
    return f"{n}B"


# ---------------------------------------------------------------- 主流程

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="从原版 APK 精确继承 runtime 资产")
    ap.add_argument("apk", help="原版 APK 路径")
    ap.add_argument("--abi", default="arm64-v8a")
    ap.add_argument("--out", default=None,
                    help="runtime/out 根目录，默认 <repo>/runtime/out")
    args = ap.parse_args(argv)

    apk = os.path.abspath(args.apk)
    if not os.path.isfile(apk):
        print(f"原版 APK 不存在: {apk}", file=sys.stderr)
        return 2

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    out_root = os.path.abspath(args.out or os.path.join(repo, "runtime", "out"))
    abi = args.abi

    abi_out = os.path.join(out_root, abi)
    assets_rt = os.path.join(abi_out, "assets", "runtime")
    assets_lc = os.path.join(assets_rt, "licenses")
    jni_out = os.path.join(abi_out, "jniLibs", abi)

    for d in (assets_rt, assets_lc, jni_out):
        os.makedirs(d, exist_ok=True)

    print(f"repo  : {repo}")
    print(f"apk   : {apk}")
    print(f"abi   : {abi}  ({human(os.path.getsize(apk))})")
    print(f"out   : {abi_out}")
    print()

    # 要抽的条目 -> 目标路径
    rootfs_name = f"rootfs-{abi}.tar.xz"
    plan: list[tuple[str, str]] = [
        ("assets/runtime/manifest.json",
         os.path.join(assets_rt, "manifest.json")),
        (f"assets/runtime/{rootfs_name}",
         os.path.join(assets_rt, rootfs_name)),
    ]
    for lic in LICENSES:
        plan.append((
            f"assets/runtime/licenses/{lic}",
            os.path.join(assets_lc, lic),
        ))
    for lib in JNI_LIBS:
        plan.append((f"lib/{abi}/{lib}", os.path.join(jni_out, lib)))

    # --- 抽取 ---------------------------------------------------
    print("== 从原版 APK 抽取 ==")
    with zipfile.ZipFile(apk) as zf:
        names = set(zf.namelist())
        for src, dst in plan:
            if src not in names:
                raise SystemExit(f"APK 里找不到条目: {src}")
            with zf.open(src) as fin, open(dst, "wb") as fout:
                shutil.copyfileobj(fin, fout, 1 << 20)
            print(f"  {src:<56} {human(os.path.getsize(dst)):>10}")

    # --- 核验 ---------------------------------------------------
    print()
    manifest_path = os.path.join(assets_rt, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    failures: list[str] = []

    print("== rootfs 归档 ==")
    rootfs_path = os.path.join(assets_rt, manifest["rootfs"])
    actual = sha256_file(rootfs_path)
    ok = actual == manifest["rootfsSha256"].lower()
    print(f"  [{'OK  ' if ok else 'FAIL'}] {manifest['rootfs']:<34} {actual}")
    if not ok:
        print(f"         期望 {manifest['rootfsSha256']}")
        failures.append("rootfs 哈希不符")
    size_ok = os.path.getsize(rootfs_path) == manifest["rootfsBytes"]
    print(f"         字节 {os.path.getsize(rootfs_path):,} / 声明 {manifest['rootfsBytes']:,}"
          f"  {'OK' if size_ok else 'MISMATCH'}")
    if not size_ok:
        failures.append("rootfs 字节数不符")

    print()
    print("== Termux 原生库 ==")
    for name, info in manifest["jniLibs"].items():
        p = os.path.join(jni_out, name)
        if not os.path.isfile(p):
            print(f"  [FAIL] {name:<34} 缺失")
            failures.append(f"{name} 缺失")
            continue
        actual = sha256_file(p)
        ok = actual == info["sha256"].lower()
        print(f"  [{'OK  ' if ok else 'FAIL'}] {name:<34} {actual}")
        if not ok:
            print(f"         期望 {info['sha256']}")
            failures.append(f"{name} 哈希不符")
        n = os.path.getsize(p)
        if n != info["bytes"]:
            print(f"         字节 {n} / 声明 {info['bytes']}")
            failures.append(f"{name} 字节数不符")

    print()
    print("== 许可文件（manifest 未声明哈希，只记大小）==")
    for lic in LICENSES:
        p = os.path.join(assets_lc, lic)
        if os.path.isfile(p):
            print(f"  [OK  ] {lic:<34} {os.path.getsize(p):>8,} B")
        else:
            print(f"  [FAIL] {lic:<34} 缺失")
            failures.append(f"{lic} 缺失")

    # --- 溯源记录 -----------------------------------------------
    report = {
        "schema": 1,
        "provenance": "inherited-from-original-apk",
        "sourceApk": apk,
        "sourceApkSha256": sha256_file(apk),
        "abi": abi,
        "runtimeVersion": manifest.get("runtimeVersion"),
        "dshVersion": manifest.get("dshVersion"),
        "nodeVersion": manifest.get("nodeVersion"),
        "ubuntuVersion": manifest.get("ubuntuVersion"),
        "prootVersion": manifest.get("prootVersion"),
        "rootfsBytes": manifest.get("rootfsBytes"),
        "rootfsSha256": manifest.get("rootfsSha256"),
        "note": (
            "rootfs 与 Termux 二进制取自原版 APK，已对 manifest.json 的 sha256 核验。"
            "本机未重建，保证与原版字节一致。runtime/build-runtime.sh 在这台机器上"
            "跑不了（需要 x86_64 Linux），而重建也会因 tar/xz 参数差异破坏哈希。"
        ),
        "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "failures": failures,
    }
    report_path = os.path.join(abi_out, "build-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print()
    print(f"写入 {report_path}")

    index_path = os.path.join(out_root, "manifest.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema": 1,
            "abis": [abi],
            "note": "index of built ABIs (replica: inherited from original APK)",
        }, f, ensure_ascii=False, indent=2)
    print(f"写入 {index_path}")

    print()
    if failures:
        print("核验未通过：")
        for x in failures:
            print(f"  - {x}")
        return 1

    print("全部核验通过：runtime 资产与原版字节一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
