# Optional headless ImageIO raster natives

`python3 tools/java25_imageio.py` compiles a bounded subset of the pinned
OpenJDK25 native sources for the PS5 target. It provides the genuine Disposer,
BufferedImage/ColorModel/Raster JNI ID initialization and bundled LCMS color
management implementation. The standard upstream Unix AWT ID initializers are
included for ImageIO registry initialization. No Java/game classes are replaced.

`java25_builtin_runtime.py --imageio` embeds these as resident `awt` and `lcms`
libraries, using the existing library discovery/table mechanism. The genuine
LCMS load hook executes normally. The generic external-probe packager accepts
`headless_imageio: true` only with target `java.desktop` classes; it also installs
the native library images/audit and upstream legal notices. Default probes retain
their existing six core libraries. The Minecraft consumer explicitly opts into
this Java capability through its own build integration.

This is image data/PNG-memory-stream support, not a complete desktop AWT port.
Windows, fonts, printing, Java2D drawing, JPEG and arbitrary codecs are outside
this subset. Unsupported JNI methods remain unavailable; no project success stubs
are introduced. OpenJDK's Unix no-op ID hooks are included unchanged as upstream
platform behavior. Existing core classes/libraries and frozen milestones remain
unchanged. The generic full `java.desktop-libs` build still requires unsupported
printing/toolkit dependencies (including CUPS); this targeted builder avoids them.

`python3 tools/test_java25_imageio.py` builds the same source subset for the host
and forces the JVM's bootstrap library search to use it before ImageIO initializes.
Host-only reflection redirects the NativeLibraries search array; no such change
is made to target classes. The test withholds host AWT/LCMS/font libraries and
checks the load trace to rule out stock-native fallback. PNG RGBA, indexed,
grayscale and RGB streams decode over three cycles, all pixel hashes match the
stock JDK, ICC profile/LCMS conversion works, and malformed input is rejected.
Target C compilation, exported symbols, no-automatic-constructor checks and
consumer package inspection complement this host evidence. Actual PS5 decoding,
color paths, resource release and consumer rendering remain pending.
