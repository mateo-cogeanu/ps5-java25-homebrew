# Variable-sized verifier reserve (runtime129)

Consumer126 still fails verifying original org.joml.Matrix4f, now site3560
(CCinit) with native2048byte allocation failure. Its previous-run native log
also records failed226,1006and2016byte allocations. The runtime128 reserve
only serves requests fitting one256byte slot including the header, so it
cannot cover this observed verifier workload.

Patch0129 preserves the default-off setter and4MiB BSS arena, but leases
contiguous256byte units for variable-sized requests. Allocation metadata is
bounded (bitmap plus32KiB run-length array), protected by an allocation-free
lock. Matching frees return whole runs, so adjacent free units can be reused
for larger buffers. Normal malloc remains first; reserve exhaustion, requests
too large, or disabled policy retain the existing anonymous fallback and OOM.
There is no extra direct-memory backend or increased Java heap. This does not
identify the cause of PS5 libc refusal or prove the whole mod set fits.

ASan/UBSan tests cover tiny-slot exhaustion, whole-arena allocation after reuse,
observed medium/large sizes, zeroing, overflow and80000 concurrent cycles.
The actual unmodified legacy verifier checks the original publisher Matrix4f,
Matrix4d,Matrix3f,Quaternionf andVector3f classes with libc and anonymous mappings
both denied while the reserve is enabled, and verifies all allocations are
released. Existing default-off success and OOM paths are also checked.
Target java.base native libraries rebuild. Consumer127 pins/enables this runtime;
actual PS5 Fabric launch/world/save/endurance remain pending. Preserve prior
candidates and milestones; raw reports and downloaded JARs stay local.
