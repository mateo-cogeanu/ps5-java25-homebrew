# Bound VM-owned libc memory on PS5 (0103)

PS5 SDK services such as pthread creation allocate outside HotSpot's page/direct
fallback. A libc-first VM allocator can keep consuming libc storage until a
later SDK allocation fails, even when Java heap space and other memory pools
are available. A native thread creation trace records successful attribute
acquisition followed by repeated EAGAIN/errno12; it does not identify the exact
SDK allocation or prove a global thread-count limit.

0103 caps HotSpot raw allocator libc ownership at2MiB, counting each compact
prefix and in-flight malloc/realloc reservation. An atomic compare/exchange
reservation never overspends the cap. Requests beyond it go through the existing
small slabs/page backend and bounded direct fallback. A failed libc allocation
returns its charge before the page retry; failed growth returns its extra charge
and preserves the original allocation/data if replacement also fails. Free
returns the full actual charge after libc free. Libc shrink retains its actual
capacity charge until successful growth/migration/free; mapped shrink keeps its
existing behavior. Header layout, NMT/pre-init format and errno contracts remain.
No static memory reserve, SDK allocator interposition or thread lifecycle change.

This cap does not reserve or guarantee2MiB for SDK services. Non-VM allocations
and OS memory/resource limits can still cause refusal. Moving VM blocks to pages
may increase mapping/slab pressure; the existing shared direct ledger remains
bounded at128MiB/2048slots. Java heap/metaspace/code-cache mappings are unchanged.
There is no OOM suppression or compiler/thread creation bailout. Consumer heap
sizing is separate configuration and must be checked together with native load.

Validation: actual allocator plus os.cpp/NMT model under ASan/UBSan, prefix-inclusive
cap boundaries, libc growth/shrink/migration, allocation/growth refusal rollback,
concurrent held reservations and complete cleanup. Existing actual allocator/
direct-kernel-model fault and concurrent lifetime tests pass. Historical prefix
comparison reverses0103and0101for its old-format control; fixed workload/alignment
models retain earlier savings. Exact forward patch application and target HotSpot
build pass. Actual PS5 SDK headroom/thread creation, page usage, GC/performance and
long-running stability remain pending. A host model is not console validation.
