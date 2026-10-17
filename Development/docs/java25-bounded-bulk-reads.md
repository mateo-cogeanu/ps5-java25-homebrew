# Bounded PS5 bulk file reads

Patch0072 caps PS5 readBytes requests to the existing8192-byte stack buffer
AFTER validating the caller's full original Java array slice. A successful
native call can return a short read, as allowed by FileInputStream and
RandomAccessFile. It performs one real IO_Read and copies exactly its returned
count. Java readFully/stream loops continue using that count and the real file
position. Null, zero-length, full-slice bounds, closed file, I/O failure and EOF
behavior are preserved. Non-PS5 allocation behavior and all bulk writes remain
unchanged. No larger stack frame, pool, pinned heap array or extra storage is
introduced. Larger callers may perform more native read calls.

This avoids allocation of a large temporary read buffer while loading JAR
entries under native pressure. It does not ensure enough storage for ZIP,
metadata, verification or subsequent allocations.

The actual io_util.c read/write bodies run under UBSan/-Xcheck:jni in a host JNI
fixture. Tests cover capped single reads, complete65537-byte continuation with
both backends refused, short reads, EOF, bounds/null, closed/error paths and
unchanged partial-write/malloc/mmap/real-OOM cleanup. The test additionally
registers the actual capped body for host RandomAccessFile.readBytes0, then
checks real RandomAccessFile.readFully position/content/EOF and real ZipFile
entry readAllBytes, asserting that ZipFile used the replacement native reader.
This temporary native registration belongs only to the host test process.
Target HotSpot/java.base-libs rebuild passes. PS5 startup/save/stop remains
unvalidated, and overall native resource capacity is still unknown.
