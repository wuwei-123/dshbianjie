#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新英文免责声明文案。"""

import re

P = r"D:\dsh-go\replica\app\lib\l10n\parts\state_en.arb"

NEW = "Built on DeepSeek Harness (dsh-go fork) \u00b7 Unofficial DeepSeek app"

raw = open(P, encoding="utf-8").read()
m = re.search(r'("stateAppDisclaimer"\s*:\s*")([^"]*)(")', raw)
if not m:
    raise SystemExit("未找到 stateAppDisclaimer")

print("旧:", m.group(2))
out = raw[: m.start(2)] + NEW + raw[m.end(2) :]
open(P, "w", encoding="utf-8").write(out)
print("新:", NEW)
