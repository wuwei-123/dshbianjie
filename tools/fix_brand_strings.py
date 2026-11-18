#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌文案收尾：把「指 App 自己的 DSH」改成 dsh边界
=================================================

原则（二开，避免与 dsh-go 资产纠纷）：
  指本 App 的地方   -> dsh边界
  指底层引擎的地方   -> 保留 DSH（那是事实，不是品牌）

因此不做全局 DSH 替换，而是逐条列明改哪些。

改（App 自己）
--------------
  chatComposerHint          给 DSH 发消息…   -> 给 dsh边界 发消息…
  chatImageOffline          未连接 DSH        -> 未连接 dsh边界
  chatDownloadsFolderHint   下载/DSH-Go       -> 下载/dsh边界
  viewShareBrandLine        手机上的 DSH       -> dsh边界
  viewShareBrandLineNoQr    手机上的 DSH       -> dsh边界
  viewSharePluginTitle      DSH 插件           -> dsh边界 插件
  phoneLogShareTitle        DSH 引擎日志        -> dsh边界 引擎日志
  phoneActionLogEmptyHint   DSH 在手机上…      -> dsh边界 在手机上…
  livePublic*               DSH 正在干活/等你   -> dsh边界 …
  accessRestricted*         无障碍里的 DSH      -> dsh边界（服务名要跟着改）
  updateWrongPackage        不是 DSH 的安装包    -> 不是 dsh边界 的安装包
  updateDowngradeBlocked*   手机上的 DSH        -> dsh边界
  webTitle                  DSH 网页版          -> dsh边界 网页版
  localEnvChooseTitle       DSH 在哪里运行      -> dsh边界 在哪里运行
  featuresExportDownloadsHint 下载/DSH-Go      -> 下载/dsh边界
  phoneDiagnosticsSaveHint  下载/DSH-Go         -> 下载/dsh边界

不改（DSH 引擎事实）
--------------------
  DSH_HOME / DSH 版本号 / DSH 插件协议 / DSH Remote / DSH 官方界面
"""

import json
import os
import re
import sys

PARTS = r"D:\dsh-go\replica\app\lib\l10n\parts"

# key -> (zh 新值, en 新值)；None 表示该语言不改
CHANGES = {
    "chatComposerHint":              ("给 dsh边界 发消息…", "Message dsh边界\u2026"),
    "chatImageOffline":              ("未连接 dsh边界", "dsh边界 not connected"),
    "chatDownloadsFolderHint":       ("下载/dsh边界 文件夹", "Download/dsh边界 folder"),
    "viewShareBrandLine":            ("dsh边界 \u00b7 扫码获取", "dsh边界 \u00b7 scan to get"),
    "viewShareBrandLineNoQr":        ("dsh边界", "dsh边界"),
    "viewSharePluginTitle":          ("dsh边界 插件\u300c{value}\u300d", "dsh边界 plugin \u201c{value}\u201d"),
    "phoneLogShareTitle":            ("dsh边界 引擎日志", "dsh边界 engine log"),
    "phoneActionLogEmptyHint":       ("dsh边界 在手机上的每一步都会记在这里", "Every step dsh边界 takes on this phone is recorded here"),
    "phoneDiagnosticsSaveHint":      ("存进 下载/dsh边界", "Saved to Download/dsh边界"),
    "featuresExportDownloadsHint":   ("存进 下载/dsh边界", "Saved to Download/dsh边界"),
    "livePublicRunning":             ("dsh边界 正在干活", "dsh边界 is working"),
    "livePublicWaiting":             ("dsh边界 在等你处理", "dsh边界 is waiting for you"),
    "livePublicDone":                ("dsh边界 做完了", "dsh边界 is done"),
    "livePublicFailed":              ("dsh边界 出错了", "dsh边界 hit an error"),
    "accessRestrictedTap":           ("在无障碍里点一下\u300cdsh边界 手机操控\u300d，出现\u300c受限制的设置\u300d时点确定",
                                      "Tap \u201cdsh边界 phone control\u201d in Accessibility, then confirm when \u201cRestricted settings\u201d appears"),
    "accessRestrictedBack":          ("回到无障碍，打开\u300cdsh边界 手机操控\u300d", "Back in Accessibility, enable \u201cdsh边界 phone control\u201d"),
    "updateWrongPackage":            ("不是 dsh边界 的安装包", "Not a dsh边界 package"),
    "updateDowngradeBlockedMessage": ("手机上的 dsh边界 比这个安装包还新。", "The installed dsh边界 is newer than this package."),
    "webTitle":                      ("dsh边界 网页版", "dsh边界 web"),
    "localEnvChooseTitle":           ("dsh边界 在哪里运行？", "Where does dsh边界 run?"),
    "phoneOpenAccessibilityFailed":  ("打不开系统设置，请到\u300c设置 \u2192 无障碍\u300d里找到 dsh边界",
                                      "Cannot open Settings; find dsh边界 under Settings \u2192 Accessibility"),
}


def patch(locale: str) -> int:
    """就地修改该语言的所有 part 文件。返回改动数。"""
    changed = 0
    for fn in sorted(os.listdir(PARTS)):
        if not fn.endswith(f"_{locale}.arb"):
            continue
        p = os.path.join(PARTS, fn)
        raw = open(p, encoding="utf-8").read()
        orig = raw
        for key, (zh, en) in CHANGES.items():
            new_val = zh if locale == "zh" else en
            if new_val is None:
                continue
            # 精确替换该 key 的值
            rx = re.compile(r'("' + re.escape(key) + r'"\s*:\s*")([^"]*)(")')
            m = rx.search(raw)
            if not m:
                continue
            if m.group(2) == new_val:
                continue
            raw = raw[: m.start(2)] + new_val + raw[m.end(2) :]
            changed += 1
        if raw != orig:
            open(p, "w", encoding="utf-8").write(raw)
    return changed


def main() -> int:
    for loc in ("zh", "en"):
        n = patch(loc)
        print(f"{loc}: 改动 {n} 处")
    print()
    print("剩余含 DSH 的 key（应只剩引擎事实类）：")
    keep = []
    for fn in sorted(os.listdir(PARTS)):
        if not fn.endswith("_zh.arb"):
            continue
        p = os.path.join(PARTS, fn)
        text = open(p, encoding="utf-8").read()
        for m in re.finditer(r'"(\w+)":\s*"([^"]*DSH[^"]*)"', text):
            keep.append((fn, m.group(1)))
    for fn, k in keep[:40]:
        print(f"   {fn:<28} {k}")
    print(f"   合计 {len(keep)} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
