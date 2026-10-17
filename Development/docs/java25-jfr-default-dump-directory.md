# PS5 JFR default emergency-dump directory

Patch0074 routes both default JFR emergency-dump directory branches through
an allocation-free helper. PS5 uses the real application-visible `/download0`
directory rather than the unsupported desktop current-directory query.
Other platforms retain os::get_current_directory. Explicit nonempty dump paths,
size rejection, filename construction, file opening/writing and failure
reporting remain unchanged. No JFR recording or native lookup is disabled.
The destination can still be unavailable/unwritable; existing open/write errors
remain real failures. No directory is created by this helper.

Evidence: preparation traces identify jdk.jfr.internal.JVM.setDumpPath(null)
with resolved target0xa2f590 in consumer048. Exact retained ELF identifies
jfr_set_dump_path at0x62f590 and handler at0xa2b030, confirming load offset
0x400000. Its set_dump_path null/empty branch tail-calls the cwd query with
_dump_path. That symbol at0x2643860 maps to0x2a43860, matching the captured
argument buffer; the captured size0x401 also matches its1025-byte extent.
The saved fault PC is external0x100026c946; no native fatal OOM is captured.
Preparation traces alone are not complete invocation tracking, but the
matching target, arguments and disassembly identify this default-path query.

Validation: actual default helper/get/set JFR path bodies compile under
ASan/UBSan. PS5 null/empty and empty-global fallback paths never call the
stubbed cwd query; explicit/max/oversize paths retain behavior; undersized,
zero-size and null destination helper calls are checked. The desktop branch
still queries cwd. File opening/writing is not modeled by that fixture.
Target HotSpot/java.base-libs rebuild passes. Actual PS5 JFR initialization,
file output and server readiness/save/stop still require console validation.
