# Scoped SDK DNS result allocation

The active consumer059 run reports UnknownHostException for its discovery
hostname before online session verification. The Java report does not contain
the native getaddrinfo result or resolver phase. This does not establish a
service outage or prove the precise DNS cause.

The pinned SDK v0.42 netdb.o (SHA256
ccf0c18495f3e1329570d4f0dac5157a00c5ab9625f2102b197e2575944197f4)
uses libc malloc for the sockaddr and addrinfo results and strdup for the
canonical-name copy, with matching freeaddrinfo releases. Libc refusal has
already occurred elsewhere in this process. The
[SDK source](https://github.com/ps5-payload-dev/sdk/blob/v0.42/libc/netdb.c)
also creates a real SceNet pool/resolver for each name request.

The runtime packager now rebinds only that object's malloc/free/strdup to a
libc-first, anonymous-map fallback with an aligned ownership prefix. It reuses
the previously tested scoped allocation backend. All allocations from that
object, including successful libc allocations, use matching ownership. Failure
of both backends remains real EAI_MEMORY. Canonical-name allocation refusal
retains the SDK's existing null-canonical-name behavior. SDK caches and the
signed runtime library are not modified; only the copied static link input is
adapted. A hash guard rejects other object versions.

Bounded existing native trace records getaddrinfo result/family/flags and actual
pool/resolver create/query/cleanup results and network errno. Original arguments,
timeouts, return values and errno are retained. No alternate DNS service,
hardcoded address, fabricated answer, IPv6 claim, certificate bypass or offline
authentication is introduced. A successful allocation fallback is a candidate
repair; DNS resolution on the console remains unvalidated.

python3 tools/test_java25_netdb.py passes ASan/UBSan using actual adapter code and
pinned SDK source lookup/free bodies, with harmless C-to-C++ allocation casts.
The network API is injected. Checks cover libc/mapped ownership, result and
canonical-name bytes, every partial/total allocation failure, all resolver
create/query/cleanup failures, unsupported IPv6, errno, overflow and400 concurrent
lookup lifetimes with matched cleanup. The source download is hash pinned.
Target packaging checks the rebound symbols and retained allocator imports.

External probes may now supply java_compile_classpath as an optional list of
existing JAR paths for consumer Java compilation. This keeps external JSON
library dependencies in their owning repository; no game code/JAR enters the
runtime source publication.

Target packaging and host tests do not establish online DNS, TLS, authentication
or player admission on PS5. The separate consumer adds real HTTPS preflight and
account provisioning; its full two-hour console result remains pending.


Patch0084 also covers the separate OpenJDK IPv4/IPv6 address-conversion list:
its duplicate-filter nodes use the already tested scoped node allocator and
matching release, while SDK-owned results continue through freeaddrinfo. This
prevents a successful SDK lookup from immediately encountering the same libc
allocation dependency during Java conversion. Both-backend failure still
throws OOM. Host regression compiles the actual allocation/link/cleanup blocks
for both implementations and checks heap/map success, complete refusal and
partial-list cleanup under ASan/UBSan; JNI conversion itself is not simulated
by that block test. Target java.base-libs compilation passes.

## Retain one bounded resolver pair under native-heap pressure

Consumer061 run `01.000.061-1792334800-999063915` confirms real DNS and
verified HTTPS preflight,111 default trust roots and real server readiness.
Minecraft's own discovery thread then receives UnknownHostException. Native
trace records later SceNetPoolCreate failure `0x8002000c` (ENOMEM), while
compiler TLS and native allocations also fall back to mapped storage. An
unrelated earlier local-hostname query returns `0x80410116`; it does not
establish failure of the successful online preflight. Raw reports stay local.

The scoped netdb adapter now retains the first successful real16KiB SceNet
pool and resolver until native app exit, across VM runs. Each SDK resolve
leases the pair from pool-create through pool-destroy. A static atomic flag
serializes the complete lease without allocating a late mutex or TLS slot;
waiting callers yield. Both forward and reverse lookup paths in the pinned
object use that lease. Successful queries continue to ask the real resolver;
no address/TTL cache or preset service address is introduced. Pool/resolver
creation failure remains real and permits a later retry; query failures are
returned unchanged and release the lease. SDK result allocation ownership is
unchanged. SDK destroy calls release the lease; native destruction is deferred
to app exit. At most one real pool and one resolver are retained.

The updated actual-adapter/SDK-body ASan/UBSan regression passes400 serialized
cross-thread fresh queries after all further pool/resolver creation is denied,
with result allocations using mapping after heap refusal. It checks changing
answers, real query failure/recovery, partial initialization failure/retry,
output allocation failures, matching releases and errno. Injected networking
cannot validate the console's cross-thread handle reuse or authentication.
Consumer062 packaging and its two-hour console result remain pending until
recorded separately in the consumer repository.
