/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "demo_renderer.hpp"
#include "pad.h"
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <pthread.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <time.h>
#include <unistd.h>
extern "C" std::uint64_t sceKernelGetProcessTime();
extern "C" int sceKernelUsleep(std::uint32_t);
namespace {
using ps5::demo::Canvas;
constexpr std::uint32_t rgb(unsigned r,unsigned g,unsigned b) {return 0xff000000u|r|(g<<8)|(b<<16);}
const char *names[]={"Monotonic clock","Virtual memory reserve / commit","Thread, mutex and thread-local storage","Loopback TCP socket","Sandbox file write / read","Executable-page permission (no execution)"};
int status[6]{}; // 0 untested, 1 pass, -1 fail, 2 running
char messages[6][104]{};
int selected=0,pending=-1,pad=-1;
std::uint32_t previous=0;
std::atomic<int> thread_done{0};
std::atomic<int> thread_result{0};
pthread_mutex_t lock{};
pthread_key_t key{};
std::uint64_t token=0x25252525;
void result(int i,int rc,const char *message) {
 status[i]=rc==0?1:-1;
 std::snprintf(messages[i],sizeof(messages[i]),"%s / code %08X",message,static_cast<unsigned>(rc));
}
void *worker(void *) {
 int rc=pthread_mutex_lock(&lock);
 if(rc==0) {
  rc=pthread_setspecific(key,&token);
  if(rc==0 && pthread_getspecific(key)!=&token) rc=-1001;
  int unlock=pthread_mutex_unlock(&lock);if(rc==0) rc=unlock;
 }
 thread_result.store(rc,std::memory_order_relaxed);
 thread_done.store(1,std::memory_order_release);
 return nullptr;
}
void run_test(int i) {
 errno=0;
 if(i==0) {
  timespec a{},b{};
  int rc=clock_gettime(CLOCK_MONOTONIC,&a);
  if(rc==0) {sceKernelUsleep(2000);rc=clock_gettime(CLOCK_MONOTONIC,&b);}
  if(rc==0 && (b.tv_sec<a.tv_sec || (b.tv_sec==a.tv_sec && b.tv_nsec<=a.tv_nsec))) rc=-1002;
  result(i,rc==0?0:errno?errno:rc,"CLOCK_MONOTONIC advances");
 } else if(i==1) {
  constexpr size_t length=64*1024*1024,page_size=16384;
  void *p=mmap(nullptr,length,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);
  if(p==MAP_FAILED) {result(i,errno,"64 MiB reserve failed");return;}
  int rc=mprotect(p,page_size,PROT_READ|PROT_WRITE);
  if(rc==0) {auto *word=static_cast<volatile std::uint64_t *>(p);*word=token;if(*word!=token) rc=-1003;}
  int code=rc==0?0:errno?errno:rc;
  int release=munmap(p,length);if(code==0 && release!=0) code=errno;
  result(i,code,"64 MiB reserve, 16 KiB commit, release");
 } else if(i==2) {
  int rc=pthread_mutex_init(&lock,nullptr);
  if(rc!=0) {result(i,rc,"Mutex init failed");return;}
  rc=pthread_key_create(&key,nullptr);
  if(rc!=0) {pthread_mutex_destroy(&lock);result(i,rc,"TLS key failed");return;}
  thread_done=0;thread_result=0;
  pthread_t thread{};
  rc=pthread_create(&thread,nullptr,worker,nullptr);
  if(rc!=0) {pthread_key_delete(key);pthread_mutex_destroy(&lock);result(i,rc,"Thread create failed");return;}
  auto start=sceKernelGetProcessTime();
  while(!thread_done.load(std::memory_order_acquire) && sceKernelGetProcessTime()-start<2000000) sceKernelUsleep(1000);
  if(!thread_done.load(std::memory_order_acquire)) {
   pthread_detach(thread);result(i,-1004,"Thread timeout, no repeat this launch");return;
  }
  rc=pthread_join(thread,nullptr);if(rc==0) rc=thread_result;
  pthread_key_delete(key);pthread_mutex_destroy(&lock);
  result(i,rc,"Create / mutex / TLS / join");
 } else if(i==3) {
  int fd=socket(AF_INET,SOCK_STREAM,0);
  if(fd<0) {result(i,errno,"Socket create failed");return;}
  sockaddr_in address{};address.sin_len=sizeof(address);address.sin_family=AF_INET;
  address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
  int rc=bind(fd,reinterpret_cast<sockaddr *>(&address),sizeof(address));
  if(rc==0) rc=listen(fd,1);
  int code=rc==0?0:errno;close(fd);result(i,code,"Bind / listen on loopback, then close");
 } else if(i==4) {
  const char *path="/download0/.java25-platform-probe.tmp";
  int fd=open(path,O_CREAT|O_EXCL|O_RDWR,0600);
  if(fd<0) {result(i,errno,"Exclusive file create failed");return;}
  const char text[]="PS5 Java 25 platform probe";
  char readback[sizeof(text)]{};
  int code=0;
  if(write(fd,text,sizeof(text))!=sizeof(text)) code=errno?errno:-1005;
  if(!code && lseek(fd,0,SEEK_SET)<0) code=errno;
  if(!code && read(fd,readback,sizeof(readback))!=sizeof(readback)) code=errno?errno:-1006;
  if(!code && std::memcmp(text,readback,sizeof(text))!=0) code=-1007;
  close(fd);if(unlink(path)!=0 && !code) code=errno;
  result(i,code,"Write / read / remove in download0");
 } else {
  constexpr size_t length=16384;
  void *p=mmap(nullptr,length,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
  if(p==MAP_FAILED) {result(i,errno,"RW page mapping failed");return;}
  int rc=mprotect(p,length,PROT_READ|PROT_EXEC);
  int code=rc==0?0:errno;munmap(p,length);
  result(i,code,"RW to RX permission only, no code executed");
 }
}
bool update() noexcept {
 if(pending>=0) {int i=pending;pending=-1;run_test(i);return true;}
 if(pad<0) return false;
 bool changed=false;
 PadSample batch[64]{};int count=scePadRead(pad,batch,64);
 if(count<0||count>64) return false;
 for(int i=0;i<count;++i) {
  auto buttons=batch[i].connected && !(batch[i].buttons&0x80000000u)?batch[i].buttons:0;
  auto pressed=buttons&~previous;previous=buttons;
  if(pressed&0x10) {selected=(selected+5)%6;changed=true;}
  if(pressed&0x40) {selected=(selected+1)%6;changed=true;}
  if((pressed&0x4000)&&status[selected]==0) {
   status[selected]=2;pending=selected;
   // Present RUN before calling the OS, and schedule only one test per batch.
   return true;
  }
 }
 return changed;
}
void draw(Canvas &c) noexcept {
 c.gradient(rgb(18,29,49),rgb(8,13,23));
 c.label(100,64,"Java 25 - platform probe",64,rgb(238,242,250));
 c.label(103,163,"First milestone: native OS capabilities. This is not a JVM yet.",24,rgb(139,153,178));
 for(int i=0;i<6;++i) {
  int y=248+i*112;
  if(selected==i) c.rounded(95,y-4,1730,100,22,rgb(109,156,255));
  c.rounded(100,y,1720,92,19,rgb(25,34,51));
  c.label(124,y+8,names[i],30,rgb(238,242,250));
  c.label(125,y+52,messages[i][0]?messages[i]:"Select and press X to run this test.",20,rgb(139,153,178));
  c.label(1650,y+25,status[i]==1?"PASS":status[i]==-1?"FAIL":status[i]==2?"RUN":"--",24,status[i]==1?rgb(105,215,172):status[i]==-1?rgb(230,176,91):rgb(139,153,178));
 }
 c.label(103,954,"D-pad: select   X: run selected test   PS: close game",24,rgb(139,153,178));
 c.label(103,1004,"Run one test at a time. Share the result screen and any crash stage.",20,rgb(139,153,178));
}
}
int main() {
 sceUserServiceInitialize(nullptr);std::int32_t user=-1;
 if(sceUserServiceGetInitialUser(&user)>=0 && scePadInit()>=0) pad=scePadOpen(user,0,0,nullptr);
 ps5::demo::run_ui(draw,update,"Java 25 platform probe ready");
}
