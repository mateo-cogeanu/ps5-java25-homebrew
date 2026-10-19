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
`mateo-cogeanu/ps5-minecraft-java` for Minecraft-specific goals; do not add game,
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
in https://github.com/mateo-cogeanu/ps5-minecraft-java and must be committed
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
