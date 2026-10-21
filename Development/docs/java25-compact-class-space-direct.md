# Compact class-space direct fallback (0108)

The first Paper consumer capture aborts inside JNI_CreateJavaVM before any game
code starts. The recorded build095 run reports `Could not allocate compressed
class space: 33554432 bytes`; native traces show repeated32MiB anonymous reserve
ENOMEM and the final aligned reserve failure. It requests384MiB Java heap and
32MiB compressed class space. This establishes the reservation failure, not a
measurement of total free physical memory or a global PS5 memory limit.

0108 extends the existing bounded direct-memory backend at the final
Metaspace::reserve_address_space_for_compressed_classes fallback. It is gated
to PS5 AMD64, compact object headers, an ordinary reservation failure with
ENOMEM, and a range within CompressedKlassPointers::max_klass_range_size.
Optimized placement and ordinary aligned mapping stay first. Fixed-address,
non-compact, Java heap and executable allocations are not changed. The original
Mojang and consumer upstream server artifacts are unaffected.

Compact headers encode narrowKlass relative to the class-region base; unlike
zero-based placement this permits a non-fixed range at the direct-map address.
The normal subsequent class-space initialization, pointer encoding and
protection-zone setup remain in force. No class pointer or encoding checks are
removed. The existing direct ledger reserves physical storage with metaspace
alignment (4MiB in this port), zeroes it and applies PROT_NONE before recording
an mtClass NMT reserve and returning ReservedSpace. Existing commit/protect paths
remain; the region is tagged metadata so subrange uncommit zeroes/protects it
rather than replacing direct storage with anonymous MAP_FIXED. Release uses the
existing exact-size backend ownership dispatch.

The class mapping shares the existing128MiB/2048-slot native direct ledger; no
new pool or raised budget is introduced. A32MiB successful reservation consumes
32MiB physical backing immediately, even when logical committed class metadata
is smaller. This leaves less direct budget for non-class metadata, native buffers
and thread stacks. Cleanup failures retain bounded ownership/budget, and failed
allocation/map/protect still fails reservation. The change cannot guarantee VM
creation, Paper startup or sustainable native headroom.

Host tests execute the actual class-space reservation function, real shared
ledger and actual native release dispatcher under ASan/UBSan with controlled
kernel APIs over real aligned storage. Cases include32MiB reservation,4MiB
alignment,mtClass NMT event, initial inaccessible/zeroed storage, subrange
uncommit/recommit with adjacent-data preservation, exact-release enforcement,
shared budget refusal, ordinary-success/non-ENOMEM/non-compact/range gates,
allocation/map/protect rollback and failed-release retention. Arithmetic
roundtrips cover compact22-bit/shift6 range offsets; this is not compiled full
HotSpot classloading/GC/NMT lifecycle proof. Existing non-class metadata tests
also pass. Target HotSpot compiles and exact patch application is checked.

Next actualPS5: VM creation with the new class-space marker, class loading and
C1 compilation, then consumer server/plugin operations and persistence. Other
native allocation failures and the128MiB shared budget can still stop progress.
Frozen passing snapshots remain unchanged. Console validation is pending.
