/* SPDX-License-Identifier: GPL-3.0-or-later
 * Exercises the real UI input path with retained controller samples.
 */
#define main application_entry
#include "../native/main.cpp"
#undef main
#include <cassert>
#include <vector>

extern "C" { std::uint64_t test_time = 1000; }
std::vector<PadSample> queued;
extern "C" int scePadRead(int, PadSample *out, int capacity) {
    int n = static_cast<int>(queued.size());
    if (n > capacity) n = capacity;
    for (int i = 0; i < n; ++i) out[i] = queued[i];
    queued.erase(queued.begin(), queued.begin() + n);
    return n;
}
void sample(std::uint32_t buttons, unsigned lx = 128) {
    PadSample s{};
    s.connected = 1; s.buttons = buttons;
    s.lx = lx; s.ly = s.rx = s.ry = 128;
    queued.push_back(s);
}
void tap(std::uint32_t buttons) { sample(buttons); sample(0); }
int main() {
    handle = 1;
    neutral();
    sample(0);
    assert(update() && connected);
    assert(!update()); // Idle polling does not trigger a redraw.

    tap(0x4000); // Open with a brief Cross tap retained between polls.
    assert(update() && detail);
    tap(0x4000); // Keep exploring must close the dialog.
    assert(update() && !detail);
    sample(0x4000);
    assert(update() && detail);
    sample(0x4000); // Holding Cross must not repeatedly toggle the dialog.
    assert(!update() && detail);
    sample(0); assert(!update());
    tap(0x2000); assert(update() && !detail);

    tap(0x20); assert(update() && focus == 1);
    tap(0x20); assert(update() && focus == 2);
    tap(0x20); assert(!update() && focus == 2);
    tap(0x2000); assert(update() && sidebar);
    tap(0x40); assert(update() && page == 1);
    tap(0x4000); assert(update() && !sidebar && !detail);

    sample(0, 30); assert(update() && focus == 1);
    test_time += 100000;
    sample(0, 30); assert(!update() && focus == 1);
    test_time += 200000;
    sample(0, 30); assert(update() && focus == 0);
    sample(0); assert(!update());

    for (int i = 0; i < 64; ++i) sample(0);
    tap(0x4000); assert(update() && detail && queued.empty());
    // Disconnect releases previous buttons so a later tap is accepted.
    queued.push_back(PadSample{});
    assert(update() && !connected);
    tap(0x4000); assert(update() && connected && !detail);
    test_time += 1100000;
    assert(update() && !connected);
    assert(!update());
    std::puts("Passed: short taps, X dismiss, held X, navigation, repeat, queue drain, disconnect and idle redraw.");
}
