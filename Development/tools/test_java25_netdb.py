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
#include <sched.h>
static std::atomic<bool> deny_heap{false},deny_map{false};
static std::atomic<int> heaps{0},maps{0},pool_live{0},resolver_live{0},fail_stage{0},map_count{0};
static std::atomic<int> queries{0},active_queries{0},pool_creates{0},resolver_creates{0};
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
int sceNetPoolCreate(const char*,int n,int f){assert(n==0x4000&&f==0);pool_creates++;if(fail_stage==1){net_error=101;return -1;}pool_live++;return 11;}
int sceNetPoolDestroy(int p){assert(p==11);pool_live--;if(fail_stage==5){net_error=105;return -1;}return 0;}
int sceNetResolverCreate(const char*,int p,int f){assert(p==11&&f==0);resolver_creates++;if(fail_stage==2){net_error=102;return -1;}resolver_live++;return 12;}
int sceNetResolverDestroy(int h){assert(h==12);resolver_live--;if(fail_stage==4){net_error=104;return -1;}return 0;}
int sceNetResolverStartNtoa(int h,const char*n,in_addr_t*a,int t,int retry,int flags){assert(h==12&&n&&t==0&&retry==0&&flags==0);assert(++active_queries==1);queries++;std::this_thread::yield();if(fail_stage==3){active_queries--;net_error=103;return -1;}*a=htonl(0xcb007109+(queries%2));active_queries--;return 0;}
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
void check(){struct addrinfo hints={};hints.ai_family=AF_UNSPEC;hints.ai_flags=AI_CANONNAME;struct addrinfo*res=nullptr;errno=EDOM;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==0);assert(res&&res->ai_family==AF_INET&&res->ai_canonname&&strcmp(res->ai_canonname,"unit.example")==0);auto ip=((struct sockaddr_in*)res->ai_addr)->sin_addr.s_addr;assert(ip==htonl(0xcb007109)||ip==htonl(0xcb00710a));assert(errno==EDOM);test_freeaddrinfo(res);assert(errno==EDOM);}
// Test-only lifecycle reset: the app normally retains the pair until exit.
void reset_pair(){fail_stage=0;if(dns_resolver>=0){assert(sceNetResolverDestroy(dns_resolver)==0);dns_resolver=-1;}if(dns_pool>=0){assert(sceNetPoolDestroy(dns_pool)==0);dns_pool=-1;}assert(!pool_live&&!resolver_live);}
void failed_lookup(){struct addrinfo hints={};hints.ai_flags=AI_CANONNAME;struct addrinfo*res=nullptr;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==EAI_FAIL&&!res);assert(!maps&&!heaps);}
int main(){
 check();assert(!maps&&!heaps&&pool_live==1&&resolver_live==1);
 // Reproduce the console: create once early, deny every later pool/resolver
 // allocation, then resolve from other threads under libc allocation refusal.
 deny_heap=true;fail_stage=1;check();fail_stage=2;check();
 int pools=pool_creates, resolvers=resolver_creates, before=queries;
 std::vector<std::thread> threads;for(int i=0;i<8;i++)threads.emplace_back([]{for(int j=0;j<50;j++)check();});for(auto&t:threads)t.join();
 assert(pool_creates==pools&&resolver_creates==resolvers&&queries==before+400);
 assert(!maps&&!heaps&&pool_live==1&&resolver_live==1&&!active_queries);
 // Fresh query errors remain real, release the lease and permit recovery.
 fail_stage=3;failed_lookup();assert(net_error==103);fail_stage=0;check();
 reset_pair();fail_stage=1;failed_lookup();assert(!pool_live&&!resolver_live&&net_error==101);
 fail_stage=2;failed_lookup();assert(pool_live==1&&!resolver_live&&net_error==102);
 fail_stage=0;check();assert(pool_live==1&&resolver_live==1);
 // Output allocation failures must also leave the resolver lease usable.
 deny_map=true;struct addrinfo hints={};hints.ai_flags=AI_CANONNAME;struct addrinfo*res=nullptr;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==EAI_MEMORY&&!res);deny_map=false;
 for(int n=1;n<=3;n++){map_count=0;fail_map_n=n;res=nullptr;int result=test_getaddrinfo("unit.example",nullptr,&hints,&res);if(n<3)assert(result==EAI_MEMORY&&!res);else{assert(result==0&&res&&!res->ai_canonname);test_freeaddrinfo(res);}assert(!maps&&!heaps);}
 fail_map_n=0;check();hints.ai_family=AF_INET6;assert(test_getaddrinfo("unit.example",nullptr,&hints,&res)==EAI_FAMILY);
 assert(!ps5_dns_malloc(SIZE_MAX)&&errno==ENOMEM);ps5_dns_free(nullptr);
 reset_pair();assert(!maps&&!heaps);
 puts("PASS: actual SDK lookup/free and scoped adapter; one retained pair,400 serialized cross-thread fresh queries with late pool/resolver/heap allocation denied, changed answers, real query failure/recovery, partial initialization failure/retry, all result allocation failures, IPv4/IPv6 conversion allocation blocks, errno, overflow, unsupported IPv6 and matched cleanup; ASan/UBSan. Network injected, not console proof.");
}

