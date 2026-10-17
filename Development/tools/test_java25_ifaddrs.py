#!/usr/bin/env python3
"""Exercise actual mapped getifaddrs fallback with injected kernel/libc results.

Uses host BSD route structure layouts and synthetic route records. The target
build checks target SDK compilation; neither proves PS5 route ABI/permissions.
"""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
header=root/'.tools/java25/openjdk/src/java.base/unix/native/libnet/ps5Ifaddrs.h'
work=root/'build/java25/ifaddrs-test';work.mkdir(parents=True,exist_ok=True)
p=work/'test.c'
p.write_text(r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/sysctl.h>
#include <sys/mman.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <net/route.h>
#include <netinet/in.h>
#include <ifaddrs.h>
static unsigned char wire[4096];static size_t wire_size;
static int native_error=ENOMEM, native_frees, calls, growth, query_error, oversized, map_calls, fail_map, live;
static struct ifaddrs native_list;
static int fake_getifaddrs(struct ifaddrs **out){if(!native_error){*out=&native_list;return 0;}errno=native_error;return -1;}
static void fake_freeifaddrs(struct ifaddrs *p){assert(p==&native_list);native_frees++;}
static int fake_sysctl(int *mib,unsigned n,void *out,size_t *size,void *v,size_t vl){
 assert(n==6&&mib[0]==CTL_NET&&mib[1]==PF_ROUTE&&mib[2]==0&&mib[3]==0&&mib[4]==NET_RT_IFLIST&&mib[5]==0&&!v&&!vl);calls++;
 if(query_error){errno=query_error;return -1;}
 if(!out){*size=oversized?2*1024*1024:wire_size;return 0;}
 if(growth){growth--;errno=ENOMEM;return -1;}
 assert(*size>=wire_size);memcpy(out,wire,wire_size);*size=wire_size;return 0;
}
static void *fake_map(void *p,size_t n,int prot,int flags,int fd,off_t offset){map_calls++;if(fail_map==map_calls){errno=ENOMEM;return MAP_FAILED;}void *v=mmap(p,n,prot,flags,fd,offset);if(v!=MAP_FAILED)live++;return v;}
static int fake_unmap(void *p,size_t n){int r=munmap(p,n);assert(r==0);live--;return r;}
#define getifaddrs fake_getifaddrs
#define freeifaddrs fake_freeifaddrs
#define sysctl fake_sysctl
#define mmap fake_map
#define munmap fake_unmap
''' + header.read_text() + r'''
#undef getifaddrs
#undef freeifaddrs
#undef sysctl
#undef mmap
#undef munmap
static size_t append_addr(const void *a,size_t n){size_t at=wire_size,rounded=(n+sizeof(long)-1)&~(sizeof(long)-1);memcpy(wire+at,a,n);memset(wire+at+n,0,rounded-n);wire_size+=rounded;return at;}
static void link_record(unsigned index,const char *name){
 size_t start=wire_size;struct if_msghdr info={0};info.ifm_version=RTM_VERSION;info.ifm_type=RTM_IFINFO;info.ifm_addrs=RTA_IFP;info.ifm_flags=IFF_UP|IFF_BROADCAST;info.ifm_index=index;
 memcpy(wire+wire_size,&info,sizeof info);wire_size+=sizeof info;
 struct sockaddr_dl link={0};link.sdl_family=AF_LINK;link.sdl_index=index;link.sdl_nlen=strlen(name);link.sdl_alen=6;link.sdl_len=offsetof(struct sockaddr_dl,sdl_data)+link.sdl_nlen+6;
 memcpy(link.sdl_data,name,link.sdl_nlen);memcpy(link.sdl_data+link.sdl_nlen,"\x02\x11\x22\x33\x44\x55",6);append_addr(&link,link.sdl_len);
 unsigned short length=wire_size-start;memcpy(wire+start,&length,2);
}
static void ip_record(unsigned index,int ipv6){
 size_t start=wire_size;struct ifa_msghdr h={0};h.ifam_version=RTM_VERSION;h.ifam_type=RTM_NEWADDR;h.ifam_index=index;h.ifam_addrs=RTA_NETMASK|RTA_IFA|(ipv6?0:RTA_BRD);
 memcpy(wire+wire_size,&h,sizeof h);wire_size+=sizeof h;
 struct sockaddr_in mask={0};mask.sin_len=8;mask.sin_addr.s_addr=0x00ffffff;append_addr(&mask,8);
 if(ipv6){struct sockaddr_in6 a={0};a.sin6_len=sizeof a;a.sin6_family=AF_INET6;a.sin6_scope_id=index;a.sin6_addr.s6_addr[0]=0xfe;a.sin6_addr.s6_addr[1]=0x80;a.sin6_addr.s6_addr[15]=1;append_addr(&a,sizeof a);}
 else{struct sockaddr_in a={0};a.sin_len=sizeof a;a.sin_family=AF_INET;a.sin_addr.s_addr=0x01020304;append_addr(&a,sizeof a);a.sin_addr.s_addr=0xffffffff;append_addr(&a,sizeof a);}
 unsigned short length=wire_size-start;memcpy(wire+start,&length,2);
}
static void fixture(void){wire_size=0;link_record(1,"lo0");ip_record(1,0);link_record(2,"eth0");ip_record(2,1);}
static void reset(void){assert(live==0);native_error=ENOMEM;calls=growth=query_error=oversized=map_calls=fail_map=0;}
int main(void){
 fixture();Ps5Ifaddrs storage={0};struct ifaddrs *list=NULL;
 reset();native_error=0;assert(ps5_getifaddrs(&list,&storage)==0&&list==&native_list&&calls==0);errno=EDOM;ps5_freeifaddrs(list,&storage);assert(native_frees==1&&errno==EDOM);
 reset();native_error=EPERM;assert(ps5_getifaddrs(&list,&storage)==-1&&errno==EPERM&&calls==0&&!list);
 reset();errno=EDOM;assert(ps5_getifaddrs(&list,&storage)==0&&errno==EDOM&&live==1&&calls==2);assert(!strcmp(list->ifa_name,"lo0")&&(list->ifa_flags&IFF_UP));
 struct sockaddr_dl *link=(void *)list->ifa_addr;assert(link->sdl_alen==6&&!memcmp(link->sdl_data+link->sdl_nlen,"\x02\x11\x22\x33\x44\x55",6));
 list=list->ifa_next;assert(list->ifa_addr->sa_family==AF_INET&&!strcmp(list->ifa_name,"lo0"));assert(((struct sockaddr_in *)list->ifa_netmask)->sin_addr.s_addr==0x00ffffff);assert(((unsigned char *)list->ifa_netmask)[15]==0);assert(((struct sockaddr_in *)list->ifa_dstaddr)->sin_addr.s_addr==0xffffffff);
 list=list->ifa_next->ifa_next;assert(list->ifa_addr->sa_family==AF_INET6&&!strcmp(list->ifa_name,"eth0"));assert(((struct sockaddr_in6 *)list->ifa_addr)->sin6_scope_id==2&&!list->ifa_next);ps5_freeifaddrs(list,&storage);assert(live==0);
 reset();growth=1;assert(!ps5_getifaddrs(&list,&storage)&&calls==4);ps5_freeifaddrs(list,&storage);
 reset();growth=6;assert(ps5_getifaddrs(&list,&storage)==-1&&errno==ENOMEM&&calls==10&&live==0);
 for(int i=1;i<=2;i++){reset();fail_map=i;assert(ps5_getifaddrs(&list,&storage)==-1&&errno==ENOMEM&&live==0);}
 reset();query_error=EACCES;assert(ps5_getifaddrs(&list,&storage)==-1&&errno==EACCES&&live==0);
 reset();oversized=1;assert(ps5_getifaddrs(&list,&storage)==-1&&errno==EOVERFLOW&&live==0);
 reset();wire_size=0;assert(!ps5_getifaddrs(&list,&storage)&&!list&&live==0);
 fixture();unsigned char original[4096];memcpy(original,wire,wire_size);size_t total=wire_size;
 /* Every truncated prefix and deterministic mutations exercise parser bounds.
  * Some prefixes are complete valid snapshots, so only memory safety asserted. */
 Ps5IfaddrNode nodes[32];size_t count;
 for(size_t i=0;i<=total;i++)(void)ps5_ifaddrs_parse(wire,i,nodes,32,&count);
 for(size_t i=0;i<total;i++){memcpy(wire,original,total);wire[i]^=0xff;(void)ps5_ifaddrs_parse(wire,total,nodes,32,&count);}
 memcpy(wire,original,total);assert(ps5_ifaddrs_parse(wire,total,nodes,0,&count)==-1&&errno==EINVAL);
 wire[2]=99;assert(ps5_ifaddrs_parse(wire,total,nodes,32,&count)==-1);reset();assert(ps5_getifaddrs(&list,&storage)==-1&&live==0&&!list);
 puts("PASS: actual fallback/parser; live-query IPv4/IPv6/link/flags/name/mask/broadcast/scope, native ownership, mapping failures, query errors/growth/retry cap, malformed/truncated records, cleanup; host BSD fixtures ASan/UBSan");
}
''')
subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p),'-o',str(work/'test')],check=True)
subprocess.run([str(work/'test')],check=True)
