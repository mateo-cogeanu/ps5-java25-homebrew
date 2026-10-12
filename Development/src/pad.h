/* SPDX-License-Identifier: GPL-3.0-or-later
 * Community ABI reference:
 * https://github.com/blackbearreloaded/ps5-native-gamepad-input-research
 * These declarations are not official Sony SDK headers.
 */
#ifndef CONTROLLER_TESTER_PAD_H
#define CONTROLLER_TESTER_PAD_H
#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint32_t buttons;
    uint8_t lx, ly, rx, ry;
    uint8_t l2, r2, reserved0[2];
    float orientation[4], acceleration[3], angular_velocity[3];
    uint8_t touch_count, reserved1[7];
    struct { uint16_t x, y; uint8_t id, reserved[3]; } touch[2];
    int32_t connected;
    uint64_t timestamp;
    uint8_t reserved2[16], connection_generation, reserved3[15];
} PadSample;

#ifdef __cplusplus
#define PAD_ASSERT static_assert
extern "C" {
#else
#define PAD_ASSERT _Static_assert
#endif
PAD_ASSERT(sizeof(PadSample) == 120, "Pad sample ABI size");
PAD_ASSERT(offsetof(PadSample, connected) == 0x4c, "Pad connection ABI offset");
PAD_ASSERT(offsetof(PadSample, timestamp) == 0x50, "Pad timestamp ABI offset");

int sceUserServiceInitialize(void *);
int sceUserServiceGetInitialUser(int32_t *);
int sceUserServiceTerminate(void);
int scePadInit(void);
int scePadOpen(int32_t user, int port, int index, const void *);
int scePadRead(int handle, PadSample *samples, int capacity);
int scePadClose(int handle);
#ifdef __cplusplus
}
#endif
#undef PAD_ASSERT
#endif
