/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "emutls_alloc.hpp"
#include "../../.tools/java25/openjdk/src/hotspot/share/runtime/ps5StartupTrace.hpp"
extern "C" {
void* ps5_emutls_malloc(size_t count){
 void* p=ps5::emutls_alloc::allocate(count);
 if(p){
  auto* h=static_cast<ps5::emutls_alloc::Header*>(p)-1;
  if(h->block.mapped)ps5_vm_trace_values("EMUTLS: mapped allocation bytes=",count," mapped=",h->block.mapped," self=",(uintptr_t)pthread_self());
 }
 return p;
}
void* ps5_emutls_realloc(void* p,size_t count){return ps5::emutls_alloc::resize(p,count);}
void ps5_emutls_free(void* p){ps5::emutls_alloc::release(p);}
}
#include "emutls_keys.hpp"
#include <sched.h>
namespace {
ps5::emutls_keys::Registry<1024> emutls_registry{};
void (*original_emutls_destructor)(void*)=nullptr;
[[noreturn]] void emutls_capacity_failure(){ps5_vm_trace("FAIL: EMUTLS identity registry exhausted");std::abort();}
// Same SDK compiler-rt address-array ABI as the adapted emutls.o: two header
// words followed by aligned variable addresses. Reclaim only after actual
// thread death (successful join or native identity reuse), never at start-routine
// return, which would precede C++/pthread key destructors.
void release_retired_array(void* value){
 if(!value)return;
 auto* h=static_cast<ps5::emutls_alloc::Header*>(value)-1;
 auto* words=static_cast<uintptr_t*>(value);
 if(h->block.size<2*sizeof(uintptr_t)||words[1]>(h->block.size-2*sizeof(uintptr_t))/sizeof(void*)){
  ps5_vm_trace("FAIL: EMUTLS address array ABI mismatch");std::abort();
 }
 for(uintptr_t i=0;i<words[1];++i){void* p=reinterpret_cast<void*>(words[2+i]);if(p)ps5::emutls_alloc::release(static_cast<void**>(p)[-1]);}
 ps5::emutls_alloc::release(value);
}
void emutls_destructor(void*){
 const int saved=errno;
 // Ignore the platform argument, which can be stale after a refused resize.
 void* value=emutls_registry.take((uintptr_t)pthread_self());
 if(value&&original_emutls_destructor)original_emutls_destructor(value);
 errno=saved;
}
struct StartContext {unsigned busy,ready;void*(*function)(void*);void* argument;};
StartContext start_contexts[128]{};
void* emutls_thread_start(void* pointer){
 auto*c=static_cast<StartContext*>(pointer);
 while(!__atomic_load_n(&c->ready,__ATOMIC_ACQUIRE))sched_yield();
 auto function=c->function;void*argument=c->argument;
 __atomic_store_n(&c->busy,0u,__ATOMIC_RELEASE);
 return function(argument);
}
}
extern "C" {
int ps5_emutls_key_create(pthread_key_t* key,void(*destructor)(void*)){
 int result=pthread_key_create(key,emutls_destructor);
 if(!result)original_emutls_destructor=destructor;
 return result;
}
void* ps5_emutls_getspecific(pthread_key_t){
 const int saved=errno;void*p=emutls_registry.get((uintptr_t)pthread_self());errno=saved;return p;
}
int ps5_emutls_setspecific(pthread_key_t key,const void* value){
 const int saved=errno;
 if(!emutls_registry.set((uintptr_t)pthread_self(),const_cast<void*>(value)))emutls_capacity_failure();
 int result=pthread_setspecific(key,value);void* observed=pthread_getspecific(key);
 if(result||observed!=value){
  ps5_vm_trace_values("EMUTLS: retained key fallback self=",(uintptr_t)pthread_self()," result=",(unsigned)result," requested=",(uintptr_t)value);
 }
 errno=saved;return 0; // Canonical storage is established even if native setter refuses.
}
int __real_pthread_create(pthread_t*,const pthread_attr_t*,void*(*)(void*),void*);
int __real_pthread_join(pthread_t,void**);
int __wrap_pthread_create(pthread_t* thread,const pthread_attr_t*attr,void*(*function)(void*),void*argument){
 const int saved=errno;StartContext*context=nullptr;
 for(auto&c:start_contexts){unsigned expected=0;if(__atomic_compare_exchange_n(&c.busy,&expected,1u,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){context=&c;break;}}
 if(!context){errno=saved;return EAGAIN;}
 context->function=function;context->argument=argument;__atomic_store_n(&context->ready,0u,__ATOMIC_RELAXED);
 int result=__real_pthread_create(thread,attr,emutls_thread_start,context);int native_errno=errno;
 if(result)__atomic_store_n(&context->busy,0u,__ATOMIC_RELEASE);
 else{
  void*retired=nullptr;
  if(!emutls_registry.begin((uintptr_t)*thread,&retired))emutls_capacity_failure();
  release_retired_array(retired);
  __atomic_store_n(&context->ready,1u,__ATOMIC_RELEASE);
 }
 errno=native_errno;return result;
}
int __wrap_pthread_join(pthread_t thread,void**value){
 const uint64_t generation=emutls_registry.generation((uintptr_t)thread);
 int result=__real_pthread_join(thread,value);const int native_errno=errno;
 if(!result&&generation)release_retired_array(emutls_registry.take((uintptr_t)thread,generation));
 errno=native_errno;return result;
}
}
