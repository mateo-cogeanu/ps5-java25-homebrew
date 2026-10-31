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
