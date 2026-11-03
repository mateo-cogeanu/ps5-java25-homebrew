# Opt-in resident symbol namespaces and builtin JNI handles

`java25_builtin_runtime.py --library-symbol-prefix group=identifier_` isolates
one explicitly listed external group's native definitions while retaining its
original JNI/C lookup ABI **on that group's handle**. Defaults, existing groups,
aliases and core lookup tables remain unchanged without the option. The prefix
must be unique and end in an underscore; the group must be an actual external
group, not a core library or an invented alias. Strict object/schema, constructor
and known-resident-only restrictions remain.

The generator merges supplied objects, then renames every real external
definition, including data, weak definitions and compiler TLS, using llvm-objcopy.
Internal references follow those definitions. Undefined imports retain their
names and provider contracts. Generated table entries retain the original lookup
name and point to the corresponding prefixed symbol. A prefix creates neither
a native implementation nor an ABI adapter. The consumer must supply matching
classes/native signatures and keep a coherent classloader owner.

Patch0137 supplies the other necessary boundary: builtin JNI libraries normally
receive the process handle in OpenJDK's original NativeLibraries.load. For selected
groups the generated optional `JVM_PS5ScopedBuiltinHandle` returns their real
resident table handle, so subsequent JNI resolution stays in that table. Original
load hooks, version/exception checks and handle-field publication remain. The
hook is weak and PS5-only; absent/unselected groups keep the process handle,
nonbuiltin loading is unchanged, and other platforms retain their body. The
generated hook is emitted only with explicit prefixes and accepts only exact
configured group/alias names. It returns no arbitrary load handle.

Process lookup retains its existing first-match behavior. A scoped group is not
hidden from enumeration or sandboxed; consumers must load it under its own
distinct library identity and classloader. Code remains resident. Existing JNI
discovery wrappers and alias-symbol restrictions remain. No arbitrary ELF loader,
platform/version spoof or default allocator policy is added.

## Validation and limits

`tools/test_java25_resident_namespace.py --java-home <JDK25> --llvm-home <LLVM>`
compiles real PS5 relocatable fixtures whose JNI functions and data initially
collide, generates actual tables and links their separated definitions. Objcopy's
allocated code/data bytes remain unchanged. The actual generated tables execute
on the host with controlled function bodies: base/scoped/alias results, unchanged
process lookup, unknown-library/name refusal and original initializer/refusal.

It also compiles the **actual patched NativeLibraries load/find bodies** against
host JNI, with OS loading/handles injected. Real JDK25 tests scoped/default/
unknown/nonbuiltin handling, missing hook, non-PS5 behavior, JNI-version refusal,
original-hook exceptions, field publication and nonbuiltin failure cleanup under
Xcheck:jni/UBSan. It does not replace installed host libjava or establish an
embedded-VM/PS5 classloader pass. Existing resident schema/constructor/alias,
actual JNI name-allocation fault and builtin discovery tests pass. Target
java.base-libs rebuild passes. [Validation](validation/resident-symbol-namespaces-2026-11-03.json).

Without the option, the complete new lookup source compares byte for byte with
the previous published generator on identical inputs. Actual PS5 dual native
generations, lookup/classloader ownership, callbacks, teardown and consumer
behavior remain pending. Adoption/pins belong in the owning consumer repository.
No release, frozen milestone or console pass follows from these checks.
