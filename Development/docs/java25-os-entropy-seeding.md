# PS5 operating-system entropy seeding

Patch0095 repairs a concrete platform gap observed during an early TLS startup
failure: Unix random-device access fails on PS5, so OpenJDK selects its threaded
seed fallback. The report shows ThreadedSeedGenerator/BogusThread initialization,
repeated native thread creation and about eight seconds spent obtaining entropy.
The last class progress is default TLS socket-factory initialization. There is
no Java exception, JVM abort report, signal record or evidence of memory
exhaustion in this run. The precise process-crash cause remains unresolved;
this repair does not establish that the seed fallback caused it.

On PS5, NativeSeedGenerator now requests bytes from the real system random
service, sceRandomGetRandomNumber. The API, success result and64-byte request
size follow the pinned SDK's hello_sprx sample. Both standalone libjava and the
embedded payload explicitly link libSceRandom. Requests are split into at most
64-byte chunks using fixed stack storage, with no native allocation. OS failure
throws ProviderException; no bytes from a substitute or threaded fallback are
accepted. The first successful request logs a source marker, never seed bytes.
Other Unix platforms retain their existing URL seed source and failure behavior.

`tools/test_java25_os_entropy.py` compiles the actual patched Java class and JNI
body on the host. A mocked OS boundary uses the host cryptographic RNG. Tests
cover zero/small/64/65/129/4097-byte requests, chunk bounds, first/later OS failure
propagation, real DRBG initialization and generateSeed, absence of fallback
threads, JNI checking and UBSan. A separate desktop control retains Unix URL
seeding. These validate routing and contracts, not PS5 entropy quality, service
availability, ABI behavior or the original crash cause. Those require console
validation with the packaged runtime.
