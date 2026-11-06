# Optional native direct mapping capacity

ProsperoCraft 233 reached Fabric 26.3 gameplay and later stopped on a C2
compiler arena allocation of 32,664 bytes. The retained runtime trace recorded
2,048 more successful mappings than releases, with policy rejections and
approximately 248 MiB of native direct storage held alongside the separate
1,536 MiB Java heap. Exact ownership of the retained mappings is unresolved.

Patch 0141 adds a bootstrap-only
`JVM_PS5SetExtendedNativeDirectBudgetEnabled` opt-in. The original 2,048 slots
and 256 MiB native budget remain the default. Explicit selection permits
4,096 slots and 512 MiB native storage. The fixed ledger metadata grows.
The setter locks policy selection and returns EBUSY after the first mapping
attempt, including a rejected attempt.

The Java heap budget, real kernel allocation, mapping ownership, failed
cleanup retention and native fallback eligibility retain their existing
behavior. The larger limit permits allocations and does not reserve or prove
available console RAM. Reports include the selected ledger capacity and budget.

Actual header host checks run both policies with forced ordinary allocator
refusal, real backing storage, slot and byte exhaustion, late setter rejection,
rollback and release faults, data preservation and concurrent lifetimes under
ASan and UBSan. PS5 Fabric gameplay, compiler pressure, save and endurance
validation are pending.
