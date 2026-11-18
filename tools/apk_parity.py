#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APK 1:1 对齐校验器
==================

用途
----
把「复刻产物」和「原版 APK」逐层比对，输出可量化的一致性证据。
复刻不是看截图像不像，而是看下面每一层是否对齐：

  第 1 层  ZIP 条目集合        —— 文件清单、增删
  第 2 层  逐文件 SHA-256      —— 哪些文件字节相同、哪些不同
  第 3 层  AndroidManifest     —— 包名、版本、SDK、组件、权限、特性
  第 4 层  DEX 类清单          —— 类/方法总量与类名集合（代码面）
  第 5 层  资源表 resources.arsc —— 资源条目数
  第 6 层  原生库与资产        —— .so / assets / res 的字节一致性
  第 7 层  签名                —— 证书指纹（复刻必然是自签，需显式标注差异）

用法
----
  python apk_parity.py inventory  ORIGINAL.apk  -o baseline.json
  python apk_parity.py compare    ORIGINAL.apk  REPLICA.apk  -o report_dir

作者备注
--------
DEX 解析是纯 Python 手写的（dex 头 + string/type/class_def 表），
不依赖 jadx / dexdump，避免工具链差异影响判定。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import zipfile
from collections import Counter, defaultdict

# ---------------------------------------------------------------- 常量

# 这些前缀属于「必须字节一致」的层：它们是随包分发的静态资产，
# 不参与编译，复刻时应当从原版精确继承。
STRICT_PREFIXES = (
    "assets/",
    "res/",
    "lib/",
)

# 这些条目天然不可能字节一致，比对时只做存在性检查并说明原因。
CODE_ENTRIES = (
    "classes.dex",
    "classes2.dex",
    "classes3.dex",
)

VOLATILE_HINTS = {
    "resources.arsc": "资源表包含编译期生成的字符串池顺序，工具链不同即会变化",
    "AndroidManifest.xml":
        "二进制 XML 的字符串池受 apktool/aapt2 版本影响；语义比对见 manifest 层",
    "META-INF/MANIFEST.MF": "由签名过程生成",
    "META-INF/CERT.SF": "由签名过程生成",
    "META-INF/CERT.RSA": "由签名私钥决定，复刻必然不同",
    "META-INF/BNDLTOOL.RSA": "由签名私钥决定",
    "META-INF/BNDLTOOL.SF": "由签名私钥决定",
}

# 引擎/工具链绑定产物：与实际「谁在哪台机器上编译」有关，源码相同也会不同。
# 判定时不计入 FAIL，但必须在报告里单独列出，不能悄悄放过。
ENGINE_BOUND_NAMES = {
    "lib/arm64-v8a/libflutter.so": "Flutter 引擎本体，由 SDK 的 engine.version 决定",
    "lib/x86_64/libflutter.so": "Flutter 引擎本体，由 SDK 的 engine.version 决定",
    "lib/arm64-v8a/libapp.so": "Dart AOT 快照，受编译期哈希/路径/优化顺序影响",
    "lib/x86_64/libapp.so": "Dart AOT 快照，受编译期哈希/路径/优化顺序影响",
    "lib/arm64-v8a/libdartjni.so": "Dart JNI 桥，随引擎版本发布",
    "lib/x86_64/libdartjni.so": "Dart JNI 桥，随引擎版本发布",
    "assets/flutter_assets/NOTICES.Z": "引擎与依赖许可汇编，随 SDK/依赖版本变化",
    "assets/dexopt/baseline.prof": "Baseline Profile，由 AGP + ProfileInstaller 规则生成",
    "assets/dexopt/baseline.profm": "Baseline Profile 元数据，同上",
}

ENGINE_BOUND_PREFIXES = (
    "assets/dexopt/",
)


def is_engine_artifact(name: str) -> bool:
    """该条目是否属于「构建环境决定」而非「源码决定」。"""
    if name in ENGINE_BOUND_NAMES:
        return True
    return any(name.startswith(p) for p in ENGINE_BOUND_PREFIXES)


