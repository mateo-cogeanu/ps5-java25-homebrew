# Opt-in libjava direct scratch fallback127

Consumer124Fabric26.2 reports failure in RandomAccessFile.open0 while its ZIP
budget reopens a JAR. Platform-string malloc fails and a16KiB anonymous mapping
returns ENOMEM; adjacent class-loader scratch buffers also use anonymous pages.
G1's last sample has about210MiBused of1176MiBcommitted Javaheap. Existing native
direct-memory reports have no failure/policy rejection. This proves a native
allocation failure, not Java heap exhaustion; it does not establish the total
console memory quota or initial allocation owner's leak/peak behavior.

Patch0127adds a **default-off** final direct-memory fallback for the existing
PS5 platform-string and classloader temporary buffers. The consumer may explicitly
call JNU_PS5SetDirectScratchEnabled(1) before Java startup. Normal libc, reusable
classloader leases and anonymous mappings retain precedence. Other platforms and
disabled behavior are unchanged. No Java API or collector/heap policy is changed.

Each of the two Ctranslation units has64static ownership entries and an8MiBbudget
(16MiBaggregate worst case). Only page-aligned temporary mappings are eligible.
Native allocation/map failure rolls back ownership when release succeeds. A
failed unmap or release retains its entry/budget; it never releases backing still
mapped or passes direct storage to libc free/munmap. No retry/recovery of orphaned
entries is claimed. No heap/code/metaspace/game/native-driver allocation is moved.

Checks: actual header under ASan/UBSan with direct-memory boundary fixtures,
disabled/anonymous-first/direct data,size/slot/budget bounds,map rollback and
unmap/release failure ownership; actual JNI platform strings and ClassLoader
conversion/definition tests with direct mode disabled; actual exclusive scratch
lease/concurrency checks; genuine target java.base-libs rebuild. The platform
allocation syscalls remain fixtures on host. Real PS5 allocation/release,Fabric
startup,world/save/endurance validation remain pending. Consumer125enablement,
package/audit and raw reports belong inProsperoCraft; frozen snapshots unchanged.
