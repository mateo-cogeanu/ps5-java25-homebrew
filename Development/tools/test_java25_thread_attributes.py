#!/usr/bin/env python3
"""Exercise the actual attribute lease with real pthreads and forced init refusal."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1];work=ROOT/'build/java25/thread-attributes-test';work.mkdir(parents=True,exist_ok=True)
header=ROOT/'.tools/java25/openjdk/src/hotspot/share/runtime/ps5ThreadAttributes.hpp'
source=r'''
#include <pthread.h>
#include <assert.h>
#include <errno.h>
#include <atomic>
#include <thread>
#include <vector>
#include <stdlib.h>
static std::atomic<bool> deny{false};static std::atomic<int> initialized{0},destroyed{0},ran{0};
static int test_init(pthread_attr_t* attr){if(deny)return ENOMEM;int r=pthread_attr_init(attr);if(!r)++initialized;return r;}
static int test_destroy(pthread_attr_t* attr){int r=pthread_attr_destroy(attr);if(!r)++destroyed;return r;}
#define pthread_attr_init test_init
#define pthread_attr_destroy test_destroy
#include "HEADER"
#undef pthread_attr_init
#undef pthread_attr_destroy
static void* child(void*){++ran;return nullptr;}
static void early_return(){ps5_thread_attributes::Lease lease;assert(lease.acquire()==0);}
int main(int argc,char**){
 using namespace ps5_thread_attributes;
 if(argc>1){deny=true;Lease failed;assert(failed.acquire()==ENOMEM);deny=false;Lease local;assert(local.acquire()==0);local.release();assert(initialized==1&&destroyed==1);return 0;}
 initialize();assert(initialized==2*capacity);deny=true;
 // Query storage is separate even when populated with a live stack address.
 QueryLease query;assert(query.acquire()==0);Lease create;assert(create.acquire()==0);
 assert(query.value!=create.value);
 void* fake_stack=nullptr;assert(posix_memalign(&fake_stack,16384,1024*1024)==0);
 assert(pthread_attr_setstack(query.value,fake_stack,1024*1024)==0);
 void* creation_stack=nullptr;assert(pthread_attr_getstackaddr(create.value,&creation_stack)==0);
 assert(creation_stack!=fake_stack);query.release();create.release();
 for(int n=0;n<100;++n){QueryLease q;assert(q.acquire()==0);size_t size=0;assert(pthread_attr_getstacksize(q.value,&size)==0&&size==1024*1024);}
 QueryLease queries[capacity];for(auto& q:queries)assert(q.acquire()==0);
 QueryLease exhausted;assert(exhausted.acquire()==ENOMEM);
 deny=false;assert(exhausted.acquire()==0);exhausted.release();deny=true;
 assert(destroyed==1);for(auto& q:queries)q.release();free(fake_stack);
 early_return();Lease slots[capacity];
 for(unsigned i=0;i<capacity;++i){assert(slots[i].acquire()==0);for(unsigned j=0;j<i;++j)assert(slots[i].value!=slots[j].value);}
 Lease extra;assert(extra.acquire()==ENOMEM);deny=false;assert(extra.acquire()==0);extra.release();assert(destroyed==2);deny=true;
 for(auto& slot:slots)slot.release();
 std::vector<std::thread> workers;
 for(int i=0;i<8;++i)workers.emplace_back([]{
  for(int n=0;n<100;++n){Lease lease;assert(lease.acquire()==0);size_t bytes=(n%2+1)*512*1024;
   assert(pthread_attr_setdetachstate(lease.value,PTHREAD_CREATE_JOINABLE)==0);
   assert(pthread_attr_setstacksize(lease.value,bytes)==0);size_t actual=0;assert(pthread_attr_getstacksize(lease.value,&actual)==0&&actual==bytes);
   pthread_t thread;assert(pthread_create(&thread,lease.value,child,nullptr)==0);
   errno=EACCES;lease.release();assert(errno==EACCES);assert(pthread_join(thread,nullptr)==0);
  }
 });
 for(auto& worker:workers)worker.join();assert(ran==800);assert(initialized==2*capacity+2&&destroyed==2);
 for(unsigned i=0;i<capacity;++i)assert(!ps5_thread_attributes::slots()[i].busy);
}
'''.replace('HEADER',str(header))
(work/'test.cpp').write_text(source)
subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-pthread',str(work/'test.cpp'),'-o',str(work/'check')],check=True)
subprocess.run([str(work/'check')],check=True);subprocess.run([str(work/'check'),'initial-failure'],check=True)
print('PASS: isolated creation/query domains, query stack contamination excluded, late query init denial/reuse/exhaustion;  real attribute objects, no opaque copies, forced late/init failure, bounded pool exhaustion/local cleanup, early-return reuse, 800 concurrent-created pthreads and stack-size reset')
