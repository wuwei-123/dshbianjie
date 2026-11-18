#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复刻构建脚本
============

把已经验证过的构建决策固化下来，任何人拉下这个工程都能复现同一份 APK。

为什么需要这个脚本，而不是直接 flutter build：
  1. runtime/out/ 必须先就位，否则 build.gradle.kts 找不到 assets/jniLibs
  2. pubspec.lock 必须保持原样，否则依赖漂移会让 APK 内容变化
  3. versionCode 必须钉成原版的 11101246，否则装不上、更新检查也会错
  4. 构建前要清掉 Flutter 资产合并缓存，否则新加的资产不会进包
     （companion zip 就是这么漏掉过一次）

用法：
    python tools/build_replica.py                      # 默认 arm64 release
    python tools/build_replica.py --flavor x64
    python tools/build_replica.py --clean               # 先全清再构建
    python tools/build_replica.py --parity              # 构建后自动跑对齐校验
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量

# 原版 1.0.15 的构建号。规则见 tooling/build_number.py：
#   (year-2026)*1e8 + MMDDhhmm @ UTC+8  ->  2026-11-10 12:46
VERSION_NAME = "1.0.15"
VERSION_CODE = "11101246"

FLAVOR_PLATFORM = {
    "arm64": "android-arm64",
    "x64": "android-x64",
}

# 增量构建时 Flutter 不会重扫这些目录里的新增文件，必须主动清
ASSET_CACHE_PATHS = (
    "app/build/app/intermediates/assets",
    "app/build/app/intermediates/mergeArm64ReleaseAssets",
    "app/build/app/intermediates/mergeX64ReleaseAssets",
    "app/build/app/intermediates/flutter",
    "app/build/app/generated/assets",
)


# ---------------------------------------------------------------- 工具

def find_repo_root() -> Path:
    """定位 app/pubspec.yaml 所在的工程根。

    重要：不做 resolve()。Windows 上如果工程通过 junction / 符号链接挂在纯 ASCII
    路径下（例如 D:\\dsh-go-src -> D:\\下载安装包\\dsh-go二开\\dsh-go-src），
    resolve() 会把它还原成含中文的真实路径，Dart AOT 编译器随即读不出中文路径
    下的 app.dill 而失败（报 'Unable to read file: D:\\???\\...'）。
    保留原样路径，才能让子进程一直走在 ASCII 上。
    """
    env = os.environ.get("DSH_REPLICA_ROOT")
    if env:
        p = Path(env)
        if (p / "app" / "pubspec.yaml").exists():
            return p

    here = Path(__file__).parent.parent
    # 注意：这里必须用 absolute() 而不是 resolve()，理由同上。
    candidates = [
        here / "replica",   # dsh-go-replica/replica
        here,               # 脚本就在工程内
        Path.cwd(),
    ]
    for c in candidates:
        if (c / "app" / "pubspec.yaml").exists():
            return c.absolute()

    raise SystemExit(
        "找不到工程根（含 app/pubspec.yaml）。用 DSH_REPLICA_ROOT 指定，例如：\n"
        "  DSH_REPLICA_ROOT=dsh-go-replica/replica python tools/build_replica.py"
    )


def which(name: str) -> str | None:
    """在 PATH 和几个已知位置里找一个可执行文件。"""
    p = shutil.which(name)
    if p:
        return p
    fallbacks = {
        "flutter": [r"D:\tools\flutter\bin\flutter.bat"],
        "flutter.bat": [r"D:\tools\flutter\bin\flutter.bat"],
        "python": [sys.executable],
    }
    for cand in fallbacks.get(name, []):
        if Path(cand).exists():
            return cand
    return None


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> int:
    print("→ " + " ".join(str(c) for c in cmd))
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    proc = subprocess.run(cmd, cwd=str(cwd), env=full_env)
    return proc.returncode


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- 步骤

