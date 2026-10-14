#!/usr/bin/env python3
"""Render the actual native UI on a Mac with synthetic controller input."""
import os
from pathlib import Path
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def main():
    subprocess.run(["python3", str(ROOT / "tools/bake_fonts.py")], check=True)
    executable = ROOT / "build/native/preview"
    subprocess.run(["/usr/bin/clang++", "-arch", "x86_64", "-std=c++20", "-O2",
                    "-Wall", "-Wextra", "-Werror", "-DHEAP_LIMIT_TEST", "-I", str(ROOT / "src"),
                    "-I", str(ROOT / "native/renderer"), "-I", str(ROOT / "build/native"),
                    str(ROOT / "native/main.cpp"), str(ROOT / "native/renderer/demo_renderer.cpp"),
                    str(ROOT / "tools/preview_native.cpp"), "-o", str(executable)], check=True)
    for mode in ("home", "detail", "collections", "appearance", "disconnected"):
        subprocess.run([str(executable)], cwd=ROOT, check=True,
                       env=dict(os.environ, UI_PREVIEW_SCENE=mode))
        raw = (ROOT / "build/native/preview.rgba").read_bytes()
        assert len(raw) == 1920 * 1080 * 4
        image = Image.frombytes("RGBA", (1920, 1080), raw)
        image.save(ROOT / f"build/native/preview-{mode}.png")
    print("Rendered home, dialog, both pages, and disconnected-controller state.")

if __name__ == "__main__":
    main()
