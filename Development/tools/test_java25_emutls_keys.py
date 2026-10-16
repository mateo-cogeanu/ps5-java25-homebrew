#!/usr/bin/env python3
"""Test the actual compiler-TLS adapter with real pthread lifecycle and failure injection."""
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[1];W=R/'build/java25/emutls-keys-test';W.mkdir(parents=True,exist_ok=True)
cpp=r'''
#include <pthread.h>
#include <sched.h>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <cerrno>
#include <cstdint>
#include <cstddef>
#include <cassert>
#include <atomic>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
static std::atomic<bool> deny_heap{true},deny_set{true},false_success{false},fail_create{false},fail_join{false};
static std::atomic<int> maps{0},heaps{0},destroyed{0},after_return{0},creates{0},sets{0};
static pthread_key_t key,late_key;
namespace injected {
void* alloc(size_t n){if(deny_heap){errno=ENOMEM;return nullptr;}void*p=::malloc(n);if(p)++heaps;return p;}
void drop(void*p){if(p)--heaps;::free(p);}
}
namespace std {inline void* injected_malloc(size_t n){return injected::alloc(n);}inline void injected_free(void*p){injected::drop(p);}}
void* test_map(void*p,size_t n,int prot,int flags,int fd,off_t off){p=::mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED)++maps;return p;}
int test_unmap(void*p,size_t n){int r=::munmap(p,n);if(!r)--maps;return r;}
int test_set(pthread_key_t k,const void*p){++sets;if(deny_set)return ENOMEM;if(false_success)return 0;return ::pthread_setspecific(k,p);}
int test_key_create(pthread_key_t*k,void(*f)(void*)){return ::pthread_key_create(k,f);}
extern "C" int __real_pthread_create(pthread_t*t,const pthread_attr_t*a,void*(*fn)(void*),void*v){++creates;if(fail_create)return EAGAIN;return ::pthread_create(t,a,fn,v);}
extern "C" int __real_pthread_join(pthread_t t,void**p){if(fail_join)return EDEADLK;return ::pthread_join(t,p);}
#define malloc injected_malloc
#define free injected_free
#define mmap test_map
#define munmap test_unmap
#define pthread_setspecific test_set
#define pthread_key_create test_key_create
#include "java25/probe/emutls_alloc.cpp"
#undef malloc
#undef free
#undef mmap
#undef munmap
#undef pthread_setspecific
#undef pthread_key_create
void* make_array(int magic){
 auto*w=(uintptr_t*)ps5_emutls_malloc(128);assert(w);memset(w,0,128);w[1]=14;
 void*raw=ps5_emutls_malloc(64);assert(raw);void*aligned=(char*)raw+16;((void**)aligned)[-1]=raw;*(int*)aligned=magic;w[2]=(uintptr_t)aligned;return w;
}
void check(void*p,int magic){assert(p);auto*w=(uintptr_t*)p;assert(*(int*)w[2]==magic);}
void normal_destructor(void*p){++destroyed;release_retired_array(p);}
void late_destructor(void*){check(ps5_emutls_getspecific(key),71);++after_return;}
void* worker(void*arg){
 int magic=(int)(uintptr_t)arg;assert(ps5_emutls_getspecific(key)==nullptr);
 void* p=make_array(magic);errno=EDOM;assert(ps5_emutls_setspecific(key,p)==0&&errno==EDOM);
 // Repeated compiler-rt lookups must retain this exact array without allocating.
 int live=maps;for(int i=0;i<1000;++i){assert(ps5_emutls_getspecific(key)==p);check(p,magic);}assert(maps==live||magic!=71);
 if(magic==71)assert(::pthread_setspecific(late_key,(void*)1)==0);
 return (void*)17;
}
void* stale_native_worker(void*){
 assert(ps5_emutls_getspecific(key)==nullptr);deny_set=false;
 void*p=make_array(92);assert(ps5_emutls_setspecific(key,p)==0);void* q=make_array(93);
 // Native key still points to p, but compiler-rt's reallocation frees it first.
 release_retired_array(p);deny_set=true;assert(ps5_emutls_setspecific(key,q)==0);check(ps5_emutls_getspecific(key),93);return nullptr;
}
int main(){
 assert(ps5_emutls_key_create(&key,normal_destructor)==0);assert(::pthread_key_create(&late_key,late_destructor)==0);
 pthread_t t;void*answer=nullptr;
 // Refused key registration: retain until native destructors have really run.
 assert(__wrap_pthread_create(&t,nullptr,worker,(void*)71)==0);assert(__wrap_pthread_join(t,&answer)==0&&answer==(void*)17);assert(after_return==1&&destroyed==0&&!maps&&!heaps);
 // Native destructor is still used when registration works.
 deny_set=false;assert(__wrap_pthread_create(&t,nullptr,worker,(void*)72)==0);assert(__wrap_pthread_join(t,nullptr)==0);assert(destroyed==1&&!maps);
 // A stale native destructor argument must never free a superseded array.
 assert(__wrap_pthread_create(&t,nullptr,stale_native_worker,nullptr)==0);assert(__wrap_pthread_join(t,nullptr)==0);assert(destroyed==2&&!maps);
 // A false-success setter also retains the canonical value.
 deny_set=false;false_success=true;assert(__wrap_pthread_create(&t,nullptr,worker,(void*)73)==0);assert(__wrap_pthread_join(t,nullptr)==0);assert(!maps);false_success=false;deny_set=true;
 // Concurrent isolation followed by joins/reused identities; no retired maps.
 for(int batch=0;batch<100;++batch){pthread_t threads[8];for(int i=0;i<8;++i)assert(__wrap_pthread_create(&threads[i],nullptr,worker,(void*)(uintptr_t)(100+i))==0);for(auto th:threads)assert(__wrap_pthread_join(th,nullptr)==0);assert(!maps&&!heaps);}
 // Reused native identities with a new generation reject stale join cleanup.
 ps5::emutls_keys::Registry<4> registry{};void*old=nullptr;assert(registry.begin(16,&old));auto g=registry.generation(16);int a=1,b=2;assert(registry.set(16,&a));assert(registry.begin(16,&old)&&old==&a);assert(registry.set(16,&b));assert(!registry.take(16,g)&&registry.get(16)==&b);
 for(uintptr_t k:{80u,144u,208u})assert(registry.set(k,&a));assert(!registry.set(272,&a));assert(registry.get(16)==&b);
 // Create/context failure paths never run user code or leak a start slot.
 fail_create=true;assert(__wrap_pthread_create(&t,nullptr,worker,(void*)99)==EAGAIN);fail_create=false;for(auto&c:start_contexts)assert(c.busy==0);
 for(auto&c:start_contexts)c.busy=1;int before=creates;assert(__wrap_pthread_create(&t,nullptr,worker,(void*)99)==EAGAIN&&creates==before);for(auto&c:start_contexts)c.busy=0;
 // Failed join must not reclaim a still-owned canonical array.
 void*p=make_array(45);ps5_emutls_setspecific(key,p);fail_join=true;assert(__wrap_pthread_join(pthread_self(),nullptr)==EDEADLK);assert(ps5_emutls_getspecific(key)==p);fail_join=false;emutls_destructor(nullptr);assert(!maps&&!heaps);
 // Explicit refused null hides a previously registered native value.
 deny_set=false;p=make_array(46);ps5_emutls_setspecific(key,p);deny_set=true;
 errno=ERANGE;assert(ps5_emutls_setspecific(key,nullptr)==0&&errno==ERANGE);assert(!ps5_emutls_getspecific(key));
 release_retired_array(p);emutls_destructor(p);assert(!maps&&!heaps);
 pthread_key_delete(key);pthread_key_delete(late_key);
 puts("PASS: actual adapter, refused/false-success/stale native keys,1000 stable lookups/thread,800 concurrent lifetimes, real destructor ordering, successful/failed join and create, generation reuse/exhaustion, complete mapped cleanup");
}
'''
p=W/'test.cpp';p.write_text(cpp)
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-pthread','-I',str(R),str(p),'-o',str(W/'test')],check=True)
subprocess.run([str(W/'test')],check=True)
