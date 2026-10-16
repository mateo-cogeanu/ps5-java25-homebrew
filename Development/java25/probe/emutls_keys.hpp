/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstdint>
#include <cstddef>
namespace ps5::emutls_keys {
// Canonical compiler-rt arrays, independent of allocating pthread key setters.
// Identity slots remain stable; generations prevent a late join from reclaiming
// a new thread after the platform reuses the same pthread identity.
template<size_t Capacity> struct Registry {
 struct Slot {uintptr_t owner; uint64_t generation; void* value;};
 Slot slots[Capacity];unsigned mutex;uint64_t sequence;
 void lock(){while(__atomic_exchange_n(&mutex,1u,__ATOMIC_ACQUIRE)){
  while(__atomic_load_n(&mutex,__ATOMIC_RELAXED)){
#if defined(__x86_64__)
   __asm__ volatile("pause");
#elif defined(__aarch64__)
   __asm__ volatile("yield");
#endif
  }
 }}
 void unlock(){__atomic_store_n(&mutex,0u,__ATOMIC_RELEASE);}
 Slot* find(uintptr_t key,bool create){
  if(!key)return nullptr;
  size_t start=(key>>4)%Capacity;
  for(size_t n=0;n<Capacity;++n){Slot*s=&slots[(start+n)%Capacity];
   if(s->owner==key)return s;
   if(!s->owner){if(!create)return nullptr;s->owner=key;s->generation=++sequence;return s;}
  }
  return nullptr;
 }
 bool set(uintptr_t key,void*value){lock();Slot*s=find(key,true);if(s)s->value=value;unlock();return s!=nullptr;}
 void* get(uintptr_t key){lock();Slot*s=find(key,false);void*v=s?s->value:nullptr;unlock();return v;}
 uint64_t generation(uintptr_t key){lock();Slot*s=find(key,false);uint64_t g=s?s->generation:0;unlock();return g;}
 // Only call begin after pthread_create succeeds: a reused identity then proves
 // that its old thread and native TLS destructors have finished.
 bool begin(uintptr_t key,void**retired){lock();Slot*s=find(key,true);if(s){*retired=s->value;s->value=nullptr;s->generation=++sequence;}unlock();return s!=nullptr;}
 void* take(uintptr_t key,uint64_t expected=0){lock();Slot*s=find(key,false);void*v=nullptr;
  if(s&&(!expected||s->generation==expected)){v=s->value;s->value=nullptr;}unlock();return v;
 }
};
}
