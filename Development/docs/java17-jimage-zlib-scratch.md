# Java 17 JIMAGE zlib allocation

Consumer 023 reported zero class-file magic for runtime classes including
DirectMethodHandle$EnsureInitialized and BoundMethodHandle species. This
identifies invalid bytes received by the class parser. The exact PS5
decompression refusal remains unobserved.

ZIP_InflateFully initializes a zlib stream for JIMAGE decompression.
Its default allocator can fail after native libc exhaustion. The caller
asserts decompression success, but release builds can continue without
valid output when decompression fails.

The PS5 Java 17 path now supplies paired zlib callbacks through the existing
native scratch allocator, including overflow checking and zeroed storage.
Other ZIP streams retain their existing policy. Original errors and zlib
cleanup remain.

A host sanitizer fixture exercised the actual callback and inflate function.
It forced the normal allocator to refuse, reproduced Z_MEM_ERROR without
callbacks, decompressed identical bytes with native fallback, and checked
paired cleanup on repeated success, corrupt input and short output refusal.
The Java 17 target and complete LTS patch checks passed. Consumer 024
physical startup and title-screen acceptance remain pending.
