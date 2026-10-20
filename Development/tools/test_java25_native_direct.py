#!/usr/bin/env python3
"""Exercise actual raw allocator/direct ledger with real storage and kernel faults."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
work=root/'build/java25/native-direct-test'
(work/'utilities').mkdir(parents=True,exist_ok=True)
(work/'runtime').mkdir(exist_ok=True)
(work/'utilities/permitForbiddenFunctions.hpp').write_text('''#pragma once
namespace permit_forbidden_function {
inline void* malloc(size_t n){return deny_heap?nullptr:std::malloc(n);}
inline void* realloc(void* p,size_t n){return deny_heap?nullptr:std::realloc(p,n);}
inline void free(void* p){std::free(p);}
}
''')
(work/'runtime/ps5StartupTrace.hpp').write_text('''#pragma once
inline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){trace_check();}
''')
source=work/'test.cpp'
source.write_text(r'''
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <cerrno>
#include <cstdint>
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <mutex>
#include <sys/mman.h>
#include <unistd.h>
static std::atomic<bool> deny_heap{false},parallel{false};
static bool fail_alloc=false,fail_map=false,fail_unmap=false,fail_release=false;
static int mmap_error=ENOMEM;
static std::mutex kernel_mutex;
struct Physical {void* p;size_t bytes;bool mapped;};
static Physical physical[4096]{};
static size_t live_physical=0,live_mappings=0,alloc_calls=0,release_calls=0;
extern "C" size_t sceKernelGetDirectMemorySize(){return 1024ULL*1024*1024;}
extern "C" int sceKernelAllocateDirectMemory(int64_t start,int64_t end,size_t bytes,size_t alignment,int type,int64_t* offset){
 std::lock_guard<std::mutex> guard(kernel_mutex);++alloc_calls;
 assert(start==0&&end==1024LL*1024*1024&&alignment==16384&&bytes%16384==0&&type==12);
 if(fail_alloc)return -17;
 for(int i=0;i<4096;++i)if(!physical[i].p){void* p=nullptr;if(posix_memalign(&p,16384,bytes))return -18;physical[i]={p,bytes,false};*offset=i;++live_physical;return 0;}
 return -19;
}
extern "C" int sceKernelMapDirectMemory(void** address,size_t bytes,int prot,int flags,int64_t offset,size_t alignment){
 std::lock_guard<std::mutex> guard(kernel_mutex);
 assert(prot==(PROT_READ|PROT_WRITE)&&flags==0&&alignment==16384&&offset>=0&&offset<4096);
 assert((uintptr_t)*address==0x1000000000ULL&&physical[offset].p&&physical[offset].bytes==bytes&&!physical[offset].mapped);
 if(fail_map)return -20;
 *address=physical[offset].p;physical[offset].mapped=true;++live_mappings;return 0;
}
extern "C" int sceKernelMunmap(void* address,size_t bytes){
 std::lock_guard<std::mutex> guard(kernel_mutex);
 for(auto& p:physical)if(p.p==address){assert(p.mapped&&p.bytes==bytes);if(fail_unmap)return -21;p.mapped=false;--live_mappings;return 0;}
 std::abort();
}
extern "C" int sceKernelReleaseDirectMemory(int64_t offset,size_t bytes){
 std::lock_guard<std::mutex> guard(kernel_mutex);++release_calls;
 assert(offset>=0&&offset<4096&&physical[offset].p&&physical[offset].bytes==bytes&&!physical[offset].mapped);
 if(fail_release)return -22;
 std::free(physical[offset].p);physical[offset]={};--live_physical;return 0;
}
static void* refused_mmap(void*,size_t,int,int,int,off_t){errno=mmap_error;return MAP_FAILED;}
static long target_page(int){return 16384;}
static void trace_check();
#define __PROSPERO__ 1
#define mmap refused_mmap
#define sysconf target_page
#include "runtime/ps5NativeHeap.hpp"
#undef mmap
#undef sysconf
namespace heap=ps5_native_heap;
namespace direct=ps5_native_direct;
static void trace_check(){if(!parallel){assert(direct::state().mutex==0);assert(*heap::mutex_word()==0);}}
static void empty(){heap::trim_idle();assert(live_physical==0&&live_mappings==0&&direct::state().held==0);}
static void clean_retained_for_test(){
 // Production intentionally retains ownership on kernel cleanup failure. The
 // fixture clears that injected failure and explicitly cleans its owned storage.
 for(unsigned i=0;i<direct::entry_count;++i){auto& e=direct::state().entries[i];if(e.occupied){assert(e.address==nullptr);assert(sceKernelReleaseDirectMemory(e.physical,e.bytes)==0);direct::abandon(i);}}
 empty();
}
int main(){
 errno=EDOM;void* p=heap::allocate(100);assert(p&&errno==EDOM&&alloc_calls==0);heap::release(p);
 deny_heap=true;
 p=heap::allocate(32664);assert(p&&errno==EDOM&&direct::state().held==32768);memset(p,0x57,32664);
 p=heap::reallocate(p,65536);assert(p&&errno==EDOM);for(int i=0;i<32664;++i)assert(((unsigned char*)p)[i]==0x57);
 fail_alloc=true;void* old=p;assert(!heap::reallocate(p,131072)&&errno==ENOMEM);p=old;for(int i=0;i<32664;++i)assert(((unsigned char*)p)[i]==0x57);fail_alloc=false;
 errno=EDOM;heap::release(p);assert(errno==EDOM);empty();
 // Small allocation slabs use and release the same exact direct-memory owner.
 std::vector<void*> small;for(int i=0;i<300;++i){void* q=heap::allocate(4096);assert(q);memset(q,0x35,4096);small.push_back(q);}
 for(void* q:small){assert(((unsigned char*)q)[4095]==0x35);heap::release(q);}empty();
 size_t before=alloc_calls;mmap_error=EACCES;assert(!heap::allocate(8192)&&errno==EACCES&&alloc_calls==before);mmap_error=ENOMEM;
 fail_map=true;assert(!heap::allocate(8192)&&errno==ENOMEM);fail_map=false;empty();
 fail_map=true;fail_release=true;assert(!heap::allocate(8192)&&errno==ENOMEM);assert(live_physical==2&&live_mappings==0&&direct::state().held==32768);fail_map=false;fail_release=false;clean_retained_for_test();
 void* mapping=direct::map(16384);assert(mapping!=MAP_FAILED);memset(mapping,0x48,16384);
 int result=0;assert(direct::unmap(mapping,32768,&result)&&result==-1&&errno==EINVAL);assert(live_physical==1&&live_mappings==1);
 fail_unmap=true;before=release_calls;assert(direct::unmap(mapping,16384,&result)&&result==-1);assert(release_calls==before&&live_mappings==1&&((char*)mapping)[0]==0x48);fail_unmap=false;
 assert(direct::unmap(mapping,16384,&result)&&result==0);empty();
 mapping=direct::map(16384);fail_release=true;assert(direct::unmap(mapping,16384,&result)&&result==-1);assert(live_mappings==0&&live_physical==1);fail_release=false;clean_retained_for_test();
 assert(direct::map(0)==MAP_FAILED&&direct::map(SIZE_MAX)==MAP_FAILED&&direct::map(1)==MAP_FAILED);
 mapping=direct::map(direct::budget_bytes);assert(mapping!=MAP_FAILED);before=alloc_calls;assert(direct::map(16384)==MAP_FAILED&&alloc_calls==before);assert(direct::unmap(mapping,direct::budget_bytes,&result)&&result==0);empty();
 std::vector<void*> slots;for(unsigned i=0;i<direct::entry_count;++i){void* q=direct::map(16384);assert(q!=MAP_FAILED);slots.push_back(q);}before=alloc_calls;assert(direct::map(16384)==MAP_FAILED&&alloc_calls==before);for(void* q:slots)assert(direct::unmap(q,16384,&result)&&result==0);empty();
 parallel=true;std::vector<std::thread> threads;for(int t=0;t<4;++t)threads.emplace_back([t]{for(int i=0;i<1000;++i){size_t n=1+(i*137+t*17)%9000;void* q=heap::allocate(n);assert(q);memset(q,t+1,n);void* grown=heap::reallocate(q,n+500);assert(grown);for(size_t j=0;j<n;++j)assert(((unsigned char*)grown)[j]==t+1);heap::release(grown);}});for(auto& t:threads)t.join();parallel=false;empty();
 assert(direct::state().mappings==direct::state().releases+1); // One mapped-release fault was explicitly cleaned by the fixture.
 puts("PASS: actual native allocator/direct ledger; exact32KiB refusal fallback, data-preserving growth, slabs, rollback/unmap/release failures, budget/slot caps and4000 concurrent lifetimes; ASan/UBSan");
}
''')
exe=work/'test'
subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-pthread','-I'+str(work),'-I'+str(root/'.tools/java25/openjdk/src/hotspot/share'),str(source),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True,timeout=120)
