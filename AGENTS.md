# Persistent GitHub publication rules

These instructions apply to this entire workspace and future chats working here.
The user authorized a public repository and explicitly requested updates with
every change. Do not ask for upload permission again within this scope.

Repository: https://github.com/mateo-cogeanu/ps5-java25-homebrew

## Publish every completed change

After every completed set of source, asset, documentation, build-script or
configuration changes, perform the relevant checks, then run:

```sh
python3 tools/sync_github.py --message "Describe the completed changes"
```

Do this before ending the turn. Publish work in progress to `Development` even
when console tests have not passed yet. Clearly record pending tests and known
failures. Do not wait for ALL PASS to upload development changes.

The sync script also publishes this file as the GitHub repository's root
`AGENTS.md`. Keep that copy consistent through the script.

The workspace `README.md` is the canonical public project README; its banner
is `docs/readme-banner.svg`. The sync script publishes both at repository root.
Keep the milestone table and release links current when freezing a milestone.
This repository's branding and roadmap cover the Java runtime only. Link to
`mateo-cogeanu/ProsperoCraft` for Minecraft-specific goals; do not add game,
graphics or mod-loader roadmaps here. Preserve frozen validation snapshots.
New inbound test apps must not contain preset device IP addresses or client-IP
filters. Listen on available interfaces; pass the target address to external
client helpers at runtime. Preserve older frozen validation snapshots.

Verify the command succeeds and the push completes. Report failures and their
reason; never claim an upload succeeded without evidence. Retry recoverable
failures. Do not overwrite remote changes or force-push to resolve a conflict.
If no publishable files changed, no new commit is necessary.

## Preserve passing milestones

`JVM_Startup` is the frozen first passing PS5 milestone, version 01.000.023.
Preserve its source snapshot and passing compiled package.

Create `IO_Probe` and subsequent named milestone folders only after the user
reports ALL PASS on the actual PS5 for that exact build. Record the title ID,
version, console results and matching package checksum. Host tests, successful
compilation and packaging checks do not establish a console pass.

Freeze each passing snapshot. Continue later changes in `Development`; do not
silently replace a previously passing snapshot with unvalidated work.

Publish passing compiled packages as GitHub release assets, with a matching
validation record and SHA-256 checksum. Verify each release upload succeeds.

## Publication boundaries

Use the sync script's source allowlist. Keep credentials, dependency caches,
build outputs, generated logs, downloaded photos and unrelated personal files
out of Git. Compiled packages belong in release assets, not source commits.

In the final response, state whether GitHub was updated and identify any console
validation still needed. These rules guide work during agent turns; they do not
create a background file watcher or automatic uploads while no agent is working.

## Separate consumer repositories

Minecraft-specific source, artifact pins, harnesses and validation belong
in https://github.com/mateo-cogeanu/ProsperoCraft and must be committed
and pushed there. Reusable Java runtime fixes, patches and packaging/image
tools belong here and are published through tools/sync_github.py. Do not
copy consumer game code or downloaded game JARs into this repository.

## Log retrieval and follow-through

When the user asks to retrieve probe logs, collect and inspect the current-run
reports, then proceed with repairs for concrete issues found within the existing
Java/Minecraft scope. Build, check and publish the resulting changes under the
repository ownership rules above. Do not wait for a separate repair request.
Keep unresolved causes and console validation explicit; raw logs remain local.

## Unmodified Minecraft server JAR direction

The user requires future compatibility fixes and features to live in the Java
port or the separately maintained Minecraft harness/configuration. Do not add
or expand server-JAR transformations, bytecode hooks or replacement game classes.
Keep the official downloaded server JAR intact. Existing local derivative
transformations are temporary migration debt, not the preferred architecture.

Gradually remove the existing transformations as working replacements are
implemented and validated. Move runtime compatibility into the Java port; use
vanilla configuration, ops.json and supported administration mechanisms for
Minecraft policy where possible. Do not silently remove required workarounds
or claim an unmodified server while a derivative is still executed. Record
each remaining transformation and console validation needed for its removal.
Preserve frozen passing snapshots; migrate development only.


## Repository ownership reminder — 2026-10-27

