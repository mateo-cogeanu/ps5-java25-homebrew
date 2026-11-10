# Java 17 file I/O native scratch

The PS5 024 run passed the previous zero-magic failure and reported
OutOfMemoryError at RandomAccessFile.readBytes while reading JAR data.
The Java heap used approximately 37 MiB. The helper allocates a native
temporary buffer when a request exceeds its 8192-byte stack buffer.

On PS5, the active Java 17 file helper now allocates and releases these
read and write buffers through the existing native scratch allocator.
Stack-sized requests, Java array bounds, file ownership, reads, writes,
exceptions and cleanup retain their original logic.

The target runtime and complete LTS patch checks passed. A local fixture
compiled the actual read/write helper bodies with JNI callbacks and real
file I/O under sanitizers. With normal allocation forced to refuse, it
checked identical read/write bytes, EOF, invalid bounds, closed-descriptor
and Java copy-exception cleanup, with no live scratch buffers afterward.
Physical consumer025 launch, title screen and subsequent I/O remain pending.