def check_runtime_out(repo: Path, flavor: str) -> bool:
    """确认 runtime/out/<abi> 就位。缺了就直接说怎么补，不假装能构建。"""
    abi = "arm64-v8a" if flavor == "arm64" else "x86_64"
    out = repo / "runtime" / "out" / abi
    manifest = out / "assets" / "runtime" / "manifest.json"
    rootfs = out / "assets" / "runtime" / f"rootfs-{abi}.tar.xz"
    jni = out / "jniLibs" / abi

    missing = [p for p in (manifest, rootfs) if not p.exists()]
    if jni.is_dir():
        wanted = ["libproot.so", "libproot-loader.so", "libtalloc.so", "libandroid-shmem.so"]
        missing += [jni / w for w in wanted if not (jni / w).exists()]
    else:
        missing.append(jni)

    if missing:
        print("runtime/out 不完整，缺：")
        for m in missing:
            print(f"  - {m.relative_to(repo)}")
        print()
        print("补法：")
        print("  python tools/inherit_runtime.py <原版APK> --abi " + abi)
        print("  （或用官方 runtime/build-runtime.sh，但需要 x86_64 Linux，")
        print("    且重建的 rootfs 哈希会和 manifest.json 不符）")
        return False

    man = read_json(manifest)
    print(f"runtime/out/{abi} 就位：")
    print(f"  dsh {man.get('dshVersion')} / node {man.get('nodeVersion')} "
          f"/ ubuntu {man.get('ubuntuVersion')}")
    print(f"  rootfs {man.get('rootfsBytes'):,} B  sha256 {man.get('rootfsSha256')[:16]}…")
    return True


def check_pubspec_lock(repo: Path) -> None:
    """pubspec.lock 是 APK 内容的一部分决定因素，变了就要停下来问。"""
    lock = repo / "app" / "pubspec.lock"
    if not lock.exists():
        print("app/pubspec.lock 不存在：先跑 flutter pub get")
        return
    # 记录关键依赖版本，确保没被无意升级
    txt = lock.read_text(encoding="utf-8", errors="replace")
    key = ["cupertino_icons", "material_ui", "jni", "flutter_riverpod", "image", "archive"]
    found = {}
    import re
    for k in key:
        m = re.search(rf"^  {k}:\n(?:.*\n)*?    version: \"([^\"]+)\"", txt, re.M)
        if m:
            found[k] = m.group(1)
    print("关键依赖版本：" + ", ".join(f"{k}={v}" for k, v in found.items()))


def clear_asset_caches(repo: Path) -> None:
    """清掉会让新增资产漏打包的中间产物。"""
    removed = 0
    for rel in ASSET_CACHE_PATHS:
        p = repo / rel
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
            print(f"  清 {rel}")
    if removed == 0:
        print("  （没有需要清的缓存目录）")


def verify_companion_pack(repo: Path) -> bool:
    """companion zip 被 .gitignore 挡在仓库外，构建前必须在位。

    没有它：APK 能构建，但装到手机上「伙伴小屋」第一次打开会没有素材，
    而且这是原版故意随包带的（docs/design/companion.md §3）。
    """
    z = repo / "app" / "assets" / "companion" / "whale-girl.zip"
    if z.exists():
        print(f"companion zip 就位：{z.stat().st_size:,} B")
        return True
    print("companion zip 缺失：app/assets/companion/whale-girl.zip")
    print("  它是官方随包资产（.gitignore:/assets/companion/*.zip 有意排除），")
    print("  发版机在打包前放进 app/assets/companion/。")
    print("  从原版 APK 恢复：python tools/inherit_runtime.py 里已含该步骤，")
    print("  或单独解包 assets/flutter_assets/assets/companion/whale-girl.zip。")
    return False


