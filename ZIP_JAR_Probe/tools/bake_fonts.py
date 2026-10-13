#!/usr/bin/env python3
"""Bake antialiased Inter glyphs for the native renderer (requires Pillow)."""
from pathlib import Path
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]

def main():
    output = ROOT / "build/native/fonts.hpp"
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["// Generated from Inter (SIL Open Font License).", "#pragma once", "#include <cstdint>",
             "namespace ui_font {", "struct Glyph { unsigned offset; short x,y,w,h,advance; };",
             "struct Font { const Glyph *glyphs; const std::uint8_t *alpha; unsigned size; };"]
    for size in (20, 24, 30, 42, 64):
        font = ImageFont.truetype(str(ROOT / "assets/fonts/Inter.ttf"), size)
        font.set_variation_by_axes([14, 600 if size >= 42 else 450])
        pixels = bytearray()
        glyphs = []
        for code in range(32, 127):
            ch = chr(code)
            mask, (x, y) = font.getmask2(ch, mode="L", anchor="la")
            width, height = mask.size
            glyphs.append((len(pixels), x, y, width, height, round(font.getlength(ch))))
            pixels.extend(bytes(mask))
        lines.append(f"inline constexpr Glyph glyphs_{size}[] = {{")
        lines.extend("{" + ",".join(map(str, glyph)) + "}," for glyph in glyphs)
        lines.append("};")
        lines.append(f"inline constexpr std::uint8_t alpha_{size}[] = {{")
        lines.extend(",".join(map(str, pixels[i:i + 64])) + "," for i in range(0, len(pixels), 64))
        lines.append("};")
        lines.append(f"inline constexpr Font font_{size}{{glyphs_{size},alpha_{size},{size}}};")
    lines.append("inline const Font &get(unsigned size) { switch(size) {")
    for size in (20, 24, 30, 42, 64):
        lines.append(f"case {size}: return font_{size};")
    lines.append("default: return font_24; } }\n}")
    output.write_text("\n".join(lines) + "\n")
    print(f"Baked Inter fonts: {output}")

if __name__ == "__main__":
    main()
