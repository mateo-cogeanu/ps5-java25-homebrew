# java.io descriptor metadata and TLS trust-store discovery

Build060 consumer run01.000.060-1792319628-77327858 returns server-row FAIL
before server launch. Full native and exception reports were retrieved locally.
The native trace records successful pool/resolver create/query/cleanup and
getaddrinfo result0. The online preflight reaches TLS but raises trustAnchors
parameter must be non-empty. The packaged target cacerts is present,134174bytes,
and contains111 roots readable with the ordinary null-password load path.

Default TrustStoreManager selects its store using java.io.File.isFile,
canRead and lastModified. The PS5 java.io backend still used desktop stat and
access directly, unlike the already-adapted NIO backend. A host regression
reproduces the failure under EPERM: real default JSSE sees zero roots despite
that same target store being readable by descriptors. This demonstrates a
metadata-discovery failure mode; the060 native trace does not separately record
those specific stat/access return values.

Patch0085 adds a PS5-only fallback after stat/access EPERM. Stat attributes are
read through actual nonblocking read-open, fstat and close. Read/write access
is checked through a corresponding real noncreating, nontruncating descriptor
and regular/directory metadata. Execute access is never inferred. Successful
original queries and other errors, including EACCES, retain their behavior.
Missing paths, open/fstat/close failures remain failures. Existing mutation APIs
still require their original native operations. No metadata or permission is
fabricated; unreadable files can remain conservatively undiscoverable.

Actual metadata JNI bodies pass a host regression that re-registers four
java.io natives only inside the isolated test JVM. With injected EPERM and
real descriptors, File type/readability/length/timestamp work and default JSSE
loads all111 target roots. The unchanged desktop branch sees zero roots under
the same injected denial, reproducing the baseline. Other errors, missing
files, every descriptor failure, close cleanup, unchanged normal queries and
no execute/EACCES inference are checked under real JNI/-Xcheck:jni and UBSan.
The test-only RegisterNatives warnings are expected; production uses the normal
compiled native methods and does not re-register methods or alter Java classes.

The regression can delegate to an external consumer fixture. With the same
injected denials and target cacerts it completes real default-validated HTTPS
discovery, account/session-profile/public-key fetches and whitelist provisioning
on the host. Neither a permissive trust manager nor a custom SSLContext is used.
Host success does not establish PS5 TLS or authenticated joining.

Target HotSpot/java.base native compilation passes. The separate consumer061
adds an early default-trust-manager issuer count and file metadata report before
its online preflight. PS5 root discovery, HTTPS, authenticated admission and
the7200second run remain pending; passing058 stays frozen.


Patch0086 makes relative File objects passed to native filesystem operations
resolve through existing user.dir policy when sun.nio.fs.ps5Sandbox=true. This
matches already-adapted stream/NIO resolution and allows relative whitelist
metadata/load checks to discover the actual preflight-generated file. Empty
path handling and absolute/public File paths are preserved; desktop policy is
unchanged when the property is false. The actual patched UnixFileSystem class
passes host checks with process cwd different from user.dir: relative existence,
type/readability/length/timestamp, rename/delete and unchanged absolute paths.
Target java.base Java/native compilation passes. No console whitelist-admission
claim is made before an actual successful join.
