#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机操控文案：把指 App 的 DSH 改成 dsh边界（第二批）
====================================================

第一批（fix_brand_strings.py）处理了输入框、分享卡、日志标题等。
这批处理手机操控页里剩下的：

  phoneDndStartPairingStep        DSH 会发一条通知        -> dsh边界
  phoneDndEnterPairingCodeStep    填进 DSH 的通知          -> dsh边界
  phoneControlReadScreenHint      看看 DSH 读到了什么       -> dsh边界
  phoneDisclosureIntro            DSH 会像你一样看屏幕      -> dsh边界
  phoneRestricted*                DSH 的开关 / 打开 DSH    -> dsh边界
  phoneFailure*                   DSH 启动失败/崩溃        -> dsh边界
  phoneSafeRestore*               DSH 会回到…              -> dsh边界
  phoneAppRulesLoosen*            让 DSH 操作 / DSH 默认…  -> dsh边界
  phoneControlRemoteHint          「{host}」上的 DSH       -> 保留（指远端引擎）
  phoneSelfCheckSaved             下载/DSH-Go              -> 下载/dsh边界

保留：指「远端主机上的 DSH 引擎」的（phoneControlRemoteHint），
      以及 DSH_HOME / DSH Remote / Shizuku 这类专有名词。
"""

import os
import re

PARTS = r"D:\dsh-go\replica\app\lib\l10n\parts"

# key -> (zh 正则, zh 替换, en 正则, en 替换)
RULES = [
    # 通知配对
    (r'回到这里点「开始配对」，DSH 会发一条通知。',
     '回到这里点「开始配对」，dsh边界 会发一条通知。'),
    (r'下拉通知栏，把配对码填进 DSH 的通知。配对成功后点「连接」。',
     '下拉通知栏，把配对码填进 dsh边界 的通知。配对成功后点「连接」。'),
    # 读屏提示
    (r'看看 DSH 读到了什么，不发给模型',
     '看看 dsh边界 读到了什么，不发给模型'),
    # 授权说明
    (r'DSH 会像你一样看屏幕、点按，帮你把事办完。开启前，先了解这几点：',
     'dsh边界 会像你一样看屏幕、点按，帮你把事办完。开启前，先了解这几点：'),
    # 受限设置引导
    (r'先去「无障碍」里点一次 DSH 的开关',
     '先去「无障碍」里点一次 dsh边界 的开关'),
    (r'回到「无障碍」，打开 DSH。',
     '回到「无障碍」，打开 dsh边界。'),
    (r'直接去「无障碍」打开 DSH。',
     '直接去「无障碍」打开 dsh边界。'),
    (r'找到 DSH 的安装包',
     '找到 dsh边界 的安装包'),
    # 启动/崩溃
    (r'"phoneFailureStartup": "DSH 启动失败"',
     '"phoneFailureStartup": "dsh边界 启动失败"'),
    (r'"phoneFailureCrashedEarly": "DSH 启动后很快崩溃了"',
     '"phoneFailureCrashedEarly": "dsh边界 启动后很快崩溃了"'),
    (r'"phoneFailureCrashedLate": "DSH 运行中崩溃了"',
     '"phoneFailureCrashedLate": "dsh边界 运行中崩溃了"'),
    # 安全模式恢复
    (r'DSH 会回到上次正常运行时的配置：',
     'dsh边界 会回到上次正常运行时的配置：'),
    (r'DSH 会回到 \{when\} 正常运行时的配置：',
     'dsh边界 会回到 {when} 正常运行时的配置：'),
    # 应用规则
    (r'"phoneAppRulesLoosenTitle": "让 DSH 操作「\{app\}」？"',
     '"phoneAppRulesLoosenTitle": "让 dsh边界 操作「{app}」？"'),
    (r'DSH 默认不输密码、不付款。',
     'dsh边界 默认不输密码、不付款。'),
    # 自检
    (r'报告已存入下载/DSH-Go。',
     '报告已存入下载/dsh边界。'),
]

EN_RULES = [
    (r'\bDSH will send a notification\b', 'dsh边界 will send a notification'),
    (r'some into DSH\u2019s notification', 'some into dsh边界\u2019s notification'),
    (r'\bDSH\b (?=reads|reads? the screen|opens|starts|crashes|returns)',
     'dsh边界 '),
]


def patch_zh() -> int:
    p = os.path.join(PARTS, "phone_zh.arb")
    raw = open(p, encoding="utf-8").read()
    n = 0
    for rx, repl in RULES:
        new, k = re.subn(rx, repl, raw)
        if k:
            raw = new
            n += k
    open(p, "w", encoding="utf-8").write(raw)
    return n


def patch_en() -> int:
    p = os.path.join(PARTS, "phone_en.arb")
    raw = open(p, encoding="utf-8").read()
    n = 0
    for rx, repl in EN_RULES:
        new, k = re.subn(rx, repl, raw)
        if k:
            raw = new
            n += k
    open(p, "w", encoding="utf-8").write(raw)
    return n


def main() -> int:
    print("zh 改动:", patch_zh())
    print("en 改动:", patch_en())
    print()
    print("剩余 phone_zh 里的 DSH（应只剩远端引擎/专有名词）：")
    text = open(os.path.join(PARTS, "phone_zh.arb"), encoding="utf-8").read()
    for m in re.finditer(r'"(\w+)":\s*"([^"]*DSH[^"]*)"', text):
        print(f"   {m.group(1):<38} {m.group(2)[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
