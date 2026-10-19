# PS5 temporary image-resource allocation

Build075 reports stop at HTTPS connection construction, after successful DNS,
URL creation and TLS factory setup. The last class load is
HttpsURLConnection$DefaultHostnameVerifier. Java heap free is51544168 of
63995904 committed bytes (max182255616). No fatal crash address or Java
exception was captured, so no exact crash cause is established.

Source inspection found that0097 adapted zlib private state but retained
ordinary C++ new[] for temporary resource bytes. That allocation can still
fail independently of Java heap or the patched zlib allocator. Patch0098
uses a scoped libc-first allocator with PS5 anonymous RW page fallback for
these buffers. An aligned ownership prefix selects matched free/munmap; size
rounding is checked for overflow. Complete allocation refusal returns false
through0097's JIMAGE/HotSpot checked-error path. No global allocator changes.

Both the decoded resource buffer and the nonresident compressed-input branch
use the helper. The resident image path has no per-resource compressed-input
allocation; this is the path exercised by the current host reader tests.
Terminal decompression now stops at its explicit terminal flag, avoiding a
speculative29-byte header read from small uncompressed resources.

## Checks and limits

The actual release-mode native reader and inflater pass ASan/UBSan tests.
Tests independently deny image-buffer libc allocation, exercise real anonymous
mapping fallback, refuse the mapping and check JIMAGE returns0 without changing
caller output, then verify recovery and zero live mappings. Exact HTTPS default
verifier/delegate, DTLS, SSL, Object/String, JFR and desktop resource bytes match
host extraction. Tiny terminal outputs of1,8,28bytes exercise the header-read
fix. Existing zlib allocation/failure/corrupt/truncated controls still pass.
Patch application against the recorded075baseline matches the target source;
HotSpot/java.base native target build passes.

These tests establish fallback/error behavior, not that075crashed for this
reason. Actual PS5 HTTPS/server readiness, memory headroom, gameplay/respawn
stability and endurance remain pending. Consumer076 retains075phase diagnostics,
the existing game derivative and world/JIT/heap/security settings. Raw reports
remain local. No game-JAR transformation is added.