Java runtime fixes belong in mateo-cogeanu/ps5-java25-homebrew; publish them
through tools/sync_github.py from the runtime workspace. Carry the corresponding
runtime integration, build references and validation into mateo-cogeanu/ProsperoCraft
so the Minecraft app actually receives the fix. Keep reusable runtime source in
the Java repository rather than duplicating it in the consumer. Minecraft-specific
code, launcher work, JVM launch-policy configuration and game validation belong
in ProsperoCraft. Publish the relevant changes to both repositories when a Java
fix requires consumer integration. Preserve frozen passing snapshots and the
existing release/Store hold until the user confirms the stutter fix.


## Optional ImageIO raster integration — 2026-10-27

The Java development runtime now offers tools/java25_imageio.py and opt-in
java25_builtin_runtime.py --imageio: genuine pinned OpenJDK Disposer/raster IDs,
Unix ID initializers/Trace and bundled LCMS. Do not advertise complete AWT,
GUI/fonts/printing/JPEG support. Preserve default core library behavior and frozen
milestones. Host PNG/ICC tests force our native subset and verify no stock fallback;
consumer104 PS5 image use and rendering remain pending. See
 docs/java25-imageio-raster.md and matching Java validation. Reusable native build
and packaging tools live here; game integration/GC policy/UI and logs remain in
ProsperoCraft. No official game/mod JARs or raw consumer logs enter this repository.


## Explicit resident aliases — 2026-10-27

The reusable runtime registry supports opt-in --library-alias alias=existing_group.
Aliases share symbols/JNI initializer and resident lifetime;no arbitrary loader,
platform spoofing or new native implementation. Defaults stay unchanged. Consumer
106uses SDL3=ps5sdl for Controlify's missing-library error;consumer integration,
HID/audio/UI and validation belong inProsperoCraft. Actual PS5 FFM/Controlify
behavior remains pending;an alias does not establish mod compatibility. See
 docs/java25-external-resident-libraries.md. Preserve frozen runtime milestones.

## Descriptor-first paths and diagnostics — 2026-10-28

Runtime0125 uses checked descriptor-first canonicalization on PS5; native symlink/relative resolution and other platforms remain.112 reproduced EMFILE, so soft-limit adjustment alone is insufficient and the leaking owner is unproven. File diagnostics use sceKernelFstat, with opt-in PS5_TRACK_FILE_ACTIVITY accounting. Keep raw paths/reports local and physical console save validation explicit. See docs/java25-descriptor-first-paths.md. Consumer rumble, mode arbitration and113 integration belong in ProsperoCraft. Preserve frozen milestones and Store108.

## Optional ZIP descriptor budget — 2026-10-28

Runtime0126 adds opt-in ps5.zip.maxOpenFiles (8–128) for immutable ZipFile sources. Defaults remain unchanged; OPEN_DELETE stays pinned. Do not claim preservation of an unlinked/replaced inode after eviction or a universal file-descriptor cap. Consumer114 enables64 after113 shows241regular files and EMFILE on deep world walks. Exact title quota and PS5 lifecycle remain pending; user reports113 haptics working. See docs/java25-bounded-zip-handles.md. Preserve frozen snapshots/Store108 and keep consumer source/raw reports separate.


## Optional genuine JNA dispatch — 2026-10-28

Runtime-owned tools/java25_jna.py builds pinned JNA5.19.1 dispatch/callback JNI (nativeABI7.0.4from common.xml, not stale Makefile defaults). Caller supplies compatible libffi/resident jnidispatch group. No default library/image changes or arbitrary loader added. Genuine host native sizes/error/memory/ffi tests force our library; target initialization/calls/callbacks remain pending. JAWT/signal protection not enabled; no broad JNA compatibility claim. Consumer launcher properties and original-game integration belong in ProsperoCraft. See docs/java25-jna-dispatch.md. Preserve frozen milestones.

## Optional libjava direct scratch — 2026-10-29

