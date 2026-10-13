#!/usr/bin/env python3
"""Draw the Interface Lab home-screen tile using the bundled OFL font."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
image = Image.new("RGB", (1024, 1024), (12, 19, 32))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((110, 110, 914, 914), radius=130, fill=(25, 38, 62))
draw.rounded_rectangle((268, 230, 756, 718), radius=140, fill=(109, 156, 255))
font = ImageFont.truetype(str(ROOT / "assets/fonts/Inter.ttf"), 330)
font.set_variation_by_axes([14, 550])
draw.text((512, 475), "S", font=font, anchor="mm", fill=(12, 19, 32))
small = ImageFont.truetype(str(ROOT / "assets/fonts/Inter.ttf"), 44)
draw.text((512, 821), "INTERFACE LAB", font=small, anchor="mm", fill=(211, 224, 245))
image.resize((512, 512), Image.Resampling.LANCZOS).save(ROOT / "sce_sys/icon0.png")
