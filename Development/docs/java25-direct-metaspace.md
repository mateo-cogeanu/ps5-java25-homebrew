# Direct-backed non-class metadata fallback (0104)

A PS5 capture fails an ordinary4MiB metadata reservation with ENOMEM during
startup, while class metadata uses about94MiB and compressed class space about
17MiB.0104targets this reservation path rather than reducing the consumer heap.

MemoryReserver retains the ordinary route first. Only a null-address,
non-executable mtMetaspace reservation ending in ENOMEM can use the existing
shared direct-memory ledger. Heap, compressed class space (mtClass), executable,
fixed-address and other-tag requests are excluded. Kernel physical/map alignment
uses the actual requested power-of-two alignment (4MiB in the observed case),
with no fixed mapping. Default raw/ZIP/image mapping alignment remains16KiB.

The fallback zeroes the new physical backing, protects it PROT_NONE, records a
normal NMT reservation and returns an ordinary ReservedSpace. Existing PS5 commit
uses mprotect RW, retaining commit limits/masks and NMT handling. For direct
metadata subranges, uncommit zeroes only unused granules and protects them NONE;
physical backing stays owned and charged to the ledger until whole-region release.
Logical committed counters therefore do not measure its held physical bytes.
Recommit sees zeroes while adjacent data stays intact. Existing Metaspace locking
protects the range lifetime; lookup alone does not pin it.

Whole-region release uses exact ledger ownership and unmap-before-physical-release.
Partial releases are refused, never passed to ordinary munmap. Cleanup refusal
retains the existing bounded ownership/budget rules. Initial protection failure
rolls back before publishing a ReservedSpace or NMT reserve event. The existing
128MiB/2048slot shared pool is unchanged; no independent metadata pool/reserve,
OOM suppression or executable/heap/class-space fallback is introduced.

Tests use actual MemoryReserver reservation code, direct ledger/helpers and OS
release dispatch over real aligned storage and controlled kernel calls under
ASan/UBSan. They check4MiB alignment, nonzero backing zeroed before first commit,
PROT_NONE access faults, zeroed subrange recommit/adjacent data, purpose/error/
fixed/executable gates, NMT reserve event, failure rollback and exact release/
cleanup retention. Existing allocator/NMT/direct fault-concurrency, metadata-hint
and historical prefix tests pass. Exact patch application and target HotSpot
build pass. These tests do not run a full target VM on host. Actual PS5 mapping,
protection/commit/reclaim/NMT behavior, memory pressure and stability are pending.
