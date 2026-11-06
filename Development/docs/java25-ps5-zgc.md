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
