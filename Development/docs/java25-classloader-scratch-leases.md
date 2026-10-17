# Reusable class-definition scratch leases

Patch0070 adds four aligned32KiB temporary buffers to ClassLoader.c on PS5.
After libc allocation refusal, a request through32KiB attempts a nonblocking
atomic lease. A successful caller owns its buffer exclusively until cleanup.
The header identifies a pool lease; release returns it with release ordering.
Concurrent or recursive callers cannot reuse an active lease. Pool exhaustion
and larger requests use the existing real mmap path and retain genuine OOM
if it also fails. The4KiB per-frame class-byte path from0069 remains.

The fixed storage costs about128KiB of BSS plus headers/lease words. It avoids
repeated mappings for medium class-file/UTF scratch; it is not a measurement
or enlargement of the native memory budget. It can shift failure to later
metadata allocations. No class verification, JNI copying or game checks are
removed. Pool acquisition has no heap, TLS or lazy mutex initialization.
The console must still validate memory backing and full startup behavior.

Validation: actual helper ASan/UBSan tests cover four simultaneous20257-byte
leases with both backends refused, alignment, intact independent bytes,
complete exhaustion, real mmap fallback,0/1/4097/32768/32769/overflow boundaries,
reuse and concurrent lifetimes. Actual ClassLoader.c JNI UBSan/-Xverify:all tests
execute medium ordinary/hidden classes repeatedly with both backends refused,
retain >32KiB heap/mmap/OOM paths and malformed/range/direct-buffer checks.
Target HotSpot/java.base-libs rebuild passes. Host tests do not prove PS5
memory availability, recursion endurance or actual server readiness/save/stop.
