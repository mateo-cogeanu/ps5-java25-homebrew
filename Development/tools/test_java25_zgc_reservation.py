#!/usr/bin/env python3
"""Test actual PS5 ZGC reservation dispatch with non-overwriting native fixtures."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
body = (root / ".tools/java25/openjdk/src/hotspot/os/posix/gc/z/zVirtualMemoryManager_posix.cpp").read_text()
body = body[body.index("bool ZVirtualMemoryReserver::pd_reserve"):]
source = r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstdlib>
#include <sys/mman.h>
#include <unistd.h>
#define __PROSPERO__ 1
using zaddress_unsafe = uintptr_t;
static uintptr_t untype(uintptr_t p) { return p; }
constexpr size_t ZGranuleSize = 2 * 1024 * 1024;
#define guarantee(condition, message) assert(condition)
#define fatal(message) std::abort()
static unsigned attempts, releases, traces;
static bool refuse, relocate;
inline void ps5_vm_trace_values(const char*, uint64_t, const char*, uint64_t, const char*, uint64_t) { ++traces; }
extern "C" int sceKernelReserveVirtualRange(void** address, size_t bytes, int flags, size_t alignment) {
  ++attempts;
  assert(flags == 0 && alignment == ZGranuleSize);
  if (refuse) return -1;
  void* result = mmap(relocate ? nullptr : *address, bytes, PROT_NONE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (result == MAP_FAILED) return -2;
  *address = result;
  return 0;
}
extern "C" int sceKernelMunmap(void* address, size_t bytes) {
  ++releases;
  return munmap(address, bytes);
}
struct ZVirtualMemoryReserver {
  static bool pd_reserve(uintptr_t, size_t);
  static void pd_unreserve(uintptr_t, size_t);
};
'''
source += body
source += r'''
int main() {
  const size_t bytes = ZGranuleSize;
  void* target = mmap(nullptr, bytes, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  assert(target != MAP_FAILED);
  assert(munmap(target, bytes) == 0);
  uintptr_t address = reinterpret_cast<uintptr_t>(target);
  assert(ZVirtualMemoryReserver::pd_reserve(address, bytes));
  ZVirtualMemoryReserver::pd_unreserve(address, bytes);
  assert(releases == 1);
  refuse = true;
  assert(!ZVirtualMemoryReserver::pd_reserve(address, bytes));
  assert(releases == 1);
  refuse = false;
  void* occupied = mmap(target, bytes, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  assert(occupied == target);
  *static_cast<unsigned char*>(occupied) = 0x5a;
  relocate = true;
  assert(!ZVirtualMemoryReserver::pd_reserve(address, bytes));
  assert(releases == 2 && *static_cast<unsigned char*>(occupied) == 0x5a);
  relocate = false;
  assert(!ZVirtualMemoryReserver::pd_reserve(address, bytes));
  assert(releases == 3 && *static_cast<unsigned char*>(occupied) == 0x5a);
  assert(munmap(occupied, bytes) == 0);
  assert(attempts == 4 && traces == 8);
}
'''
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    (work / "test.cpp").write_text(source)
    subprocess.run([
        "clang++", "-std=c++17", "-O1", "-g", "-fsanitize=address,undefined",
        str(work / "test.cpp"), "-o", str(work / "test")
    ], check=True)
    subprocess.run([str(work / "test")], check=True)
print("PASS actual ZGC reservation body: native dispatch, exact placement, refusal, moved-range cleanup and occupied bytes preserved")
