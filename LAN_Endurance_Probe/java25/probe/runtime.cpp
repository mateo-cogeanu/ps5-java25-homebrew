/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "demo_renderer.hpp"
#include "pad.h"
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
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
constexpr int test_count=4;
const char *names[]={"Runtime page size","Condition variable wakeup","SIGUSR1 handler and delivery","Generated machine code: return 25"};
int status[test_count]{}; // 0 untested, 1 pass, -1 fail, 2 running
char messages[test_count][104]{};
int selected=0,pending=-1,pad=-1;
std::uint32_t previous=0;
pthread_mutex_t lock{};
pthread_cond_t condition{};
bool ready=false;
int worker_code=0;
std::atomic<int> worker_done{0};
volatile sig_atomic_t signal_seen=0;
void result(int i,int rc,const char *message) {
 status[i]=rc==0?1:-1;
 std::snprintf(messages[i],sizeof(messages[i]),"%s / code %08X",message,static_cast<unsigned>(rc));
}
void *worker(void *) {
 int rc=pthread_mutex_lock(&lock);
 if(rc==0) {
  ready=true;
  rc=pthread_cond_signal(&condition);
  int unlock=pthread_mutex_unlock(&lock);if(rc==0) rc=unlock;
 }
 worker_code=rc;
 worker_done.store(1,std::memory_order_release);
 return nullptr;
}
void signal_handler(int number,siginfo_t *,void *) {
 if(number==SIGUSR1) signal_seen=1;
}
void run_test(int i) {
 errno=0;
 if(i==0) {
  long size=sysconf(_SC_PAGESIZE);
  int rc=(size>0 && (size&(size-1))==0)?0:(errno?errno:-1101);
  char text[80]{};
  std::snprintf(text,sizeof(text),"OS page size: %ld bytes",size);
  result(i,rc,text);
 } else if(i==1) {
  int rc=pthread_mutex_init(&lock,nullptr);
  if(rc!=0) {result(i,rc,"Mutex init failed");return;}
  rc=pthread_cond_init(&condition,nullptr);
  if(rc!=0) {pthread_mutex_destroy(&lock);result(i,rc,"Condition init failed");return;}
  rc=pthread_mutex_lock(&lock);
  if(rc!=0) {pthread_cond_destroy(&condition);pthread_mutex_destroy(&lock);result(i,rc,"Mutex lock failed");return;}
  timespec deadline{};
  if(clock_gettime(CLOCK_REALTIME,&deadline)!=0) {
   int code=errno;pthread_mutex_unlock(&lock);pthread_cond_destroy(&condition);pthread_mutex_destroy(&lock);
   result(i,code,"Deadline clock failed");return;
  }
  deadline.tv_sec+=2;
  ready=false;worker_done=0;worker_code=0;
  pthread_t thread{};
  rc=pthread_create(&thread,nullptr,worker,nullptr);
  if(rc!=0) {pthread_mutex_unlock(&lock);pthread_cond_destroy(&condition);pthread_mutex_destroy(&lock);result(i,rc,"Thread create failed");return;}
  while(!ready && rc==0) rc=pthread_cond_timedwait(&condition,&lock,&deadline);
  int unlock=pthread_mutex_unlock(&lock);if(rc==0) rc=unlock;
  auto start=sceKernelGetProcessTime();
  while(!worker_done.load(std::memory_order_acquire) && sceKernelGetProcessTime()-start<2000000) sceKernelUsleep(1000);
  if(!worker_done.load(std::memory_order_acquire)) {
   pthread_detach(thread);result(i,rc?rc:-1102,"Worker timeout; resources retained");return;
  }
  int join=pthread_join(thread,nullptr);if(rc==0) rc=join;if(rc==0) rc=worker_code;
  pthread_cond_destroy(&condition);pthread_mutex_destroy(&lock);
  result(i,rc,"Timed wait / signal / predicate / join");
 } else if(i==2) {
  struct sigaction action{},old_action{};
  sigset_t old_mask{},mask{};
  int rc=pthread_sigmask(SIG_SETMASK,nullptr,&old_mask);
  if(rc!=0) {result(i,rc,"Read signal mask failed");return;}
  mask=old_mask;sigdelset(&mask,SIGUSR1);
  action.sa_sigaction=signal_handler;action.sa_flags=SA_SIGINFO;sigemptyset(&action.sa_mask);
  if(sigaction(SIGUSR1,&action,&old_action)!=0) {result(i,errno,"Install handler failed");return;}
  rc=pthread_sigmask(SIG_SETMASK,&mask,nullptr);
  if(rc!=0) {sigaction(SIGUSR1,&old_action,nullptr);result(i,rc,"Unblock SIGUSR1 failed");return;}
  signal_seen=0;
  if(kill(getpid(),SIGUSR1)!=0) {
   int code=errno;pthread_sigmask(SIG_SETMASK,&old_mask,nullptr);sigaction(SIGUSR1,&old_action,nullptr);
   result(i,code,"Self-signal failed");return;
  }
  auto start=sceKernelGetProcessTime();
  while(!signal_seen && sceKernelGetProcessTime()-start<2000000) sceKernelUsleep(1000);
  if(!signal_seen) {
   // Keep our harmless handler installed if delivery is delayed.
   result(i,-1103,"Signal timeout; handler retained");return;
  }
  rc=pthread_sigmask(SIG_SETMASK,&old_mask,nullptr);
  if(sigaction(SIGUSR1,&old_action,nullptr)!=0 && rc==0) rc=errno;
  result(i,rc,"SA_SIGINFO self-signal, restore handler / mask");
 } else {
  long page_size=sysconf(_SC_PAGESIZE);
  if(page_size<=0) {result(i,errno?errno:-1101,"Page size unavailable");return;}
  size_t length=static_cast<size_t>(page_size);
  void *p=mmap(nullptr,length,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
  if(p==MAP_FAILED) {result(i,errno,"RW allocation failed");return;}
  // x86-64: mov eax, 25; ret. The page becomes RX before the call.
  const unsigned char code[]={0xb8,0x19,0x00,0x00,0x00,0xc3};
  std::memcpy(p,code,sizeof(code));
  if(mprotect(p,length,PROT_READ|PROT_EXEC)!=0) {
   int error=errno;munmap(p,length);result(i,error,"RW to RX failed");return;
  }
  __builtin___clear_cache(static_cast<char *>(p),static_cast<char *>(p)+sizeof(code));
  auto function=reinterpret_cast<int (*)()>(p);
  int value=function();
  int rc=value==25?0:-1104;
  if(munmap(p,length)!=0 && rc==0) rc=errno;
  result(i,rc,"Executed generated function; expected 25");
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
  if(pressed&0x10) {selected=(selected+test_count-1)%test_count;changed=true;}
  if(pressed&0x40) {selected=(selected+1)%test_count;changed=true;}
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
 c.label(100,64,"Java 25 - runtime probe",64,rgb(238,242,250));
 c.label(103,163,"Second milestone: VM mechanisms. This is not a JVM yet.",24,rgb(139,153,178));
 for(int i=0;i<test_count;++i) {
  int y=248+i*112;
  if(selected==i) c.rounded(95,y-4,1730,100,22,rgb(109,156,255));
  c.rounded(100,y,1720,92,19,rgb(25,34,51));
  c.label(124,y+8,names[i],30,rgb(238,242,250));
  c.label(125,y+52,messages[i][0]?messages[i]:"Select and press X to run this test.",20,rgb(139,153,178));
  c.label(1650,y+25,status[i]==1?"PASS":status[i]==-1?"FAIL":status[i]==2?"RUN":"--",24,status[i]==1?rgb(105,215,172):status[i]==-1?rgb(230,176,91):rgb(139,153,178));
 }
 c.label(103,954,"D-pad: select   X: run selected test   PS: close game",24,rgb(139,153,178));
 c.label(103,1004,"The final test executes six generated bytes. Report any crash at RUN.",20,rgb(139,153,178));
}
}
int main() {
 sceUserServiceInitialize(nullptr);std::int32_t user=-1;
 if(sceUserServiceGetInitialUser(&user)>=0 && scePadInit()>=0) pad=scePadOpen(user,0,0,nullptr);
 ps5::demo::run_ui(draw,update,"Java 25 runtime probe ready");
}
