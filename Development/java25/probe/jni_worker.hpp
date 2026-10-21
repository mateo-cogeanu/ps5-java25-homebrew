/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <atomic>
#include <cstddef>
#include <cerrno>
#include <pthread.h>
#include "jni.h"
#ifdef __PROSPERO__
#include <sys/mman.h>
#include <cstring>
extern "C" JNIEXPORT void* JNICALL JVM_PS5MapNativeThreadStack(size_t);
extern "C" JNIEXPORT int JNICALL JVM_PS5UnmapNativeMemory(void*,size_t);
#endif
namespace ps5::jni_worker {
// Main-thread ownership of prepare/start/join; callback owns its attached JNIEnv.
struct Job {
 using Callback=void (*)(JNIEnv *,void *);
 JavaVM *vm=nullptr;Callback callback=nullptr;void *context=nullptr;
 pthread_t thread{};std::atomic<bool> done{false};int error=0;bool started=false;
 const char* phase="idle";
#ifdef __PROSPERO__
 pthread_attr_t ordinary_attr{},direct_attr{};bool ordinary_valid=false,direct_valid=false;
 void* stack_memory=nullptr;size_t stack_bytes=0;
 // Cache attribute objects before VM pressure; never reuse active attributes.
 int prepare() {
  if(started||stack_memory)return EBUSY;
  phase="worker ordinary attribute init";
  int rc=ordinary_valid?0:pthread_attr_init(&ordinary_attr);if(rc)return rc;ordinary_valid=true;
  phase="worker direct attribute init";
  rc=direct_valid?0:pthread_attr_init(&direct_attr);if(rc)return rc;direct_valid=true;
  rc=pthread_attr_setdetachstate(&ordinary_attr,PTHREAD_CREATE_JOINABLE);if(rc)return rc;
  rc=pthread_attr_setdetachstate(&direct_attr,PTHREAD_CREATE_JOINABLE);if(rc)return rc;
  rc=pthread_attr_setguardsize(&direct_attr,0);if(rc)return rc;
  phase="worker attributes ready";return 0;
 }
 int release_stack(){
  if(!stack_memory)return 0;
  int rc=JVM_PS5UnmapNativeMemory(stack_memory,stack_bytes);
  if(!rc){stack_memory=nullptr;stack_bytes=0;} // Failed cleanup retains ownership.
  return rc;
 }
#else
 int prepare(){return started?EBUSY:0;}
#endif
 static void *entry(void *pointer) {
  auto &job=*static_cast<Job *>(pointer);JNIEnv *env=nullptr;
  JavaVMAttachArgs args{JNI_VERSION_1_8,const_cast<char *>("PS5-probe-worker"),nullptr};
  job.phase="worker AttachCurrentThread";
  job.error=job.vm->AttachCurrentThread(reinterpret_cast<void **>(&env),&args);
  if(job.error==JNI_OK){job.phase="worker callback";job.callback(env,job.context);job.phase="worker DetachCurrentThread";job.error=job.vm->DetachCurrentThread();}
  job.done.store(true,std::memory_order_release);return nullptr;
 }
 int start(JavaVM *target,Callback fn,void *data=nullptr,size_t stack_size=8*1024*1024) {
  if(started||!target||!fn)return EINVAL;
#ifdef __PROSPERO__
  if(stack_memory)return EBUSY;
#endif
  vm=target;callback=fn;context=data;error=0;done=false;
#ifdef __PROSPERO__
  int rc=prepare();if(rc)return rc;
  phase="worker ordinary stack size";rc=pthread_attr_setstacksize(&ordinary_attr,stack_size);if(rc)return rc;
  phase="worker ordinary pthread_create";errno=0;rc=pthread_create(&thread,&ordinary_attr,entry,this);int native_error=errno;
  if(rc==EAGAIN&&native_error==ENOMEM&&stack_size&&stack_size%16384==0&&stack_size<=8*1024*1024){
   phase="worker direct stack allocation";
   stack_memory=JVM_PS5MapNativeThreadStack(stack_size);
   if(stack_memory==MAP_FAILED){stack_memory=nullptr;return ENOMEM;}
   stack_bytes=stack_size;std::memset(stack_memory,0,stack_size);
   phase="worker direct stack attributes";rc=pthread_attr_setstack(&direct_attr,stack_memory,stack_size);
   if(!rc){phase="worker direct pthread_create";rc=pthread_create(&thread,&direct_attr,entry,this);}
   if(rc){int cleanup=release_stack();if(cleanup){phase="worker failed-create stack cleanup";return cleanup;}return rc;}
  }
  if(!rc)started=true;return rc;
#else
  phase="worker attribute init";pthread_attr_t attr;int rc=pthread_attr_init(&attr);if(rc)return rc;
  phase="worker stack size";rc=pthread_attr_setstacksize(&attr,stack_size);
  if(!rc){phase="worker pthread_create";rc=pthread_create(&thread,&attr,entry,this);}
  pthread_attr_destroy(&attr);if(!rc)started=true;return rc;
#endif
 }
 bool ready() const {return started&&done.load(std::memory_order_acquire);}
 int join() {
  if(!ready())return EBUSY;int rc=pthread_join(thread,nullptr);if(rc){phase="worker pthread_join";return rc;}
  started=false;
#ifdef __PROSPERO__
  rc=release_stack();if(rc){phase="worker joined stack cleanup";return rc;}
#endif
  return error;
 }
};
}
