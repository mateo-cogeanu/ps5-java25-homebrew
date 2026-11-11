# Java 17 Parker synchronization leases on PS5

The Minecraft 1.20 probe's build 035 reproduced the build 034 native SIGBUS.
Its worker stack sample captured an address immediately after the call to
`PlatformParker::~PlatformParker` in `JavaThread::~JavaThread`, followed by
the deleting destructor and worker teardown addresses. The target
disassembly shows that the Parker destructor calls the two condition
destructors and ends with a tail jump through the imported
`pthread_mutex_destroy`. The faulting PC is outside the probe ELF. The
sample points to Parker teardown and does not establish which native
destructor faulted or whether native initialization had returned an error.

Patch 0019 uses the existing native mutex and relative condition leases
for the Java 17 PS5 Parker. It adds 256 early default-clock condition
slots for absolute waits. The existing relative pool keeps its configured
clock, and each lease retains native initialization as a fallback when
its pool has no available slot. Constructor and destructor return codes
are checked in product builds. A refusal records the failing operation
and status before the VM stops. An unsuccessfully initialized handle
cannot reach the normal destruction path. Existing wait, timeout, wakeup
and thread retirement rules still apply.

This change is scoped to PS5 Java 17. Java 21 and Java 25 use their
existing code. Console validation must confirm that the earlier teardown
crash is gone and that Minecraft reaches its title screen and shuts down.

The host sanitizer fixtures used real pthreads to check pool exhaustion,
forced initialization refusal, separate clock domains, wait and wakeup,
locked mutex refusal and concurrent reuse. The extracted Parker lifecycle
stopped before destruction on refused initialization and completed 512
pooled constructor/destructor cycles while native initialization was
forced to fail. The Java 17 target build and the Java 17 and 21 ordered
patch replay checks passed.
