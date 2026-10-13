/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "pad.h"
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define SYSTEM_OWNED 0x80000000u
#define EXIT_CHORD (0x00000008u | 0x00002000u)

static const struct { uint32_t mask; const char *name; } buttons[] = {
    {1, "Create"}, {2, "L3"}, {4, "R3"}, {8, "Options"},
    {0x10, "Up"}, {0x20, "Right"}, {0x40, "Down"}, {0x80, "Left"},
    {0x100, "L2"}, {0x200, "R2"}, {0x400, "L1"}, {0x800, "R1"},
    {0x1000, "Triangle"}, {0x2000, "Circle"}, {0x4000, "Cross"},
    {0x8000, "Square"}, {0x100000, "Touchpad"}
};

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1000000000.0;
}

static PadSample neutral(void) {
    PadSample s = {0};
    s.lx = s.ly = s.rx = s.ry = 128;
    return s;
}

static void show(const PadSample *s, bool blocked, unsigned long count,
                 uint32_t seen) {
    printf("%s | L %3u,%3u R %3u,%3u | L2 %3u R2 %3u | touch %u | ",
           blocked ? "SYSTEM INPUT" : s->connected ? "CONNECTED" : "DISCONNECTED",
           s->lx, s->ly, s->rx, s->ry, s->l2, s->r2, s->touch_count);
    bool any = false;
    for (size_t i = 0; i < sizeof(buttons) / sizeof(buttons[0]); i++) {
        if (s->buttons & buttons[i].mask) {
            printf("%s%s", any ? "+" : "", buttons[i].name);
            any = true;
        }
    }
    if (!any) printf("none");
    printf(" | samples %lu seen 0x%08x\n", count, seen);
    fflush(stdout);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    puts("PS5 Controller Tester v0.1 — native ELF smoke test");
    puts("Move sticks, pull triggers, press buttons. Raw axes: 0..255, center ~128.");
    puts("Hold Options + Circle for 1 second to exit. Auto-exit after 120 seconds.");
    int init = sceUserServiceInitialize(NULL);
    bool owns_service = init == 0;
    int result = 1, handle = -1;
    int32_t user = -1;
    int rc = sceUserServiceGetInitialUser(&user);
    if (rc < 0) {
        printf("GetInitialUser failed: 0x%08x (initialize: 0x%08x)\n", rc, init);
        goto done;
    }
    rc = scePadInit();
    if (rc < 0) { printf("scePadInit failed: 0x%08x\n", rc); goto done; }
    /* Native PS5 standard pad port is 0 in the community ABI reference. */
    handle = scePadOpen(user, 0, 0, NULL);
    if (handle < 0) {
        printf("scePadOpen failed: 0x%08x. Loader process may lack pad access.\n", handle);
        goto done;
    }
    printf("User %d, pad handle %d opened.\n", user, handle);
    PadSample samples[64], state = neutral();
    double start = now(), last_print = start - 1, last_error = start - 1;
    double last_sample = start, held_since = -1;
    unsigned long total = 0;
    uint32_t seen = 0, last_buttons = 0;
    bool blocked = false, changed = true;
    while (now() - start < 120) {
        double t = now();
        int count = scePadRead(handle, samples, 64);
        if (count < 0 || count > 64) {
            if (t - last_error >= 1) {
                printf("scePadRead failed/unexpected count: 0x%08x\n", count);
                last_error = t;
            }
            state = neutral();
            blocked = false;
            held_since = -1;
        } else {
            for (int i = 0; i < count; i++) {
                total++;
                last_sample = t;
                blocked = (samples[i].buttons & SYSTEM_OWNED) != 0;
                state = samples[i].connected && !blocked ? samples[i] : neutral();
                seen |= state.buttons;
                if (state.buttons != last_buttons) {
                    show(&state, blocked, total, seen);
                    last_print = t;
                    last_buttons = state.buttons;
                }
                if ((state.buttons & EXIT_CHORD) == EXIT_CHORD) {
                    if (held_since < 0) held_since = t;
                } else held_since = -1;
                changed = true;
            }
        }
        /* Clear stale input instead of displaying stuck controls indefinitely. */
        if (t - last_sample > 1) {
            state = neutral();
            blocked = false;
            held_since = -1;
        }
        if ((changed && t - last_print >= 0.1) || t - last_print >= 1) {
            show(&state, blocked, total, seen);
            last_print = t;
            changed = false;
        }
        if (held_since >= 0 && t - held_since >= 1) break;
        usleep(4000);
    }
    printf("Finished: %lu samples; observed buttons 0x%08x.\n", total, seen);
    result = total ? 0 : 1;
done:
    if (handle >= 0) scePadClose(handle);
    if (owns_service) sceUserServiceTerminate();
    return result;
}
