/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host-only layout preview. These synthetic APIs do not test console access.
 */
#include "pad.h"
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <new>

#ifdef HEAP_LIMIT_TEST
// Regression guard: the old startup path tried new uint32_t[16 MB] and
// would abort here. Cached staging must not depend on a large array allocation.
void *operator new[](std::size_t size) {
  if (size >= 1024 * 1024) {
    std::fputs("Large array allocation during startup\n", stderr);
    std::abort();
  }
  if (void *p = std::malloc(size)) return p;
  throw std::bad_alloc{};
}
void operator delete[](void *p) noexcept { std::free(p); }
#endif

namespace {
void *frame_memory = nullptr;
}
extern "C" {
int sceUserServiceInitialize(void *) { return 0; }
int sceUserServiceGetInitialUser(std::int32_t *user) {
  *user = 1;
  return 0;
}
int sceUserServiceTerminate() { return 0; }
int scePadInit() { return 0; }
int scePadOpen(std::int32_t, int, int, const void *) { return 1; }
int scePadClose(int) { return 0; }
#ifndef NAVIGATION_TEST
int scePadRead(int, PadSample *s, int) {
  static bool first = true;
  const char *mode = std::getenv("UI_PREVIEW_SCENE");
  std::uint32_t sequence[6]{};
  int count = 1;
  if (first && mode && std::strcmp(mode, "detail") == 0)
    sequence[0] = 0x4000;
  if (first && mode && std::strcmp(mode, "collections") == 0) {
    count = 4;
    sequence[0] = 0x2000;
    sequence[2] = 0x40;
  }
  if (first && mode && std::strcmp(mode, "appearance") == 0) {
    count = 6;
    sequence[0] = 0x2000;
    sequence[2] = sequence[4] = 0x40;
  }
  for (int i = 0; i < count; ++i) {
    s[i] = {};
    s[i].connected = !(mode && std::strcmp(mode, "disconnected") == 0);
    s[i].lx = s[i].ly = s[i].rx = s[i].ry = 128;
    s[i].buttons = sequence[i];
  }
  first = false;
  return count;
}
#endif
#ifdef NAVIGATION_TEST
extern std::uint64_t test_time;
std::uint64_t sceKernelGetProcessTime() { return test_time; }
#else
std::uint64_t sceKernelGetProcessTime() { return 1000; }
#endif
std::size_t sceKernelGetDirectMemorySize() { return 1ULL << 30; }
int sceKernelAllocateDirectMemory(std::int64_t, std::int64_t, std::size_t,
                                  std::size_t, int, std::int64_t *address) {
  *address = 0;
  return 0;
}
int sceKernelMapDirectMemory(void **address, std::size_t length, int, int,
                             std::int64_t, std::size_t) {
  frame_memory = std::calloc(1, length);
  *address = frame_memory;
  return frame_memory ? 0 : -1;
}
int sceKernelMunmap(void *, std::size_t) { return 0; }
int sceKernelReleaseDirectMemory(std::int64_t, std::size_t) {
  std::free(frame_memory); frame_memory = nullptr; return 0;
}
int sceVideoOutClose(std::int32_t) { return 0; }
int sceKernelSendNotificationRequest(std::uint32_t, void *, std::size_t, int) {
  return 0;
}
int sceKernelUsleep(std::uint32_t) { return 0; }
int sceSystemServiceHideSplashScreen() { return 0; }
bool ps5ObserveOwnedAllocation(const void *address) noexcept {
  return address != nullptr;
}
int sceVideoOutOpen(std::int32_t, std::int32_t, std::int32_t, const void *) {
  return 1;
}
int sceVideoOutSetFlipRate(std::int32_t, std::int32_t) { return 0; }
int sceVideoOutSubmitFlip(std::int32_t, std::int32_t, std::uint32_t,
                          std::int64_t) {
  return 0;
}
void sceVideoOutSetBufferAttribute2(void *, std::uint64_t, std::uint32_t,
                                    std::uint32_t, std::uint32_t, std::uint64_t,
                                    std::uint32_t, std::uint64_t) {}
int sceVideoOutRegisterBuffers2(std::int32_t, std::int32_t, std::int32_t,
                                void *, std::int32_t, void *, std::int32_t,
                                void *) {
  return 0;
}
int sceVideoOutWaitVblank(std::int32_t) {
  auto *file = std::fopen("build/native/preview.rgba", "wb");
  if (!file)
    std::exit(1);
  std::vector<std::uint32_t> pixels(1920 * 1080);
  auto *bytes = static_cast<std::uint8_t *>(frame_memory);
  for (unsigned y = 0; y < 1080; ++y)
    for (unsigned x = 0; x < 1920; ++x) {
      auto offset =
          ((y << 4) & 0x70U) ^ ((y << 5) & 0xf00U) ^ ((y << 9) & 0x1000U) ^
          ((y << 8) & 0x4000U) ^ ((x << 2) & 0xcU) ^ ((x << 5) & 0x380U) ^
          ((x << 4) & 0x400U) ^ ((x << 6) & 0x800U) ^ ((x << 9) & 0xa000U);
      auto block = (y >> 7) * 15 + (x >> 7);
      pixels[y * 1920 + x] =
          *reinterpret_cast<std::uint32_t *>(bytes + (block << 16) + offset);
    }
  auto size = std::fwrite(pixels.data(), 1, pixels.size() * 4, file);
  std::fclose(file);
  std::exit(size == 1920 * 1080 * 4 ? 0 : 1);
}
}
