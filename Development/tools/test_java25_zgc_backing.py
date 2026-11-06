#!/usr/bin/env python3
"""Exercise PS5 ZGC backing with real shared aliases and injected kernel refusals."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
assert (root / "java25/probe/zgc_backing.hpp").read_bytes() == (
    root / ".tools/java25/openjdk/src/hotspot/share/gc/z/ps5ZBacking.hpp"
).read_bytes()
source = r'''
#include "zgc_backing.hpp"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <unistd.h>
#include <fcntl.h>

static bool fail_allocate, fail_map, fail_release, fail_detach;
static std::vector<int> files;
extern "C" size_t sceKernelGetDirectMemorySize() { return 8ULL << 30; }
extern "C" int sceKernelAllocateDirectMemory(int64_t, int64_t, size_t bytes,
                                             size_t alignment, int type, int64_t* physical) {
  if (fail_allocate) return -1;
  assert(bytes == ps5_zgc::Backing::granule && alignment == bytes && type == 12);
  char path[] = "/tmp/zgc-backing-XXXXXX";
  int fd = mkstemp(path);
  assert(fd >= 0 && unlink(path) == 0 && ftruncate(fd, bytes) == 0);
  *physical = files.size() * bytes;
  files.push_back(fd);
  return 0;
}
static void* reserve(size_t size) {
  const size_t alignment = ps5_zgc::Backing::granule;
  void* raw = mmap(nullptr, size + alignment, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  assert(raw != MAP_FAILED);
  uintptr_t base = reinterpret_cast<uintptr_t>(raw);
  uintptr_t aligned = (base + alignment - 1) & ~(alignment - 1);
  if (aligned > base) assert(munmap(raw, aligned - base) == 0);
  size_t tail = size + alignment - (aligned - base) - size;
  if (tail) assert(munmap(reinterpret_cast<void*>(aligned + size), tail) == 0);
  return reinterpret_cast<void*>(aligned);
}
extern "C" int sceKernelMapDirectMemory(void** address, size_t bytes, int protection,
                                        int flags, int64_t physical, size_t alignment) {
  if (fail_map) return -2;
  assert(alignment == bytes && physical >= 0);
  size_t index = physical / ps5_zgc::Backing::granule;
  assert(index < files.size() && files[index] >= 0);
  assert(flags == 0);
  void* target = *address ? *address : reserve(bytes);
  void* result = mmap(target, bytes, protection, MAP_SHARED | MAP_FIXED, files[index], 0);
  if (result == MAP_FAILED) return -3;
  *address = result;
  return 0;
}
extern "C" int sceKernelMunmap(void* address, size_t bytes) {
  if (fail_detach) return -4;
  return munmap(address, bytes);
}
extern "C" int sceKernelReleaseDirectMemory(int64_t physical, size_t bytes) {
  if (fail_release) return -5;
  size_t index = physical / bytes;
  assert(index < files.size() && files[index] >= 0);
  int result = close(files[index]);
  files[index] = -1;
  return result;
}
int main() {
  const size_t granule = ps5_zgc::Backing::granule;
  ps5_zgc::Backing backing;
  assert(!backing.initialize(1));
  assert(backing.initialize(4 * granule));
  assert(!backing.initialize(4 * granule));
  fail_allocate = true;
  assert(backing.commit(0, granule) == 0);
  fail_allocate = false;
  assert(backing.commit(0, 2 * granule) == 2 * granule);
  assert(backing.commit(0, granule) == 0); // Never replace owned backing.
  assert(backing.commit(4 * granule, granule) == 0);
  auto* a = static_cast<unsigned char*>(reserve(2 * granule));
  auto* b = static_cast<unsigned char*>(reserve(2 * granule));
  assert(backing.map(reinterpret_cast<uintptr_t>(a), 0, 2 * granule));
  assert(backing.map(reinterpret_cast<uintptr_t>(b), 0, 2 * granule));
  assert(a[0] == 0 && b[granule] == 0);
  a[0] = 0x35;
  b[granule + 99] = 0x72;
  assert(b[0] == 0x35 && a[granule + 99] == 0x72);
  fail_map = true;
  assert(!backing.map(reinterpret_cast<uintptr_t>(a), 0, granule));
  assert(backing.map_result() == -2 && backing.map_physical() >= 0);
  fail_map = false;
  assert(backing.unmap(reinterpret_cast<uintptr_t>(a), 2 * granule));
  assert(b[0] == 0x35);
  assert(backing.unmap(reinterpret_cast<uintptr_t>(b), 2 * granule));
  assert(backing.map(reinterpret_cast<uintptr_t>(a), 0, granule));
  assert(a[0] == 0x35);
  assert(backing.unmap(reinterpret_cast<uintptr_t>(a), granule));
  fail_release = true;
  assert(backing.uncommit(0, 2 * granule) == 0);
  fail_release = false;
  assert(backing.uncommit(0, 2 * granule) == 2 * granule);
  assert(!backing.map(reinterpret_cast<uintptr_t>(a), 0, granule));
  fail_map = true;
  assert(backing.commit(2 * granule, granule) == 0);
  fail_map = false;
  assert(backing.commit(2 * granule, granule) == 0); // Failed setup stays owned.
  assert(backing.uncommit(2 * granule, granule) == granule);
  assert(munmap(a, 2 * granule) == 0 && munmap(b, 2 * granule) == 0);
  for (int fd : files) assert(fd == -1);
  puts("PASS PS5 ZGC backing: real shared aliases, initial zeroes, remap preservation, bounds, allocation/map/release failure and retained ownership");
}
'''
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    (work / "test.cpp").write_text(source)
    subprocess.run([
        "clang++", "-std=c++17", "-O1", "-g", "-fsanitize=address,undefined",
        "-I" + str(root / "java25/probe"), str(work / "test.cpp"),
        "-o", str(work / "test")
    ], check=True)
    subprocess.run([str(work / "test")], check=True)
