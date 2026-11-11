# Java 17 hidden class metaspace locks on PS5

Minecraft consumer 027 captured a fault at the pthread lock call during
class metadata allocation. Consumer 028 initialized its early
synchronization pools, reached the original Main and then aborted in
native code. The retained reports do not identify that abort's caller.

The [independent tmghd272 PS5 port](https://github.com/tmghd272/ProsperoCraft/blob/bc7ce9cdb8f3a0a520eae76603cc0ee8897a23fc/tools/build/ps5_jdk_patch.py#L835-L860)
documents reducing native lock demand by sharing a mutex across hidden
classes. Its reported native quota is specific to that port. Patch 0013
implements this resource reduction in the pinned Java 17 port with 32
shared mutexes to reduce contention. Only loader data for non-strong
hidden classes selects a shared mutex. Ordinary loaders and the
bootstrap loader still own individual mutexes. Each shared lock retains
the original rank and safepoint policy. Loader unloading releases its
own metaspace and leaves the shared mutex available for other loaders.
The lock pool size and native allocator behavior are unchanged.

The pinned patch application and PS5 target build passed. The target
class loader object contains a 256-byte table for the 32 lock pointers.
The next console test is Minecraft consumer 029. Check row 3 and the
Minecraft title screen first. Class loading, unloading, throughput and
the cause of the 028 native abort remain unverified on PS5.
