# PS5 bulk file-I/O temporary buffers

Patch 0041 covers the native `readBytes` / `writeBytes` helpers in libjava
`io_util.c`, used by RandomAccessFile and stream I/O. Requests through 8192 bytes
keep the original stack buffer. Larger requests first try libc malloc; on PS5
only, refusal falls back to page-rounded anonymous read/write mappings. If both
backends fail, the existing OutOfMemoryError is retained. The original JNI range
checks, read/EOF/error behavior and partial-write loop remain.

Mapping length is stored independently of the write loop's shrinking length.
All exit paths release the actual backend; cleanup preserves errno. Diagnostic
lines identify the requested size, libc errno, successful mapping bytes and
mapping errno. A null malloc may report errno zero on this target.

This path is separate from HotSpot's native heap fallback (0040) and classloader
scratch fallback (0038); it does not increase the Java heap or bypass JAR checks.

The build 016 console capture shows 13 successful HotSpot slab mappings and two
successful direct mappings, followed by OutOfMemoryError from
RandomAccessFile.readBytes0 during JAR class loading. No SIGNAL record or abort
report was captured in that run. This identifies a remaining temporary native
buffer allocation path, not proven Java heap exhaustion or proof that earlier
native crashes are resolved. Raw console logs remain local.

`python3 tools/test_java25_io_scratch.py` extracts the actual native helper and
read/write function bodies, compiles them with UBSan and drives them through
real host JNI and POSIX I/O. It forces libc and mapping refusal and verifies
payloads, short reads, EOF, partial writes, the stack threshold, bounds/null
exceptions, closed/error descriptors and matching cleanup on success/failure.
The non-PS5 allocation branch also compiles. These are host checks; the target
build and a new PS5 console test are required separately.
