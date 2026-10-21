# Directory buffer fallback (0106)

A PS5 capture reaches server initialization after successful direct metadata and
Java thread-stack creation, then java.io.File.list returns null with native
errnoENOMEM. The caller assumes an array and throws NullPointerException.
The old open diagnostic did not distinguish fd/context/buffer failure, so it
does not prove which allocation failed.0106targets the remaining buffer path
and adds that distinction; actual PS5 repair remains pending.

The shared PS5 directory helper maps a descriptor context and a64KiB kernel
record buffer. Each now has separate backend ownership. Ordinary mappings stay
first; only ENOMEM can use the existing VM direct-memory C ABI/shared ledger.
Context mapping length is rounded to16KiB; data remains page-aligned. Closing or
partial initialization releases each allocation through its matching backend,
with original error/real failure retained. Refused direct budget returns failure,
not a fabricated empty or partial directory. Kernel open/read/parser/filter/EOF
behavior is unchanged. Open errors now distinguish1=fd,2=context,3=record buffer.
An fd-level ENOMEM cannot be fixed by buffer fallback.

Both java.io and NIO compile the same helper. PS5 libnio explicitly links libjvm
for the existing shared VM C ABI; other targets retain their old dependencies.
There is no new pool, VM export or unbounded allocation; the existing128MiB/
2048slot ledger and cleanup-refusal ownership rules apply. Non-PS5 helper builds
retain ordinary mapping behavior. Game/data files are not removed or rewritten.

Validation uses actual File.list/listFiles JNI with -Xcheck:jni/UBSan, real host
entries serialized to the PS5 record layout, and actual VM C ABI/shared ledger
over controlled kernel allocations. Forced ordinary context/data mapping refusal
still yields351exact Unicode names, converter-style .dat filtering and empty
listings across repeated lifetimes; partial direct budget rolls back without
fd/map/direct ownership leaks. Earlier open/read/partial-read/close/map failures,
symlink paths, array growth and recovery remain checked. Actual NIO JNI/Files.walk
normal controls and standalone parser malformed/error/EOF tests underASan/UBSan
pass. Exact patch and targetjava.base native build pass. This does not run the
full target VM/SDK; actual open stage, kernel enumeration/cache/memory pressure,
resource cleanup and stability require PS5 validation.
