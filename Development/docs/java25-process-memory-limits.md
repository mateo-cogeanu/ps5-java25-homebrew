# Read-only process memory-limit diagnostics

The shared native process sampler now records getrlimit results for RLIMIT_DATA,
RLIMIT_AS and RLIMIT_RSS at elapsed second zero and once per minute. It keeps the
existing per-second getrusage samples. Each limit record includes the return
code, errno, raw soft/hard values and explicit RLIM_INFINITY indicators. Failed
queries do not establish a limit; their zero-initialized values are unavailable.

These are operating-system process-policy values. They do not measure currently
available memory, a flexible/direct memory pool, allocator fragmentation, or a
PS5 container's actual enforced budget. An unlimited policy does not guarantee
that an allocation can succeed. ru_maxrss remains raw with no inferred units or
hard-limit claim. Diagnostics never call setrlimit or reserve test memory.

Formatting uses bounded stack storage and existing checked descriptor writes;
the sampler restores the caller's errno. No JNI or VM heap operation occurs on
the UI thread. The ASan/UBSan HTTP/collector test covers real successful queries,
injected query failures, errno preservation, unavailable output paths, report
archival and downloading. Target linking/package checks and actual PS5 report
values are separate validations. No frozen milestone is modified.
