# Optional64MiB owned Java/compiler stack budget

Patch0134 adds bootstrap-only JVM_PS5SetExtendedThreadStackBudgetEnabled.
Default remains64 slots/32MiB. Explicit enablement selects64MiB in the same64
slots before initialization; later changes return EBUSY. Setter and initialize
serialize policy freezing. No physical memory is allocated by the setter.

Consumer171's complete native trace was ultimately retrieved through Safari's
read-only HTTP diagnostics. Accounting complete successful create/reap records
shows32MiB held and eight EAGAIN native attempts while that full budget remains
held, followed by GC/emergency shutdown. All stacks are1MiB. This identifies the
existing fallback budget boundary during Sodium/Vitrail terrain failure; the
original native libc stack refusal remains unresolved. The trace supports budget
exhaustion;0133's errno gate is a separate correctness fix, not this run's cause.
File status at retrieval showed192 descriptors, soft/hard12555; no EMFILE claim.

Consumer172 explicitly enables64MiB. Requested stack sizes, guard handling,
actual native pthread_create, native-direct ledger and physical map ownership
remain. Native thread quotas/other resource failures still return real errors.
Only successful joins permit stack release; failed joins or releases retain
ownership and budget. Existing generic native-data budget stays256MiB.
No global allocator/Java heap/GC/mod bytecode changes are introduced.

Host ASan/UBSan tests use the actual stack owner: default rejects the33rd live
1MiB stack, extended admits33 concurrent real custom-stack threads and reclaims
all after join, plus220 lifecycle/TLS destructor/fault cases and budget/slot
controls. Setter default/enable/late rejection and target HotSpot build pass.
Exact PS5 world entry, shader warmup, save/reload, voice, transitions and endurance
remain pending. A larger bound is not proof of compatibility or elimination of
all native exhaustion. Raw reports stay local; release/Store gate remains.
