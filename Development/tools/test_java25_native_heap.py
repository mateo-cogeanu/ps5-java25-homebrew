#!/usr/bin/env python3
"""Exercise the actual PS5 HotSpot raw allocator with forced libc/map failures."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'build/java25/native-heap-test'
(WORK/'utilities').mkdir(parents=True,exist_ok=True);(WORK/'runtime').mkdir(exist_ok=True)
(WORK/'utilities/permitForbiddenFunctions.hpp').write_text('''#pragma once
namespace permit_forbidden_function {
inline void* malloc(size_t n){return test_malloc(n);}
inline void* realloc(void* p,size_t n){return test_realloc(p,n);}
inline void free(void* p){test_free(p);}
}
''')
(WORK/'runtime/ps5StartupTrace.hpp').write_text('''#pragma once
inline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){test_note();}
''')
cpp=r'''
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <cerrno>
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
static std::atomic<bool> deny_heap{false},deny_maps{false},deny_resize{false},parallel{false};
static std::atomic<size_t> map_limit{SIZE_MAX};
static std::atomic<long> heap_live{0},map_live{0},map_total{0},notes{0};
static void* test_malloc(size_t n){if(deny_heap)return nullptr;void* p=std::malloc(n);if(p)++heap_live;return p;}
static void* test_realloc(void* p,size_t n){if(deny_heap||deny_resize)return nullptr;return std::realloc(p,n);}
static void test_free(void* p){if(p)--heap_live;std::free(p);}
static void test_note();
extern "C" size_t sceKernelGetDirectMemorySize(){return 0;}
extern "C" int sceKernelAllocateDirectMemory(int64_t,int64_t,size_t,size_t,int,int64_t*){return -1;}
extern "C" int sceKernelMapDirectMemory(void**,size_t,int,int,int64_t,size_t){return -1;}
extern "C" int sceKernelMunmap(void*,size_t){return -1;}
extern "C" int sceKernelReleaseDirectMemory(int64_t,size_t){return -1;}

static void* test_mmap(void* p,size_t n,int prot,int flags,int fd,off_t off){
 if(deny_maps||n>map_limit){errno=ENOMEM;return MAP_FAILED;}
 void* memory=::mmap(p,n,prot,flags,fd,off);if(memory!=MAP_FAILED){++map_live;++map_total;}return memory;
}
static int test_munmap(void* p,size_t n){int result=::munmap(p,n);if(!result)--map_live;return result;}
static long test_sysconf(int name){assert(name==_SC_PAGESIZE);return 16384;}
#define __PROSPERO__ 1
#define sysconf test_sysconf
#define mmap test_mmap
#define munmap test_munmap
#include "runtime/ps5NativeHeap.hpp"
#undef mmap
#undef munmap
#undef sysconf
static void test_note(){if(!parallel)assert(__atomic_load_n(ps5_native_heap::mutex_word(),__ATOMIC_RELAXED)==0);++notes;}
namespace heap=ps5_native_heap;
static void check(void* p,size_t n,unsigned char value){assert(p);assert((uintptr_t)p%alignof(max_align_t)==0);for(size_t i=0;i<n;++i)assert(((unsigned char*)p)[i]==value);}
int main(){
 errno=EDOM;void* p=heap::allocate(128);assert(p&&heap_live==1&&errno==EDOM);std::memset(p,0x35,128);
 p=heap::reallocate(p,256);check(p,128,0x35);assert(heap_live==1);
 deny_resize=true;void* migrated=heap::reallocate(p,512);check(migrated,128,0x35);p=migrated;deny_resize=false;
 // A pre-NMT raw block and a post-init block have identical storage contracts.
 deny_heap=true;p=heap::reallocate(p,1024);check(p,128,0x35);assert(heap_live==0&&map_live==1);
 p=heap::reallocate(p,8192);check(p,128,0x35);heap::trim_idle();assert(map_live==1);
 std::memset(p,0x79,8192);deny_maps=true;assert(!heap::reallocate(p,16384));check(p,8192,0x79);
 assert(!heap::allocate(128));assert(!heap::allocate(SIZE_MAX));check(p,8192,0x79);deny_maps=false;
 void* shrink=heap::reallocate(p,32);assert(shrink==p);check(p,32,0x79);heap::release(p);heap::trim_idle();assert(map_live==0);
 p=heap::allocate(0);assert(p);p=heap::reallocate(p,0);assert(p);heap::release(p);heap::release(nullptr);
 // Ten thousand full allocation/free lifetimes use just one warm slab.
 heap::trim_idle();long warm_before=map_total;
 for(int i=0;i<10000;i++){errno=EDOM;void* q=heap::allocate(4088);assert(q&&errno==EDOM);memset(q,0x49,4088);heap::release(q);assert(errno==EDOM);}
 assert(map_total-warm_before==1&&map_live==1);
 heap::trim_idle();assert(map_live==0);
 // One retained idle slab/class stays bounded even after multiple live slabs.
 std::vector<void*> warm_blocks;for(int i=0;i<200;i++)warm_blocks.push_back(heap::allocate(4096));
 for(void* q:warm_blocks)heap::release(q);assert(map_live==1);
 // A pressure failure drains idle storage before the large allocation fails.
 deny_maps=true;assert(!heap::allocate(32768)&&errno==ENOMEM&&map_live==0);deny_maps=false;
 // A refused full slab retries a real minimal page, with matching cleanup.
 map_limit=16384;
 for(size_t n:{24u,48u,4096u}) {
  void* q=heap::allocate(n);assert(q);std::memset(q,0x59,n);check(q,n,0x59);
  assert(heap::owning_slab((heap::Header*)q-1)->mapped<=16384);
  heap::release(q);heap::trim_idle();assert(map_live==0);
 }
 map_limit=1;assert(!heap::allocate(24)&&errno==ENOMEM&&map_live==0);
 map_limit=SIZE_MAX;
 // Mapping refusal must reuse compatible capacity, never smaller slots.
 for(size_t owner_size:{64u,256u,4096u}) {
  void* owner=heap::allocate(owner_size);assert(owner);std::memset(owner,0x71,owner_size);
  auto owner_slab=heap::owning_slab((heap::Header*)owner-1);
  size_t slots=(owner_slab->mapped-sizeof(heap::Slab))/owner_slab->stride;
  deny_maps=true;long mappings=map_total;std::vector<void*> borrowed;
  for(size_t i=1;i<slots;i++){
   errno=EDOM;void* q=heap::allocate(16);assert(q&&errno==EDOM);
   assert(heap::owning_slab((heap::Header*)q-1)==owner_slab);
   std::memset(q,0x36,16);borrowed.push_back(q);
  }
  assert(!heap::allocate(16)&&errno==ENOMEM);assert(map_total==mappings);
  check(owner,owner_size,0x71);heap::release(owner);assert(map_live==1);
  for(void* q:borrowed){check(q,16,0x36);heap::release(q);}heap::trim_idle();assert(map_live==0);
  deny_maps=false;
 }
 // An undersized slot cannot satisfy a larger request; failed growth retains data.
 void* small=heap::allocate(16);std::memset(small,0x25,16);deny_maps=true;
 assert(!heap::allocate(64));assert(!heap::reallocate(small,64));check(small,16,0x25);
 heap::release(small);heap::trim_idle();assert(map_live==0);deny_maps=false;
 // All size classes and direct mappings, with concurrent ownership and reuse.
 long before=map_total;
 std::vector<void*> blocks;
 for(size_t n:{1u,32u,33u,64u,65u,128u,129u,256u,257u,512u,513u,1024u,1025u,2048u,2049u,4096u,4097u}) {
  void* q=heap::allocate(n);assert(q);std::memset(q,0x41,n);check(q,n,0x41);blocks.push_back(q);
 }
 for(void* q:blocks)heap::release(q);heap::trim_idle();assert(map_live==0);
 blocks.clear();before=map_total;
 for(int i=0;i<1000;++i){void* q=heap::allocate(128);assert(q);blocks.push_back(q);}
 assert(map_total-before<10); // Small failed mallocs share real mapped pages.
 for(void* q:blocks)heap::release(q);heap::trim_idle();assert(map_live==0);
 parallel=true;std::vector<std::thread> workers;
 for(int t=0;t<8;++t)workers.emplace_back([t]{
  for(int turn=0;turn<2000;++turn){
   size_t n=1+(turn*137+t*17)%6000;void* q=heap::allocate(n);assert(q);std::memset(q,t+1,n);
   size_t next=n+400;void* grown=heap::reallocate(q,next);check(grown,n,t+1);heap::release(grown);
  }
 });
 for(auto &thread:workers)thread.join();assert(map_live<=8);heap::trim_idle();assert(map_live==0&&heap_live==0&&notes>0);
 deny_heap=false;p=heap::allocate(90);assert(p&&heap_live==1);heap::release(p);assert(heap_live==0);
 std::puts("PASS: real mapped storage, bounded idle slab reuse/pressure trimming, eight pooled classes, alignment, normal/mapped realloc migration, failed growth preserves bytes, overflow, concurrency and complete backend cleanup");
}
'''
# Reuse the same actual raw allocator and stress test, then exercise the exact
# os.cpp API bodies with a narrow NMT model (not a claim of host JMM testing).
model=r'''
// NMT contract fixture around the actual os.cpp allocation entry points.
enum MemTag { mtInternal };
struct NativeCallStack {};
#define CALLER_PC NativeCallStack{}
#define DEBUG_ONLY(x)
#define MAX2(a,b) ((a)>(b)?(a):(b))
#define MIN2(a,b) ((a)<(b)?(a):(b))
#define assert(ignore,... ) do {if(!(ignore))std::abort();}while(0)
struct FreeInfo {size_t size;};
static bool tracking=false;static size_t accounted=0,limit=SIZE_MAX;
struct alignas(max_align_t) MallocHeader {
 using FreeInfo=::FreeInfo;
 size_t length;bool dead;
 size_t size()const{return length;}
 MemTag mem_tag()const{return mtInternal;}
 FreeInfo free_info()const{return {length};}
 void mark_block_as_dead(){assert(!dead);dead=true;}
 void revive(){assert(dead);dead=false;}
 static MallocHeader* resolve_checked(void* p){auto h=(MallocHeader*)p-1;assert(!h->dead);return h;}
};
struct MallocTracker {static MallocHeader* malloc_header(void* p){return (MallocHeader*)p-1;}};
using address=unsigned char*;
struct MemTracker {
 static size_t overhead_per_malloc(){return tracking?sizeof(MallocHeader):0;}
 static bool enabled(){return tracking;}
 static bool check_exceeds_limit(size_t n,MemTag){return n>limit-accounted;}
 static void* record_malloc(void* p,size_t n,MemTag,const NativeCallStack&){
  if(!tracking)return p;auto h=(MallocHeader*)p;h->length=n;h->dead=false;accounted+=n;return h+1;
 }
 static void deaccount(FreeInfo info){assert(accounted>=info.size);accounted-=info.size;}
 static void* record_free(void* p){if(!tracking)return p;auto h=MallocHeader::resolve_checked(p);deaccount(h->free_info());h->dead=true;return h;}
};
struct NMTPreInit {static bool handle_malloc(void**,size_t){return false;}static bool handle_realloc(void**,void*,size_t,MemTag){return false;}static bool handle_free(void*){return false;}};
struct CDSConfig {static bool is_dumping_static_archive(){return false;}};
static bool ZapCHeap=false;static const int uninitBlockPad=0xba;
struct os {
 static void* malloc(size_t,MemTag);static void* malloc(size_t,MemTag,const NativeCallStack&);
 static void* realloc(void*,size_t,MemTag);static void* realloc(void*,size_t,MemTag,const NativeCallStack&);
 static void free(void*);
};
'''
os_source=(ROOT/'.tools/java25/openjdk/src/hotspot/share/runtime/os.cpp').read_text()
start=os_source.index('void* os::malloc(size_t size, MemTag mem_tag)')
end=os_source.index('void os::init_random',start)
functions=os_source[start:end]
preinit=(ROOT/'.tools/java25/openjdk/src/hotspot/share/nmt/nmtPreInit.cpp').read_text()
a=preinit.index('static void* raw_malloc(size_t s) { return ps5_native_heap::allocate(s); }');b=preinit.index('#else',a)
functions=preinit[a:b]+'\n'+functions
arena=(ROOT/'.tools/java25/openjdk/src/hotspot/share/memory/arena.hpp').read_text()
a=arena.index('  enum {');b=arena.index('\n  };',a)+5
arena_enum=arena[a:b]
checks=r'''
static constexpr size_t K=1024;
struct ArenaChunkLayoutContract {void* next;size_t length;uint64_t stamp;
ARENA_ENUM_PLACEHOLDER
};
int main(){
 heap_stress_main();deny_heap=false;deny_maps=false;
 assert(heap::libc_held()==0);
 // Prefix-inclusive cap, retained shrink capacity, failed growth rollback,
 // migration and full backend refusal must all preserve exact accounting.
 void* budget=heap::allocate(1024*1024);assert(budget&&heap::libc_held()==1024*1024+sizeof(heap::Header));
 void* overflow=heap::allocate(1024*1024);assert(overflow&&heap::libc_held()==1024*1024+sizeof(heap::Header));
 budget=heap::reallocate(budget,64);assert(heap::libc_held()==1024*1024+sizeof(heap::Header));
 std::memset(budget,0x25,64);budget=heap::reallocate(budget,1536*1024);check(budget,64,0x25);assert(heap::libc_held()==1536*1024+sizeof(heap::Header));
 deny_resize=true;budget=heap::reallocate(budget,1600*1024);check(budget,64,0x25);assert(heap::libc_held()==0);deny_resize=false;
 heap::release(budget);heap::release(overflow);heap::trim_idle();assert(heap::libc_held()==0&&heap_live==0&&map_live==0);
 budget=heap::allocate(heap::libc_budget-sizeof(heap::Header));assert(budget&&heap::libc_held()==heap::libc_budget);
 deny_maps=true;assert(!heap::allocate(8192));assert(heap::libc_held()==heap::libc_budget);deny_maps=false;heap::release(budget);
 // Hold simultaneous allocations above the cap while sampling the atomic
 // reservation. In-flight reservations are included, so no race can overspend.
 parallel=true;std::atomic<int> arrivals{0};std::atomic<bool> proceed{false};std::vector<std::thread> budget_workers;
 for(int i=0;i<8;++i)budget_workers.emplace_back([&]{void* p=heap::allocate(512*1024);assert(p&&heap::libc_held()<=heap::libc_budget);++arrivals;while(!proceed.load())std::this_thread::yield();heap::release(p);});
 while(arrivals.load()!=8)std::this_thread::yield();assert(heap::libc_held()<=heap::libc_budget&&heap_live==3);proceed=true;
 for(auto& worker:budget_workers)worker.join();parallel=false;heap::trim_idle();assert(heap::libc_held()==0&&heap_live==0&&map_live==0);
 std::puts("PASS: libc prefix-inclusive2MiB cap, exact grow/shrink/migrate/failure accounting, true refusal and concurrent reservations/cleanup");

 // Raw NMT pre-init block survives transition to ordinary NMT-off os APIs.
 void* early=raw_malloc(90);assert(early);std::memset(early,0x61,90);
 deny_heap=true;early=raw_realloc(early,128);check(early,90,0x61);
 deny_heap=true;early=os::realloc(early,300,mtInternal);check(early,90,0x61);os::free(early);
 // The default arena request must fit two16KiB pages even with NMT overhead.
 for(bool nmt:{false,true}) {
  tracking=nmt;accounted=0;limit=SIZE_MAX;deny_heap=true;map_limit=32768;
  size_t request=sizeof(ArenaChunkLayoutContract)+ArenaChunkLayoutContract::size;
  void* arena=os::malloc(request,mtInternal);assert(arena);
  void* raw=nmt?(void*)((MallocHeader*)arena-1):arena;
  assert(heap::mapped_bytes((heap::Header*)raw-1)==32768);
  memset(arena,0x47,request);os::free(arena);heap::trim_idle();assert(map_live==0&&accounted==0);
  // The compact prefix also keeps the old untracked32752-byte request in32KiB.
  tracking=false;void* old_arena=os::malloc(32752,mtInternal);assert(old_arena);os::free(old_arena);heap::trim_idle();assert(map_live==0);
 }
 map_limit=SIZE_MAX;
 std::puts("PASS: exact arena size enum with layout/NMT contracts and16KiB page model fits32KiB; compact prefix also fits32752-byte untracked request at32KiB mapping limit");
 for(bool nmt:{false,true}) {
  tracking=nmt;accounted=0;limit=SIZE_MAX;deny_heap=false;
  void* p=os::malloc(128,mtInternal);assert(p);std::memset(p,0x52,128);
  assert(accounted==(nmt?128u:0u));
  deny_heap=true;p=os::realloc(p,512,mtInternal);check(p,128,0x52);
  assert(accounted==(nmt?512u:0u));
  deny_maps=true;assert(!os::realloc(p,9000,mtInternal));check(p,128,0x52);
  if(nmt)assert(!MallocTracker::malloc_header(p)->dead);
  assert(accounted==(nmt?512u:0u));deny_maps=false;
  if(nmt){limit=accounted;assert(!os::malloc(1,mtInternal));assert(!os::realloc(p,513,mtInternal));limit=SIZE_MAX;}
  p=os::realloc(p,32,mtInternal);check(p,32,0x52);os::free(p);assert(accounted==0);
  assert(!os::malloc(SIZE_MAX,mtInternal));os::free(nullptr);
  heap::trim_idle();assert(heap_live==0&&map_live==0);
 }
 std::puts("PASS: actual os.cpp malloc/realloc/free preserve NMT model accounting/limits, revive headers after failed resize and accept raw pre-init blocks with tracking off");
}
'''
cpp=cpp.replace('int main(){','int heap_stress_main(){').replace('complete backend cleanup");','complete backend cleanup");return 0;')
checks=checks.replace('ARENA_ENUM_PLACEHOLDER',arena_enum)
cpp+='\n#undef assert\n'+model+'\n'+functions+'\n'+checks

source=WORK/'test.cpp';source.write_text(cpp);exe=WORK/'test-native-heap'
subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-pthread','-I'+str(WORK),'-I'+str(ROOT/'.tools/java25/openjdk/src/hotspot/share'),str(source),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True,timeout=90)