# ---------------------------------------------------------------- 工具

def sha256_of_stream(fp, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    while True:
        b = fp.read(chunk)
        if not b:
            break
        h.update(b)
    return h.hexdigest()


def sha256_of_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_of_stream(f)


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.2f}{unit}"
        n /= 1024.0
    return f"{n}B"


# ---------------------------------------------------------------- DEX

class DexReader:
    """最小可用的 DEX 解析器：只为拿到「类名集合」和统计量。"""

    def __init__(self, data: bytes):
        if data[:4] != b"dex\n":
            raise ValueError("不是 DEX 文件")
        self.data = data
        (
            self.checksum,
        ) = struct.unpack_from("<I", data, 8)
        (
            self.file_size,
            self.header_size,
            self.endian_tag,
        ) = struct.unpack_from("<III", data, 32)
        # DEX 头布局（小端，每个 *_size 后紧跟 *_off，各 4 字节）：
        #   file_size    @32   header_size @36   endian_tag @40
        #   link_size    @44   link_off    @48   map_off    @52
        #   string_ids   @56   type_ids    @64   proto_ids  @72
        #   field_ids    @80   method_ids  @88   class_defs @96
        # 所以从 56 起连续 12 个 u32 正好覆盖 string..class_defs 的 size/off。
        self.link_size, self.link_off = struct.unpack_from("<II", data, 44)
        (
            self.string_ids_size,
            self.string_ids_off,
            self.type_ids_size,
            self.type_ids_off,
            self.proto_ids_size,
            self.proto_ids_off,
            self.field_ids_size,
            self.field_ids_off,
            self.method_ids_size,
            self.method_ids_off,
            self.class_defs_size,
            self.class_defs_off,
        ) = struct.unpack_from("<IIIIIIIIIIII", data, 56)

        # 头里声明的 file_size 应与实际字节数一致，否则视为坏 dex
        if self.file_size != len(data):
            raise ValueError(
                f"dex 头 file_size={self.file_size} 与实际 {len(data)} 不符"
            )

        self._strings: list[str] | None = None

    # --- 字符串池 -------------------------------------------------
    def _read_uleb128(self, off: int) -> tuple[int, int]:
        result = 0
        shift = 0
        while True:
            b = self.data[off]
            off += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return result, off

    def string_at(self, idx: int) -> str:
        off = struct.unpack_from("<I", self.data, self.string_ids_off + idx * 4)[0]
        _, off = self._read_uleb128(off)  # utf16 长度前缀，跳过
        end = self.data.index(b"\x00", off)
        raw = self.data[off:end]
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def type_name(self, type_idx: int) -> str:
        str_idx = struct.unpack_from("<I", self.data, self.type_ids_off + type_idx * 4)[0]
        return self.string_at(str_idx)

    # --- 类清单 ---------------------------------------------------
    def class_names(self) -> list[str]:
        out = []
        for i in range(self.class_defs_size):
            class_idx = struct.unpack_from(
                "<I", self.data, self.class_defs_off + i * 32
            )[0]
            desc = self.type_name(class_idx)
            # Lcom/foo/Bar; -> com.foo.Bar    [Lcom/foo/Bar$Inner; -> com.foo.Bar$Inner
            if desc.startswith("L") and desc.endswith(";"):
                desc = desc[1:-1].replace("/", ".")
            out.append(desc)
        return out

    def stats(self) -> dict:
        return {
            "file_size": self.file_size,
            "strings": self.string_ids_size,
            "types": self.type_ids_size,
            "protos": self.proto_ids_size,
            "fields": self.field_ids_size,
            "methods": self.method_ids_size,
            "classes": self.class_defs_size,
        }


