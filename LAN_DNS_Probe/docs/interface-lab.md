# PS5 Interface Lab

A native PS5 interface prototype with smooth Inter typography, antialiased
rounded panels, a quiet dark palette, and controller navigation. It is a visual
playground: cards and pages have preview content, with no application features,
network requests, or saved settings.

The preceding controller-tester build was confirmed working by the user on
firmware **13.60**. This update preserves its native startup, community runtime,
VideoOut initialization, and controller ABI. The new interface has passed local
build/package checks and host screenshot review; it needs its own console test.

## Install the update

Close the currently running app. Copy the entire `dist/PPSA99861/` folder over
your existing `/data/homebrew/PPSA99861/` folder (or the same custom scan location
you used previously). A ZIP is also available at `dist/PPSA99861.zip`; extract
it before copying. Keep the files at these levels:

```text
/data/homebrew/PPSA99861/
  eboot.bin
  sce_sys/
    param.json
    icon0.png
  sce_module/
    libc.prx
  licenses/
```

Let your existing ShadowMountPlus setup rescan/register the folder and launch
it from the home screen. The title is now **Interface Lab**, version
`01.001.002`, retaining the original title ID. Existing home-screen name/artwork
may remain cached until the loader refreshes it. The packaging follows the
[ShadowMountPlus folder layout](https://github.com/drakmor/ShadowMountPlus).

## Explore with the controller

- D-pad or left stick: move between cards; move left from the first card to
  focus the sidebar.
- Up/down in the sidebar: switch Explore, Collections, and Appearance pages.
- Cross: explore a selected card or leave the sidebar. Cross in the dialog
  returns to the page.
- Circle: close the dialog or switch between sidebar and cards.
- PS button, then Close Game: exit through the console home screen.

Appearance cards are visual previews; they do not apply themes. The interface
stays open until closed through the PS5 shell. No automatic timeout or exit
chord applies to the native app. CPU rendering makes it an interface experiment,
not a controller-latency benchmark.

The user-confirmed controller-tester package is preserved at
`dist/ControllerTester-01.000.000.zip`. Extract it and replace the same title
folder to return to that build. Its copy is also kept in
`.tools/working-controller-test/` outside build outputs.

## Build

```sh
make package
```

The build uses the pinned community native tools, public PS5 Payload SDK v0.42,
Homebrew LLVM, and Python with Pillow. The generated libc runtime must match
its upstream SHA-256 reference; eboot and runtime FSELF integrity are checked.
Metadata, icon, runtime, and license files are included in the folder and ZIP.
See `THIRD_PARTY_NOTICES.md` for dependency provenance and licenses.

## Preview on this Mac

```sh
python3 tools/preview_ui.py
```

The preview compiles the actual UI/renderer for x86 macOS and uses Rosetta on
Apple Silicon. Synthetic controller inputs render the home page, preview
dialog, both additional pages, and disconnected-controller state under
`build/native/preview-*.png`. These previews verify layout, not PS5 video/input
compatibility.

The font baker embeds antialiased glyph coverage at five sizes inside the
native executable. `native/renderer/` extends the community framebuffer renderer
while retaining its tiled VideoOut format. No font/runtime library needs to be
installed on the PS5.

### Responsiveness fix (01.001.001)

The first smooth-interface build had roughly one second of input lag on the
user's console. It blended pixels directly in write-combined video memory and
only read the controller between full redraws. The renderer now draws in
cached CPU memory and publishes the finished frame with streaming writes.
The UI polls at 4 ms while idle and renders only when visible state changes;
input queues are drained before drawing. The dialog's X action is covered by
short-tap and held-button regression checks. This update needs a console
latency retest; host previews do not measure PS5 performance.

### Startup allocation fix (01.001.002)

The user reported that 01.001.001 crashed before showing the interface.
Its new staging frame used a 16 MB throwing heap allocation; the native C++
runtime traps if that allocation fails. This is a suspected startup cause,
not a diagnosis from a console crash trace. The staging frame is now aligned,
zero-initialized executable storage, avoiding that large heap allocation.
Cached drawing and idle input polling remain in place. Host previews reject
large array allocations during startup and still render all preview states.
Native package integrity and input regression tests pass. The user has now
confirmed that 01.001.002 runs and responds well on their PS5.

## Java 25 / Minecraft work

The target is Minecraft Java Edition, Fabric/Forge support, and a Minecraft
server. All six initial platform tests passed on the user's console. HotSpot
and java.base now cross-build successfully, but JVM startup on PS5 remains
untested. See [java25/README.md](java25/README.md) for the pinned
source, build blocker, milestones, and console probe instructions.

`make java25-probe` builds the separate `dist/PPSA99862/` title folder and
`dist/PPSA99862.zip`, leaving the working Interface Lab title intact.

`make java25-runtime-probe` builds `dist/PPSA99863.zip`, the second console
probe for page size, condition variables, signal delivery and generated-code
execution. It is not a JVM launcher.

All four runtime probe tests have now passed on the user's console.
`make java25-jni-probe` builds `dist/PPSA99864.zip` with the real embedded
HotSpot objects for constructor initialization and JNI setup checks. VM
creation and Java bytecode execution remain the next milestone.

The embedded HotSpot setup tests now also pass on the user's console.
`make java25-startup` builds `dist/PPSA99865.zip` for the first actual VM
creation, Hello25 and shutdown attempts. These attempts are not yet validated
on PS5; this package includes persistent startup diagnostics.

Run the input regressions on this Mac after baking the fonts:

```sh
/usr/bin/clang++ -arch x86_64 -std=c++20 -O2 -Wall -Wextra -Werror \
  -DNAVIGATION_TEST -I src -I native/renderer -I build/native \
  tools/test_navigation.cpp native/renderer/demo_renderer.cpp \
  tools/preview_native.cpp -o build/native/test-navigation
build/native/test-navigation
```

## Standalone ELF smoke test

The original text-based payload remains available independently:

```sh
make
python3 tools/send_elf.py YOUR_PS5_IP --port 9021
```

`build/controller-tester.elf` reports raw controller values through the loader's
stdout. It exits on Options + Circle held for one second, or after two minutes.
Use your existing ELF loader's actual port. Closing the sender does not stop
the payload.
