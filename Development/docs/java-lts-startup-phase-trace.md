# Java17 early VM startup phase trace

The extended-module consumer001 reaches JNI_CreateJavaVM and completes the native
anonymous JIMAGE allocation, file read and read-only protection, then crashes
before the call returns. The retained trace alone does not identify its PC or
which subsequent VM subsystem fails. No underlying heap, module or JNI cause is
established. Raw reports remain local in the consumer's private retrieval folder.

Active17's Threads::create_vm now emits bounded fixed phase messages through the
existing PS5 trace helper around OS initialization, JDK-version initialization,
argument parsing, ergonomics, OS init2, VM globals/universe, java.lang and module
initialization. Existing return values, ordering, allocations, VM options, heap,
collector and JNI behavior are retained. Non-PS5 trace calls inline to no-ops.
The helper preserves errno, uses fixed literals and open/write/close, and needs
no VM locks or allocation. Default Java25 and frozen17/21 milestones are untouched.

The original trace file is private0600 by default. A consumer that explicitly
shares its unauthenticated startup diagnostics over FTP can precreate/chmod only
its own diagnostic files0644. The consumer owns that sharing boundary; runtime
trace defaults do not expose unrelated logs/accounts or change directory access.

The consumer002 also links its existing scoped native fault recorder around VM
creation, forwards pre-existing handlers without recovery/context rewriting,
records its image anchor and bounded signal frame, and preserves VM-installed
handlers on scope exit. That consumer integration is not runtime source here.
Exact PS5 failure PC, new phase result and any causal repair remain pending.
Host source replay/standalone JNI checks and target17 build pass; they do not
establish physical crash resolution. See the
[build record](validation/java17-startup-phase-trace-2026-11-09.json).


## Universe boundary follow-up —2026-11-09

Consumer002's retained phases pass argument parsing, ergonomics, OS init2 and
VM globals, then stop inside init_globals before returning. No fault frame was
captured by the external handler (its file is empty); its initial installation
was reported successful. The runtime may replace those handlers during startup;
that alone does not establish the crash signal or cause. Original game entry and
Java module initialization were not reached.

Active17 now brackets management/JVMTI storage, class loader, code cache, CPU
version, stub generation, universe/heap and interpreter initialization. Its fatal
VMError entry records numeric ID, PC, requested bytes and source line before the
ordinary error printer, limited to four reports by a native atomic counter. The
fixed96byte formatter uses no allocation, dynamic error message or caller path.
Error handling and return/control-flow semantics remain intact; non-PS5 calls
remain no-ops. Target17 and scoped standalone JNI checks pass; physical evidence
is pending. Consumer003 separately tests128MiB instead of512MiB; no runtime heap
policy/default or working25 game setting is changed, and no cause/fix is claimed.