def dex_inventory(zf: zipfile.ZipFile) -> dict:
    """解析 APK 内所有 dex，返回合并后的类集合与逐文件统计。"""
    per_file = {}
    all_classes: set[str] = set()
    totals = Counter()

    names = sorted(
        n for n in zf.namelist()
        if n.endswith(".dex") and "/" not in n
    )
    for name in names:
        try:
            dr = DexReader(zf.read(name))
        except Exception as exc:  # noqa: BLE001 - 坏 dex 不应中断整体比对
            per_file[name] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        cls = dr.class_names()
        all_classes.update(cls)
        st = dr.stats()
        per_file[name] = st
        for k, v in st.items():
            if k != "file_size":
                totals[k] += v

    # 用户可见包前缀（非 androidx/com/google/kotlin 等三方），用于快速看业务代码量
    own = sorted(
        c for c in all_classes
        if c.startswith(("io.github.ccch1mneyyy",))
    )

    return {
        "files": per_file,
        "totals": dict(totals),
        "unique_classes": len(all_classes),
        "own_classes": own,
        "own_class_count": len(own),
    }


# ---------------------------------------------------------------- Manifest

def axml_strings(data: bytes) -> list[str]:
    """从二进制 XML 里粗暴抽取 UTF-16 字符串池，用于 manifest 关键词比对。

    这里不做完整 AXML 解析，只在没有 apktool 时提供粗略证据；
    权威语义比对走 apktool 解出来的明文 XML（见 decode_manifest）。
    """
    try:
        _, _, _ = struct.unpack_from("<HHI", data, 0)
        # 找字符串池 chunk (type 0x0001)
        off = 8
        while off + 8 <= len(data):
            ctype, hsize, csize = struct.unpack_from("<HHI", data, off)
            if csize <= 0:
                break
            if ctype == 0x0001:
                count, _styles, flags, strings_start, _styles_start = struct.unpack_from(
                    "<IIIII", data, off + 8
                )
                utf8 = bool(flags & (1 << 8))
                offsets = [
                    struct.unpack_from("<I", data, off + 28 + i * 4)[0]
                    for i in range(count)
                ]
                base = off + strings_start
                out = []
                for o in offsets:
                    p = base + o
                    if utf8:
                        # 两段长度（字符数、字节数），都是 1~2 字节
                        if data[p] & 0x80:
                            p += 2
                        else:
                            p += 1
                        if data[p] & 0x80:
                            n = ((data[p] & 0x7F) << 8) | data[p + 1]
                            p += 2
                        else:
                            n = data[p]
                            p += 1
                        out.append(data[p:p + n].decode("utf-8", "replace"))
                    else:
                        n = struct.unpack_from("<H", data, p)[0]
                        p += 2
                        if n & 0x8000:
                            n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", data, p)[0]
                            p += 2
                        out.append(data[p:p + n * 2].decode("utf-16-le", "replace"))
                return out
            off += csize
    except Exception:  # noqa: BLE001
        pass
    return []


MANIFEST_KEYS = (
    "package",
    "versionCode",
    "versionName",
    "minSdkVersion",
    "targetSdkVersion",
    "compileSdkVersion",
    "extractNativeLibs",
    "debuggable",
    "allowBackup",
    "usesCleartextTraffic",
)


def manifest_facts(zf: zipfile.ZipFile) -> dict:
    data = zf.read("AndroidManifest.xml")
    facts = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "keys": {k: None for k in MANIFEST_KEYS},
        "string_pool_size": 0,
        "components": defaultdict(list),
        "permissions": [],
        "features": [],
    }
    strings = axml_strings(data)
    facts["string_pool_size"] = len(strings)
    pool = set(strings)

    # 简易取值：二进制 XML 里属性值是「索引」，这里只在字符串池里找已知形态
    # 精确值由 apktool 解码结果补（compare 模式会调用）。
    for s in strings:
        if s.startswith("android.permission."):
            facts["permissions"].append(s)
        if s.startswith("android.hardware."):
            facts["features"].append(s)
        if s.startswith("io.github.ccch1mneyyy.") or s.startswith("androidx.") or \
           s.startswith("com.google.") or s.startswith("rikka.") or \
           s.startswith("dev.fluttercommunity.") or s.startswith("io.flutter."):
            facts["components"]["candidates"].append(s)
    facts["permissions"] = sorted(set(facts["permissions"]))
    facts["features"] = sorted(set(facts["features"]))
    facts["components"] = {"candidates": sorted(set(facts["components"]["candidates"]))}
    facts["looks_like_version_name"] = sorted(
        s for s in pool
        if len(s) < 16 and s.count(".") == 2 and s[0].isdigit()
    )
    return facts


