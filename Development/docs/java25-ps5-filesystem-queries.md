# PS5 stream paths and unavailable mount enumeration

## Captured build057 result

Run01.000.057-1792256201-182793185 crashed and was relaunched according to
the user; the saved session remains RUN server worker. Full server/native
reports were collected and retained locally. Interface flag ioctls return
EACCES and the fresh route fallback resolves flags. The server reaches its
real Done readiness message and starts saving chunks for all three dimensions.
This is readiness progress, not a completed passing save/stop test.

The final native preparation sequence on the server thread is
BsdNativeDispatcher.getfsstat, with lookup/signature installation complete.
The target matches the exact057 retained ELF plus its0x400000 load offset.
The linked getfsstat body executes raw desktop syscall395. No final native
signal or VM abort is captured at this point, so this identifies an unvalidated
API at the interruption boundary, not an exact fault-PC proof. A separate
fatal-error report could not be collected. Raw logs remain local.

The server also reports Invalid argument opening relative banned-players.json,
banned-ips.json, ops.json and whitelist.json. java.io native fileOpen passes
these relative paths directly to open, unlike the configured NIO user.dir
resolution. Descriptor-based native I/O does not share a validated desktop cwd.

## Patch0082: explicit unsupported mount query

On PS5, BsdNativeDispatcher.getfsstat now throws UnixException(ENOSYS) before
native iterator allocation or a kernel call. The desktop branch remains intact.
This honestly exposes an unavailable API; it does not implement mount discovery,
return invented mount entries, infer free capacity or claim a filesystem ABI.
Existing Java handling can turn mount lookup failure into IOException. Whether
consumer startup/save tolerates this unavailable query remains a console test.
The rebuilt target object has no getfsstat or malloc dependency.

## Patch0083: stream opens use Java path resolution

On PS5, the common libjava fileOpen path resolves nonempty relative filenames
through java.io.File.getAbsolutePath before platform-string conversion. This
uses File's existing startup user.dir policy. Absolute and empty inputs retain
the original path, and errors retain the original supplied filename. JVM/JNI
exceptions propagate. Input/output/random-access opens share this native path;
file-descriptor constructors are unaffected. Other java.io File operations are
outside this patch. No process cwd mutation, lexical existence claim or
fabricated successful write is introduced.

## Checks and limits

python3 tools/test_java25_ps5_filesystem.py compiles actual helper/fileOpen/
handleOpen and mount/end bodies, runs real JNI with -Xcheck:jni and UBSan,
and verifies relative/absolute read/write/append/read-write, dot/parent paths,
empty/missing-parent errors and differing process cwd versus user.dir. PS5
and desktop controls both pass. The platform-string transport in this host
fixture uses JNI UTF transport for ASCII fixtures, not the target conversion
implementation. Mount syscalls and diagnostic allocation are injected; the
PS5 branch makes zero such calls and throws ENOSYS, while desktop success,
query failures, allocation failure and cleanup remain exercised. Actual JNI
exception construction in this fixture uses IOException in place of internal
UnixException. The target build uses the real UnixException constructor.

Target HotSpot/java.base native build passes. Console mount-query handling,
relative stream files, verified saved world/thread exit and all058 rows remain
pending. Readiness from057 is not a new passing milestone. Discovery DNS and
overall native memory capacity remain unresolved.


## Exact058 console result

On2026-10-18 the human reported ALL PASS for the delivered01.000.058 package.
The consumer's five rows cover runtime initialization, VM creation, artifact/
asset preflight, real server readiness, clean stop/thread exit, nonempty saved
world metadata and VM destruction. The matching runtime pin is
`aab0d2fa8ad58ba8ceb58561a33a9a5fe50fd583`. Consumer source/package hashes and
release are frozen in the separate
[Server_Start validation](https://github.com/mateo-cogeanu/ps5-minecraft-java/tree/main/Server_Start).
This supersedes the058 pending result above for those rows. It does not turn
unimplemented mount enumeration/capacity into a supported API or establish DNS,
reload, player joins, performance or endurance. No runtime binary rebuild was
made to freeze the human-tested package.
