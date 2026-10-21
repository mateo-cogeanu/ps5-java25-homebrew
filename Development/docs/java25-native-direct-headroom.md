# Native direct-memory headroom (0111)

The shared PS5 native-data ledger now permits256MiB of held backing instead of128MiB. This is a ceiling, not a reservation or available-memory claim. The2048-entry limit, in-flight accounting, exact ownership, failed-cleanup retention, type12 CPU read/write mappings and non-replacing address hints remain unchanged. Java heap and executable mappings remain excluded. Dedicated thread-owner budgets remain unchanged.

Budget/slot refusals now increment a separate policy_rejections counter. Kernel failures retain their existing counter and native result; a zero kernel-failure count does not establish spare ledger capacity.

Host validation exercises the actual allocator and ledger under ASan/UBSan: mixed data/metadata owners pass the old128MiB boundary, fill256MiB exactly, reject another page without a kernel allocation, recover capacity on exact release, and clean up fully. Existing concurrent allocation, slot, rollback and failed-release controls remain. Metadata/class-space and attached-worker stack ABI regression checks also pass. The target HotSpot rebuild passes.

Actual PS5 backing availability, higher peak residency, class loading, GC, thread cleanup and sustained stability still require console validation. The increased allowance does not guarantee allocation success or eliminate other process limits. Frozen passing snapshots are preserved.
