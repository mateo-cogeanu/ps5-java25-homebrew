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