Runtime127adds default-offJNU_PS5SetDirectScratchEnabled for temporaryClassLoader/
platform-string buffers after libc/anonymous failure. Consumer124Fabric26.2logs
show tinystringmallocfailure+anonymousENOMEMwith lowJavaheapuse;exact nativequota/
owner unproven. Preserve defaults; consumer125explicitly enables. EachCunit64slots/
8MiB(16MiBtotal), noheap/metadata/driverpolicychange. Mapfailrollback,uncertain
unmap/release retainbudget/backingownership;noorphanrecoveryclaim. Hostheader
ASan/UBSan,actualdisabledJNIstring/ClassLoader/leaseconcurrency,targetbasebuildpass;
PS5allocation/release/startup/world/endurancepending. See docs/java25-core-direct-scratch.md.
Publishreusablepatch/runtimehereandconsumerintegrationseparately;frozenpreserved.

## Optional verifier small reserve — 2026-10-29

Runtime128 adds default-off JNU_PS5SetVerifierSmallReserveEnabled: after libc
refusal, up to16384aligned256byte verifier slots (4MiB BSS) avoid mapping16KiB
per tiny name/node; larger/exhausted requests retain anonymous fallback. Consumer125
Fabric26.2 Matrix4f site4221/ENOMEM reproduced this waste. Host bounds/ownership/
concurrency and actual disabled verifier tests pass; target rebuild and PS5
Fabric/world/endurance validation recorded separately. Reusable patch here;
consumer126 explicit enablement/integration in ProsperoCraft. See
 docs/java25-verifier-small-reserve.md. No frozen milestone or Store pass implied.

## Variable-sized verifier reserve — 2026-10-29

Runtime129 extends opt-in128's fixed4MiB arena to contiguous256byte unit runs,
so originalMatrix4f verifier2048byteCCinit and larger buffers fit without one
mapping per request. Defaultoff/mallocfirst/anonymousfallback remain. Real
publisherJOML classes pass fulllegacyverification with malloc+mmapdenied;
bounds,wholearena reuse,concurrency and targetbuild checked. See
 docs/java25-verifier-variable-reserve.md. Consumer127 integration separate;
PS5Fabric launch/world/endurancepending. Underlying libc refusal unproven.

## Opt-in compiler-TLS direct fallback — 2026-10-29

Consumer129 retained128-style nativeabort identifies compiler-rt__emutls_get_address
and48byteprefixed allocation afterlibc/anonymousfailure;loadadjustment0x400000
fromin-imageanchor. Reusableemutlsadapteraddsdefaultoff enable_direct setter and
existing shared256MiB/2048entrynative-directledgerfallback onlyafterENOMEM.
Matchingunmapownership/failedgrowthpreserved;noheap/GC/globalallocator change.
See docs/java25-emutls-direct-fallback.md. Hostfailure/lifecycle/ledger/target
checks recorded;consumer130integration andPS5launch/world/endurancepending.

## Optional native network-node scratch — 2026-10-29

Patch0130 gives libnet DNS/interface conversion nodes independent default-off
JNU_PS5SetNetworkScratchEnabled policy. Reuses0127mapper afterlibc/anonymousENOMEM,
64slots/8MiB perInet4/Inet6/NetworkInterfaceCunit,24MiBaggregate;pairedreleaseand
boundedretainedcleanupfailureownership,noDNSanswer/auth/heap/GC/globalallocator
change. Consumer140reports original Inet4lookup Nativeheapallocationfailed.
Hostactualheader/mapperASan/UBSan andexistingDNS/conversion/cleanupregressions,
PS5java.base-libsbuild/exportschecked;actualconsolelookup/Fabric/world/savepending.
See docs/java25-network-direct-scratch.md. Consumer141pin/enable/package belongs
inProsperoCraft;rawreportslocal,preservefrozenmilestones/Store121.

## Optional extended native synchronization reserve — 2026-10-29

