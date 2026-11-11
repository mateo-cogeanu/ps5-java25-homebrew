# Java 17 platform string scratch on PS5

ProsperoCraft build 039 returned an OutOfMemoryError from
`UnixFileSystem.getBooleanAttributes0` while opening a classpath JAR.
The native trace records libjava requesting the exception. The native
method converts the Java path to a platform string before calling
`stat`. The console report does not identify the specific allocation
or the underlying reason for refusal.

Patch 0021 routes the buffers returned by `JNU_GetStringPlatformChars`
through the existing Java 17 native scratch allocator on PS5.
`JNU_ReleaseStringPlatformChars` uses its paired release. The encoder
allocates outside JNI critical regions, including the Latin-1 fast
path for UTF-8, which releases and reacquires the immutable byte
array after counting the output length. The native conversion still
preserves its charset rules, terminator, and overflow checks. The
UTF-8 PS5 path counts encoded bytes in an unsigned size before
applying the existing maximum. File queries still use the real
filesystem result. Other platforms keep their existing allocator.

Host JNI checks covered UTF-8, ISO-8859-1, ASCII, CP1252, and the
generic charset path, forced refusal and paired release. The fixture
also passed a converted UTF-8 path to real `stat`. The target Java 17
build and the ordered Java 17 and 21 patch replay checks passed.
Physical validation of the original classpath operation is pending.
