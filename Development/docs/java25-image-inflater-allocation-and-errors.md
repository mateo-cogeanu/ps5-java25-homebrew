# Native image inflater storage and failure handling

Consumer 073 confirms DRBG initialization succeeds with the kernel entropy
repair. TLS factory setup then reports ClassFormatError for
sun/security/ssl/DTLSInputRecord, with magic 0x07000f0c instead of CAFEBABE.
No server readiness was reached. The precise inflater status was not logged,
so the captured report alone does not prove the allocation that failed.

Source inspection exposes two concrete gaps. The native ZIP_InflateFully path
used by compressed Java images still used zlib's ordinary allocator, whereas
Java Inflater/Deflater already used the PS5 libc/page-backed adapter. The image
reader also discarded inflate failure in release builds, potentially copying
uninitialized temporary bytes into class data.

Patch 0097 installs the existing matched PS5 allocation/free callbacks in both
native full-inflate paths. The image inflater requires stream completion and
an exact output length; failed initialization, corrupt/truncated streams and
other zlib failures return an error. Failure propagates through image
resource retrieval: JIMAGE_GetResource returns zero, and HotSpot raises a
resource-named IOException instead of parsing failed class output. Optional
VM-resource and package-table lookups likewise stop on failed reads.

The image-reader reference count is now explicitly initialized to zero. The
sanitized release-mode test exposed this uninitialized field when repeated
open/close operations failed to release the image mapping. This is a separate
ownership defect, not established as the cause of the console class error.

The host regression now compiles the actual native ZIP_InflateFully body and
PS5 allocation adapter; it no longer substitutes the host JDK's libzip.
Release-mode image-reader objects run with ASan/UBSan. Tests cover normal and
forced-libc-refusal decompression, total storage refusal, corrupt/truncated
streams, insufficient output, complete cleanup and recovery. Actual DTLS,
SSL, Object/String, desktop and JFR bytes match extracted image resources.
Failed image decoding returns zero without publishing temporary bytes.
Anonymous-copy/mapping rejection and repeated-open cleanup checks remain.

Target HotSpot and java.base native libraries rebuild. The module set and
resident compressed-image strategy are retained. PS5 TLS startup, allocation
behavior and the earlier 071 failure remain pending. No consumer game classes
are changed by this repair.