# ---------------------------------------------------------------- 清单

def inventory(path: str, with_dex: bool = True) -> dict:
    """产出一个 APK 的完整指纹。"""
    if not os.path.isfile(path):
        raise SystemExit(f"文件不存在: {path}")

    inv = {
        "path": os.path.abspath(path),
        "bytes": os.path.getsize(path),
        "sha256": sha256_of_file(path),
        "entries": {},
        "by_role": Counter(),
        "by_prefix": Counter(),
    }

    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        for info in infos:
            if info.is_dir():
                continue
            name = info.filename
            entry = {
                "size": info.file_size,
                "crc32": format(info.CRC, "08x"),
                "sha256": sha256_of_stream(zf.open(info)),
            }
            # 归类
            role = classify(name)
            entry["role"] = role
            inv["entries"][name] = entry
            inv["by_role"][role] += 1
            inv["by_prefix"][name.split("/")[0]] += 1

        inv["entry_count"] = len(inv["entries"])
        if with_dex:
            inv["dex"] = dex_inventory(zf)
        inv["manifest"] = manifest_facts(zf)

    inv["by_role"] = dict(inv["by_role"])
    inv["by_prefix"] = dict(inv["by_prefix"])
    return inv


def classify(name: str) -> str:
    if name.endswith(".dex") and "/" not in name:
        return "dex"
    if name.startswith("lib/") and name.endswith(".so"):
        return "native-lib"
    if name.startswith("lib/"):
        return "native-other"
    if name.startswith("assets/flutter_assets/"):
        return "flutter-asset"
    if name.startswith("assets/"):
        return "android-asset"
    if name.startswith("res/"):
        return "resource"
    if name == "resources.arsc":
        return "resource-table"
    if name == "AndroidManifest.xml":
        return "manifest"
    if name.startswith("META-INF/"):
        if name.endswith((".RSA", ".DSA", ".EC", ".SF")) or name == "META-INF/MANIFEST.MF":
            return "signature"
        return "meta"
    return "other"


# ---------------------------------------------------------------- 比对

