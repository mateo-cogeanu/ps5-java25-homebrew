# PS5 native platform strings

Patch 0042 adds a PS5-only libc-first / anonymous-RW-page fallback to native
platform-string buffers in libjava jni_util.c. All five MALLOC_MIN4 conversion
paths use an aligned backend header; normal release and strict-NUL rejection
both match free or munmap to the allocation. JNU_ReleaseStringPlatformChars
remains the release API. Other platforms retain malloc/free behavior. Cleanup
preserves errno; size guards and at least four bytes of storage remain.

This covers UTF-8 (Latin-1 fast path and Java Charset conversion), ISO-8859-1,
US-ASCII and CP1252 platform strings. Encoding rules and strict-NUL validation
are unchanged. On PS5, the UTF-8 OOM message now distinguishes native allocation
failure/size limits instead of asserting an oversized Java array.

Build 017 logs show successful bulk file-I/O fallback for a 13,310-byte request,
then OutOfMemoryError with "requested array size exceeds VM limit" from
FileInputStream.open0 while java.util.logging opens its configuration. That
exact message is emitted when getStringUTF8's native MALLOC_MIN4 returns NULL,
including ordinary-sized paths. This identifies a native allocation path;
it does not establish Java heap exhaustion. No signal record or abort report
was captured. Server ready/save/stop remains unvalidated on PS5.

Run `python3 tools/test_java25_platform_string.py`. It compiles the actual
allocator, five conversion bodies and release API, then exercises real JNI
under UBSan with forced libc/mmap failure. It checks ASCII, Latin-1 and non-Latin
UTF-8, legacy charset behavior, long/empty strings, permissive embedded NUL,
strict NUL rejection, size guards and matching cleanup. Legacy converters
retain their original per-UTF-16-code-unit replacement behavior. The ordinary
platform branch also compiles. Target compilation/package and actual PS5
validation are separate checks.
