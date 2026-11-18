#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 manifest.json 里 rootfs 的哈希与大小
========================================

改名后 rootfs 重新打包，sha256 / bytes / tarSha256 都变了。
App 启动时会校验这些值，不更新会直接拒绝启动。
"""

import hashlib
import json
import os
import sys

RT = r"D:\dsh-go\replica\runtime\out\arm64-v8a\assets\runtime"
MANIFEST = os.path.join(RT, "manifest.json")
ROOTFS = os.path.join(RT, "rootfs-arm64-v8a.tar.xz")
TAR = r"D:\dsh-go\_work\rootfs\rootfs-arm64-v8a.tar"


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def count_entries(tar_path: str) -> dict:
    import tarfile
    d = {"dir": 0, "file": 0, "symlink": 0}
    with tarfile.open(tar_path, "r:") as tf:
        for m in tf:
            if m.isdir():
                d["dir"] += 1
            elif m.issym():
                d["symlink"] += 1
            elif m.isreg():
                d["file"] += 1
    return d


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as f:
        man = json.load(f)

    old = {
        "rootfsSha256": man.get("rootfsSha256"),
        "rootfsBytes": man.get("rootfsBytes"),
        "tarSha256": man.get("tarSha256"),
        "uncompressedBytes": man.get("uncompressedBytes"),
    }

    man["rootfsSha256"] = sha256_file(ROOTFS)
    man["rootfsBytes"] = os.path.getsize(ROOTFS)

    if os.path.exists(TAR):
        man["tarSha256"] = sha256_file(TAR)
        man["uncompressedBytes"] = os.path.getsize(TAR)
        ents = count_entries(TAR)
        man["entries"] = ents
        print("tar 条目统计:", ents)

    # 改名后 runtimeVersion 里的指纹也该跟着变，避免与旧版本混为一谈
    rv = man.get("runtimeVersion", "")
    if "dsh-go" in rv or True:
        # 保持结构，只改品牌前缀部分
        man["runtimeVersion"] = rv.replace("dsh", "dshbianjie", 0)  # 不动，另行说明

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)

    print("=" * 66)
    print("manifest.json 已更新")
    print("=" * 66)
    for k in ("rootfsSha256", "rootfsBytes", "tarSha256", "uncompressedBytes"):
        print(f"  {k}")
        print(f"    旧: {old.get(k)}")
        print(f"    新: {man.get(k)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
