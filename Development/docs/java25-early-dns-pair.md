# Prepare the retained DNS pair before VM pressure

A consumer capture reaches its JNI worker callback, verifies TLS trust and
initializes DRBG/default TLS. Its first online DNS lookup fails. Native output
identifies `DNS pool create` result0x804101ce, net_errno206 and errnoENOMEM;
getaddrinfo returns EAI_FAIL. Thus no remote query is proven, and this is not
evidence of Mojang service downtime. Previously retained-pair reuse only helped
when an earlier lookup happened before memory pressure.

The scoped pinned SDK adapter now exposes ps5_dns_prepare(). It leases/creates
the same16KiB pool and resolver as the pinned netdb lookup path, then releases
the lease, retaining the real pair for the app lifetime. No query is performed,
no DNS answer or hostname/IP is cached, and no credential is read. Success is
idempotent; partial resolver creation failure keeps the pool but releases its
lease so a later attempt can retry. Native failure/error details stay real.
The consumer calls this before JNI_CreateJavaVM, and reports a preparation
failure explicitly rather than proceeding with unavailable DNS infrastructure.
No additional pool, resolver, network interface filter or preset target address
is introduced. Actual subsequent lookups still use the normal SDK resolver.

ASan/UBSan tests compile the actual adapter plus hash-verified SDK lookup/free
and JDK conversion allocation blocks. New cases cover pool and resolver prepare
failure, partial initialization retry, lease release, repeated preparation with
zero queries and errno preservation. Existing400serializedcross-thread fresh
queries with late pool/resolver/heap refusal, changed answers, query failure/
recovery, allocation rollback and exact cleanup remain passing. Network APIs
are controlled host models; actualPS5 early availability and later query/TLS/
resource lifecycle remain pending. Frozen snapshots are unchanged.
