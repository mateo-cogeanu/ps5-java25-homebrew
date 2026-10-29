# Optional compiler-TLS direct fallback (runtime130 integration)

Consumer129's retained preceding trace identifies an SDK compiler-rt abort in
__emutls_get_address. The runtime termination anchor gives load delta0x400000;
subtracting it resolves abort return0x2dffbc9 to0x29ffbc9 and the preceding malloc
return0x2dfe551 to0x29fe551 in the exact129symbols. Disassembly confirms the
compiler TLS helper's abort branch and emutls_alloc::allocate's48byte malloc
failure. The adapter already tries anonymous mapping after libc refusal, but
both routes failed for this worker's TLS variable. This establishes the abort
path, not the full cause of libc/anonymous exhaustion or total console quota.

The reusable SDK emutls adapter now offers ps5_emutls_enable_direct(int), disabled
by default. When enabled, an ENOMEM anonymous fallback can use the existing
ps5_native_direct ledger. This shares its256MiB native-data budget/2048entries
with existing native allocations and preserves its separate1536MiB heap policy;
no extra heap budget or executable mappings are introduced. Native map/unmap and
physical-release ownership/rollback remain in that existing implementation.
Cleanup queries direct ownership before ordinary munmap; known direct failures
never fall through to libc. Resize keeps old data/allocation on failure.
Only pinned SDK emutls references are adapted; general libc remains unchanged.

Host ASan/UBSan tests cover the observed16byte payload/48byte prefixed request
with libc+anonymous denied, opt-in/default-off policy, resize preservation,
failed growth, matching cleanup and800concurrent direct lifetimes, plus existing
1600ordinary/map fallback lifetimes. Existing direct ledger fault/rollback/budget/
concurrency tests and actual key/destructor/join lifecycle tests pass. Target
adapter compiles under-Wall-Wextra-Werror with no lazy guard or emulated TLS.
Consumer130 explicitly enables this path before JVM creation and records object,
source and existing-ledger hashes. PS5 launch/world/TLS lifecycle/endurance
validation remain pending. Preserve frozen snapshots and consumer129; no broad
mod compatibility or all-memory-pressure-fixed claim. Raw traces remain local.
