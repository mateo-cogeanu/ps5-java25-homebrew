/* SPDX-License-Identifier: GPL-2.0-only */
#pragma once
#include <atomic>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>

extern "C" size_t sceKernelGetDirectMemorySize();
extern "C" int sceKernelAllocateDirectMemory(int64_t, int64_t, size_t, size_t, int, int64_t*);
extern "C" int sceKernelMapDirectMemory(void**, size_t, int, int, int64_t, size_t);
extern "C" int sceKernelReleaseDirectMemory(int64_t, size_t);
extern "C" int sceKernelMunmap(void*, size_t);

namespace ps5_zgc {
class Backing {
 public:
  static constexpr size_t granule = 2 * 1024 * 1024;
  static constexpr size_t maximum_granules = 4096;

 private:
  struct Entry { int64_t physical; bool owned; bool ready; };
  Entry entries_[maximum_granules]{};
  std::atomic_flag guard_ = ATOMIC_FLAG_INIT;
  size_t capacity_ = 0;
  int device_ = -1;
  std::atomic<int> map_result_{0};
  std::atomic<int64_t> map_physical_{-1};

  class Guard {
    Backing& backing_;
   public:
    explicit Guard(Backing& backing) : backing_(backing) {
      while (backing_.guard_.test_and_set(std::memory_order_acquire)) {}
    }
    ~Guard() { backing_.guard_.clear(std::memory_order_release); }
  };

  bool valid(size_t offset, size_t length) const {
    return offset % granule == 0 && length % granule == 0 &&
           offset <= capacity_ && length <= capacity_ - offset;
  }

 public:
  ~Backing() { if (device_ >= 0) ::close(device_); }

  bool initialize(size_t capacity) {
    if (capacity_ || !capacity || capacity % granule ||
        capacity / granule > maximum_granules) return false;
    capacity_ = capacity;
    return true;
  }

  size_t commit(size_t offset, size_t length) {
    if (!valid(offset, length)) return 0;
    Guard guard(*this);
    size_t committed = 0;
    const size_t pool = sceKernelGetDirectMemorySize();
    if (pool < granule || pool > INT64_MAX) return 0;
    for (; committed < length; committed += granule) {
      auto& entry = entries_[(offset + committed) / granule];
      if (entry.owned) break;
      int64_t result = -1;
      if (sceKernelAllocateDirectMemory(0, static_cast<int64_t>(pool),
                                       granule, granule, 12, &result) != 0) break;
      entry = {result, true, false};
      if (result < 0 || result % granule) break;
      void* temporary = nullptr;
      if (sceKernelMapDirectMemory(&temporary, granule, PROT_READ | PROT_WRITE,
                                   0, result, granule) != 0) break;
      if (!temporary || temporary == MAP_FAILED ||
          reinterpret_cast<uintptr_t>(temporary) % granule) break;
      std::memset(temporary, 0, granule);
      if (sceKernelMunmap(temporary, granule) != 0) break;
      entry.ready = true;
    }
    return committed;
  }

  size_t uncommit(size_t offset, size_t length) {
    if (!valid(offset, length)) return 0;
    Guard guard(*this);
    size_t released = 0;
    for (; released < length; released += granule) {
      auto& entry = entries_[(offset + released) / granule];
      if (!entry.owned || sceKernelReleaseDirectMemory(entry.physical, granule) != 0) break;
      entry = {};
    }
    return released;
  }

  int map_result() const { return map_result_.load(std::memory_order_relaxed); }
  int64_t map_physical() const { return map_physical_.load(std::memory_order_relaxed); }

  // The caller supplies an address range reserved exclusively for this ZGC heap.
  bool map(uintptr_t address, size_t offset, size_t length) {
    if (!address || address % granule || address > UINTPTR_MAX - length ||
        !valid(offset, length)) return false;
    Guard guard(*this);
    for (size_t done = 0; done < length; done += granule) {
      const auto& entry = entries_[(offset + done) / granule];
      map_physical_.store(entry.physical, std::memory_order_relaxed);
      if (!entry.ready) {
        map_result_.store(ENOENT, std::memory_order_relaxed);
        return false;
      }
      void* mapped = reinterpret_cast<void*>(address + done);
      const int result = sceKernelMapDirectMemory(
          &mapped, granule, PROT_READ | PROT_WRITE, 0, entry.physical, granule);
      map_result_.store(result, std::memory_order_relaxed);
      if (result == 0 && mapped == reinterpret_cast<void*>(address + done)) continue;
      if (result == 0) {
        // An accepted hint must exactly match this collector-owned reservation.
        const int cleanup = sceKernelMunmap(mapped, granule);
        if (cleanup != 0) {
          map_result_.store(cleanup, std::memory_order_relaxed);
          return false;
        }
      }
      // Mapping a direct-memory device offset uses the collector's existing
      // reservation. It never requests physical memory or changes its owner.
      if (device_ < 0) device_ = ::open("/dev/dmem0", O_RDWR);
      if (device_ < 0) {
        map_result_.store(errno, std::memory_order_relaxed);
        return false;
      }
      void* target = reinterpret_cast<void*>(address + done);
      void* exact = ::mmap(target, granule, PROT_READ | PROT_WRITE,
                           MAP_SHARED | MAP_FIXED, device_, entry.physical);
      if (exact == MAP_FAILED) {
        map_result_.store(errno, std::memory_order_relaxed);
        return false;
      }
      if (exact != target) {
        const int cleanup = ::munmap(exact, granule);
        map_result_.store(cleanup ? errno : ERANGE, std::memory_order_relaxed);
        return false;
      }
      map_result_.store(0, std::memory_order_relaxed);
    }
    return true;
  }

  bool unmap(uintptr_t address, size_t length) {
    if (!address || address % granule || length % granule ||
        address > UINTPTR_MAX - length) return false;
    // Restore a non-accessible reservation. The backing stays committed until
    // ZGC returns its physical segments through uncommit.
    return mmap(reinterpret_cast<void*>(address), length, PROT_NONE,
                MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS, -1, 0) ==
           reinterpret_cast<void*>(address);
  }
};
}