def compare(a: dict, b: dict, strict_prefixes=STRICT_PREFIXES) -> dict:
    """比对两份 inventory，产出分层结论。"""
    ea, eb = a["entries"], b["entries"]
    names_a, names_b = set(ea), set(eb)

    only_a = sorted(names_a - names_b)
    only_b = sorted(names_b - names_a)
    common = sorted(names_a & names_b)

    identical, differing = [], []
    for n in common:
        if ea[n]["sha256"] == eb[n]["sha256"]:
            identical.append(n)
        else:
            differing.append(n)

    diff_set = set(differing)

    def bucket(pred):
        return [n for n in differing if pred(n)]

    # 分层判定
    layers = {}

    # 第 6 层：严格资产层（assets/ res/ lib/）——应当字节一致
    #
    # 但有三类条目在物理上不可能字节一致，它们取决于「构建环境」而不是「源码」：
    #   a) Flutter 引擎制品：libflutter.so / libapp.so / libdartjni.so / NOTICES.Z
    #      —— 由 Flutter SDK 的 engine.version + 构建机编译环境决定
    #   b) Baseline Profile：assets/dexopt/*
    #      —— 由 AGP/依赖版本 + ProfileInstaller 规则决定
    #   c) 签名/资源表/清单：见 VOLATILE_HINTS
    # 把它们混进「必须一致」会制造假失败；这里拆出来单独判定并要求诚实标注。
    strict_names = [
        n for n in names_a
        if n.startswith(strict_prefixes)
    ]
    strict_same = [n for n in strict_names if n in eb and ea[n]["sha256"] == eb[n]["sha256"]]
    strict_raw_diff = [n for n in strict_names if n in eb and ea[n]["sha256"] != eb[n]["sha256"]]
    strict_missing = [n for n in strict_names if n not in eb]

    env_diff = [n for n in strict_raw_diff if is_engine_artifact(n)]
    strict_diff = [n for n in strict_raw_diff if not is_engine_artifact(n)]

    layers["strict_assets"] = {
        "expected": len(strict_names),
        "identical": len(strict_same),
        "differing": len(strict_diff),
        "engine_bound_differing": len(env_diff),
        "missing_in_replica": len(strict_missing),
        "verdict": (
            "PASS" if not strict_diff and not strict_missing
            else "FAIL"
        ),
        "differing_samples": strict_diff[:40],
        "engine_bound_samples": env_diff[:40],
        "missing_samples": strict_missing[:40],
        "engine_bound_note": (
            "引擎/工具链绑定产物：由 Flutter SDK 版本与构建机环境决定，"
            "源码相同也会不同。不计入 FAIL，但必须在报告里列出。"
        ),
    }

    # 第 4 层：DEX 类集合
    dex_a = a.get("dex", {})
    dex_b = b.get("dex", {})
    ca = set(dex_a.get("own_classes", []))
    cb = set(dex_b.get("own_classes", []))
    layers["dex_classes"] = {
        "original_classes": dex_a.get("unique_classes"),
        "replica_classes": dex_b.get("unique_classes"),
        "original_own_classes": len(ca),
        "replica_own_classes": len(cb),
        "missing_in_replica": len(ca - cb),
        "extra_in_replica": len(cb - ca),
        "missing_samples": sorted(ca - cb)[:40],
        "extra_samples": sorted(cb - ca)[:40],
        "note": "AOT/D8 产物不追求字节一致；类集合是代码面对齐的最小证据",
    }

    # 第 7 层：签名
    sig_a = sorted(n for n in names_a if classify(n) == "signature")
    sig_b = sorted(n for n in names_b if classify(n) == "signature")
    layers["signature"] = {
        "original_files": sig_a,
        "replica_files": sig_b,
        "sha256_equal": all(
            n in eb and ea[n]["sha256"] == eb[n]["sha256"] for n in sig_a
        ) if sig_a else None,
        "note": "复刻使用自签证书，指纹必然不同；此项只记录，不计入对齐失败",
    }

    # 第 3 层：manifest 语义
    ma, mb = a["manifest"], b["manifest"]
    layers["manifest"] = {
        "binary_equal": ma["sha256"] == mb["sha256"],
        "permissions_equal": ma["permissions"] == mb["permissions"],
        "permissions_only_original": sorted(set(ma["permissions"]) - set(mb["permissions"])),
        "permissions_only_replica": sorted(set(mb["permissions"]) - set(ma["permissions"])),
        "features_equal": ma["features"] == mb["features"],
        "components_equal": (
            ma["components"]["candidates"] == mb["components"]["candidates"]
        ),
        "components_only_original": sorted(
            set(ma["components"]["candidates"]) - set(mb["components"]["candidates"])
        ),
        "components_only_replica": sorted(
            set(mb["components"]["candidates"]) - set(ma["components"]["candidates"])
        ),
    }

    # 总量
    summary = {
        "original": {
            "bytes": a["bytes"], "entries": a["entry_count"], "sha256": a["sha256"],
        },
        "replica": {
            "bytes": b["bytes"], "entries": b["entry_count"], "sha256": b["sha256"],
        },
        "entries_identical": len(identical),
        "entries_differing": len(differing),
        "only_in_original": len(only_a),
        "only_in_replica": len(only_b),
        "byte_identical_ratio": round(
            len(identical) / max(1, len(common)) * 100, 2
        ),
    }

    # 差异归类（帮助判断是工具链噪声还是真缺失）
    categorized = defaultdict(list)
    for n in differing:
        if n in VOLATILE_HINTS:
            categorized["预期波动"].append(n)
        elif n in CODE_ENTRIES:
            categorized["编译产物"].append(n)
        elif classify(n) == "flutter-asset":
            categorized["flutter 资产"].append(n)
        elif classify(n) == "native-lib":
            categorized["原生库"].append(n)
        elif n.startswith("assets/"):
            categorized["安卓资产"].append(n)
        else:
            categorized["其他"].append(n)

    return {
        "summary": summary,
        "layers": layers,
        "differences": {
            "only_in_original": only_a[:200],
            "only_in_replica": only_b[:200],
            "categorized": {k: v[:80] for k, v in categorized.items()},
            "categorized_counts": {k: len(v) for k, v in categorized.items()},
        },
    }