'''
# Compile the actual JDK conversion-list allocation/link/free blocks as well.
node_tests = r"""
inline void* injected_malloc(size_t n){return std::injected_malloc(n);}
inline void injected_free(void*p){std::injected_free(p);}
#define malloc injected_malloc
#define free injected_free
#define mmap test_mmap
#define munmap test_munmap
#include ".tools/java25/openjdk/src/java.base/unix/native/libnet/ps5NetifAlloc.h"
#undef malloc
#undef free
#undef mmap
#undef munmap
#define DNS_NODE_ALLOC ps5_netif_allocate
#define DNS_NODE_FREE ps5_netif_release
"""
node_header=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnet/ps5NetifAlloc.h').read_text().replace('owner=malloc(', 'owner=(Ps5NetifAllocation*)malloc(').replace('owner=mmap(', 'owner=(Ps5NetifAllocation*)mmap(')
node_tests=node_tests.replace('#include ".tools/java25/openjdk/src/java.base/unix/native/libnet/ps5NetifAlloc.h"',node_header)
for number,filename in enumerate(['Inet4AddressImpl.c','Inet6AddressImpl.c']):
 text=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnet'/filename).read_text()
 a=text.index('            if (!skip) {',text.index('lookupAllHostAddr'))
 b=text.index('            iterator = iterator->ai_next;',a)
 block=text[a:b]
 a=text.index('    while (resNew != NULL)',b);b=text.index('    if (res != NULL)',a)
 cleanup=text[a:b]
 node_tests+='static int convert'+str(number)+r"""(struct addrinfo *res,bool &oom){
 int i=0,inetCount=0,inet6Count=0,skip=0;int *env=nullptr;void*ret=(void*)1;
 struct addrinfo *resNew=nullptr,*last=nullptr,*iterator=res;
 auto JNU_ThrowOutOfMemoryError=[&](int*,const char*){oom=true;};
 while(iterator){
"""+block+r"""
 iterator=iterator->ai_next;
 }
cleanupAndReturn:
"""+cleanup+' return ret?i:-1; }\n'
node_tests+=r"""
void check_conversion(){
 struct addrinfo entries[3]={};for(int n=0;n<3;n++){entries[n].ai_family=AF_INET;entries[n].ai_next=n<2?&entries[n+1]:nullptr;}
 for(auto convert:{convert0,convert1}){
  bool oom=false;deny_heap=false;assert(convert(entries,oom)==3&&!oom);assert(!heaps&&!maps);
  deny_heap=true;assert(convert(entries,oom)==3&&!oom);assert(!heaps&&!maps);
  deny_map=true;assert(convert(entries,oom)==-1&&oom);assert(!heaps&&!maps);deny_map=false;
  oom=false;map_count=0;fail_map_n=2;assert(convert(entries,oom)==-1&&oom);assert(!heaps&&!maps);fail_map_n=0;
 }
}
"""
source=source.replace('int main(){',node_tests+'\nint main(){\n check_conversion();deny_heap=false;')

cpp=w/'test.cpp';cpp.write_text(source)
subprocess.run(['clang++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-pthread','-I',str(r),str(cpp),'-o',str(w/'test')],check=True)
subprocess.run([str(w/'test')],check=True)
