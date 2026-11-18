#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成发布签名密钥（密码由你自己输入，不落盘明文除外 key.properties）
================================================================

为什么必须自己设：
  Android 的签名密钥一旦用于发布，就永久绑定这个应用 —— 换密钥需要用户
  先卸载再装（数据全丢），上架渠道更不可能。所以密码强度只由你决定。

用法（在你的终端里运行，会提示输入密码）：
    python tools/make-release-key.py

它做三件事：
  1. 交互式让你输入两次密码（不回显、不留 shell 历史）
  2. 用 keytool 生成 4096 位 RSA / 10000 天有效期的密钥
  3. 写 app/android/key.properties，并把原临时密钥改名留档

安全约定：
  - showFile / keyAlias 写进 key.properties（这两个不是秘密）
  - 两个密码也写进 key.properties —— Android Gradle 插件就是这么读的，
    所以该文件必须留在本地、永远不进 git（.gitignore 已排除）
  - 生成后请把密钥文件与密码另存到密码管理器
"""

from __future__ import annotations

import getpass
import os
import secrets
import subprocess
import sys

ANDROID = r"D:\dsh-go\replica\app\android"
KEYSTORE = os.path.join(ANDROID, "app", "release.keystore")
KEYPROPS = os.path.join(ANDROID, "key.properties")
OLD = os.path.join(ANDROID, "app", "replica-release.keystore")

ALIAS = "dshbianjie"
DN = "CN=dshbianjie, O=dshbianjie, C=CN"


def find_keytool() -> str:
    home = os.environ.get("JAVA_HOME")
    if home:
        p = os.path.join(home, "bin", "keytool.exe" if os.name == "nt" else "keytool")
        if os.path.exists(p):
            return p
    return "keytool"


def ask_password() -> str:
    while True:
        p1 = getpass.getpass("设置密钥库密码（至少 12 位，建议含大小写/数字/符号）: ")
        if len(p1) < 12:
            print("  太短了，至少 12 位。")
            continue
        weak = {"password", "123456", "replicapass", "android", "dshbianjie"}
        if p1.lower() in weak:
            print("  这个太常见，换一个。")
            continue
        p2 = getpass.getpass("再输一次确认: ")
        if p1 != p2:
            print("  两次不一致，重新来。")
            continue
        return p1


def main() -> int:
    print("=" * 64)
    print("生成发布签名密钥")
    print("=" * 64)
    print(f"  密钥文件 : {KEYSTORE}")
    print(f"  别名     : {ALIAS}")
    print(f"  算法     : RSA 4096, 有效期 10000 天")
    print()

    if os.path.exists(KEYSTORE):
        ans = input(f"{KEYSTORE} 已存在，覆盖吗？(yes/no): ").strip().lower()
        if ans != "yes":
            print("已取消。")
            return 1

    pwd = ask_password()

    # keytool 要求 storepass 与 keypass 一致（PKCS12 强制）
    kt = find_keytool()
    cmd = [
        kt, "-genkeypair",
        "-keystore", KEYSTORE,
        "-storetype", "PKCS12",
        "-alias", ALIAS,
        "-keyalg", "RSA",
        "-keysize", "4096",
        "-validity", "10000",
        "-storepass", pwd,
        "-keypass", pwd,
        "-dname", DN,
    ]
    print()
    print("正在生成（约需几秒，4096 位密钥较慢）…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("生成失败：")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        return 2

    # key.properties
    lines = [
        "# 发布签名。本文件含密码，永远不要提交到 git（.gitignore 已排除）。",
        f"storeFile={os.path.basename(KEYSTORE)}",
        f"storePassword={pwd}",
        f"keyAlias={ALIAS}",
        f"keyPassword={pwd}",
        "",
    ]
    with open(KEYPROPS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # 旧临时密钥改名留档（不删，万一要回滚）
    if os.path.exists(OLD):
        bak = OLD + ".tmp-backup"
        os.replace(OLD, bak)
        print(f"  旧临时密钥已改名：{os.path.basename(bak)}")

    # 读回指纹
    r2 = subprocess.run(
        [kt, "-list", "-v", "-keystore", KEYSTORE, "-storepass", pwd],
        capture_output=True, text=True,
    )
    print()
    print("=" * 64)
    print("完成")
    print("=" * 64)
    print(f"  key.properties : {KEYPROPS}")
    for line in r2.stdout.splitlines():
        s = line.strip()
        if s.startswith(("Owner:", "Valid from", "SHA256:")):
            print(f"  {s}")

    print()
    print("接下来必须做的（否则重装设备会丢数据）：")
    print("  1. 把 app/android/app/release.keystore 和密码存进密码管理器")
    print("  2. 确认 app/android/key.properties 不在 git 里：")
    print("       git check-ignore -v app/android/key.properties")
    print("  3. 以后每次发布都用这同一个密钥，不要重新生成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