Patch0131 adds bootstrap-only JVM_PS5SetExtendedSyncReserveEnabled;default native
counts4096mutex/4096relative/2048absolute unchanged,explicitmode8192/8192/2048.
Fixedmaximum metadata grows;nativeextraobjects onlyopt-in. SetterEBUSYafterprime,
bootstrapthreadonly. Existingprimingcounts/nativefallback/checks/attributeclock/
wait/ownership semanticsretained. Consumer141fatalmonitorinitENOMEM and4096/4096
leasedtrace duringControlifyFFMclassgeneration. Hostactualdefault+extended native
pool/exhaustion/reuse/wait/8000concurrency/cleanup andtargetIRchecks;PS5counts,
FFM/startup/world/save/regressionpending. See docs/java25-extended-sync-reserve.md.
Consumer142pin/enable/package/rawreports inProsperoCraft;frozenmilestonespreserved.

## Optional native library-name scratch — 2026-10-29

0132routes NativeLibraries.c temporaryname buffers through0127mapper/pairedrelease;
existingJNU_PS5SetDirectScratchEnabled defaultoff,libc/anonymousfirst. Addsone
64slot/8MiB Cunit (libjava3units24MiBaggregate);libnetindependent. No registry/
nameparsing/JNIlifecycle/searchpath/arbitraryloader/heap/GC/globalallocchange.
Consumer143menuworksbutControlifyfindBuiltinLibOOM and Deflaterclinit sameOOM
blocks integratedworldstart. HostactualJNI default/direct/refusal/cleanupcontrols,
existingmapperfailure/bounds andPS5java.base-libs/objecthashchecks;consolepending.
See docs/java25-native-library-direct-scratch.md. Consumer144integrationpin belongs
inProsperoCraft,rawreportlocal,preservefrozenmilestones/Store121.

## Source history migration — 2026-10-30

Frozen top-level milestone sources now live in https://github.com/mateo-cogeanu/ps5-homebrew-history at commit aa7db35ee9aa5cc6515f49b23ebda6d1ecfcf91d, separated into runtime/ and prosperocraft/. This supersedes earlier instructions requiring frozen folders in the active tree: preserve their bytes in the archive, existing tags and original release assets. Do not recreate historical folders during sync or new development. New passing snapshots belong in the archive with provenance, checksums and original validation. Compatibility implementations, unfinished features, active regression fixtures and licensing/relink tooling stay in their canonical active project. Do not remove an implementation because its feature is disabled or awaiting console acceptance. See docs/source-organization.md (Development/docs/source-organization.md in the published runtime layout).

## Explicit release approval gate — 2026-10-30

The user requires physical-console confirmation that the exact build works before creating any further GitHub release, including development prereleases. Continue authorized source commits/pushes and local test builds, but do not create a release until the user confirms that build works. This supersedes earlier practice of publishing unvalidated hardware-test prereleases. Remove only the three specifically identified 154/155/156 hardware-test releases; all other releases/assets, including 153, remain preserved. Local test artifacts and source tags for the withdrawn releases stay retained.

## Optional resident alias symbol lookup — 2026-10-30

The runtime registry supports explicit --alias-symbol Alias:export=resident_symbol
on a known resident alias. Both functions must be actual exports in its existing
group; defaults/base tables unchanged, no loader/newobjects/platformspoofing.
Schema/duplicates/missing/crossgroup/JNIentrypoint rejection and actual generated
hosttable calls tested. Consumer owns ABI correctness; generator cannot infer C
signatures. See docs/java25-resident-alias-symbols.md. ProsperoCraft SDL3 event
facade/isolation/physicalhandoff belongs in consumer;target+console validation
recorded separately. Preserve frozen snapshots and release/Store hold.

## ProsperoCraft portable host verification — 2026-10-31

Append to, and preserve, all existing rules. Launcher host tooling and Actions
live in the active ProsperoCraft checkout, not the runtime tree. Follow that
repository's docs/host-testing.md and tests/host-lanes.json: run
`python3 tools/run_host_tests.py` (first use `--fetch-deps`) for deterministic
launcher policy assertions, and `--lane native` for affected scoped native code.
Require Python3.10+ without optimization, JDK25 and verified host-only library
pins; use explicit options/JAVA_HOME/CC/CXX/LLVM_HOME/PATH/HOMEBREW_PREFIX instead
of machine paths. Keep shared discovery import-safe and fail clearly on missing
required tools/dependencies; never silently substitute private game caches.
Verify portability in a source-only checkout with empty dependency cache and
outside-root invocation. Consult the consumer inventory for SDK/package,
graphics/audio and downloaded-game checks; do not equate file counts with
coverage or one Vulkan backend with another. Preserve active compatibility
implementations, original JARs and archived snapshots. Publish source changes to
the owning repositories, inspect actual Actions jobs, and distinguish local,
hosted and physical-console results. Existing release/Store gates remain in force;
host CI does not establish an exact PS5 build pass. New workflow rules must be
added alongside existing AGENTS.md rules rather than replacing them.

