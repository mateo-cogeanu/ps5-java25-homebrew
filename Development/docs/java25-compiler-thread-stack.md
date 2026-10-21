# Owned compiler-thread stacks (0109)

A current PS5 capture shows0108 successfully reserving32MiB compressed class
space through direct memory, with4MiB alignment and zero allocator failures.
VM initialization then reaches thread type3 (compiler_thread) and fails all
ordinary pthread_create attempts: EAGAIN with errnoENOMEM, requested stack1MiB.
The VM aborts with unable-to-create-native-thread before any consumer server
runs. Class reservation success is only partial validation of0108; full class
loading/GC/NMT/protection lifecycle remains pending.

0109 permits compiler_thread alongside java_thread in the existing final
owned-stack fallback. CompilerThread derives from JavaThread and enters through
the same thread_native_entry path; its larger requested stack is kept. The
fallback still requires finalEAGAIN plus errnoENOMEM after ordinary retries.
VM/GC/watcher threads, other errors and successful ordinary creates remain
excluded. There is no compiler disable, stack shrink or change to C1 settings.

The0105 ownership model remains unchanged: non-fixed direct backing, separate
persistent joinable attributes, zeroed explicit stack and normal VM guard setup;
wrapper marks entry return, native reaper joins through real TLS destruction
before releasing storage. Non-return and failed cleanup retain bounded ownership.
Compiler stacks consume the existing32MiB stack-held budget and128MiB shared
native direct budget/2048slots; no additional pool or budget increase. A failed
allocation/attribute/create/join/release does not become a false success.

Host tests compile the actual fallback gate from os::create_thread and cover
Java/compiler/VM/watcher/GC types with ordinary success,EAGAIN/other errors and
ENOMEM/other errno combinations. Actual owned-stack tests run real1MiB custom
pthread stacks with gated TLS destructors and join-before-free,220reclaimed
lifetimes, allocation/attribute/create/join/release faults and slot/budget
refusal under ASan/UBSan. Existing512KiB Java-stack controls also pass. These
are owner lifecycle controls, not a full HotSpot C1 compilation test on PS5.
TargetHotSpot compiles and exact patch application is checked.

NextPS5: createVM, verify actual C1 results and class loading, then consumer
startup/plugin/join/persistence/shutdown checks. SDK thread descriptors/TLS and
native allocations may still refuse even when direct backing exists. Long-run
reaping/compiler/native pressure and earlier class/metadata lifecycle remain
unvalidated. Frozen passing snapshots are unchanged.
