#!/usr/bin/env python3
"""Actual scoped DNS adapter and pinned SDK lookup/cleanup under ASan/UBSan.

Network calls are injected; this checks ownership/propagation, not PS5 DNS.
"""
from pathlib import Path
import subprocess,hashlib,urllib.request
r=Path(__file__).resolve().parents[1];w=r/'build/java25/netdb-test';w.mkdir(parents=True,exist_ok=True)
p=r/'build/java25/sdk-netdb-v042.c'
if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/ps5-payload-dev/sdk/v0.42/libc/netdb.c').read())
assert hashlib.sha256(p.read_bytes()).hexdigest()=='e98d7906f4095125893e83efa1311a16873b1d193fba06e965ae498987fbe723'
s=p.read_text()
def body(mark):
 a=s.index(mark);b=s.index('{',a);depth=1;i=b+1
 while depth:
  if s[i]=='{':depth+=1
  if s[i]=='}':depth-=1
  i+=1
 return s[a:i]
adapter=(r/'java25/probe/netdb_alloc.cpp').read_text();adapter='\n'.join(x for x in adapter.splitlines() if not x.startswith('#include'));adapter=adapter.replace('int getaddrinfo(','int test_getaddrinfo(')
source=r'''
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <cstdio>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/mman.h>
#include <unistd.h>
static std::atomic<bool> deny_heap{false},deny_map{false};
static std::atomic<int> heaps{0},maps{0},pool_live{0},resolver_live{0},fail_stage{0},map_count{0};
static int fail_map_n=0;static thread_local int net_error=0;
namespace std {inline void* injected_malloc(size_t n){if(deny_heap){errno=ENOMEM;return nullptr;}void*p=::malloc(n);if(p)heaps++;return p;}inline void injected_free(void*p){if(p)heaps--;::free(p);}}
void* test_mmap(void*p,size_t n,int prot,int flags,int fd,off_t off){int count=++map_count;if(deny_map||(fail_map_n&&count==fail_map_n)){errno=ENOMEM;return MAP_FAILED;}p=::mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED)maps++;return p;}
int test_munmap(void*p,size_t n){int e=::munmap(p,n);if(!e)maps--;return e;}
#define malloc injected_malloc
#define free injected_free
#define mmap test_mmap
#define munmap test_munmap
#include "java25/probe/emutls_alloc.hpp"
#undef malloc
#undef free
#undef mmap
#undef munmap
void ps5_vm_trace(const char*){errno=EINTR;}
void ps5_vm_trace_values(const char*,uintptr_t,const char*,uintptr_t,const char*,uintptr_t){errno=EINTR;}
extern "C" {
int* sceNetErrnoLoc(){return &net_error;}
int sceNetPoolCreate(const char*,int n,int f){assert(n==0x4000&&f==0);if(fail_stage==1){net_error=101;return -1;}pool_live++;return 11;}
int sceNetPoolDestroy(int p){assert(p==11);pool_live--;if(fail_stage==5){net_error=105;return -1;}return 0;}
int sceNetResolverCreate(const char*,int p,int f){assert(p==11&&f==0);if(fail_stage==2){net_error=102;return -1;}resolver_live++;return 12;}
int sceNetResolverDestroy(int h){assert(h==12);resolver_live--;if(fail_stage==4){net_error=104;return -1;}return 0;}
int sceNetResolverStartNtoa(int h,const char*n,in_addr_t*a,int t,int retry,int flags){assert(h==12&&n&&t==0&&retry==0&&flags==0);if(fail_stage==3){net_error=103;return -1;}*a=htonl(0xcb007109);return 0;}
}
''' +adapter+r'''
#define sceNetPoolCreate ps5_dns_pool_create
#define sceNetPoolDestroy ps5_dns_pool_destroy
#define sceNetResolverCreate ps5_dns_resolver_create
#define sceNetResolverDestroy ps5_dns_resolver_destroy
#define sceNetResolverStartNtoa ps5_dns_ntoa
static int
'''+body('resolve_ntoa(').replace('h_errno','net_error')+r'''
#undef sceNetPoolCreate
#undef sceNetPoolDestroy
#undef sceNetResolverCreate
#undef sceNetResolverDestroy
#undef sceNetResolverStartNtoa
static int addrconfig(int){return 1;}
#define malloc ps5_dns_malloc
#define free ps5_dns_free
#define strdup ps5_dns_strdup
int
'''+body('getaddrinfo(').replace('getaddrinfo(','ps5_sdk_getaddrinfo(',1).replace('sock_addr=malloc(', 'sock_addr=(struct sockaddr_in*)malloc(').replace('info=malloc(', 'info=(struct addrinfo*)malloc(')+'\nvoid\n'+body('freeaddrinfo(').replace('freeaddrinfo(','test_freeaddrinfo(',1)+r'''
#undef malloc
#undef free
#undef strdup
void check(){struct addrinfo hints={};hints.ai_family=AF_UNSPEC;hints.ai_flags=AI_CANONNAME;struct addrinfo*res=nullptr;errno=EDOM;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==0);assert(res&&res->ai_family==AF_INET&&res->ai_canonname&&strcmp(res->ai_canonname,"unit.example")==0);assert(((struct sockaddr_in*)res->ai_addr)->sin_addr.s_addr==htonl(0xcb007109));assert(errno==EDOM);test_freeaddrinfo(res);assert(errno==EDOM);}
int main(){
 check();assert(!maps&&!heaps&&!pool_live&&!resolver_live);
 deny_heap=true;check();assert(!maps&&!heaps);
 for(int stage=1;stage<=5;stage++){fail_stage=stage;struct addrinfo hints={};hints.ai_flags=AI_CANONNAME;struct addrinfo*res=nullptr;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==EAI_FAIL&&!res);assert(!maps&&!heaps&&!pool_live&&!resolver_live);}
 fail_stage=0;deny_map=true;struct addrinfo hints={};hints.ai_flags=AI_CANONNAME;struct addrinfo*res=nullptr;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==EAI_MEMORY&&!res);deny_map=false;
 for(int n=1;n<=3;n++){map_count=0;fail_map_n=n;res=nullptr;int result=test_getaddrinfo("unit.example",nullptr,&hints,&res);if(n<3)assert(result==EAI_MEMORY&&!res);else{assert(result==0&&res&&!res->ai_canonname);test_freeaddrinfo(res);}assert(!maps&&!heaps);}
 fail_map_n=0;hints.ai_family=AF_INET6;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==EAI_FAMILY);
 assert(!ps5_dns_malloc(SIZE_MAX)&&errno==ENOMEM);ps5_dns_free(nullptr);
 std::vector<std::thread> threads;for(int i=0;i<8;i++)threads.emplace_back([]{for(int j=0;j<50;j++)check();});for(auto&t:threads)t.join();assert(!maps&&!heaps&&!pool_live&&!resolver_live);
 puts("PASS: actual SDK lookup/free and scoped adapter; libc/mapped results/canonical names, every partial/total allocation failure, resolver create/query/cleanup failures preserved, unsupported IPv6, errno, overflow and400 concurrent lookups with complete cleanup; ASan/UBSan. Network injected, not console proof.");
}
'''
cpp=w/'test.cpp';cpp.write_text(source)
subprocess.run(['clang++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-pthread','-I',str(r),str(cpp),'-o',str(w/'test')],check=True)
subprocess.run([str(w/'test')],check=True)