## Optional C++ exception compiler TLS — 2026-10-31

Runtime-owned tools/java25_cxxabi_tls.py builds pinned genuine LLVM18.1.8
exception globals HAS_THREAD_LOCAL branch, explicitly linked by consumer171.
Defaults/SDK archives unchanged; existing compiler-TLS allocation/retirement
policy remains. Consumer170 voice-chat playback abort reports native key setter
failure after real AudioOut0x8026000d refusal. Host storage concurrency/reuse and
nested exception checks with setter refusal plus target symbol audit pass;
PS5 world/voice/error recovery/save/endurance pending. AudioOut cause unresolved.
See docs/java25-cxxabi-compiler-tls.md. Consumer integration separate, raw logs
local, preserve frozen history and release/Store gate.

## Returned pthread error stack fallback — 2026-10-31

Patch0133 removes errno dependence from PS5 Java/compiler EAGAIN owned-stack
retry. Native pthread return controls it; unchanged64slots/32MiB/requested sizes,
realcreate/quota/ledger/join/failedcleanup semantics. Adds rejection/budget trace.
Consumer171 Sodium/Vitrail EAGAIN+OOM observed; live VMtrace denied, exact cause
unproven. Hostgate/actual1024KiB lifecycle+faulttests,targetHotSpotpass;172world,
shader on/off,save,voice,endurancepending. See docs/java25-pthread-return-stack-fallback.md.
Publish runtime+consumer integration separately; no release/Store or frozen pass.

## Optional owned thread-stack budget — 2026-10-31

0134 bootstrap-only JVM_PS5SetExtendedThreadStackBudgetEnabled selects64MiB;
default32MiB/64slots unchanged,lateEBUSY,serializedfreeze,noallocationinsetter.
Full171trace retrieved viaSafariHTTP shows32MiBlive and8nativeEAGAINattempts
beforeemergencyshutdown;errno gate133notthisrun'scause,nativeallocatorrefusal
unresolved.172explicitlyenables. Actualhostdefault32reject/extended33concurrent
1MiBthreads,joinedreclaim,TLS/fault/budgettests,targetHotSpotpass;PS5world/shader/
save/voice/endurancepending. See docs/java25-thread-stack-budget.md. Shared256MiB
nativeledger,requestedstacks,realnativecreate/quotas,conservativecleanupretained.

## PS5 socket pre-close — 2026-10-31

Patch0135 replaces PS5 socket preClose0 dup2 (consumer173 SVC disconnect EPERM)
with checked shutdown(SHUT_RDWR), EINTR retry/ENOTCONN acceptance. Descriptor
ownership, Java closing state/signals and deferred final close remain; never
close/recycle an in-flight descriptor. ENOTSOCK retains original non-socket error
path; other platforms unchanged. Actual JNI JDK25 blocked UDP/TCP/accept repeated
close, negative controls and target java.base rebuild pass; PS5 wakeup/disconnect/
rejoin/save pending. See docs/java25-socket-preclose.md. Consumer174 integration
and mic diagnostics belong in ProsperoCraft; release/Store holds remain.


## Optional JDK management extensions —2026-11-02

The runtime registry supports default-off --management-extensions for genuine
OpenJDK jdk.management/libmanagement_ext, implying java.management. Consumer must
include target-built module classes and matching resident native library. Keep real
JMM values/flag origins/read-only behavior; no replacement MBeans, fabricated VM
flags or game JAR rewrites. Full OS/sysctl/procfs/heap-dump/diagnostic-command
behavior is not established by flag queries. See docs/management-runtime.md.
Consumer shader acceptance is an explicit physical-console release prerequisite;
its pack/build integration and validation belong in ProsperoCraft. No runtime host
result or shader compilation alone substitutes for that consumer confirmation.


