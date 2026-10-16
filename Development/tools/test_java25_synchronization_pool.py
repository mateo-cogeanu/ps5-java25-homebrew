#!/usr/bin/env python3
"""Exercise real pthread resources while denying all late native initialization."""
from pathlib import Path
import subprocess,os
R=Path(__file__).resolve().parents[1];W=R/'build/java25/sync-pool-test';(W/'runtime').mkdir(parents=True,exist_ok=True)
(W/'runtime/ps5StartupTrace.hpp').write_text(r'''#pragma once
#include <cstdint>
#include <cstring>
static unsigned long long seen_status,seen_leased,seen_initialized,seen_state,seen_match,seen_caller;
inline void ps5_vm_trace_values(const char*label,unsigned long long a,const char*,unsigned long long b,const char*,unsigned long long c){
 if(std::strstr(label,"failure status=")){seen_status=a;seen_leased=b;seen_initialized=c;}
 if(std::strstr(label,"fallback config=")){seen_state=a;seen_match=b;seen_caller=c;}
}
''')
cpp=r'''
#include <pthread.h>
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <memory>
#include <cerrno>
#include <ctime>
#include <cstdio>
static std::atomic<bool> deny{false};static std::atomic<int> mutex_calls{0},relative_calls{0},absolute_calls{0};
int test_mutex_init(pthread_mutex_t*p,const pthread_mutexattr_t*a){++mutex_calls;if(deny)return ENOMEM;return ::pthread_mutex_init(p,a);}
int test_cond_init(pthread_cond_t*p,const pthread_condattr_t*a){if(a)++relative_calls;else ++absolute_calls;if(deny)return ENOMEM;return ::pthread_cond_init(p,a);}
#define __PROSPERO__ 1
#define pthread_mutex_init test_mutex_init
#define pthread_cond_init test_cond_init
#include "runtime/ps5Synchronization.hpp"
#undef pthread_mutex_init
#undef pthread_cond_init
using namespace ps5_sync;
int main(){
 pthread_mutexattr_t ma,other;pthread_condattr_t ca;assert(pthread_mutexattr_init(&ma)==0);assert(pthread_mutexattr_settype(&ma,PTHREAD_MUTEX_NORMAL)==0);assert(pthread_mutexattr_init(&other)==0);assert(pthread_condattr_init(&ca)==0);
 // Existing early/local objects remain native-owned, rather than copied.
 MutexLease early;assert(early.init(&ma)==0);auto*early_address=early.get();assert(pthread_mutex_lock(early.get())==0);assert(pthread_mutex_unlock(early.get())==0);
 auto counts=prime(&ma,&ca);assert(counts.mutexes==mutex_capacity&&counts.relative==512&&counts.absolute==256);
 assert(early.get()==early_address&&early.destroy()==0);deny=true;
 int before=mutex_calls;MutexLease m;CondLease relative,absolute;errno=EDOM;
 assert(m.init(&ma)==0&&relative.init(&ca)==0&&absolute.init(nullptr)==0&&errno==EDOM&&mutex_calls==before);
 assert(relative.get()!=absolute.get());assert(pthread_mutex_lock(m.get())==0);
 assert(m.destroy()==EBUSY); // Never give a locked mutex to a new owner.
 timespec limit;clock_gettime(CLOCK_REALTIME,&limit);limit.tv_nsec+=1000000;if(limit.tv_nsec>=1000000000){++limit.tv_sec;limit.tv_nsec-=1000000000;}
 assert(pthread_cond_timedwait(absolute.get(),m.get(),&limit)==ETIMEDOUT);
 assert(pthread_mutex_unlock(m.get())==0);assert(relative.destroy()==0&&absolute.destroy()==0&&m.destroy()==0);
 // All configured pool entries are exclusive and exhaustion propagates real ENOMEM.
 std::vector<std::unique_ptr<MutexLease>> held;
 for(int i=0;i<mutex_capacity;++i){auto item=std::make_unique<MutexLease>();assert(item->init(&ma)==0);for(auto&other_item:held)assert(other_item->get()!=item->get());held.push_back(std::move(item));}
 MutexLease extra;auto full=mutex_pool().stats();assert(full.initialized==mutex_capacity&&full.leased==mutex_capacity);assert(extra.init(&ma)==ENOMEM&&extra.destroy()==EINVAL);assert(seen_status==ENOMEM&&seen_leased==mutex_capacity&&seen_initialized==mutex_capacity&&seen_state==2&&seen_match==1&&seen_caller);auto*returned=held.back()->get();assert(held.back()->destroy()==0);held.pop_back();assert(extra.init(&ma)==0&&extra.get()==returned);assert(extra.destroy()==0);for(auto&item:held)assert(item->destroy()==0);held.clear();
 MutexLease custom;assert(custom.init(&other)==ENOMEM);assert(seen_status==ENOMEM&&seen_leased==0&&seen_initialized==mutex_capacity&&seen_state==2&&seen_match==0&&seen_caller); // A different attribute never borrows a configured mutex.
 CondLease custom_cond;pthread_condattr_t different;pthread_condattr_init(&different);assert(custom_cond.init(&different)==ENOMEM);
 // Condition-pair syntax retains distinct relative/absolute resources.
 CondPair pair;assert(cond_init_at(pair,0,&ca)==0&&cond_init_at(pair,1,nullptr)==0);assert(&pair[0]!=&pair[1]);assert(cond_destroy_at(pair,0)==0&&cond_destroy_at(pair,1)==0);
 // Actual condition wait/signal exchange after initialization refusal.
 MutexLease shared;CondLease signal;assert(shared.init(&ma)==0&&signal.init(&ca)==0);bool ready=false;
 std::thread waiter([&]{assert(pthread_mutex_lock(shared.get())==0);while(!ready)assert(pthread_cond_wait(signal.get(),shared.get())==0);assert(pthread_mutex_unlock(shared.get())==0);});
 assert(pthread_mutex_lock(shared.get())==0);ready=true;assert(pthread_cond_signal(signal.get())==0);assert(pthread_mutex_unlock(shared.get())==0);waiter.join();assert(signal.destroy()==0&&shared.destroy()==0);
 std::vector<std::thread> workers;
 before=mutex_calls;
 for(int i=0;i<8;++i)workers.emplace_back([&]{for(int n=0;n<1000;++n){MutexLease lock;CondLease cond;assert(lock.init(&ma)==0&&cond.init(&ca)==0);assert(pthread_mutex_lock(lock.get())==0);assert(pthread_mutex_unlock(lock.get())==0);assert(cond.destroy()==0&&lock.destroy()==0);}});
 for(auto&t:workers)t.join();assert(mutex_calls==before);
 // Test-only teardown of process-lifetime caches after every lease is returned.
 for(auto&s:mutex_pool().slots){assert(s.initialized&&!s.busy);assert(pthread_mutex_destroy(&s.native)==0);}
 for(auto&s:relative_pool().slots){assert(s.initialized&&!s.busy);assert(pthread_cond_destroy(&s.native)==0);}
 for(auto&s:absolute_pool().slots){assert(s.initialized&&!s.busy);assert(pthread_cond_destroy(&s.native)==0);}
 pthread_condattr_destroy(&different);pthread_condattr_destroy(&ca);pthread_mutexattr_destroy(&ma);pthread_mutexattr_destroy(&other);
 puts("PASS: real pooled mutex/cond objects, late init ENOMEM, no handle copying, lock/busy and wait/signal/timeout behavior, exact attrs,4096-slot exhaustion/reuse,8000 concurrent lease lifetimes and complete native teardown and distinct exhaustion/attribute-mismatch diagnostics");
}
'''
p=W/'test.cpp';p.write_text(cpp)
subprocess.run(['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-pthread','-I',str(W),'-I',str(R/'.tools/java25/openjdk/src/hotspot/share'),str(p),'-o',str(W/'test')],check=True)
subprocess.run([str(W/'test')],check=True)
source=W/'target.cpp';source.write_text('#include "runtime/ps5Synchronization.hpp"\nextern "C" int probe(){ps5_sync::MutexLease m;return m.init(nullptr);}\n')
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config')
subprocess.run([str(R/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang++'),'-std=c++17','-O2','-S','-emit-llvm','-I'+str(R/'.tools/java25/openjdk/src/hotspot/share'),str(source),'-o',str(W/'target.ll')],env=env,check=True)
ir=(W/'target.ll').read_text();assert '__emutls' not in ir and '__cxa_guard' not in ir and '@malloc' not in ir
print('PASS: target lease metadata uses fixed storage/atomics and native pthread APIs without heap/compiler TLS/lazy guards')
