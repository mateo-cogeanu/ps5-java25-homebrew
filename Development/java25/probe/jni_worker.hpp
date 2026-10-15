/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <atomic>
#include <cstddef>
#include <cerrno>
#include <pthread.h>
#include "jni.h"
namespace ps5::jni_worker {
// Main-thread ownership of start/join; the callback owns only its attached JNIEnv.
struct Job {
 using Callback=void (*)(JNIEnv *,void *);
 JavaVM *vm=nullptr;Callback callback=nullptr;void *context=nullptr;
 pthread_t thread{};std::atomic<bool> done{false};int error=0;bool started=false;
 static void *entry(void *pointer) {
  auto &job=*static_cast<Job *>(pointer);JNIEnv *env=nullptr;
  JavaVMAttachArgs args{JNI_VERSION_1_8,const_cast<char *>("PS5-probe-worker"),nullptr};
  job.error=job.vm->AttachCurrentThread(reinterpret_cast<void **>(&env),&args);
  if(job.error==JNI_OK){job.callback(env,job.context);job.error=job.vm->DetachCurrentThread();}
  job.done.store(true,std::memory_order_release);return nullptr;
 }
 int start(JavaVM *target,Callback fn,void *data=nullptr,size_t stack_size=8*1024*1024) {
  if(started||!target||!fn)return EINVAL;
  vm=target;callback=fn;context=data;error=0;done=false;
  pthread_attr_t attr;int rc=pthread_attr_init(&attr);if(rc)return rc;
  rc=pthread_attr_setstacksize(&attr,stack_size);
  if(!rc)rc=pthread_create(&thread,&attr,entry,this);
  pthread_attr_destroy(&attr);if(!rc)started=true;return rc;
 }
 bool ready() const {return started&&done.load(std::memory_order_acquire);}
 int join() {if(!ready())return EBUSY;int rc=pthread_join(thread,nullptr);started=false;return rc?rc:error;}
};
}
