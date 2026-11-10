# Java 17 thread attribute leases

Consumer 025 logged pthread_create returning EINVAL for a detached thread
with a 1024 KiB requested stack, then a native SIGABRT. The preceding
large file buffer OOM was absent. The precise abort site and whether
attribute allocation caused the thread refusal remain unresolved.

The active PS5 Java 17 runtime reuses Java 25's genuine pthread attribute
pool. Thirty-two creation slots and thirty-two separate stack-query slots
are initialized early and borrowed exclusively. Native opaque objects are
passed by address and retained for process lifetime. Exhaustion retains
local initialization and its real failure result. Thread creation checks
attribute acquisition and detach-setting results before using the object.
The creation lease is released after pthread_create returns, before waiting
for child initialization. Stack-query attributes never enter the creation
pool because a query can record a live stack address.

Requested stack sizes, native pthread creation and original failure
handling remain. New bounded refusal records include the native return
and requested stack size. This does not establish the cause of the abort.

The target runtime and complete LTS patch checks passed. The existing
actual attribute-pool host fixture, directed at the Java 17 header, passed
separate creation/query ownership, opaque-object reuse, forced late init
refusal, exhaustion, cleanup and 800 concurrently created pthread checks.
Consumer 026 requires exact physical startup and title-screen validation.
