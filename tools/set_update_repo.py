"""Point the update channel at your own GitHub Releases repo.

The in-app updater reads updateRepo (app/lib/update/update_config.dart) and
builds everything from it:

  https://api.github.com/repos/<repo>/releases/latest
  https://github.com/<repo>/releases/latest/download/update.json
  https://github.com/<repo>/releases/download/<tag>/<file>

Until this runs, updateRepo still names the upstream project
(ccch1mneyyy/dsh-go), so a build would check somebody else's releases and
report "up to date" forever - which is exactly the P1 symptom.

What this changes:
  - app/lib/update/update_config.dart: updateRepo
  - the release-URL literals in test/update/ and two other tests, which spell
    the repo out because they assert the exact URLs the encoder produces

The repository must be public: /releases/latest is read anonymously, and a
private repo answers 404.

Usage:
  python tools\\set_update_repo.py <owner>/<repo>
  python tools\\set_update_repo.py <owner>/<repo> --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "app" / "lib" / "update" / "update_config.dart"
TEST_DIRS = [ROOT / "app" / "test"]

# The repo the build currently names. Everything below swaps it for the new one.
CURRENT = "ccch1mneyyy/dsh-go"
CURRENT_MARKET = "ccch1mneyyy/dsh-go-market"

# Files that mention the repo as a *sized fixture*, not as a URL to follow:
# test/share/qr_logo_test.dart pins QR version and module size to a 58-byte
# string, so a longer slug silently changes what it asserts. Leave it alone.
SKIP = {"app/test/share/qr_logo_test.dart"}


def slug_ok(slug: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+", slug) is not None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="owner/repo, e.g. wuwei-123/dshbianjie")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    slug = args.slug.strip().strip("/")
    if not slug_ok(slug):
        print(f"not an owner/repo slug: {slug!r}")
        return 2

    if not CONFIG.exists():
        print(f"missing {CONFIG}")
        return 2

    edits: list[tuple[Path, int]] = []

    # 1) the one constant the app compiles in
    text = CONFIG.read_text(encoding="utf-8")
    new = re.sub(r"(const updateRepo = ')[^']*(';)", rf"\g<1>{slug}\g<2>", text)
    if new == text and f"const updateRepo = '{slug}';" not in text:
        print("could not rewrite updateRepo")
        return 1
    if new != text:
        edits.append((CONFIG, 1))
        if not args.dry_run:
            CONFIG.write_text(new, encoding="utf-8")

    # 2) test literals that spell the release URLs out
    for root in TEST_DIRS:
        for path in sorted(root.rglob("*.dart")):
            if path.relative_to(ROOT).as_posix() in SKIP:
                continue
            old = path.read_text(encoding="utf-8")
            if CURRENT not in old:
                continue
            done = old.replace(CURRENT, slug)
            if done != old:
                edits.append((path, old.count(CURRENT)))
                if not args.dry_run:
                    path.write_text(done, encoding="utf-8")

    # 3) fixtures: release_test parses a recorded GitHub API answer, so the
    #    URLs inside it must name the same repo the encoder builds.
    for root in TEST_DIRS:
        for path in sorted(root.rglob("*.json")):
            old = path.read_text(encoding="utf-8")
            if CURRENT not in old:
                continue
            done = old.replace(CURRENT, slug)
            if done != old:
                edits.append((path, old.count(CURRENT)))
                if not args.dry_run:
                    path.write_text(done, encoding="utf-8")

    print(f"update channel -> {slug}")
    for path, n in edits:
        print(f"  {path.relative_to(ROOT).as_posix()}  ({n} {'constant' if n == 1 else 'literal(s)'})")
    if args.dry_run:
        print("\ndry run: nothing written")
        return 0

    print("\nNext:")
    print("  1. make the repository public, and create a release with")
    print("     update.json + SHA256SUMS + the APK attached")
    print("  2. rebuild, install, and tap 检查更新 on the phone")
    print(f"  3. confirm https://api.github.com/repos/{slug}/releases/latest answers 200")
    print("\nThe submission-guide link still points at the upstream market repo:")
    print(f"  app/lib/ui/plugins/market_tab.dart  marketSubmitUrl ({CURRENT_MARKET})")
    print("  Change it if you host your own plugin market.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