## PS5 management small-query stack —2026-11-02

0136 uses per-call stack storage for up to16original jmmVMGlobal flag records;
larger requests retain malloc/refusal, all free paths distinguish ownership and
other platforms stay unchanged. Actual JMM/values/origins remain; Java/VM allocation
failure is still possible. Forced native host1/16/17/refusal/concurrent tests and
target management_ext build are scoped evidence, not PS5 shader acceptance. See
docs/management-runtime.md. Consumer202integration/pack/quit remain separate and
release/Store gates stay held.

## Optional resident symbol namespaces —2026-11-03

Runtime137 adds default-off --library-symbol-prefix external_group=prefix_ and
PS5 weak JVM_PS5ScopedBuiltinHandle selection for explicit namespaced groups.
Actual code/data/TLS definitions are separated; handle lookup retains original
names, process-first lookup/default groups remain. Native signatures and coherent
classloader ownership remain consumer responsibilities; no ABI adapter or arbitrary
loader. Schema/collision/link/code-byte/generated-table/actual JNI load-body/error/
default/alias tests and target java.base-libs pass; PS5 dual-generation lookup,
callbacks/lifecycle remain pending. See docs/java25-resident-symbol-namespaces.md.
ProsperoCraft owns approved333 Vanilla integration; Fabric is deferred until
Vanilla121 is validated. Preserve released204, frozen history and release gates.


## Report HTTP stack repair —2026-11-04

The shared handler's512-row diagnostic formerly imposed a70,472byte target frame
on every request. Fixed BSS snapshot ownership and4KiB request/stream reuse remove
that large automatic array; concurrent full snapshots return503 and release on
send failure. Actual64KiB pthread O0/O2 and historical x86_64 fault controls plus
HTTP/collector/writer/file accounting tests are scoped host evidence. PS5 HTTP
access after consumer rebuild remains pending; do not infer exact native stack
size or physical fault address. See docs/java25-log-share-stack.md. Consumer121
callback allocation and candidate integration remain in ProsperoCraft.

## Optional native presenter high refresh —2026-11-04

The reusable native renderer keeps default60 behavior; explicit constructor-free
ps5DemoPresentationTargetHz120 opts into native support/configure/vblank verification,
checked restore before close and fast tiled RGBA publication. Caller owns manifest
0x40, UI pacing/workload and integration. Default no-query and actual policy refusal,
old/fast full-pixel/pitch/short-input sanitizer and target-object checks pass; actual
PS5 refresh/FPS/reset/handoff remain pending. See docs/native-presenter-high-refresh.md.
Source/runtime helper belongs here; ProsperoCraft owns launcher211 integration and
physical animation/trigger/menu acceptance. Preserve frozen bytes and release gates.

## Optional bootstrap report directory —2026-11-05

The reusable native HTTP handler supports explicit configure_root before start,
with bounded BSS path/allowlist storage and default archive/session relocation.
Defaults remain download0; caller owns actual access, consistent writers and
storage fallback. No mounts/elevation/arbitrary URLs or VM/image policy change.
start freezes selection, including after failure/stop; late EBUSY. Default,
refusal/actual HTTP bytes/session and existing collector/64KiB stack regressions
pass. Consumer216 all-data/report/tmp migration and fallback belongs in
ProsperoCraft; physical console validation pending. See docs/probe-report-root.md.


## Separate Java17 and21 baseline builds —2026-11-08

The maintainer prioritizes a genuine Java17 runtime before Vanilla1.20 and also
requests Java21 for1.21.x comparison. Version-pinned FreeBSD/OpenJDK source,
bootstrap pins and rebased patches live under java25/lts; tools/java_lts.py builds
isolated HotSpot C1+C2/java.base baselines and class-only images. DefaultJava25
source/images/configuration and frozen milestones remain unchanged. These builds
are not console-ready runtimes: image/resident lookup, sandbox CPU/signal/memory/
thread/TLS services, native packaging and consumer bootstrap need explicit
porting/validation. Preserve genuine classes/native generation ownership and
original game JARs; never relabel an existing runtime or claim lower overhead
without matched measurements. Reusable implementation here; consumer selection/
graphics/mods/worlds/shaders in ProsperoCraft. Follow docs/java-lts-runtimes.md
and existing physical-console/release/shader gates. Host image/ELF audits are
scoped build evidence, not a PS5 pass.


