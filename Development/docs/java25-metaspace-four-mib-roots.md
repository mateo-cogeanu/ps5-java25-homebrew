# PS5 metaspace reservation granularity

Consumer068 aborts on the server thread at74.03seconds VM uptime, after real
readiness and online authentication during configuration completion. The actual
failure is a16MiB PROT_NONE reservation for non-class metaspace, errno12. The
stack is loading generated protocol classes through GameProtocols.<clinit>.
The last resource maxrss_raw is504384; exact units and title ceiling are not
independently established. Non-class metadata has79.06MiB used in80MiB reserved,
while class metadata has17MiB used in its separate32MiB region. Java heap usage
and class-space free space cannot satisfy a new non-class reservation directly.
The previous C1 arena failure is not recorded in this run. Raw logs stay local.

Patch0092 changes only PS5 metaspace buddy geometry to a4MiB root with13levels,
retaining the1KiB leaf and exact named sizes from1KiB through4MiB. The existing
PS5 one-root node setting then reserves4MiB per non-class growth step and uses
4MiB alignment. Growth policies retain their actual byte sizes, including the
boot loader's4MiB first chunk. Class-space capacity stays32MiB. Other platforms
keep16MiB roots,15levels and their existing node multipliers.

This also reduces PS5's maximum single metadata allocation from16MiB to4MiB;
exceptionally large definitions need separate validation. It does not impose a
4MiB total metadata cap: the list grows additional nodes normally. It does not
relax mapping failures, fabricate metadata or change heap/GC behavior. Smaller
steps can avoid the demonstrated16MiB cliff but do not prove all future join
and sustained-load allocations fit the native title budget.

The target gtest root-level assertion follows the platform root. Product target
HotSpot/java.base-libs rebuild passes. `test_java25_metaspace_nodes.py` compiles
the actual Settings/geometry headers and level-fitting implementation under
ASan/UBSan. It checks every word request through each root size, named sizes,
valid boundaries, leaf/commit sizes, buddy geometry and reservation pressure
models. PS5, desktop64 and desktop32 configuration branches run; VM types,
printing and power-of-two utilities are explicit host stand-ins. The buddy
geometry checks are a model, not execution of the full VM buddy allocator.
`test_java25_metaspace_hints.py` retains actual MemoryReserver control flow with
real non-replacing host mappings and cleanup/denial controls. Console metadata
growth, class-space encoding, joins and two-hour stability remain pending.