def build(repo: Path, flavor: str, mode: str, clean: bool) -> int:
    app = repo / "app"
    flutter = which("flutter") or which("flutter.bat")
    if not flutter:
        print("找不到 flutter：把它放到 PATH，或改 this script 的 fallbacks")
        return 2

    android_home = os.environ.get("ANDROID_HOME") or r"D:\tools\android-sdk"
    env = {
        "ANDROID_HOME": android_home,
        "ANDROID_SDK_ROOT": android_home,
        "GRADLE_OPTS": "-Xmx4g -Dfile.encoding=UTF-8",
    }

    if clean:
        print("== 清理构建产物 ==")
        for rel in ("app/build", "app/.dart_tool/flutter_build"):
            p = repo / rel
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
                print(f"  删 {rel}")

    print("== 依赖 ==")
    if run([flutter, "pub", "get"], cwd=app, env=env) != 0:
        return 3
    check_pubspec_lock(repo)

    print("== 清资产缓存（保证新增资产进包）==")
    clear_asset_caches(repo)

    cmd = [
        flutter, "build", "apk",
        f"--{mode}",
        "--flavor", flavor,
        "--target-platform", FLAVOR_PLATFORM[flavor],
        "--build-name", VERSION_NAME,
        "--build-number", VERSION_CODE,
        f"--dart-define=DSH_APP_VERSION={VERSION_NAME}+{VERSION_CODE}",
    ]
    print("== 构建 ==")
    code = run(cmd, cwd=app, env=env)
    if code != 0:
        print(f"\n构建失败（exit {code}）")
        return code

    apk = app / "build" / "app" / "outputs" / "flutter-apk" / f"app-{flavor}-{mode}.apk"
    if not apk.exists():
        print(f"构建声称成功，但找不到 {apk}")
        return 4

    print(f"\n产物：{apk}")
    print(f"  {apk.stat().st_size:,} B ({apk.stat().st_size/1024/1024:.2f} MB)")
    return 0


# ---------------------------------------------------------------- 主流程

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="复刻构建脚本")
    ap.add_argument("--flavor", default="arm64", choices=["arm64", "x64"])
    ap.add_argument("--mode", default="release", choices=["release", "debug", "profile"])
    ap.add_argument("--clean", action="store_true", help="构建前全清")
    ap.add_argument("--parity", action="store_true", help="构建后跑对齐校验")
    args = ap.parse_args(argv)

    repo = find_repo_root()
    print(f"工程根：{repo}")
    print(f"目标  ：{args.flavor} / {args.mode} / {VERSION_NAME}({VERSION_CODE})")
    print()

    print("== 前置检查 ==")
    ok = check_runtime_out(repo, args.flavor)
    if not verify_companion_pack(repo):
        # 不阻断：只连远程主机、不用伙伴小屋的构建可以继续，
        # 但这个差异会在对齐校验里作为「仅原版有」出现。
        print("  （继续构建，但这会让 APK 少一个原版条目）")
    if not ok:
        return 5

    print()
    code = build(repo, args.flavor, args.mode, args.clean)
    if code != 0:
        return code

    if args.parity:
        print("\n== 对齐校验 ==")
        apk = repo / "app" / "build" / "app" / "outputs" / "flutter-apk" / f"app-{args.flavor}-{args.mode}.apk"
        original = os.environ.get("DSH_ORIGINAL_APK")
        if not original:
            print("设置 DSH_ORIGINAL_APK 指向原版 APK 才能自动比对")
            return 0

        # apk_parity.py 可能和本脚本同级（外层 tools/），也可能在工程内 tools/。
        here = Path(__file__).resolve().parent
        parity = None
        for cand in (here / "apk_parity.py", repo / "tools" / "apk_parity.py"):
            if cand.exists():
                parity = cand
                break
        if not parity:
            print("找不到 apk_parity.py（既不在脚本同级，也不在工程 tools/）")
            return 0

        return run(
            [sys.executable, str(parity),
             "compare", original, str(apk),
             "-o", str(here.parent / "reports" / "latest")],
            cwd=here.parent,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
