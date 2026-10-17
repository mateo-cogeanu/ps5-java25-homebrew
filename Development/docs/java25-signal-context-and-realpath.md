# Signal context and canonical asset paths

Consumer build 033 reached vanilla asset lookup after world metadata validation. Its complete server log records realpath EPERM on the asset JAR; its native trace records SIGSEGV at address 0xc. The historical startup download stalled and was canceled, so collection is explicitly partial. Raw reports remain local.

## PS5 signal register layout

Patch 0058 uses a PS5-only context view with the machine context at offset 0x40, rather than the SDK outer structure offset 0x10. The captured original bytes put RIP at 0xe0, RSP at 0xf8, RBP at 0x88 and interpreter BCP/r13 at 0xa8. The old RIP accessor at 0xb0 read a stack address. Both reads and continuation writes now use the corrected view; the original pointer supplied by the kernel is preserved. Non-PS5 platforms use their original layout.

The [public PS5 layout description](https://github.com/boykopovar/AnyPS5/discussions/727) independently describes a 16-byte signal mask, 48 reserved bytes and RSP at 0xf8. Compile-time assertions bind the adaptation to the pinned SDK mcontext definition. The host replay uses literal console bytes, confirms the incorrect old result and ensures continuation updates change only true RIP bytes. Target LLVM IR confirms offset 224 and no allocation/TLS/guard dependencies. Target HotSpot rebuild passes.

`python3 tools/test_java25_signal_context.py`

This defect can prevent normal implicit null exceptions from reaching their Java handler. That explanation fits fault address 0xc and the captured interpreter register values, but live signal recovery and the whole-app crash fix still require PS5 validation. A consumer preflight deliberately catches a real Java null access before loading the server, and signal recovery records the chosen continuation.

## Descriptor-verified realpath fallback

Patch 0059 retains native realpath success and non-EPERM errors. After EPERM only, an absolute path is walked from an opened root descriptor with openat and O_NOFOLLOW on every component. Intermediate components must be directories. Each component is verified before removing dot/parent components, so missing or non-directory prefixes cannot be skipped. At most two descriptors are live; cleanup preserves the actual failure. Fixed-size buffers enforce path/name limits. When native realpath cannot resolve a symlink, fallback refuses it instead of bypassing link semantics.

`python3 tools/test_java25_realpath_fallback.py`

The regression registers the actual patched JNI realpath0 in the host JDK, forces native EPERM and mounts/reads a real ZipFS asset. It checks successful native link resolution, missing components, denied paths, conservative link refusal, descriptor cleanup and bounds. Additional actual-helper ASan/UBSan coverage tests trailing slashes and thousands of operations under a descriptor limit. Target java.base-libs rebuild passes. Consumer preflight now canonicalizes the actual asset JAR and mounts/reads its version.json. These host checks do not establish target openat or signal behavior; all console rows remain pending.

## Desktop stack-gap query during signal recovery

Build034 console runs stop in the deliberate null-access preflight. The corrected context reader now reports PC0x206083d8a consistently with raw offset0xe0, while the fault address is0 and no continuation marker is emitted. This validates the register read on the console but does not establish successful signal recovery. The exception report is still a placeholder and no fatal report is available.

Before continuation selection, the inherited FreeBSD branch queries procctl(PROC_STACKGAP_STATUS) and potentially security.bsd.stack_guard_page. Disassembly confirms the linked procctl issues raw syscall544, a desktop ABI assumption. The logs do not pinpoint that call as the terminating instruction. Patch0060 excludes this desktop-specific kernel workaround on PS5 while retaining the normal JVM stack guard/overflow checks and all implicit-exception checks. Other FreeBSD builds retain the adjustment. New checkpoints report entry to stack triage, thread state/interpreter classification and null continuation selection.

`python3 tools/test_java25_signal_triage.py` compiles the actual triage block for both branches under ASan/UBSan with instrumented kernel calls. It confirms actual JVM stack checks and overflow handling still run, desktop adjustment still runs, and PS5 makes no desktop queries. The rebuilt target signal object has no procctl or sysctlbyname dependency. Target HotSpot compilation passes. Build035 requires console validation; this is a portability repair and a narrowed hypothesis, not a confirmed crash fix.

## Console signal recovery and the resident filesystem boundary

Build035 confirms real implicit Java null-exception handling: state8/interpreter1, null continuation selected at0x20607b61d, interrupted PC0x206083d8a, then all40 JAR checksum stages complete. The final stage is canonicalize/mount vanilla assets. The complete150069-byte native trace has no later signal record. Exact terminating instruction is not captured.

The earlier patch0059 helper invokes openat, whose linked SDK implementation issues raw desktop syscall499. Patch0061 replaces that dependency with resident libc open/close of each absolute component prefix. Every component (including dot/parent before reduction) is opened with O_NOFOLLOW, and intermediate/trailing-slash components require directories. Native realpath success and non-EPERM errors remain unchanged. Missing components and link-dependent fallback paths remain real errors. Like path-based canonicalization generally, prefix checks do not supply anchored-directory guarantees against concurrent namespace replacement; callers requiring that guarantee must not use this as a secure-directory handle API. No process chdir, lexical existence shortcut or invented file attributes are used. This supersedes the anchored openat implementation described above.

PS5 UnixNativeDispatcher no longer advertises the optional desktop openat/fstatat/unlinkat/renameat/fdopendir capability. Default path-based directory APIs remain; SecureDirectoryStream is unavailable until a native anchored backend is ported. Other BSD branches retain their original capability discovery. Descriptor-only realpath phase/component checkpoints preserve errno without a new FILE allocation. Consumer preflight separates canonicalization, mount, read and close stages.

Actual JNI/ZipFS host regressions and component/bounds/link/FD cleanup ASan/UBSan tests pass with the replacement. `python3 tools/test_java25_filesystem_capabilities.py` runs the actual capability block under both configurations and verifies target helper IR uses open/close with no openat or compiler TLS. Target java.base-libs rebuild passes. These checks do not prove the current crash occurs at openat; the resident-call repair and finer checkpoints require build036 console testing.
