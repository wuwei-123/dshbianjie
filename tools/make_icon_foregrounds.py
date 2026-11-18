"""Rebuild the adaptive-icon foreground layers from the shipped glyph shape.

Two separate defects in tools/make_icons.py:

1. make_foreground() pasted the whole finished icon - dark rounded tile,
   border and glyph - into the adaptive icon's foreground layer. An adaptive
   icon is two layers: the background gradient (res/drawable/
   ic_launcher_<theme>_background.xml) and a foreground that is the glyph
   alone on transparency. The pasted tile covered the gradient.
2. It then copied one foreground onto frost/ink/night, so all four themes
   showed the same picture. ink and night have dark backgrounds, so the dark
   tile sat on a dark gradient and the glyph vanished.

There is no separate source for the glyph: assets-in/icon-final.png carries a
rounded tile with a hairline border, and app/assets/brand/glyph-mono.svg is a
thin outline - neither matches the solid lemniscate on a phone. The shape that
ships is the one in the pre-rename icons, so its alpha is the source here:

  D:\\dsh-go\\_backup\\src-pre-rename\\app\\android\\app\\src\\main\\res\\
      mipmap-xxxhdpi\\ic_launcher_ink_foreground.png

That file is the 432x432 layer whose glyph covered 27.0..81.0 x 26.8..80.0 of
the 108 grid - the footprint app_icon_picker_test.dart samples. Only the
colour changes per theme; the geometry is preserved by construction.
"""

from __future__ import annotations

import os
import sys

from PIL import Image

BACKUP_RES = r"D:\dsh-go\_backup\src-pre-rename\app\android\app\src\main\res"
RES = r"D:\dsh-go\replica\app\android\app\src\main\res"
SHAPE = os.path.join(BACKUP_RES, "mipmap-xxxhdpi", "ic_launcher_ink_foreground.png")

DENSITIES = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}

# theme -> glyph colour, each readable on that theme's background gradient:
#   (none)/mist  #9AB0E8 -> #405AAD   light glyph
#   night        #2C3D6C -> #0C122D   light glyph
#   ink          #292B30 -> #0D0E11   near-white glyph
#   frost        #FCFDFF -> #DDE5F8   mid blue glyph
GLYPH = {
    "": (199, 213, 251),
    "_night": (193, 205, 250),
    "_ink": (245, 247, 251),   # AppIconArt.of(AppIcon.ink).mono = 0xFFF5F7FB
    "_frost": (130, 152, 229),
}


def shape_alpha() -> Image.Image:
    """The shipped glyph as an L mask, cropped to its bbox."""
    art = Image.open(SHAPE).convert("RGBA")
    alpha = art.getchannel("A")
    box = alpha.getbbox()
    if box is None:
        raise SystemExit(f"no glyph in {SHAPE}")
    return alpha.crop(box)


def layer(alpha: Image.Image, size: int, rgb: tuple[int, int, int]) -> Image.Image:
    """[alpha] tinted [rgb], centred on a [size] square, keeping its aspect."""
    gw, gh = alpha.size
    scale = size / 432.0  # the shape is authored for the xxxhdpi 108 grid
    scaled = alpha.resize((max(1, round(gw * scale)), max(1, round(gh * scale))), Image.LANCZOS)

    canvas = Image.new("L", (size, size), 0)
    canvas.paste(scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2))

    out = Image.new("RGBA", (size, size), rgb + (0,))
    out.putalpha(canvas)
    return out


def main() -> int:
    res = sys.argv[1] if len(sys.argv) > 1 else RES
    if not os.path.exists(SHAPE):
        print(f"missing shape source: {SHAPE}")
        return 2

    alpha = shape_alpha()
    print(f"glyph shape from {os.path.basename(SHAPE)}: {alpha.size[0]}x{alpha.size[1]}")

    written = 0
    for dens, size in DENSITIES.items():
        d = os.path.join(res, dens)
        if not os.path.isdir(d):
            print(f"  {dens:<16} (no such dir, skipped)")
            continue
        for suffix, rgb in GLYPH.items():
            layer(alpha, size, rgb).save(os.path.join(d, f"ic_launcher{suffix}_foreground.png"), optimize=True)
            written += 1
        print(f"  {dens:<16} {size}x{size}  ({len(GLYPH)} themes)")

    print(f"\nwrote {written} foreground layers into {res}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
