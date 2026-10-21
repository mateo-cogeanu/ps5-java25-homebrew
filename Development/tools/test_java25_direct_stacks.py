#!/usr/bin/env python3
"""Actual direct stack owner with real custom-stack pthreads and gated TLS destruction."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/direct-stack-test';(w/'runtime').mkdir(parents=True,exist_ok=True)
(w/'runtime/ps5StartupTrace.hpp').write_text('#pragma once\ninline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){}\n')
code=r'''
#include <pthread.h>
#include <cassert>
#include <atomic>
#include <thread>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <sys/mman.h>
#include <unistd.h>
static bool initializing=true,deny_create=false,deny_stack=false,deny_join=false,deny_release=false,deny_alloc=false;
static std::atomic<int> live{0},unmaps{0};
static void* physical[128]{};static size_t sizes[128]{};
extern "C" size_t sceKernelGetDirectMemorySize(){return 1024ULL*1024*1024;}
extern "C" int sceKernelAllocateDirectMemory(int64_t,int64_t,size_t bytes,size_t alignment,int,int64_t* offset){if(deny_alloc)return -1;for(int i=0;i<128;++i)if(!physical[i]){assert(!posix_memalign(&physical[i],alignment,bytes));sizes[i]=bytes;*offset=i;++live;return 0;}return -2;}
extern "C" int sceKernelMapDirectMemory(void** p,size_t bytes,int,int,int64_t offset,size_t){assert(physical[offset]&&sizes[offset]==bytes);*p=physical[offset];return 0;}
extern "C" int sceKernelMunmap(void* p,size_t bytes){for(int i=0;i<128;++i)if(physical[i]==p){assert(bytes==sizes[i]);++unmaps;return ::mprotect(p,bytes,PROT_READ|PROT_WRITE);}abort();}
extern "C" int sceKernelReleaseDirectMemory(int64_t offset,size_t bytes){assert(physical[offset]&&sizes[offset]==bytes);if(deny_release)return -3;free(physical[offset]);physical[offset]=nullptr;--live;return 0;}
static int create(pthread_t* t,const pthread_attr_t* a,void*(*f)(void*),void* p){if(initializing){*t=pthread_self();return 0;}if(deny_create)return EAGAIN;return pthread_create(t,a,f,p);}
static int stack(pthread_attr_t* a,void* p,size_t n){return deny_stack?EINVAL:pthread_attr_setstack(a,p,n);}
static int join(pthread_t t,void** p){return deny_join?EINVAL:pthread_join(t,p);}
#define __PROSPERO__ 1
#define pthread_create create
#define pthread_attr_setstack stack
#define pthread_join join
#include "runtime/ps5ThreadStacks.hpp"
#undef pthread_join
#undef pthread_attr_setstack
#undef pthread_create
namespace owner=ps5_thread_stacks;
static std::atomic<bool> destructor_entered{false},allow_destructor{false},destructor_done{false};
struct Sentinel{int value=0;~Sentinel(){destructor_entered=true;while(!allow_destructor)std::this_thread::yield();destructor_done=true;}};
static void* work(void*){thread_local Sentinel sentinel;sentinel.value=42;return nullptr;}
static void wait_for(std::atomic<bool>& value){while(!value)std::this_thread::yield();}
static void* empty(void*){return nullptr;}
static void drain(){for(unsigned n=0;n<10000&&*owner::held();++n){owner::reap_once();usleep(100);}assert(*owner::held()==0&&live==0);}
int main(){
 owner::initialize();initializing=false;assert(*owner::available()==1);constexpr size_t bytes=512*1024;pthread_t child;
 errno=EDOM;deny_alloc=true;assert(owner::create(&child,bytes,empty,nullptr)==EAGAIN&&errno==EDOM&&!*owner::held()&&!live);deny_alloc=false;
 deny_stack=true;assert(owner::create(&child,bytes,empty,nullptr)==EINVAL&&!*owner::held()&&!live);deny_stack=false;
 deny_create=true;assert(owner::create(&child,bytes,empty,nullptr)==EAGAIN&&!*owner::held()&&!live);deny_create=false;
 *owner::held()=owner::stack_budget;assert(owner::create(&child,bytes,empty,nullptr)==EAGAIN&&!live);*owner::held()=0;
 for(unsigned i=0;i<owner::capacity;++i)owner::slots()[i].state=4;assert(owner::create(&child,bytes,empty,nullptr)==EAGAIN);for(unsigned i=0;i<owner::capacity;++i)owner::slots()[i].state=0;
 for(int round=0;round<20;++round){
  destructor_entered=false;allow_destructor=false;destructor_done=false;int before=unmaps;
  assert(!owner::create(&child,bytes,work,nullptr));wait_for(destructor_entered);assert(live==1&&*owner::held()==bytes);
  assert(ps5_native_direct::stack_range(owner::slots()[0].memory,bytes)&&!ps5_native_direct::metadata_range(owner::slots()[0].memory,bytes));
  assert(ps5_native_direct::uncommit_metadata(owner::slots()[0].memory,16384));
  assert(!mprotect(owner::slots()[0].memory,16384,PROT_READ|PROT_WRITE));
  std::atomic<bool> reaped{false};std::thread reaping([&]{owner::reap_once();reaped=true;});usleep(5000);assert(!reaped&&unmaps==before&&!destructor_done);
  allow_destructor=true;reaping.join();assert(destructor_done&&reaped&&unmaps==before+1&&!live&&!*owner::held());
 }
 for(int i=0;i<200;++i){assert(!owner::create(&child,bytes,empty,nullptr));drain();}
 // A failed join must retain the mapping; test-only later join proves death.
 assert(!owner::create(&child,bytes,empty,nullptr));while(!__atomic_load_n(&owner::slots()[0].done,__ATOMIC_ACQUIRE))std::this_thread::yield();deny_join=true;owner::reap_once();deny_join=false;assert(live==1&&owner::slots()[0].state==4);assert(!pthread_join(child,nullptr));int rc;assert(ps5_native_direct::unmap(owner::slots()[0].memory,bytes,&rc)&&!rc);*owner::held()=0;owner::slots()[0].state=0;
 // Physical release refusal stays charged/owned, even after successful join.
 assert(!owner::create(&child,bytes,empty,nullptr));while(!__atomic_load_n(&owner::slots()[0].done,__ATOMIC_ACQUIRE))std::this_thread::yield();deny_release=true;owner::reap_once();deny_release=false;assert(live==1&&*owner::held()==bytes&&owner::slots()[0].state==4);
 for(unsigned i=0;i<ps5_native_direct::entry_count;++i){auto& e=ps5_native_direct::state().entries[i];if(e.occupied){assert(!sceKernelReleaseDirectMemory(e.physical,e.bytes));ps5_native_direct::abandon(i);}}
 assert(!live&&!ps5_native_direct::state().held);
 puts("PASS: actual direct stack owner, real512KiB custom-stack pthreads, gated TLS destructors/join-before-free,220reclaimed lifetimes, allocation/attribute/create/join/release faults and slot/budget caps; ASan/UBSan");
}
'''
(w/'test.cpp').write_text('#include <cstdio>\n'+code)
subprocess.run(['clang++','-std=c++17','-O1','-g','-pthread','-fsanitize=address,undefined','-I'+str(w),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),str(w/'test.cpp'),'-o',str(w/'check')],check=True)
subprocess.run([str(w/'check')],check=True,timeout=90)
