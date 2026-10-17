# Bounded temporary class-byte storage

Patch0069 gives PS5 byte-array class definition entry points (`defineClass0`
and `defineClass1`) a4096-byte local buffer. Nonnegative class lengths through
4096 use it; larger classes retain the existing libc/mmap allocator. Negative
lengths and null arrays retain their existing exceptions. `GetByteArrayRegion`
still checks offsets/ranges and copies bytes; JVM class definition and bytecode
verification are unchanged. Direct-buffer definition retains its caller-owned
storage path. Cleanup frees only dynamically owned storage.

This avoids a fresh16KiB anonymous mapping for small generated class files
when libc refuses temporary storage. It does not create more native capacity
or repair exhaustion in HotSpot metadata. Each active definition adds4KiB to
its native frame, including recursive class-loading calls. This is bounded
per call, not a total recursive stack bound; normal JVM stack protections are
retained. The consumer worker already uses an8MiB native stack.

The actual ClassLoader.c JNI fixture runs with UBSan and `-Xverify:all`:
ordinary and hidden small classes execute with both backends refused;
large classes exercise heap/mmap success and genuine OOM; zero/4096 invalid
classes reach real ClassFormatError;4097 requires backend storage; range,
malformed-class, long UTF-source and direct-buffer cleanup checks pass.
Target hotspot/java.base-libs rebuild passes. PS5 startup/save/stop and stack
behavior still require console validation.