## Java17 isolated startup candidate002 —2026-11-08

The maintainer requests startup integration. Java17's reviewed patch adds actual
packaged17 paths, explicit options, native system queries, reservation commit,
PS5 register/fpstate view, native sandbox properties and JIMAGE read-only copies.
Default25 and21baseline remain unchanged. Local PPSA99876/01.000.002 is a separate
startup probe, not ProsperoCraft: staged constructors, genuine17VM/-Xint/SerialGC,
Java arithmetic/StrictMath/exception/registered JNI/worker/join and destruction.
These are probe limits only; C2/game/shader/performance not established. Native
lookup is actual matched17 symbols with bounded VM text dladdr; no arbitrary ELF.
Host exactJNI/JIMAGE/registry/signal/source controls pass; physical4rows pending.
Untested001 retained, superseded after final fpstate audit. Do not freeze/publish
any release before exact console confirmation. Source publication remains required.
See docs/java17-startup-probe.md and matching build record. No NAS writes or changes
to supported Minecraft instances. Existing frozen snapshots and releases preserved.


## Java17 startup acceptance and separate Java21 candidate —2026-11-08

Java17 Startup PPSA99876/01.000.002 received exact-build user ALL PASS for its
four interpreter startup/JNI/thread/destruction rows. Preserve package SHA256
c2241e10bb8c0cb895c7fc02a8490cdd50b2be670e54bc561c90e98c43776c29,
source d503c8336d1b4e55faf9e4dc5f147ce596d3ab1d and the frozen archive snapshot
runtime/Java17_Startup at279f6b84352064dd646864d3f59cd29c80422fee. Its verified
release contains exact package, complete original upstream+port source and checksums.
No C2/game/performance/collector/endurance pass is implied. Java21 startup001,
PPSA99877, is a separate local candidate with matching21 classes/core objects;
physical startup pending. Shared helpers default17 and require explicit --major21
for21. Preserve Java25 consumer and original JARs; consumer integration and exact
hardware/shader release gates remain separate. See docs/java21-startup-probe.md.


## Java21 startup acceptance —2026-11-08

Exact standalone Java21 PPSA99877/01.000.001 received user ALL PASS for all four
interpreter startup/JNI/worker/destruction rows. Preserve package SHA256
33598afb949733eedfc328695d4fffcc81091ed46d1ff92654dc3611cc5d2260,
source051cbf7e22583d7c11010710d854685f3fb1e731 and archive snapshot
runtime/Java21_Startup at2468e3d5034b4c5122e14bf5a461fdc0db27ce0a. Verified release contains unchanged passing
package, complete original upstream+frozen port source, build/console records and
checksums. This supersedes pending startup status only; C2, general API/FFM/virtual
threads, Minecraft, shaders, performance and endurance remain unvalidated. Keep
both17/21 frozen bytes and working25 consumer. Consumer bootstrap/bindings and
physical game/release gates remain separate; see docs/java21-startup-probe.md.


## Opt-in LTS consumer bootstrap integration —2026-11-09

Active LTS tools accept explicit class-only --modules images, genuine matching
management groups and statically linked --library name=object inputs. Default
core images/probes remain unchanged; no runtime arbitrary ELF loader is added.
Separate management/consumer JVM globals and JNI initializers retain private
ownership and constructor staging. Explicit consumer --probe-dir/extra assets/
link objects support local tests; consumers own original publisher inputs,
ABI/classloader coherence and their game harnesses. Desktop class availability
is not native AWT/fonts/GUI/printing support. See docs/java-lts-bootstrap-integration.md.
PPSA99878/01.000.001 is an unvalidated consumer1.20 entry/JNI bootstrap test, not
playable-world/C2/shader/performance acceptance; no release/Store or frozen pass.


