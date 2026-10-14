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
#include "jni.h"
using Initializer=void (*)();
extern "C" Initializer __jvm_init_array_start[],__jvm_init_array_end[];
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
constexpr int test_count=3;
const char *names[]={"Initialize embedded HotSpot constructors","JNI defaults: latest API in this JDK 25 build","JNI VM registry: expect zero before startup"};
int status[test_count]{}; // 0 untested, 1 pass, -1 fail, 2 running
char messages[test_count][104]{};
int selected=0,pending=-1,pad=-1;
std::uint32_t previous=0;
bool initialized=false;
void result(int i,int rc,const char *message) {
 status[i]=rc==0?1:-1;
 std::snprintf(messages[i],sizeof(messages[i]),"%s / code %08X",message,static_cast<unsigned>(rc));
}
void run_test(int i) {
 if(i==0) {
  size_t count=0;
  for(auto *fn=__jvm_init_array_start;fn!=__jvm_init_array_end;++fn) {if(*fn) {(*fn)();++count;}}
  initialized=true;
  char text[80]{};std::snprintf(text,sizeof(text),"Ran %zu real HotSpot static constructors",count);
  result(i,0,text);
 } else if(!initialized) {
  result(i,-1201,"Run constructors first, then relaunch to retry");
 } else if(i==1) {
  JavaVMInitArgs args{};args.version=JNI_VERSION_24;
  int rc=JNI_GetDefaultJavaVMInitArgs(&args);
  result(i,rc,"Real JDK 25 JNI defaults, JNI_VERSION_24");
 } else {
  JavaVM *vm=nullptr;jsize count=-1;
  int rc=JNI_GetCreatedJavaVMs(&vm,1,&count);
  if(rc==JNI_OK && count!=0) rc=-1202;
  result(i,rc,"Real JNI_GetCreatedJavaVMs, zero VMs expected");
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
 c.label(100,64,"Java 25 - embedded HotSpot",64,rgb(238,242,250));
 c.label(103,163,"Real compiled JVM code. Setup APIs only; Java execution comes next.",24,rgb(139,153,178));
 for(int i=0;i<test_count;++i) {
  int y=248+i*112;
  if(selected==i) c.rounded(95,y-4,1730,100,22,rgb(109,156,255));
  c.rounded(100,y,1720,92,19,rgb(25,34,51));
  c.label(124,y+8,names[i],30,rgb(238,242,250));
  c.label(125,y+52,messages[i][0]?messages[i]:"Select and press X to run this test.",20,rgb(139,153,178));
  c.label(1650,y+25,status[i]==1?"PASS":status[i]==-1?"FAIL":status[i]==2?"RUN":"--",24,status[i]==1?rgb(105,215,172):status[i]==-1?rgb(230,176,91):rgb(139,153,178));
 }
 c.label(103,954,"D-pad: select   X: run selected test   PS: close game",24,rgb(139,153,178));
 c.label(103,1004,"Run top to bottom. Report any crash before UI or at a selected RUN.",20,rgb(139,153,178));
}
}
int main() {
 sceUserServiceInitialize(nullptr);std::int32_t user=-1;
 if(sceUserServiceGetInitialUser(&user)>=0 && scePadInit()>=0) pad=scePadOpen(user,0,0,nullptr);
 ps5::demo::run_ui(draw,update,"Embedded HotSpot setup ready");
}
