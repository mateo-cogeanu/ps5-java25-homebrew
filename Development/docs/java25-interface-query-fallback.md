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
