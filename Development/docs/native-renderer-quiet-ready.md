# Optional quiet native-renderer startup

`run_ui_until` and the shared presentation path now omit the system ready
notification when the caller supplies an empty ready message. Nonempty messages
retain their existing behavior. The ProsperoCraft consumer uses this to keep
routine launcher startup checkpoints out of console notification overlays.
Diagnostic files and fatal-error reporting remain available.

Validation: the actual native renderer was compiled and executed through the
consumer `tools/preview_launcher.py` fixture on the host. Frontend-before-JVM,
JNI thread ownership and close/unmap/release behavior passed. This does not
establish PS5 display handoff or a new passing runtime milestone.
