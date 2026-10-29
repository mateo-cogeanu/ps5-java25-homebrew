# Optional native library-name direct scratch, patch0132

Consumer143 reaches the Minecraft26.2/Fabric menu but records a bare native
OutOfMemoryError in NativeLibraries.findBuiltinLib during Controlify loading.
An integrated-world attempt then fails because Deflater's earlier initialization
hit the same loader error while loading compression support. This does not
establish Java heap exhaustion or world-generation performance. Consumer logs
and game-specific validation remain in ProsperoCraft.

Patch0132 connects the existing temporary native library/symbol-name allocator
to patch0127's bounded direct scratch mapper and paired release. It uses the
existing default-off JNU_PS5SetDirectScratchEnabled policy; libc and anonymous
allocations retain precedence, with direct fallback only on anonymous ENOMEM
when enabled. No library registry, name parsing, search path, JNI lifecycle,
resolver, arbitrary loader, Java API, heap/GC or global allocator changes.

NativeLibraries.c owns one additional64slot/8MiB ledger, bringing libjava's
three opt-in scratch translation units to24MiB aggregate maximum. Libnet's
separately gated ledgers remain independent. Names retain their original owner
prefix. Libc/anonymous/direct allocations use their matching release, with
conservative retained ownership on failed direct cleanup as in0127. Overflow
and resource exhaustion still fail. No universal native memory budget or orphan
recovery is claimed. Non-PS5 and disabled behavior remain unchanged.

The actual NativeLibraries JNI lookup/symbol bodies run under a real host JVM
with Xcheck:jni/UBSan. Tests preserve default-off libc/mapped/error controls and
exercise opt-in direct name construction under simultaneous libc/anonymous
refusal, matching cleanup, null/short/oversized/unknown names, Java string failure,
OnLoad/OnUnload lookup and512repeated lifetimes. Direct syscalls are host fixtures.
Existing actual scratch mapper tests cover bounds, concurrency and failed cleanup
ownership. Genuine target java.base-libs, object/library hashes and applied patch
checks are recorded in validation. This is not PS5 library/Controlify/world pass.

Consumer144 owns the runtime pin/integration and package. Preserve frozen
milestones. PS5 native library loading, Controlify, compression/world save/load,
audio and regression remain pending; no Store release or new frozen pass.