## Java17 early startup phase diagnostics —2026-11-09

Consumer001 crashes in JNI_CreateJavaVM after extended JIMAGE allocation/read/
read-only protection completes. Retained trace has no PC; heap/module/JNI cause
is unproven. Active17 Threads::create_vm adds fixed phase trace calls only,
preserving semantics/options and non-PS5 no-op behavior. Runtime trace0600 remains
private by default. Consumer002 owns explicit diagnostic-only0644 sharing and
existing scoped fault capture around VM creation; preserve prior handlers/context
and working25/frozen17/21 bytes. No crash resolution, game/shader/endurance pass
or release/Store approval. See docs/java-lts-startup-phase-trace.md.


## Java17 init_globals boundary diagnostics —2026-11-09

Consumer002 reaches init_globals after OS init2/VM globals; external fault file is
empty despite reported installation. Cause/PC unproven. Active17 adds fixed inner
initialization markers and at most4numeric VMError entry records (ID/PC/size/line),
using bounded stack formatting, no error strings/caller paths or changed failure
semantics. Consumer003 alone reduces its test heap512to128MiB to isolate the
passing probe profile while retaining extended modules/bindings. No production
heap/GC/Java25 default change or game/crash acceptance; frozenbytes preserved.


## Optional LTS JNI-stage callbacks —2026-11-09

Shared17/21probe JNI helper gains default-null fixed trace/on-class callbacks for
explicit consumer diagnostics, with original default/check/error/ref behavior.
Consumer003physically creates the extended VM at128MiB, then crashes row3before
its Java stage file; exact boundary/cause unproven.004adds native checkpoints and
consumer-owned nativeStage registration plus scoped bounded signal capture. No
new Java API/game class/native policy replacement, frozen pass or release claim.
See docs/java-lts-bootstrap-integration.md; consumer source/fault policy stays there.


## Java17 NIO bootstrap boundary —2026-11-09

Consumer004successfully enters its Java probe, then faults at first Path.of before
management/bindings/original Main. Captured SIGSEGV PC is not yet region-resolved;
getcwd/native cause unproven. Runtime17adds fixed UnixNativeDispatcher init/getcwd
markers only, preserving errno and genuine return/capability/syscall semantics.
Consumer005tests upstream sun.nio.fs.chdirAllowed=true to resolve paths against
configured user.dir without the native cwd comparison; no global default or fake
filesystem answer. Exact PS5 result pending. See docs/java17-nio-bootstrap-boundary.md.

## Java17 memory failure trace —2026-11-10

Consumer017 starts the VM and shuts it down cleanly. Original Main reports an
unclassified OOM at aoi.<clinit> with roughly53MiB Java heap in use; the failing
resource is unproven. Active17 traces first HotSpot OOM category, bounded commit
refusals and bounded libjava OOM requests without exception messages. No memory
policy or frozen changes. Consumer018 keeps the017 heap settings. See
docs/java17-memory-failure-trace.md; physical console result pending.

## Java17 verifier scratch fallback —2026-11-10

Consumer018 reproduced row3 OOM with none of its new markers. Active17 uses
the existing native heap allocator for PS5 legacy verifier owned scratch,
with paired cleanup and a fixed verifier OOM marker. Exact failing path is
unconfirmed. Preserve original JARs and frozen snapshots. Consumer019 exact
PS5 result and release remain pending. See docs/java17-verifier-native-scratch.md.

## Java17 core native scratch —2026-11-10

Consumer019 logs libjava OOM and a SIGILL resolved to the process C++ array
allocation trap. Exact callers remain unconfirmed. Active17 shares paired
native scratch with ClassLoader-owned buffers and libjimage arrays. Preserve
original game inputs and frozen builds. See docs/java17-core-native-scratch.md.
Consumer020 physical row3 and title screen pending.

## Java17 pending exception trace —2026-11-10

Consumer021 stops after original Main initializes with no growth in the
retained fault file. Active17 offers explicit default-off pending exception
class/source-line tracing with128process records, fixed buffers and original
handling. Consumer022 scopes enablement to Main. Cause and physical startup
remain pending. See docs/java17-pending-exception-trace.md.
