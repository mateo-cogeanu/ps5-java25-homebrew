#!/usr/bin/env python3
"""Real host JVM worker with controlled PS5 native-stack failures and actual pthreads."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/jni-worker-direct-test';w.mkdir(exist_ok=True);jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
src=r'''
#include <pthread.h>
#include <sys/mman.h>
#include <cerrno>
#include <atomic>
#include <cassert>
#include <cstring>
#include <jni.h>
static int mode=0,init_calls=0,maps=0,unmaps=0,ordinary_calls=0,direct_calls=0;
static const pthread_attr_t* explicit_attr=nullptr;
static int fake_stack(pthread_attr_t*a,void*p,size_t n){explicit_attr=a;return pthread_attr_setstack(a,p,n);}
static bool late=false;static void* memory=nullptr;static size_t length=0;
static int fake_init(pthread_attr_t* a){++init_calls;if(late){errno=ENOMEM;return ENOMEM;}return pthread_attr_init(a);}
static int fake_create(pthread_t*t,const pthread_attr_t*a,void*(*f)(void*),void*p){
 void* stack=nullptr;size_t bytes=0;assert(!pthread_attr_getstack(a,&stack,&bytes));
 if(a==explicit_attr){++direct_calls;assert(stack==memory&&bytes==length);if(mode==4){errno=ENOMEM;return EAGAIN;}}
 else {++ordinary_calls;errno=mode==2?EACCES:ENOMEM;return mode==2?EINVAL:EAGAIN;}
 return pthread_create(t,a,f,p);
}
static bool refuse_join=false,refuse_release=false;
static int fake_join(pthread_t t,void**v){return refuse_join?EINVAL:pthread_join(t,v);}
extern "C" JNIEXPORT void* JNICALL JVM_PS5MapNativeMemory(size_t bytes){
 ++maps;if(mode==3){errno=ENOMEM;return MAP_FAILED;}assert(!memory);length=bytes;memory=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(memory!=MAP_FAILED);memset(memory,0x71,bytes);return memory;
}
extern "C" JNIEXPORT int JNICALL JVM_PS5UnmapNativeMemory(void*p,size_t bytes){assert(p==memory&&bytes==length);if(refuse_release)return EIO;++unmaps;int rc=munmap(p,bytes);memory=nullptr;return rc;}
#define __PROSPERO__ 1
#define pthread_attr_init fake_init
#define pthread_attr_setstack fake_stack
#define pthread_create fake_create
#define pthread_join fake_join
#include "jni_worker.hpp"
#undef pthread_attr_init
#undef pthread_attr_setstack
#undef pthread_create
#undef pthread_join
#include <thread>
#include <chrono>
struct Data{JNIEnv* main;bool called=false;};
static std::atomic<bool> tls_entered{false},tls_release{false},tls_done{false};
struct TLS{~TLS(){tls_entered=true;while(!tls_release)std::this_thread::yield();tls_done=true;}};
static void callback(JNIEnv*env,void*p){auto&d=*(Data*)p;assert(env&&env!=d.main);thread_local TLS tls;(void)tls;assert(env->FindClass("java/lang/String"));d.called=true;}
static void wait(ps5::jni_worker::Job&job){while(!job.ready())std::this_thread::yield();}
int main(){
 JavaVMInitArgs args{};args.version=JNI_VERSION_1_8;JavaVM*vm;JNIEnv*env;assert(JNI_CreateJavaVM(&vm,(void**)&env,&args)==JNI_OK);
 ps5::jni_worker::Job job;assert(!job.prepare()&&init_calls==2);late=true;
 Data data{env};mode=2;assert(job.start(vm,callback,&data)==EINVAL&&maps==0&&!job.started);mode=3;assert(job.start(vm,callback,&data)==ENOMEM&&!job.started&&!memory);
 mode=4;assert(job.start(vm,callback,&data)==EAGAIN&&!job.started&&!memory&&unmaps==1);
 mode=0;assert(!job.start(vm,callback,&data));wait(job);while(!tls_entered)std::this_thread::yield();assert(data.called&&memory&&unmaps==1&&!tls_done);
 std::atomic<bool> joined{false};std::thread joiner([&]{assert(!job.join());joined=true;});std::this_thread::sleep_for(std::chrono::milliseconds(20));assert(!joined&&memory&&unmaps==1);tls_release=true;joiner.join();assert(joined&&tls_done&&!memory&&unmaps==2&&init_calls==2);
 // Join failure cannot free or permit a new live worker; retry real join safely in fixture.
 assert(!job.start(vm,callback,&data));wait(job);refuse_join=true;assert(job.join()==EINVAL&&memory&&job.started);refuse_join=false;assert(!job.join()&&!memory);
 // Release failure preserves mapping and blocks reuse, even after thread death.
 assert(!job.start(vm,callback,&data));wait(job);refuse_release=true;assert(job.join()==EIO&&memory&&!job.started);assert(job.start(vm,callback,&data)==EBUSY);refuse_release=false;assert(!job.release_stack()&&!memory);
 assert(vm->DestroyJavaVM()==JNI_OK);assert(direct_calls==4&&ordinary_calls==6);
 puts("PASS actual PS5 worker header/real JVM attachment/callback/detach, early cached attrs under forced lateENOMEM,8MiBexplicitstack,join-through-TLS-beforefree,nonENOMEM exclusion,alloc/create/join/release faults and ownership retention");
}
'''
(w/'test.cpp').write_text(src)
exe=w/'check'
subprocess.run(['/usr/bin/clang++','-std=c++17','-pthread','-fsanitize=undefined','-I'+str(r/'java25/probe'),'-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(w/'test.cpp'),'-L'+str(jdk/'lib/server'),'-Wl,-rpath,'+str(jdk/'lib/server'),'-ljvm','-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True,timeout=60)
