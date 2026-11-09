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
