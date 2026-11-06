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
