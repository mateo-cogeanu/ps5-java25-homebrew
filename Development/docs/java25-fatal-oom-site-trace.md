# Native fatal allocation-site diagnostics

Patch 0067 records the requested allocation size, source file/line, VM error
type and original detail format through the existing raw trace helper before
entering the full native fatal reporter on PS5. It changes no allocation or
error propagation policy. Desktop builds retain the existing behavior.

This is needed when the ordinary error file is unavailable during resource
exhaustion. The raw helper uses stack formatting and file IO; it can still fail
if the OS refuses the file operation. Detail arguments are not formatted here.

`python3 tools/test_java25_fatal_oom_trace.py` compiles the actual fatal entry
body under ASan/UBSan and checks ordering and size/source/type preservation.
Trace and reporter contracts are stubbed; this does not validate target IO or
prove available native memory. Target HotSpot/java.base-libs rebuild passes.
Console validation of the new fatal trace remains pending.
