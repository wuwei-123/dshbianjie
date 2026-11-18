#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查：品牌名替换有没有误伤代码标识符。"""

import os
import re

ROOT = r"D:\dsh-go\replica"
SKIP = {"build", ".dart_tool", ".gradle", "node_modules", ".git",
        "pub-cache", ".idea", ".vscode", "_work", "_backup"}

CODE_EXTS = {".dart", ".kt", ".java", ".js", ".mjs", ".sh",
             ".py", ".gradle", ".kts", ".yml", ".yaml", ".json"}

CN_BRAND = "\u8fb9\u754c"   # 边界


def main() -> int:
    bad = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in CODE_EXTS:
                continue
            p = os.path.join(dirpath, fn)
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
            for i, line in enumerate(lines, 1):
                if CN_BRAND not in line:
                    continue
                total += 1
                s = line.strip()
                # 注释里出现是正常的
                if s.startswith(("//", "#", "*", "/*", "<!--")):
                    continue
                # 出现在引号内是正常的（字符串字面量）
                in_str = bool(
                    re.search(r'"[^"]*' + CN_BRAND, line)
                    or re.search(r"'[^']*" + CN_BRAND, line)
                    or re.search(r"`[^`]*" + CN_BRAND, line)
                )
                if in_str:
                    continue
                bad.append((os.path.relpath(p, ROOT), i, s[:110]))

    print(f"含品牌中文的行: {total}")
    print(f"可疑（既非注释也非字符串）: {len(bad)}")
    for path, ln, text in bad[:30]:
        print(f"  {path}:{ln}")
        print(f"     {text}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
