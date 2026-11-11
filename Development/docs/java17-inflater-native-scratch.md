# Java 17 ZIP inflater allocation on PS5

Consumer 033 reported `OutOfMemoryError` in native
`Inflater.inflateBytesBytes` while reading a JAR manifest. The Java heap
held about 42 MB against a maximum of 195 MB. The VM trace also recorded
socket exceptions during startup before the probe returned the inflater
failure. The title screen was not reached.

Patch 0017 routes the PS5 inflater's stream state and zlib allocations
through the existing paired scratch allocator, including zlib's lazy
history window. It uses the same allocation and zero-initialization policy
as the Java 17 runtime image decompressor. JNI exception and zlib status
handling retain their existing behavior. The exact 033 allocation that
failed and the source of the native memory pressure remain unconfirmed.

Host ASan and UBSan checks ran the patched inflater initialization and
cleanup with real zlib, verified byte-exact output across the lazy window
allocation, and forced refusal of stream, state and window allocations.
The PS5 target build passed. Consumer 034 needs row 3 and title-screen
verification on the console.
