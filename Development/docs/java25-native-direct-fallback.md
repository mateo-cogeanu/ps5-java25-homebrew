# PS5 native allocator direct-memory fallback (0101)

Update: raw direct mapping/release is observed on PS5, but a native ZIP save
allocation then fails. [0102](java25-zip-image-direct-memory.md) extends the same
ledger to ZIP/image temporary buffers. The original0101scope below is historical.

A consumer's current-run fatal report identifies C1 native arena allocation
failure:32664bytes requested, followed by two failed32KiB anonymous-page attempts
with ENOMEM, then Chunk::new abort. The fault occurs124.632seconds into the JVM.
Process-policy queries report32GiB RLIMIT_DATA and unlimited AS/RSS; those are
not measurements of available memory or a physical/flexible-pool hard limit.
Raw reports and account/address fields remain local to the consumer project.

0101 extends only the existing raw HotSpot native allocator's page fallback.
Successful libc allocations and successful ordinary anonymous mappings retain
their existing paths. When anonymous mapping returns ENOMEM, a bounded ledger
can allocate/map real PS5 direct memory for native data. The CPU mapping is RW,
not executable or GPU-accessible by its protection mask; no fixed mapping can
replace existing VM storage. A64GiB address hint is advisory. The Java heap,
metaspace reservation/commit machinery and executable code cache are unchanged.

The kernel calls are declared with the SDK's64-bit offsets/sizes and linked
through its existing libkernel stubs. Allocation uses16KiB granules/type12;
map uses CPU read/write protection and flags0. The API/lifetime reference is the
primary [PS5_Vulkan direct-memory implementation](https://github.com/mihawk-99/PS5_Vulkan/blob/f410e67a0241b3e8edcdbcd2a9b285dfc4a412ed/driver/ps5vk_direct_memory.c).
This is API research, not adoption of a graphics dependency or renderer.
Our allocator/ledger implementation is independent and scoped to native data.

The ledger has2048static entries and a128MiB held-byte budget, including
in-flight calls and failed cleanup. It never preallocates128MiB or uses the
native allocator to allocate its own metadata. Kernel failure/slot exhaustion/
budget exhaustion still return allocation failure. Map failure releases its
physical allocation; a failed rollback retains ownership and budget. Free unmaps
first and releases physical storage only on successful unmap. Failed unmap must
not free backing that remains mapped; failed release keeps its slot/budget and
is an explicit leak pending process teardown, not silently counted as freed.
Wrong-size free is rejected. No active allocation is relocated by cleanup.

Small fallback slabs and large fallback blocks share the same release wrapper,
so both return their direct backing using the recorded physical offset and
exact size. Existing compact raw headers/NMT-preinit compatibility remain intact.
Allocator diagnostics report direct held bytes, mapped/released totals, failure
count and last raw kernel result. Kernel callbacks do no trace IO while the raw
allocator lock may be held; reporting occurs at its existing outer trace point.

## Verification and limits

The ASan/UBSan test executes the actual raw allocator and direct ledger over
real aligned storage, with simulated kernel calls. It covers the exact32KiB
allocation, data-preserving growth/failed growth, small slabs, allocation refusal,
map rollback, unmap refusal, physical-release refusal, budget/entry exhaustion,
4000concurrent allocate/grow/free lifetimes, ordinary-allocation control and
non-ENOMEM refusal. It explicitly observes that failed unmap never releases
still-mapped physical storage. Fault-test cleanup is performed by the fixture;
production does not pretend a failed kernel cleanup succeeded.

The existing raw allocator/os.cpp NMT/preinit regression passes with direct
memory unavailable, retaining ordinary successful mappings and real final OOM.
The exact0101patch applies cleanly and matches the rebuilt source. Target
HotSpot builds and kernel imports are checked separately during packaging.
These host tests do not validate console kernel behavior, direct-memory type/
cache performance, pool permissions, peak headroom, or sustained stability.

Actual PS5 direct mapping/release counters and joined-load stability remain
pending. This does not add a C1 compilation bailout: if all real backends fail,
the original fatal allocation contract remains. Other native-library allocators,
Java-heap pressure and executable-memory commitment can still fail. Preserve
passing snapshots and the prior consumer fallback until console validation.
