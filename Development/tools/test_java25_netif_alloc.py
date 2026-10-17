#!/usr/bin/env python3
"""Run actual node allocator/addif/freeif bodies under forced failures.

Kernel flag/index queries and JNI OOM construction are narrow stubs. Native
storage/copies/ownership are real; this does not prove console availability.
"""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
base=root/'.tools/java25/openjdk/src/java.base/unix/native/libnet'
s=(base/'NetworkInterface.c').read_text()
header=(base/'ps5NetifAlloc.h').read_text()
macros=s[s.index('#define CHECKED_MALLOC_CLEANUP'):s.index('typedef struct _netaddr')]
types=s[s.index('typedef struct _netaddr'):s.index('} netif;')+len('} netif;')]
a=s.index('static void freeif(netif *ifs) {');free=s[a:s.index('\nstatic netif *addif(',a)]
a=s.rindex('static netif *addif(');add=s[a:s.index('\n/*',a)]
work=root/'build/java25/netif-alloc-test';work.mkdir(parents=True,exist_ok=True)
p=work/'test.c'
p.write_text(r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <net/if.h>
#include <netinet/in.h>
static int deny_heap,deny_maps,fail_map,map_calls,live_maps,live_heap;
static void *test_malloc(size_t n){if(deny_heap){errno=ENOMEM;return NULL;}void*p=malloc(n);assert(p);live_heap++;return p;}
static void test_free(void*p){if(p){live_heap--;assert(live_heap>=0);free(p);}}
static void *test_map(void*p,size_t n,int prot,int flags,int fd,off_t o){map_calls++;if(deny_maps||map_calls==fail_map){errno=ENOMEM;return MAP_FAILED;}assert(n%16384==0);void*v=mmap(p,n,prot,flags,fd,o);assert(v!=MAP_FAILED);live_maps++;return v;}
static int test_unmap(void*p,size_t n){assert(n%16384==0);int r=munmap(p,n);assert(!r);live_maps--;assert(live_maps>=0);return r;}
#define malloc test_malloc
#define free test_free
#define mmap test_map
#define munmap test_unmap
''' + header + r'''
#undef malloc
#undef free
#undef mmap
#undef munmap
typedef void JNIEnv;
static int pending;
static void JNU_ThrowOutOfMemoryError(JNIEnv *env,const char *message){(void)env;assert(!strcmp(message,"Native heap allocation failed"));pending=1;}
static int getFlags(int sock,const char *name,int *flags){(void)sock;(void)name;*flags=IFF_UP;return 0;}
static int getIndex(int sock,const char *name){(void)sock;(void)name;return 7;}
#define IFNAMESIZE IFNAMSIZ
#define NETIF_NOTE(phase,value) ((void)0)
#define NETIF_ALLOC(n) ps5_netif_allocate(n)
#define NETIF_FREE(p) ps5_netif_release(p)
''' + macros + types + free + add + r'''
static void reset(void){assert(!live_maps&&!live_heap);deny_heap=deny_maps=fail_map=map_calls=pending=0;}
static struct sockaddr_in address,broadcast;
static netif *one(netif *list,const char *name){return addif(NULL,0,name,list,(struct sockaddr*)&address,(struct sockaddr*)&broadcast,AF_INET,24);}
static void verify(netif *list){assert(list&&!strcmp(list->name,"eth0")&&list->index==7&&list->addr&&list->addr->mask==24);assert(!memcmp(list->addr->addr,&address,sizeof address));assert(!memcmp(list->addr->brdcast,&broadcast,sizeof broadcast));}
int main(void){
 address.sin_len=sizeof address;address.sin_family=AF_INET;address.sin_addr.s_addr=0x01020304;
 broadcast=address;broadcast.sin_addr.s_addr=0xffffffff;
 for(int backend=0;backend<2;backend++){
  reset();deny_heap=backend;deny_maps=!backend;errno=EDOM;
  netif *list=one(NULL,"eth0");assert(!pending&&errno==EDOM);verify(list);
  list=one(list,"eth0");assert(!pending&&list->addr->next);
  struct sockaddr_in6 v6={0};v6.sin6_len=sizeof v6;v6.sin6_family=AF_INET6;v6.sin6_scope_id=7;v6.sin6_addr.s6_addr[15]=1;
  list=addif(NULL,0,"eth0",list,(struct sockaddr*)&v6,NULL,AF_INET6,64);assert(!pending&&list->addr->family==AF_INET6&&!list->addr->brdcast&&list->addr->mask==64);assert(!memcmp(list->addr->addr,&v6,sizeof v6));errno=ERANGE;freeif(list);assert(errno==ERANGE&&!live_maps&&!live_heap);
 }
 reset();netif *list=one(NULL,"eth0");deny_heap=1;list=one(list,"eth0");assert(live_maps&&live_heap);freeif(list);assert(!live_maps&&!live_heap);
 /* Each virtual-interface allocation failure retains genuine OOM and frees
  * both returned partial lists and the first unlinked address on node failure. */
 for(int failed=1;failed<=4;failed++){
  reset();deny_heap=1;fail_map=failed;list=one(NULL,"eth0:1");assert(pending);freeif(list);assert(!live_maps&&!live_heap);
 }
 reset();deny_heap=1;list=one(NULL,"eth0:1");assert(!pending&&list&&list->childs&&list->childs->virtual&&list->childs->addr);assert(!strcmp(list->childs->name,"eth0:1"));freeif(list);
 reset();list=one(NULL,"eth0");netif *original=list;deny_heap=1;fail_map=map_calls+2;list=one(list,"eth1");assert(pending&&list==original&&live_maps==0);verify(list);freeif(list);
 reset();deny_heap=deny_maps=1;assert(!one(NULL,"eth0")&&pending&&!live_maps&&!live_heap);
 reset();deny_heap=1;
 size_t sizes[]={0,1,64,88,16384,32769};
 for(size_t i=0;i<sizeof sizes/sizeof sizes[0];i++){errno=EDOM;void *v=ps5_netif_allocate(sizes[i]);assert(v&&(uintptr_t)v%_Alignof(max_align_t)==0&&errno==EDOM);memset(v,0x5a,sizes[i]);errno=ERANGE;ps5_netif_release(v);assert(errno==ERANGE&&!live_maps);}
 int before=map_calls;assert(!ps5_netif_allocate(SIZE_MAX)&&errno==ENOMEM&&map_calls==before);ps5_netif_release(NULL);
 puts("PASS: actual allocator/addif/freeif ASan/UBSan libc/mapped/mixed ownership, real IPv4/IPv6/broadcast copies, virtual nodes, every partial failure/unlinked cleanup, genuine OOM, bounds/alignment/errno");
}
''')
subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(work/'test')],check=True)
subprocess.run([str(work/'test')],check=True)