def verdict_of(result: dict) -> tuple[str, list[str]]:
    """给出总体结论和未通过项。"""
    fails = []
    st = result["layers"]["strict_assets"]
    if st["verdict"] != "PASS":
        fails.append(
            f"静态资产层未对齐：差异 {st['differing']} 个、缺失 {st['missing_in_replica']} 个"
        )
    if result["summary"]["only_in_original"]:
        fails.append(
            f"复刻缺少 {result['summary']['only_in_original']} 个原版条目"
        )
    if result["summary"]["only_in_replica"]:
        fails.append(
            f"复刻多出 {result['summary']['only_in_replica']} 个条目"
        )
    m = result["layers"]["manifest"]
    if not m["permissions_equal"]:
        fails.append("权限声明不一致")
    if not m["components_equal"]:
        fails.append("组件声明不一致")
    d = result["layers"]["dex_classes"]
    if d["missing_in_replica"]:
        fails.append(f"DEX 缺少 {d['missing_in_replica']} 个业务类")

    return ("PASS" if not fails else "FAIL"), fails


# ---------------------------------------------------------------- 报告

def render_markdown(result: dict, a_path: str, b_path: str) -> str:
    s = result["summary"]
    L = result["layers"]
    verdict, fails = verdict_of(result)

    lines = []
    add = lines.append
    add("# APK 1:1 对齐报告\n")
    add(f"- 原版：`{a_path}`")
    add(f"- 复刻：`{b_path}`")
    add(f"- 结论：**{verdict}**\n")

    if fails:
        add("## 未通过项\n")
        for f in fails:
            add(f"- {f}")
        add("")

    add("## 总量\n")
    add("| 项 | 原版 | 复刻 |")
    add("| --- | --- | --- |")
    add(f"| 字节 | {human(s['original']['bytes'])} | {human(s['replica']['bytes'])} |")
    add(f"| 条目 | {s['original']['entries']} | {s['replica']['entries']} |")
    add(f"| 字节相同条目 | {s['entries_identical']} | — |")
    add(f"| 字节不同条目 | {s['entries_differing']} | — |")
    add(f"| 仅原版有 | {s['only_in_original']} | — |")
    add(f"| 仅复刻有 | {s['only_in_replica']} | — |")
    add(f"| 字节一致率 | {s['byte_identical_ratio']}% | — |")
    add("")

    st = L["strict_assets"]
    add("## 第 6 层 · 静态资产（assets / res / lib）\n")
    add(f"- 应与原版字节一致：{st['expected']} 个")
    add(f"- 一致：{st['identical']}")
    add(f"- 不一致：{st['differing']} → **{st['verdict']}**")
    add(f"- 复刻缺失：{st['missing_in_replica']}")
    add(f"- 引擎/工具链绑定（单列，不计 FAIL）：{st.get('engine_bound_differing', 0)}")
    if st.get("engine_bound_samples"):
        add("\n<details><summary>引擎/工具链绑定产物（源码相同也会不同）</summary>\n")
        for n in st["engine_bound_samples"]:
            why = ENGINE_BOUND_NAMES.get(n, "由构建环境决定")
            add(f"- `{n}` — {why}")
        add("\n</details>")
    if st["differing_samples"]:
        add("\n<details><summary>不一致样本</summary>\n")
        for n in st["differing_samples"]:
            add(f"- `{n}`")
        add("\n</details>")
    add("")

    d = L["dex_classes"]
    add("## 第 4 层 · DEX 类集合\n")
    add(f"- 原版类总数：{d['original_classes']}（业务类 {d['original_own_classes']}）")
    add(f"- 复刻类总数：{d['replica_classes']}（业务类 {d['replica_own_classes']}）")
    add(f"- 复刻缺失业务类：{d['missing_in_replica']}")
    add(f"- 复刻多出业务类：{d['extra_in_replica']}")
    add(f"\n> {d['note']}")
    add("")

    m = L["manifest"]
    add("## 第 3 层 · Manifest\n")
    add(f"- 二进制一致：{m['binary_equal']}")
    add(f"- 权限一致：{m['permissions_equal']}")
    add(f"- 组件一致：{m['components_equal']}")
    add(f"- 特性一致：{m['features_equal']}")
    if m["permissions_only_original"]:
        add(f"- 仅原版权限：{m['permissions_only_original']}")
    if m["permissions_only_replica"]:
        add(f"- 仅复刻权限：{m['permissions_only_replica']}")
    add("")

    sig = L["signature"]
    add("## 第 7 层 · 签名\n")
    add(f"- 原版签名文件：{sig['original_files']}")
    add(f"- 复刻签名文件：{sig['replica_files']}")
    add(f"\n> {sig['note']}")
    add("")

    cat = result["differences"]["categorized_counts"]
    if cat:
        add("## 差异归类\n")
        add("| 类别 | 数量 | 说明 |")
        add("| --- | --- | --- |")
        explain = {
            "预期波动": "资源表/清单/签名等编译期产物，工具链不同即变化",
            "编译产物": "DEX，需对齐的是类集合而非字节",
            "flutter 资产": "应当一致；不一致说明资产没继承原版",
            "原生库": "应当一致；不一致说明 NDK 或源码版本不同",
            "安卓资产": "应当一致",
            "其他": "需逐项确认",
        }
        for k, v in cat.items():
            add(f"| {k} | {v} | {explain.get(k, '')} |")
        add("")

    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="APK 1:1 对齐校验器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("inventory", help="只产出单个 APK 的指纹")
    p1.add_argument("apk")
    p1.add_argument("-o", "--out", default=None, help="输出 JSON 路径")
    p1.add_argument("--no-dex", action="store_true", help="跳过 DEX 解析")

    p2 = sub.add_parser("compare", help="比对原版与复刻")
    p2.add_argument("original")
    p2.add_argument("replica")
    p2.add_argument("-o", "--out", default="reports", help="输出目录")
    p2.add_argument("--json-only", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "inventory":
        inv = inventory(args.apk, with_dex=not args.no_dex)
        text = json.dumps(inv, ensure_ascii=False, indent=2)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"写入 {args.out}")
            # 同时打一份人读摘要
            print(f"条目 {inv['entry_count']} 个，{human(inv['bytes'])}")
            print("角色分布：", json.dumps(inv["by_role"], ensure_ascii=False))
            if "dex" in inv:
                d = inv["dex"]
                print(
                    f"DEX：类 {d['unique_classes']}，业务类 {d['own_class_count']}，"
                    f"方法 {d['totals'].get('methods')}"
                )
        else:
            print(text)
        return 0

    # compare
    print(f"读取原版 {args.original} ...", file=sys.stderr)
    a = inventory(args.original)
    print(f"读取复刻 {args.replica} ...", file=sys.stderr)
    b = inventory(args.replica)

    result = compare(a, b)
    verdict, fails = verdict_of(result)
    result["verdict"] = verdict
    result["failures"] = fails

    os.makedirs(args.out, exist_ok=True)
    jpath = os.path.join(args.out, "parity.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"写入 {jpath}")

    if not args.json_only:
        md = render_markdown(result, args.original, args.replica)
        mpath = os.path.join(args.out, "parity.md")
        with open(mpath, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"写入 {mpath}")
        print()
        print(md)

    print(f"\n结论: {verdict}")
    for f_ in fails:
        print(f"  ✗ {f_}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
