# Optional native network-node direct scratch, patch0130

Consumer140's original Minecraft26.2 report records
`OutOfMemoryError: Native heap allocation failed` from
`Inet4AddressImpl.lookupAllHostAddr`, after account-service HTTPS lookup.
The OpenJDK conversion-node allocator already tries libc and anonymous pages;
those can both fail under native pressure while the Java heap still has room.
This is not proof of total memory availability or a resolved allocation leak.
Consumer raw logs and game integration remain in ProsperoCraft.

Patch0130 gives the existing DNS/interface conversion-node allocator an
independent default-off policy. A consumer explicitly calls
`JNU_PS5SetNetworkScratchEnabled(1)` before JVM startup; its flag is separate
from the libjava temporary-buffer flag. Existing libc and anonymous allocations
remain first. On anonymous ENOMEM only, the allocator reuses patch0127's bounded
direct-memory scratch implementation and paired release function. No DNS answer,
resolver retry, authentication policy, Java heap/GC or process-wide allocator is
changed. Non-PS5 and disabled paths retain their previous allocation behavior.

Inet4AddressImpl, Inet6AddressImpl and NetworkInterface each have an independent
64-entry/8MiB ledger (24MiB aggregate maximum), separate from libjava's two
existing ledgers. Nodes retain their aligned common owner prefix for every
allocation kind. Libc blocks go to free; anonymous mappings go to munmap; direct
mappings use their exact kernel unmap/release pairing. Exhaustion and overflow
still fail. Failed cleanup retains bounded ownership/budget as in0127; no orphan
recovery or universal native-memory cap is claimed. No broad network or game
compatibility claim follows from this change.

Host tests exercise the actual node header and actual scratch mapper with
forced malloc/anonymous ENOMEM: default off, libc/anonymous precedence, direct
node data/errno, overflow/64slots, allocation/map rollback and8,000 concurrent
allocation/release operations under ASan/UBSan. Existing scratch cleanup-failure
and budget tests, SDK DNS lookup/result/ownership tests and actual extracted
OpenJDK conversion controls remain required. Platform direct syscalls are host
fixtures. Genuine PS5 java.base-libs rebuild and export/object hashes are recorded
in validation; PS5 lookup/Fabric startup/world/save/endurance remain pending.
Preserve all frozen passing milestone source/packages. Consumer source/pin/
package/audit and raw reports belong in ProsperoCraft, with no Store release.
