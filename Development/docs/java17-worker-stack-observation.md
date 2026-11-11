# Java 17 worker stack observation on PS5

Patch 0018 lets a statically linked probe observe the existing HotSpot worker
stack bounds after `record_stack_base_and_size()` and before thread
initialization. The worker calls the same optional symbol with a zero size at
normal native entry return, using the saved stack top because HotSpot may have
deleted its Thread object. Without a linked observer, both calls are skipped.
The hook does not change stack queries, pthread creation, signal handling, or
monitor behavior. Java 21 and Java 25 do not acquire the hook.

The Minecraft 1.20 probe's 034 console run reached original Main and recorded
a native SIGBUS. The saved PC was outside the matching probe ELF. A saved
register held a pointer to HotSpot's monitor wait function, but the main-only
stack scan supplied no caller for this fault. The probe's next build uses the
hook to add bounded worker stack samples to its existing report. The cause and
physical capture remain unverified.

The Java 17 target HotSpot and native ELF audit passed. The linked probe
resolves the hook to its own recorder, and the resident VM object retains
a weak reference. The ordered Java 17 and Java 21 patch replay checks passed.
The probe owns the stack scan, report and console validation.
