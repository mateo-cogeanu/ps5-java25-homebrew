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
// Preserve the SDK's key semantics, but expose refusals instead of silently
// concealing them behind a later abort or loss of emulated TLS state.
int ps5_emutls_setspecific(pthread_key_t key,const void* value){
 const int saved=errno;int result=pthread_setspecific(key,value);
 if(result||pthread_getspecific(key)!=value){
  ps5_vm_trace_values("EMUTLS: native key update refused self=",(uintptr_t)pthread_self()," result=",(unsigned)result," requested=",(uintptr_t)value);
 }
 errno=saved;return result;
}
}
