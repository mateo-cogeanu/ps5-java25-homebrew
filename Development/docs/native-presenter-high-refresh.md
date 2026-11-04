# Optional high-refresh native presentation

The reusable CPU VideoOut presenter keeps its default60Hz API behavior. A caller
may define the constructor-free C hook `unsigned ps5DemoPresentationTargetHz()
noexcept` returning120. This requests the existing native high-frame-rate mode15;
the title must declare the existing attribute3 bit0x40. The presenter queries real
support, configures that same open handle and measures six vblank intervals after
finding phase. Only a median7–10ms admits the requested120Hz mode. Unsupported or
refused configuration keeps the default; failed/slow/impossible-fast measurement
requests restore mode1. Failed restore forbids handoff. On normal high-refresh
session shutdown, restore must succeed before VideoOut close/unmap/release.
The existing allocation, two-buffer ownership and conservative cleanup remain.

The explicit120 caller also opts into four-pixel tiled RGBA copies with unchanged
bounds/pitch/refusal behavior. Initial buffers still receive the full16MiB state;
subsequent frames publish the complete15x9 64KiB tile footprint (8,847,360bytes)
instead of copying unused allocation tail. No buffer size, memory quota, game
resolution or default drawing path changes. Renderer/update/UI performance is
separate from display refresh. Opt-in reports expose selected mode/measurement
and two-second submitted-frame rate plus average draw/publish/wait times. These
are measured diagnostics, not a promised120FPS workload result.

`tools/test_presentation_refresh.py` runs the actual policy under default-no-query,
verified120, unsupported/config-refusal, slow/failed/impossible waits and refused
restore controls. `tools/test_canvas_blit.py` checks actual old/fast full1080p pixels,
padded rows and unchanged short/invalid-input refusal under ASan/UBSan.
`tools/build_native_presenter.py` compiles the actual target object using explicit
SDK/compiler/generated-font inputs and records output/source hashes. Integration
must replace the matching old renderer object once, retaining original display
ownership. Physical output, delivered FPS, reset and handoff remain pending.
Consumer UI, pacing, performance tuning and console acceptance belong separately
in ProsperoCraft. No Java runtime milestone or release acceptance is implied.
