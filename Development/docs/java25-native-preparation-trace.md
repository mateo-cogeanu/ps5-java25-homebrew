# PS5 native-method preparation diagnostics

Patch0073 adds bounded traces to InterpreterRuntime::prepare_native_call:
before creating its methodHandle, after native lookup, and after signature
handler installation. Each line records the length-delimited holder/name/JNI
signature and current thread identity, with the resolved native target where
available. Formatting uses a384-byte stack buffer, bounded per-part copies,
printable-byte substitution and visible truncation markers; it does not use
Symbol::as_C_string, ResourceMark, heap allocation or new TLS initialization.

These are preparation events, not a complete JNI invocation trace. A method
prepared earlier can execute again without an event, registered methods can
skip lookup, and nested calls may supersede the latest recorded method.
Do not equate the latest preparation with the active native method at a fault.
Existing trace IO still opens/writes/closes a file and can fail; the formatter
adds no method/signal recovery or changes to native resolution semantics.

This narrows an external-address signal seen after lowering the Java heap
ceiling; its cause remains unknown. The target build passes. An actual-header
ASan/UBSan fixture tests unterminated Symbol-like byte slices, normal output,
long/truncated/nonprintable/empty inputs, target and thread identities, and
concurrent formatting with stubbed trace IO. It does not execute HotSpot
preparation or actual PS5 IO. Console trace usefulness and native target fault
resolution remain pending.
