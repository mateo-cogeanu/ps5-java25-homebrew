# Java 17 platform synchronization on PS5

Build 027 captured a main-stack return address immediately after the
pthread_mutex_lock import call in Mutex::lock_without_safepoint_check.
Other captured addresses place the call in class metadata allocation.
The exact native mutex initialization result from that run is unknown.

The active PS5 Java 17 PlatformMutex and PlatformMonitor implementations
lease real objects from the Java 25 synchronization pool design. The
runtime initializes up to 4096 mutexes and 4096 conditions early, after
setting their native attributes. Each lease retains its own native
object through lock, wait and release. Exhaustion falls back to normal
native initialization. The checked constructors record refusals before
an uninitialized object can reach a lock or wait in a release build.

The host sanitizer fixture passed forced late initialization refusal,
pool exhaustion, locked-mutex release rejection, reuse and concurrent
lease tests. Exact PS5 startup and the Minecraft title screen require
consumer 028 validation.
