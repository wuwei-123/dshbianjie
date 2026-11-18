#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把改名后的 bridge 同步进 rootfs tar
====================================

为什么必须做：
  rootfs 里的 opt/dsh-go/dsh-go-bridge 是源码 runtime/bridge/dsh-go-bridge
  的**独立副本**。源码改了协议（/dsh-go/v1 -> /dshbianjie/v1），
  但 rootfs 里的副本还是旧的 —— App 按新路径请求，bridge 只认旧路径，连不上。

本脚本：
  1. 删掉 tar 里的旧 bridge 目录条目
  2. 用源码里的 dshbianjie-bridge 重新写入
  3. 同时改 opt/dsh-go -> opt/dshbianjie、etc/dsh-app -> etc/dshbianjie
"""

from __future__ import annotations

import io
import os
import sys
import tarfile

TAR = r"D:\dsh-go\_work\rootfs\rootfs-arm64-v8a.tar"
SRC_BRIDGE = r"D:\dsh-go\replica\runtime\bridge\dshbianjie-bridge"

OLD_BRIDGE_PREFIX = "opt/dsh-go/dsh-go-bridge"
NEW_BRIDGE_PREFIX = "opt/dshbianjie/dshbianjie-bridge"


def main() -> int:
    if not os.path.exists(TAR):
        print(f"找不到 {TAR}", file=sys.stderr)
        return 2
    if not os.path.isdir(SRC_BRIDGE):
        print(f"找不到源码 bridge {SRC_BRIDGE}", file=sys.stderr)
        return 2

    out = TAR + ".synced"
    kept = dropped = 0
    written = 0

    with tarfile.open(TAR, "r:") as src, tarfile.open(out, "w") as dst:
        for m in src:
            # 丢弃 rootfs 里的旧 bridge（会用源码版本重写）
            if m.name == OLD_BRIDGE_PREFIX or m.name.startswith(OLD_BRIDGE_PREFIX + "/"):
                dropped += 1
                continue

            # 路径改名
            name = m.name
            name = name.replace("opt/dsh-go", "opt/dshbianjie")
            name = name.replace("etc/dsh-app", "etc/dshbianjie")
            m.name = name

            if m.issym():
                m.linkname = (
                    m.linkname
                    .replace("opt/dsh-go", "opt/dshbianjie")
                    .replace("etc/dsh-app", "etc/dshbianjie")
                )

            # 目录/链接直接写
            if not m.isreg():
                dst.addfile(m)
                kept += 1
                continue

            # 普通文件：读入内容
            f = src.extractfile(m)
            data = f.read() if f else b""
            kept += 1

            # 文本内容里的路径与协议也改
            if b"\x00" not in data[:4096]:
                try:
                    t = data.decode("utf-8")
                    orig = t
                    t = t.replace("opt/dsh-go", "opt/dshbianjie")
                    t = t.replace("etc/dsh-app", "etc/dshbianjie")
                    t = t.replace("/opt/dsh-go", "/opt/dshbianjie")
                    t = t.replace("/etc/dsh-app", "/etc/dshbianjie")
                    t = t.replace("dsh-go-bridge", "dshbianjie-bridge")
                    # 协议
                    t = t.replace("/dsh-go/v1", "/dshbianjie/v1")
                    t = t.replace("/dsh-go-guard-canary", "/dshbianjie-guard-canary")
                    t = t.replace("/dsh-go-guard", "/dshbianjie-guard")
                    t = t.replace("dsh-go.guarded", "dshbianjie.guarded")
                    t = t.replace("/dsh-go/plugins", "/dshbianjie/plugins")
                    t = t.replace(".dsh-go-l2s-", ".dshbianjie-l2s-")
                    t = t.replace("/dshGo/", "/dshbianjie/")
                    t = t.replace('"/dsh-go"', '"/dshbianjie"')
                    if t != orig:
                        data = t.encode("utf-8")
                except UnicodeDecodeError:
                    pass

            fresh = tarfile.TarInfo(name=m.name)
            fresh.size = len(data)
            fresh.mode = m.mode
            fresh.uid = m.uid
            fresh.gid = m.gid
            fresh.uname = m.uname
            fresh.gname = m.gname
            fresh.mtime = m.mtime
            fresh.type = tarfile.REGTYPE
            dst.addfile(fresh, io.BytesIO(data))

        # 写入源码里的 bridge（新协议）
        for dirpath, dirnames, filenames in os.walk(SRC_BRIDGE):
            rel_dir = os.path.relpath(dirpath, SRC_BRIDGE).replace("\\", "/")
            arc_dir = NEW_BRIDGE_PREFIX if rel_dir == "." else f"{NEW_BRIDGE_PREFIX}/{rel_dir}"

            info = tarfile.TarInfo(name=arc_dir)
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.mtime = 1767225600
            info.uname = "root"
            info.gname = "root"
            dst.addfile(info)

            for fn in filenames:
                p = os.path.join(dirpath, fn)
                with open(p, "rb") as fh:
                    content = fh.read()
                arc = f"{arc_dir}/{fn}"
                ti = tarfile.TarInfo(name=arc)
                ti.size = len(content)
                ti.mode = 0o644
                ti.mtime = 1767225600
                ti.uname = "root"
                ti.gname = "root"
                ti.type = tarfile.REGTYPE
                dst.addfile(ti, io.BytesIO(content))
                written += 1

    print("=" * 66)
    print("bridge 同步完成")
    print("=" * 66)
    print(f"  tar 条目保留/改写 : {kept}")
    print(f"  旧 bridge 丢弃    : {dropped}")
    print(f"  新 bridge 写入    : {written} 个文件")
    print(f"  输出              : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
