#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
欢迎页：海报背景 + 亮色文字（整段替换 build 方法）
=================================================

海报是深底，浅色主题的深灰文字看不清，所以这一页用固定浅色文字。
"""

from __future__ import annotations

import re

P = r"D:\dsh-go\replica\app\lib\ui\onboarding\welcome_page.dart"

raw = open(P, encoding="utf-8").read()

# 1) import
if "launch_poster.dart" not in raw:
    raw = raw.replace(
        "import 'onboarding_scaffold.dart';",
        "import 'launch_poster.dart';\nimport 'onboarding_scaffold.dart';",
    )

# 2) 整段替换 build 方法（用正则跨行匹配）
pattern = re.compile(
    r"  @override\n  Widget build\(BuildContext context\) \{\n.*?\n  \}\n\}",
    re.S,
)

new_build = """  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return LaunchPosterLoader(
      builder: (context) => LaunchPosterBackdrop(
        child: OnboardingScaffold(
          transparentBackdrop: true,
          lightContent: true,
          children: [
            const Spacer(flex: 5),
            const Center(child: _BrandArrival()),
            const SizedBox(height: 36),
            FadeSlideIn(
              delay: const Duration(milliseconds: 180),
              // Letter spacing also trails the last letter: pad the leading side
              // by the same amount so the word sits on the centre line.
              child: const Padding(
                padding: EdgeInsets.only(left: 3),
                child: Text(
                  'dsh\\u8fb9\\u754c',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 15,
                    letterSpacing: 3,
                    color: Colors.white70,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
            FadeSlideIn(
              delay: const Duration(milliseconds: 220),
              child: Text(
                l10n.shellWelcomeMessage,
                textAlign: TextAlign.center,
                style: theme.textTheme.displaySmall?.copyWith(height: 1.35, color: Colors.white),
              ),
            ),
            const Spacer(flex: 6),
            const FadeSlideIn(delay: Duration(milliseconds: 280), child: UsageNoticeRow()),
            const SizedBox(height: 20),
            FadeSlideIn(
              delay: const Duration(milliseconds: 320),
              child: FilledButton(
                onPressed: onStart,
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: const Color(0xFF11131A),
                ),
                child: Text(l10n.shellGetStarted),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              AppInfo.slogan,
              textAlign: TextAlign.center,
              style: theme.textTheme.labelSmall?.copyWith(color: Colors.white60),
            ),
          ],
        ),
      ),
    );
  }
}"""

new_raw, count = pattern.subn(lambda m: new_build, raw, count=1)
if count == 0:
    raise SystemExit("未匹配到 build 方法")

open(P, "w", encoding="utf-8").write(new_raw)
print("已替换 build 方法")

for i, line in enumerate(new_raw.splitlines(), 1):
    if any(k in line for k in ("LaunchPoster", "transparentBackdrop", "lightContent", "Colors.white")):
        print(f"  L{i}: {line.strip()[:88]}")
