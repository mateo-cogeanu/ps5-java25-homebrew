# Resident java.io directory listing

Consumer 064 run `01.000.064-1792338320-865804474` fails before readiness in
Minecraft OldUsersConverter.convertPlayers: File.listFiles returns null for an
existing legacy-player directory, then the converter dereferences the result.
The saved session is FAIL, not VM ABORT. Online DNS/TLS/account preflight passes;
this run never reaches gameplay, eating samples or the timed phase. The captured
native trace does not record the original desktop opendir errno.

java.io UnixFileSystem.list0 still used SDK opendir/readdir/closedir, while the
NIO dispatcher already uses the resident directory helper. Patch 0089 adapts
only the PS5 java.io implementation to that same helper: real descriptor open,
resident getdents/getdirentries, validated records and matched close/unmapping.
The desktop branch retains its original directory API. Relative-path policy
remains the existing PS5 UnixFileSystem policy.

Java array growth, child-name conversion and filtering of dot entries remain
unchanged. An empty directory returns an empty array; real open, enumeration,
malformed-record or close failure returns null. A mid-read failure discards
partial contents. JNI exceptions remain pending and cleanup still runs. Native
error diagnostics identify open/read/close errno without publishing filenames.
No legacy files are deleted, renamed, fabricated or silently skipped by this fix.
Minecraft's own migration behavior remains unchanged.

The new isolated host regression registers the actual list0 JNI body for
java.io.File. Its real host directory records are serialized into the PS5
helper layout while SDK opendir is denied. It checks 351 names including Greek
Unicode, Java array growth, listFiles child paths, symlinks, empty/missing/file
paths, partial enumeration failure, close refusal, both mapping failures,
recovery and 256 repeated listings with no descriptor/map leaks. Desktop
control retains unsupported-opendir failure. It runs with -Xcheck:jni/UBSan;
the existing actual NIO/JNI and ASan/UBSan record-parser regressions also pass.
The host serializer is not console ABI validation.

Target java.base-libs compilation passes. The consumer adds a read-only legacy
directory preflight and an existing-directory host fixture. Console startup,
legacy conversion, authenticated gameplay, eating/performance and full
endurance still require validation in the next packaged consumer build.
