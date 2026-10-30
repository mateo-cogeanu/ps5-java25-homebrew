# Opt-in resident alias symbol lookup

`java25_builtin_runtime.py --alias-symbol Alias:export=resident_symbol` changes
one generated lookup entry on an explicitly configured resident alias. Both
names must already be actual C function exports in that alias's target group.
Defaults and the base group's table remain unchanged. The alias retains the
same objects, initializer, memory and lifetime; no loader, platform identity,
new native implementation or Java class transformation is added.

Invalid/unknown aliases, malformed C names, duplicate overrides, absent or
cross-group exports and JNI/JVM entrypoint redirection are rejected. Overrides
are recorded in `builtin-resident-audit.json`. Consumer code is responsible for
ABI compatibility and the behavior of its explicitly chosen exported functions.
The generator cannot infer compatible C signatures from object symbols.

The host test compiles the exact generated table expressions and calls both
base and alias entries under ASan/UBSan, verifying scoped redirection and default/
unrelated table preservation. Existing real PS5 object/schema/constructor/alias
validation also runs. Actual target generation is checked through the consumer
integration. Console behavior remains consumer validation.

ProsperoCraft uses this facility to isolate the known Controlify SDL3 frontend's
event filter/polling from Minecraft's shared resident SDL event queue. Its native
facade, event ownership, bounded queue, physical handoff tests and validation
belong in the Minecraft repository. This runtime facility alone establishes no
SDL/mod compatibility claim. Frozen Java milestones remain preserved.
