#!/usr/bin/env python3
"""Exercise actual ZGC reentrant lock bodies with native-lease accounting."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
hotspot = root / ".tools/java25/openjdk/src/hotspot/share/gc/z"
header = (hotspot / "zLock.hpp").read_text()
declaration = header[header.index("class ZReentrantLock {"):header.index("class ZConditionLock")]
inline = (hotspot / "zLock.inline.hpp").read_text()
methods = inline[inline.index("inline ZReentrantLock::ZReentrantLock()"):inline.index("inline void ZConditionLock::lock()")]
source = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>
static std::atomic<int> native_leases{0};
static void verify(bool test) { assert(test); }
#undef assert
#define assert(condition, message) verify(condition)
class Thread {
 public:
  static Thread* current() { static thread_local Thread self; return &self; }
};
struct Atomic {
 template<class T> static T load(const volatile T* p) { return __atomic_load_n(p,__ATOMIC_SEQ_CST); }
 template<class T> static void store(volatile T* p, T value) { __atomic_store_n(p,value,__ATOMIC_SEQ_CST); }
 template<class T> static void release_store(volatile T* p,T value) { __atomic_store_n(p,value,__ATOMIC_RELEASE); }
 template<class T> static T cmpxchg(volatile T* p,T expected,T desired) {
   __atomic_compare_exchange_n(p,&expected,desired,false,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);
   return expected;
 }
};
class ZLock {
 std::mutex lock_;
 public:
  ZLock() { ++native_leases; }
  ~ZLock() { --native_leases; }
  void lock() { lock_.lock(); }
  void unlock() { lock_.unlock(); }
};
static int SpinPause() { return 0; }
namespace os { static void naked_yield() { std::this_thread::yield(); } }
'''
source += declaration + methods
source += r'''
int main() {
 constexpr unsigned count=32768;
 {
  auto locks=std::make_unique<ZReentrantLock[]>(count);
#ifdef __PROSPERO__
  verify(native_leases==0);
#else
  verify(native_leases==count);
#endif
  locks[0].lock();
  locks[0].lock();
  verify(locks[0].is_owned()&&!locks[1].is_owned());
  locks[0].unlock();
  verify(locks[0].is_owned());
  locks[0].unlock();
  verify(!locks[0].is_owned());
  std::vector<uint64_t> protected_values(count);
  std::vector<std::thread> workers;
  for(unsigned worker=0;worker<8;++worker)workers.emplace_back([&] {
    for(unsigned i=0;i<50000;++i) {
      const unsigned index=(i*17)%count;
      auto& lock=locks[index];
      lock.lock();
      verify(lock.is_owned());
      lock.lock();
      ++protected_values[index];
      lock.unlock();
      verify(lock.is_owned());
      lock.unlock();
    }
  });
  for(auto& worker:workers)worker.join();
  uint64_t sum=0;
  for(auto value:protected_values)sum+=value;
  verify(sum==400000);
  // A contended lock must preserve publication and exclude a different owner.
  bool entered=false;
  locks[0].lock();
  std::atomic<bool> waiting{false};
  std::thread contender([&] {
    waiting=true;
    locks[0].lock();
    verify(entered&&locks[0].is_owned());
    locks[0].unlock();
  });
  while(!waiting)std::this_thread::yield();
  entered=true;
  locks[0].unlock();
  contender.join();
 }
 verify(native_leases==0);
}
'''
with tempfile.TemporaryDirectory() as directory:
    work=Path(directory)
    (work/"test.cpp").write_text(source)
    for name,flags in (("ps5",["-D__PROSPERO__"]),("desktop",[])):
        subprocess.run([
            "clang++","-std=c++17","-O1","-g","-fsanitize=address,undefined",
            "-pthread",*flags,str(work/"test.cpp"),"-o",str(work/name)
        ],check=True)
        subprocess.run([str(work/name)],check=True,timeout=30)
print("PASS actual ZGC locks:32768 identities, zero PS5 native leases, desktop control, recursion, contention, publication and400000 concurrent updates;ASan/UBSan")
