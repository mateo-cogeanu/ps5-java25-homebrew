/* SPDX-License-Identifier: GPL-3.0-or-later */
// Scoped adapter for the pinned SDK netdb.o, never a process-wide allocator.
#include "emutls_alloc.hpp"
#include "../../.tools/java25/openjdk/src/hotspot/share/runtime/ps5StartupTrace.hpp"
#include <netdb.h>
#include <netinet/in.h>
#include <atomic>
#include <sched.h>
// The pinned SDK destroys its pool after every lookup. Keep one real pair for
// this app lifetime: late pool creation can fail after the VM consumes libc's
// heap. A lease spans pool-create through pool-destroy, including reverse DNS.
// Static atomics avoid late pthread mutex/TLS allocation. No answers are cached.
static std::atomic_flag dns_busy=ATOMIC_FLAG_INIT;
static int dns_pool=-1,dns_resolver=-1;
extern "C" {
int* sceNetErrnoLoc();
int sceNetPoolCreate(const char*,int,int);
int sceNetPoolDestroy(int);
int sceNetResolverCreate(const char*,int,int);
int sceNetResolverDestroy(int);
int sceNetResolverStartNtoa(int,const char*,in_addr_t*,int,int,int);
int ps5_sdk_getaddrinfo(const char*,const char*,const struct addrinfo*,struct addrinfo**);
void* ps5_dns_malloc(size_t n){
 void*p=ps5::emutls_alloc::allocate(n);int saved=errno;
 if(!p)ps5_vm_trace_values("DNS allocation failed bytes=",n," errno=",errno," reserved=",0);
 else {auto*h=static_cast<ps5::emutls_alloc::Header*>(p)-1;if(h->block.mapped)ps5_vm_trace_values("DNS mapped allocation bytes=",n," mapped=",h->block.mapped," reserved=",0);}
 errno=saved;return p;
}
void ps5_dns_free(void*p){ps5::emutls_alloc::release(p);}
char* ps5_dns_strdup(const char*s){size_t n=std::strlen(s);if(n==SIZE_MAX){errno=ENOMEM;return nullptr;}char*p=static_cast<char*>(ps5_dns_malloc(n+1));if(p)std::memcpy(p,s,n+1);return p;}
static void dns_result(const char*stage,int result,int error){
 int saved=errno;ps5_vm_trace(stage);ps5_vm_trace_values("DNS result=",(uint32_t)result," net_errno=",(uint32_t)error," errno=",saved);errno=saved;
}
int ps5_dns_pool_create(const char*n,int size,int flags){
 while(dns_busy.test_and_set(std::memory_order_acquire))sched_yield();
 int r=dns_pool;
 if(r<0){r=sceNetPoolCreate(n,size,flags);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS pool create",r,e);if(r>=0)dns_pool=r;}
 else dns_result("DNS pool reuse",r,0);
 if(r<0)dns_busy.clear(std::memory_order_release);
 return r;
}
int ps5_dns_pool_destroy(int h){
 // Only the pinned SDK calls these adapters, with its matching lease handle.
 if(h!=dns_pool)return sceNetPoolDestroy(h);
 dns_result("DNS pool lease release",0,0);dns_busy.clear(std::memory_order_release);return 0;
}
int ps5_dns_resolver_create(const char*n,int pool,int flags){
 if(pool!=dns_pool)return sceNetResolverCreate(n,pool,flags);
 int r=dns_resolver;
 if(r<0){r=sceNetResolverCreate(n,pool,flags);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS resolver create",r,e);if(r>=0)dns_resolver=r;}
 else dns_result("DNS resolver reuse",r,0);
 return r;
}
int ps5_dns_resolver_destroy(int h){
 if(h!=dns_resolver)return sceNetResolverDestroy(h);
 dns_result("DNS resolver lease release",0,0);return 0;
}
int ps5_dns_ntoa(int h,const char*n,in_addr_t*a,int timeout,int retry,int flags){
 // The pinned SDK uses synchronous default parameters and turns every DNS
 // error into EAI_FAIL. Retry only a completed timeout before that conversion
 // and before Java can negatively cache it. Preserve explicit caller policy.
 if(timeout!=0 || retry!=0 || flags!=0){
  int r=sceNetResolverStartNtoa(h,n,a,timeout,retry,flags);
  dns_result("DNS resolver query",r,r<0?*sceNetErrnoLoc():0);return r;
 }
 const unsigned attempts=3;
 const int saved_errno=errno,saved_net_error=*sceNetErrnoLoc();
 for(unsigned attempt=0;attempt<attempts;++attempt){
  in_addr_t answer=0;
  int r=sceNetResolverStartNtoa(h,n,&answer,timeout,retry,flags);
  int e=r<0?*sceNetErrnoLoc():0;
  dns_result("DNS resolver query",r,e);
  if(r>=0){*a=answer;errno=saved_errno;*sceNetErrnoLoc()=saved_net_error;return r;}
  // SCE_NET_RESOLVER_ETIMEDOUT=226; console returned0x804101E2/neterrno226.
  if(e!=226 || attempt+1==attempts)return r;
  ps5_vm_trace_values("DNS resolver timeout retry attempt=",attempt+2," max_attempts=",attempts," net_errno=",e);
  // Tracing must not change the failure state presented to the next call.
  errno=saved_errno;*sceNetErrnoLoc()=saved_net_error;
 }
 return -1; // The bounded loop always returns on success or its last failure.
}
// Create the same pinned SDK pair before VM allocation pressure, without a
// DNS query or cached answer. Release the normal lease on every path.
int ps5_dns_prepare(){
 int saved=errno;
 int pool=ps5_dns_pool_create("",0x4000,0);if(pool<0)return pool;
 int resolver=ps5_dns_resolver_create("",pool,0);
 int failure=resolver<0?*sceNetErrnoLoc():0;
 if(resolver>=0)ps5_dns_resolver_destroy(resolver);
 ps5_dns_pool_destroy(pool);
 if(resolver<0){*sceNetErrnoLoc()=failure;return resolver;}
 dns_result("DNS early pair ready",0,0);errno=saved;return 0;
}
int getaddrinfo(const char*n,const char*s,const struct addrinfo*h,struct addrinfo**r){
 int result=ps5_sdk_getaddrinfo(n,s,h,r),saved=errno;
 ps5_vm_trace_values("DNS getaddrinfo result=",(uint32_t)result," family=",h?(uint32_t)h->ai_family:0," flags=",h?(uint32_t)h->ai_flags:0);
 errno=saved;return result;
}
}
