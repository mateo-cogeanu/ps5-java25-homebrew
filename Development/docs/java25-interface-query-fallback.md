# PS5 interface enumeration after resident ENOMEM

Build051's current-run native trace records three successful interface-list
calls with two Java interfaces, then IPv4 `getifaddrs()` returns errno12 before
any Java interface conversion starts. The server console reports Netty channel
ID initialization failing through `NetworkInterface.getAll()`. This identifies
the failing platform operation, not whether its internal allocator or kernel
query produced ENOMEM. There is no evidence of a fixed one-minute deadline.

Patch0076 keeps successful resident calls and all non-ENOMEM errors unchanged.
Only after ENOMEM, a fresh `sysctl(CTL_NET, PF_ROUTE, 0, 0, NET_RT_IFLIST, 0)`
query supplies current interface records. This is the route-query mechanism
used by [FreeBSD getifaddrs](https://raw.githubusercontent.com/freebsd/freebsd-src/releng/9.0/lib/libc/net/getifaddrs.c).
The fallback uses mapped storage, independently of the resident libc heap.
The query and parser are scoped to libnet's BSD IPv4/IPv6 enumeration and
hardware-address lookup; there is no global libc replacement.

Each call owns its snapshot and converted nodes, with explicit matching
munmap cleanup. No cached interface state or preset addresses are returned.
Native names, flags, IPv4/IPv6 addresses, scope fields, masks, broadcast/peer
and link/MAC data are retained. Short route netmasks are copied into zero-padded
sockaddr storage before the existing prefix conversion reads them. Unused
interface statistics (`ifa_data`) are omitted; these libnet callers do not
read them. Existing Java object creation and native addif allocations remain.

Parsing validates route framing/version, full known headers, address bitmap
and aligned lengths, link-name/MAC bounds, interface index association, IP
address lengths and output capacity. Unknown message types are skipped after
framing validation. Malformed/unsupported data returns EINVAL. Snapshots above
1MiB and node storage above16MiB fail with EOVERFLOW. Up to five fresh query
attempts handle a size race; persistent ENOMEM, mapping refusal and kernel
permission/query errors remain real failures. Successful mapped cleanup
preserves errno. Native diagnostics retain the route-fallback entry/count.

`python3 tools/test_java25_ifaddrs.py` compiles the actual fallback/parser
with host BSD structures and synthetic kernel records under ASan/UBSan. It
checks IPv4/IPv6/link records, names/flags/MAC/mask/broadcast/scope, normal
resident ownership, non-ENOMEM behavior, both mapping failures, query errors,
size growth/retry exhaustion, bounds, truncated/mutated inputs and cleanup.
`test_java25_netif_trace.py` retains actual diagnostic writer/getAll coverage
with JNI/enumeration stubs. Target HotSpot/java.base native compilation passes.

Host fixtures use the host BSD ABI. Target compilation uses target SDK layouts;
neither establishes PS5 kernel route layout compatibility or permissions.
Console validation, successful Java interface conversion under pressure, TCP
listener readiness and downstream consumer save/stop remain pending. The
fallback does not claim to repair the overall native capacity limit or DNS.

## Build052 result and patch0077 diagnostics

Run01.000.052-1792251903-802361895 returned server-row FAIL. The current
native trace was inspected in Firefox: resident ENOMEM triggers the route
fallback, which returns EINVAL; getAll then returns null with an exception.
The visible server tail again reports Netty channel-ID initialization failing
through NetworkInterface.getAll. No real readiness/save verification occurred.
Firefox Save As was disabled and a direct-link download could not be obtained;
these are UI observations, not a full downloaded trace. No claim is made about
absent markers elsewhere in that trace.

The existing EINVAL exit does not distinguish kernel query rejection from
parser/layout rejection. Patch0077 adds size/data query errors, requested and
received sizes, target SDK header sizes, mapping-stage errors, retry exhaustion,
exact parser source line and byte offset. Parser/framing failure logs up to
2048 input bytes as32-byte hex rows in the existing bounded descriptor trace.
The total and captured lengths distinguish truncation; query failures before
receiving data produce no snapshot. Raw route data remains local to console
reports and is not committed. There are no new endpoints or preset addresses.

The diagnostic snapshot uses stack storage and preserves errno. Sanitizer
checks now reconstruct its exact bytes at0/31/32/33-byte and4096-byte inputs,
verify the2048-byte cap, and assert query-error/parser-line diagnostics as well
as prior fallback/cleanup/bounds tests. Target builds and packaging checks
pass. This is diagnostic development; EINVAL cause, PS5 ABI/permissions and
consumer readiness/save/stop remain unresolved. Parser acceptance and query
behavior are unchanged.

## Build053 capture: confirmed PS5 interface-info header mismatch

The full downloaded current-run trace for
01.000.053-1792252782-830533839 records a successful route size/data query:
1320 bytes requested and received. The parser rejects source line90 at offset0.
Its complete1320-byte hex snapshot shows four248-byte RTM_IFINFO messages.
Each link sockaddr starts at byte192 of its message, while the target SDK's
`sizeof(struct if_msghdr)` is168. Reading at168 interprets interface statistics
as sockaddr lengths; the first apparent length is1 and validation rejects it.
The address-message header remains20 bytes and sockaddr alignment8.

Patch0078 uses the observed192-byte PS5 interface-info header and copies only
the stable bitmap/flags/index prefix into the aligned SDK structure. It never
interprets opaque kernel statistics. Static assertions check prefix offsets
4/8/12, address-message header size20 and long alignment8 against the build
headers. Other validation, resident-success path and failure propagation are
retained. No arbitrary scanning or cached/fabricated interfaces are added.

The host regression now builds synthetic records with the actual192-byte
wire header and uses the PS5 IPv6 family value28 with the matching host BSD
sockaddr layout. An optional `--route-snapshot PATH` replays a local binary
snapshot, both directly through the parser and through the actual mapped
fallback with injected resident ENOMEM/kernel responses. The actual1320-byte
capture creates eight records: four link, two IPv4 and two IPv6; mappings are
released correctly. Raw addresses, MAC data, statistics and logs stay local.
Only the test driver and generated synthetic fixtures are published. Existing
query/mapping/bounds/truncation/mutation/diagnostic tests still pass ASan/UBSan.

Target HotSpot/java.base native compilation passes. This repairs the confirmed
parser layout mismatch; host replay does not establish console fallback
completion, Java interface conversion, TCP readiness or verified save/stop.
Resident ENOMEM's internal cause, overall native capacity and service DNS
remain unresolved.

## Build054: route parsing succeeds, list-node malloc fails

Run01.000.054-1792253539-553195562 confirms live route fallback completion
with eight records and the192-byte header. IPv4 enumeration then fails the
64-byte `addrP` allocation in `addif`, with a checked native malloc error.
The full saved server log now includes `OutOfMemoryError: Native heap allocation
failed`, through Netty channel-ID initialization at listener setup. Three
signals each resume; no native fatal OOM/VM ABORT marker is captured. The
fixture returns failure before real readiness/save verification.

Patch0079 adds a PS5-only libc-first allocator for libnet's internal interface
and address nodes. Every node has an aligned ownership prefix, including
libc successes. After libc refusal, page-rounded anonymous mappings supply
real storage; both backend failures still throw the checked OOM. Recursive
`freeif` uses the matching free/munmap operation, preserving errno. Resident
getifaddrs pointers and route-snapshot ownership are separate and unchanged.
This is scoped to nodes built by this native file; no global allocator,
shared pool, reserved fake interface or Java heap increase is introduced.
Each failed-libc node uses at least one16KiB page; this trades mapping overhead
for independence from libc allocation refusal, and does not establish a fix
for the overall native memory limit.

The patch also frees the first unlinked address if allocating a new parent
interface fails. Other partial lists remain owned by the existing caller
cleanup. This narrow cleanup repair applies to the common addif code.

`python3 tools/test_java25_netif_alloc.py` compiles the actual allocator,
addif and recursive freeif bodies under ASan/UBSan. Narrow JNI OOM and kernel
flag/index stubs surround real storage/copies. It covers libc, mapped and
mixed lists; IPv4/IPv6/broadcast copies; virtual parent/child nodes; each
allocation failure including unlinked cleanup; complete refusal/real OOM;
zero/64/88/page boundaries, overflow, alignment and errno preservation.
Target HotSpot/java.base native compilation passes. Console node mapping
availability, Java interface conversion, listener readiness and verified
save/stop remain pending. Discovery DNS and total native capacity remain
unresolved.

## Build055: node mappings work, second resident query fails

Run01.000.055-1792254170-750451055 confirms four successful16KiB node
mappings after libc refusals for64/56-byte IPv4 list nodes. The following
resident getifaddrs call for IPv6 enumeration returns failure with errno13
(EACCES), so the ENOMEM-only retry is not entered. The full saved console
again reports Netty initialization OOM through NetworkInterface.getAll.
The saved trace has three resumed signals, fixture failure, no captured
VM ABORT/native fatal OOM, and no real readiness/save verification.

The earlier libc refusal logs also carry errno13 after an ioctl. Build055
does not clear errno before libc allocation or resident getifaddrs, so the
trace alone cannot establish whether13 is fresh or stale. Patch0080 clears
errno before those calls. Resident success restores the caller's prior errno.
The live route-query fallback now also handles resident EACCES and failure
with errno0, recording the actual resident error value. Other resident errors
remain failures; actual kernel query/mapping/parser errors remain failures,
including EACCES from the kernel query itself. No fabricated error, interface,
cached list or success result is introduced. Node ownership/layout is unchanged.

The actual fallback regression covers explicit resident EACCES, failure that
leaves errno untouched after a stale EACCES/EPERM, unchanged EPERM/EIO failures,
and EACCES/EIO query failure propagation. Native node regression also injects
libc refusal without errno. Full captured-route replay, prior ownership/bounds/
diagnostic tests and target compilation pass. Console IPv6 enumeration, Java
interface conversion, listener readiness and verified save/stop remain pending.


## Build056 evidence and build057 flag-query fallback

Run01.000.056-1792254703-782971695 returned server-row FAIL. Full reports
were retrieved after reopening the probe without running rows. Both resident
getifaddrs calls fail with fresh errno0; both live1320-byte route queries parse
eight records. Six internal nodes use successful16KiB mappings after libc
refusal, and getAll completes two Java interfaces with no pending exception.
The server then fails in NetworkInterface.isLoopback0 through Netty MAC/channel
ID initialization. This establishes enumeration progress, not listener readiness
or a verified saved world. Discovery DNS still fails. Raw reports remain local.

Patch0081 retries SIOCGIFFLAGS EACCES/EPERM using a fresh route snapshot and
actual flags for the requested interface. Normal ioctl success and other errors
are unchanged; missing interfaces, query failures and allocation failures remain
errors. It preserves the actual query errno across close/string cleanup and
adds flag-query/name-conversion diagnostics. The056 trace does not identify
which flag-query substage failed; denied ioctl is a repair candidate supported
by earlier ioctl errors, not a confirmed056 root cause.

The shared last-error formatter previously needed native malloc even for a
short diagnostic suffix, potentially replacing SocketException with OOM when
libc refuses. PS5 now uses a256-byte stack buffer for short suffixes; long
messages retain allocation/error behavior. Java string/exception failures still
propagate. No global allocator or fabricated flags are introduced.

Actual BSD getFlags and route fallback regression passes ASan/UBSan, covering
normal ioctl, both denied errors, loopback/multicast bits, missing interface,
query/mapping failures and unchanged unrelated errors. The actual last-error
formatter passes real JNI/-Xcheck:jni and UBSan for PS5 and desktop controls,
null/empty/252/253-byte boundaries, injected scratch allocation refusal, exact
exception text and cleanup. Target native compilation passes. All057 console
rows, flag resolution, actual readiness/save/stop and native capacity remain
unvalidated.
