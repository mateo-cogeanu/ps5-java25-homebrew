/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <sys/mman.h>
#include <unistd.h>
// Used only by the SDK compiler-rt emutls.o. Never mix these prefixed
// allocations with ordinary libc pointers. All three allocator refs are rebound.
namespace ps5::emutls_alloc {
union Header {
 struct {size_t size, mapped;} block;
 max_align_t alignment;
};
inline void* allocate(size_t count) {
 const int saved=errno;
 count=count?count:1;
 if(count>SIZE_MAX-sizeof(Header)){errno=ENOMEM;return nullptr;}
 const size_t total=count+sizeof(Header);
 Header* h=static_cast<Header*>(std::malloc(total));
 size_t mapped=0;
 if(!h){
  const long page=::sysconf(_SC_PAGESIZE);
  if(page<=0||total>SIZE_MAX-(size_t)page+1){errno=ENOMEM;return nullptr;}
  mapped=(total+(size_t)page-1)/(size_t)page*(size_t)page;
  void* p=::mmap(nullptr,mapped,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
  if(p==MAP_FAILED)return nullptr;
  h=static_cast<Header*>(p);
 }
 h->block={count,mapped};errno=saved;return h+1;
}
inline void release(void* p){
 if(!p)return;
 const int saved=errno;Header* h=static_cast<Header*>(p)-1;
 if(h->block.mapped)::munmap(h,h->block.mapped);else std::free(h);
 errno=saved;
}
inline void* resize(void* p,size_t count){
 if(!p)return allocate(count);
 if(!count){release(p);return nullptr;}
 Header* h=static_cast<Header*>(p)-1;
 if(count<=h->block.size){h->block.size=count;return p;}
 const int saved=errno;void* next=allocate(count);
 if(!next)return nullptr;
 std::memcpy(next,p,h->block.size);release(p);errno=saved;return next;
}
static_assert(sizeof(Header)%alignof(max_align_t)==0);
}
