# Align Java and native PS5 image readers

Build078reports a controlled failure in VerifyJARs at the server-bytecode
check, after all40official SHA256checks complete. Its report contains
ExceptionInInitializerError without its nested cause. The index-only native
trace confirms a1000498byte index copy instead of the full image. No console
crash is reported for this failure. Raw logs remain local.

## Missed Java side of0099

The native reader now shares only its index through NativeImageBuffer. Java
BasicImageReader still selects MAP_ALL=true by default on64bit systems, omits
its file channel and slices resource data from the index buffer. That mode is
incompatible with the new native mapping. Native-only resource tests did not
exercise this Java/JNI handoff.

Patch0100detects os.name=PS5 and selects the existing Java index/channel path,
even if jdk.image.map.all=true. Desktop property behavior remains unchanged.
It keeps the index-only resident-memory saving, all modules, all ZIP/JAR checks
and the official server JAR. No game transformation or replacement is added.

## Integration regression test

tools/test_java25_image_handoff.py builds actual native image-reader/ZIP/JNI
sources for the host under UBSan and patches the actual Java BasicImageReader
into hostJDK25. Test-only NativeImageBuffer registration opens the real image
and invokes the actual JNI entry under a renamed test binding. There is no
substitute image buffer, decompressor or BasicImageReader. The OS and VM are
host implementations; this is not PS5 execution. UBSan signal interception is
disabled so the host JVM retains its normal fault/safepoint handlers.

The old MAP_ALLbehavior with the real native index reproduces an initialization
error in the exact JarFile input-stream/bytecode-read operation used by the
consumer. Its nested cause is a resource-buffer bounds exception while reading
Unicode NFKC normalization data. This identifies the concrete incompatibility;
078did not preserve its own underlying cause, so that exact console stack is
not claimed as observed.

The fixed PS5-mode Java/JNI reader succeeds with jdk.image.map.all=true forced,
and compares actual Object, Unicode normalization, HTTPS, DTLS and JFR bytes
with extracted target resources. A desktop control uses the ordinary host JNI
map and unchanged Java property behavior. The native ASan/UBSan reader tests
also include Unicode resource identity and the existing partial/error reads
and allocation controls. Target HotSpot/java.base Java/native rebuild passes.

Consumer079also retains up to8nested causes in preflight reports. Host/package
checks do not establish console acceptance: verify-row success, server startup,
joined memory headroom/read latency and eventual two-hour stability remain
pending. Earlier native OOM can still abort if available headroom is exhausted.
