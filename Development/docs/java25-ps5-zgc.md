# Experimental PS5 generational ZGC

Patch 0142 adds opt-in x86-64 PS5 ZGC build eligibility and a PS5 direct-memory
implementation of OpenJDK's physical backing interface. Existing macOS and
other platform implementations remain selected on their own targets.
Configure the separate runtime with `tools/java25_source.py --zgc --build-hotspot`
on a clean pinned source tree. It selects `ps5-zgc`, leaving the normal
`ps5-bootstrap` build configuration available.

The backend allocates 2 MiB physical granules, clears each allocation before
publication and maps the backing at virtual ranges already reserved by ZGC.
Unmapping restores an inaccessible anonymous reservation. Physical backing is
released separately when requested by the collector. A fixed table supports
up to 8 GiB of committed backing. Failed setup or release retains the owned
entry so another request cannot reuse its backing. Mapping errors are fatal,
with the failed address/offset recorded, rather than continuing with an
invalid heap view. Partial successful commits are returned to the collector.

Host ASan/UBSan tests exercise the actual backing helper with real shared
file mappings as the kernel fixture. They verify writes through two aliases,
zeroed allocation, detach/remap preservation, invalid bounds and explicit
allocation/mapping/release failures. Host aliases do not prove PS5 direct-memory
aliasing, exact-address reservations or collector behavior.

The PS5 kernel must accept the collector's address ranges and alias mappings.
Target compilation and a signed application can establish build integration.
They cannot establish console JVM creation, barriers, concurrent relocation,
reference processing, world saving or frame pacing. These need physical tests
of the exact ZGC candidate before any release or Store publication.

The initial 2026-11-06 target build compiled all ZGC HotSpot objects. Its
standalone shared-library link was rejected by the SDK driver's simultaneous
shared/PIE selection. The compiled object set was merged with
`tools/java25_embedded_hotspot.py` and then linked successfully into the signed
ProsperoCraft 237 application. Thus the embedded application link passes,
while the standalone shared-library target remains unresolved. This distinction
also applies when reproducing the build command above.

Consumer237 reports check2 failure with "Failed to reserve1536M address space
for Java heap", before physical heap commitment. Patch0143 selects the native
sceKernelReserveVirtualRange hint API for PS5 ZGC reservations and checks exact
placement. It releases a returned range at an unexpected address, without
replacing occupied mappings. Native unreserve failures stop the VM. The first
16 attempts and all successful native calls record address/size/result so an
unsupported address window can be distinguished from other refusal on console.
The host test uses the actual platform reservation body and checks refusal,
moved-range cleanup and preservation of occupied bytes under ASan/UBSan.
Target compilation and embedded application linking are scoped checks.
Native PS5 reservation acceptance and all collector behavior remain pending.

Consumer238 reports native reservation ENOMEM for a24GiB virtual heap window
starting at4TiB. Patch0144 adjusts only the PS5 x86 address-offset limits to
35..37bits. The current1536MiB maximum heap needs24GiB at16:1, so its selected
heap base is32GiB with a32GiB offset window. Base and offset bits remain
disjoint, and pointer color/phase layout stays the OpenJDK implementation.
The desktop x86 defaults remain42..44bits.

Host tests extract the actual platform selection and color/uncolor functions.
ASan/UBSan verifies all four remap phases, metadata combinations and address
boundaries, with desktop-default controls. This establishes arithmetic only.
PS5 acceptance of the lower virtual window, generated barriers, concurrent
collection and gameplay still need physical validation.

Consumer239 passed virtual reservation and initial physical commitment, then
aborted while mapping128MiB at0x818000000. Patch0145 maps each2MiB granule with
a checked native hint inside the collector's owned reservation. It verifies the
returned address and releases a successfully returned mapping at an unexpected
address. Native result and physical offset are retained for the fatal diagnostic.
It does not continue with a missing heap mapping. The host shared-alias fixture
requires flags0 and covers native mapping refusal/result preservation.
PS5 hint placement and subsequent GC operation remain pending.

Recovered consumer240 reports ERANGE from the exact-placement check: the
native mapping succeeded but returned a different address. Patch0146 retains
the existing direct-memory allocation and, after safely cleaning an unexpected
mapping, falls back to a shared fixed mapping of its physical offset through
/dev/dmem0. Only the existing collector-owned reservation may be replaced.
The device descriptor is opened lazily under the backing lock and closed with
the backing. Device open and mapping refusal retain the physical allocation
and stop heap initialization with the recorded error.

The actual helper's host tests verify fallback aliases, preserved bytes,
unexpected hint cleanup, device-open and device-map refusal, and descriptor
teardown under ASan/UBSan. They model the device with shared backing files,
so native device access and GC still need PS5 validation. Native FTP inventory
confirms that the console exposes /dev/dmem0; title access is unverified.

A direct-memory device mapping example is documented in this independent
PS5 research source. It motivates the candidate and does not establish a
ProsperoCraft console pass.
https://github.com/ZigZagBoi1/PS5-14.10-Research/blob/master/docs/FINDINGS.md

Consumer241 reached Vanilla26.3 gameplay, saved and then rejoined. The user
reports strong first-run performance and quick saving, followed by stutter
and a crash after rejoin. The retained fatal report identifies reservation
restoration after detaching a physical view. GC logs also show allocation
stalls near140..175ms before failure; their complete cause is unproven.

Patch0147 replaces the remaining anonymous fixed mmap restoration with
sceKernelMunmap followed by a checked native virtual reservation. Physical
backing ownership and other aliases are retained. A moved reservation is
released and treated as failure. Native detach/reserve/cleanup errors remain
fatal and record their result. The host backing test covers detach refusal,
native reserve refusal, moved-range cleanup and surviving-alias data.
PS5 repeated collection, world save/rejoin and frame pacing remain pending.

Consumer242 Fabric26.3 exhausted all12,288 primed HotSpot mutexes during
compilation of an LWJGL generated binding. Its fatal report lists14,718
compiled methods. ZNMethodData embeds two ZReentrantLock instances per method,
each previously backed by a native PlatformMutex. This is a substantial
source of native synchronization demand; the report is not a complete census
of native owners.

Patch0148 gives PS5 ZReentrantLock a distinct atomic lock word, retaining its
existing per-object owner and recursive count. A contended acquire uses bounded
pause iterations then native yield. Release publishes prior writes before the
word becomes available. Other ZGC lock classes and other platforms retain
their native implementation. No shared stripes or new lock ordering are used.

The actual class and inline bodies pass host ASan/UBSan checks with32,768
identities, recursion, publication, contention and400,000 concurrent updates.
A desktop control still constructs the original lock member. Target builds
check the PS5 atomic/yield calls. Fabric startup, GC, saving and contention/frame
pacing remain physical-console validation.
