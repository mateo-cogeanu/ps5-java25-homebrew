/* SPDX-License-Identifier: GPL-3.0-or-later */
// Scoped adapter for the pinned SDK netdb.o, never a process-wide allocator.
#include "emutls_alloc.hpp"
#include "../../.tools/java25/openjdk/src/hotspot/share/runtime/ps5StartupTrace.hpp"
#include <netdb.h>
#include <netinet/in.h>
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
int ps5_dns_pool_create(const char*n,int size,int flags){int r=sceNetPoolCreate(n,size,flags);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS pool create",r,e);return r;}
int ps5_dns_pool_destroy(int h){int r=sceNetPoolDestroy(h);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS pool destroy",r,e);return r;}
int ps5_dns_resolver_create(const char*n,int pool,int flags){int r=sceNetResolverCreate(n,pool,flags);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS resolver create",r,e);return r;}
int ps5_dns_resolver_destroy(int h){int r=sceNetResolverDestroy(h);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS resolver destroy",r,e);return r;}
int ps5_dns_ntoa(int h,const char*n,in_addr_t*a,int timeout,int retry,int flags){int r=sceNetResolverStartNtoa(h,n,a,timeout,retry,flags);int e=r<0?*sceNetErrnoLoc():0;dns_result("DNS resolver query",r,e);return r;}
int getaddrinfo(const char*n,const char*s,const struct addrinfo*h,struct addrinfo**r){
 int result=ps5_sdk_getaddrinfo(n,s,h,r),saved=errno;
 ps5_vm_trace_values("DNS getaddrinfo result=",(uint32_t)result," family=",h?(uint32_t)h->ai_family:0," flags=",h?(uint32_t)h->ai_flags:0);
 errno=saved;return result;
}
}
