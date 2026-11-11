# Exact aligned metaspace reservations on PS5 Java 17

The build 036 Minecraft probe reported a HotSpot native mapping OOM
for 16 MiB. Its numeric source line matches the failed reservation
branch in `metaspace::VirtualSpaceNode::create_node` in the exact
Java 17 build. The subsequent signal stack contains core dump path
and prerequisite checks. The reports contain no native errno for the
failed reservation and do not establish an OS quota or the reason
the request was refused.

Patch 0020 tries one anonymous `PROT_NONE` mapping with the SDK's
`MAP_ALIGNED` flag for dynamically created metaspace nodes. The
normal HotSpot path can first try an unaligned mapping and then
temporarily reserve the node size plus the alignment. The new attempt
asks for only the final size. It verifies the returned alignment and
records the accepted reservation with HotSpot memory tracking. A
native refusal or an unaligned result returns to the previous path,
after releasing any misaligned mapping. A cleanup refusal is fatal
and does not trigger a second reservation.

The existing commit, release and metadata accounting still own the
accepted mapping. The change does not add backing memory, change
metadata or heap limits, or alter class space reservation, Java 21 or
Java 25. The host sanitizer fixture exercises the actual helper with
controlled alignment and refusal results and real anonymous mappings,
including commit protection, release and the cleanup refusal path.
Whether the PS5 honors the flag and can reserve another node remains
for the build 037 console test.

The Java 17 target build and the Java 17 and 21 ordered patch replay
checks passed. The probe alone disables core dumps to avoid repeating
the failing report path while keeping the normal fatal error report.
