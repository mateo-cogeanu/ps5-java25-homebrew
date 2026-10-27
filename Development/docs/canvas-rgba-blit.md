# Tiled canvas RGBA upload

`Canvas::blit_rgba` accepts a complete top-row-first1920×1080 RGBA8 frame,
with an optional row pitch in pixels. It validates the entire input before
writing and converts into the existing VideoOut tiling. Empty, short or
undersized-pitch input returns false without changing the canvas.

This reusable presentation primitive avoids millions of individual rectangle
calls for offscreen renderer readback. It changes no VideoOut ownership,
mapping, submission, cleanup or frozen snapshot. The existing cached staging
canvas and sequential SSE publication into write-combined scanout remain.

`python3 tools/test_canvas_blit.py` checks every pixel at1080p, padded rows,
short input, invalid/overflow-size pitch and unchanged destination on rejection
under ASan/UBSan. Consumer toolkit/readback and actual PS5 presentation timing
require independent validation; this primitive does not establish a console pass.
