# Returning native UI sessions

`native/renderer/demo_renderer.hpp` adds `run_ui_until(draw, update, stop, message)`
for consumers that need to hand VideoOut to another renderer after a native menu.
The callbacks run on the caller's thread. `update` returns whether a redraw is
needed; `stop` is checked between updates. A non-null stop callback is required.
Existing persistent `run`, `run_frames` and `run_ui` keep their behavior.

A completed session closes VideoOut before unmapping its direct-memory buffers,
then releases the physical allocation. It returns true only when all three calls
succeed. On failure it retains the remaining ownership and returns false; callers
must refuse a second display owner. Setup failures still hold the existing native
error screen rather than returning into an uncertain display state.

Host verification on 2026-10-26: existing native preview compiles with warnings as
errors and renders its five states. The consumer launcher fixture compiles the
actual renderer and exercises successful cleanup and injected close, unmap and
release failures, checking ordering and retention. Consumer test:
`ps5-minecraft-java/tools/preview_launcher.py --runtime-workspace <runtime-root>`.
Target compile/link succeeds in consumer candidate075. Host fixtures do not prove
PS5 VideoOut teardown, direct-memory release or the following GPU/SDL handoff.
Those require a console run. No frozen runtime milestone is changed.

Minecraft-specific launcher UI, Microsoft public application ID and authentication
belong in [ps5-minecraft-java](https://github.com/mateo-cogeanu/ps5-minecraft-java).
