# Optional verifier small-allocation reserve (runtime128)

Consumer125 Fabric26.2 failed while verifying org.joml.Matrix4f (site4221,
errno12). Its native report shows repeated 24-byte allocations backed by
16KiB anonymous pages, then anonymous mapping exhaustion. This is native
allocation pressure, not evidence of Java heap exhaustion; the underlying
libc refusal and total title quota remain unproven.

Patch0128 adds an independently enabled, default-off verifier reserve. After
libc refuses an allocation, requests including their aligned header that fit
256bytes can use one of16384 fixed aligned slots (4MiB BSS plus bitmap/lock).
Larger allocations and exhausted reserves keep the existing anonymous fallback.
No new direct mappings or changes to Java heap, GC, class verification decisions
or official JARs. Matching cleanup returns slots, including verifier error cleanup.
The consumer explicitly calls JNU_PS5SetVerifierSmallReserveEnabled before JVM startup.

Host ASan/UBSan exercises default-off failure, full exhaustion, zeroing, overflow,
reuse and80000 concurrent allocation/free cycles. Existing actual verifier pool
and real org.joml.Matrix4f legacy verifier tests pass with reserve disabled.
Target java.base native libraries rebuild. PS5 Fabric startup, world lifecycle
and sustained memory behavior remain pending. This is bounded mitigation, not
a claim that all native memory pressure or mod incompatibilities are solved.
