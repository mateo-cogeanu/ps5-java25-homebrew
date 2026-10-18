# Bound PS5 arena chunk retention and retry after reclaim

Consumer067 aborts on C1 CompilerThread0 at66.53seconds: os::malloc cannot supply
32664bytes for Chunk::new. The actual native allocator also reports refusal of
the rounded32768byte mapping with errno12 after idle raw slabs are trimmed.
This is native allocation failure, not a Java socket or Java heap exception.
Native resource maxrss_raw reaches512096; exact units/title ceiling remain
platform-dependent. Raw reports stay local.

The existing ChunkPool caches every returned standard-sized arena chunk until
its five-second cleaner. Patch0091 bounds PS5 retention to eight chunks in each
of the four size classes. Excess chunks are immediately freed under the existing
pool/NMT lock. Pool take/prune maintain the cached count. A real allocation
refusal now clears all unused arena pools and retries the real allocator once
before retaining the original fatal-OOM behavior. Active chunks are never freed
or displaced. Non-PS5 behavior is unchanged. This bounds a concrete retention
source; it does not establish that cached chunks caused all observed pressure
or make the process memory budget unlimited.

`python3 tools/test_java25_arena_pool.py` executes the actual ChunkPool class and
allocation/deallocation functions with explicit host stand-ins for HotSpot
locks, allocator and compilation-statistics interface. ASan/UBSan checks128chunk
bursts in every class, eight-per-class PS5 retention, unbounded desktop control,
prune/reset, cross-size allocation refusal and successful retry, final refusal
without live-chunk corruption and4000 concurrent lifetimes with complete cleanup.
`python3 tools/test_java25_native_heap.py` retains actual raw allocator/NMT model,
16KiB pages, failure and concurrency checks. Target HotSpot/java.base-libs rebuild
passes. Console resolution, compiler peaks and sustained use remain pending.
