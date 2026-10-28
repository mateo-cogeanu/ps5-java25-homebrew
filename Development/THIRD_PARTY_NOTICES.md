# Community native runtime and renderer

The native title uses the renderer, startup code, allocation bridge, build
converter and source-generated libc runtime from BlackBearReloaded's
[ps5-native-app-boilerplate](https://github.com/blackbearreloaded/ps5-native-app-boilerplate)
at commit `e79502f4ce3c278e41c172fe14b6ffe5164b29d3`.
Copyright (C) 2026 BlackBearReloaded. Licensed GPL-3.0-or-later.
The source is cached at `.tools/native-app`; `make package` fetches the pinned
source when absent. The package includes its GPL license.

The VideoOut renderer is vendored under `native/renderer/`, retaining upstream
attribution, and extended locally with antialiased font coverage and rounded
UI primitives. Its video initialization and tiled framebuffer format are
preserved from the console-tested baseline.

Inter by the Inter Project Authors is bundled under `assets/fonts/` and
licensed under the SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). Glyphs
are baked at build time with Pillow and packaged inside the native executable.
The console package includes `licenses/Inter-OFL.txt`.

The PS5 Payload SDK is by John Tornblom and its contributors, under GPL-3.0+
except otherwise indicated, with BSD-licensed FreeBSD headers. Native builds
use the pinned public SDK v0.42. Controller ABI reference:
https://github.com/blackbearreloaded/ps5-native-gamepad-input-research

The local controller-tester sources are licensed GPL-3.0-or-later. The host
converter links the system zlib library (zlib license); that host library is
not included in the console package. No vendor runtime modules are bundled.

## Optional native storage build tools

The opt-in builder retrieves pinned Zstd JNI (BSD-2-Clause), Zstandard (BSD-3-Clause or GPL-2.0), SQLite JDBC (Apache-2.0; bundled Zentus notice) and SQLite (public domain). Sources are not vendored here. Generated source trees retain upstream notices; consumers must ship the corresponding LICENSE/NOTICE files with embedded libraries. See docs/java25-native-storage.md for pins and restrictions.
