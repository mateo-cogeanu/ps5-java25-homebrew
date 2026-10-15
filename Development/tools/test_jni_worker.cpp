// SPDX-License-Identifier: GPL-3.0-or-later
#include "jni_worker.hpp"
#include <cassert>
#include <chrono>
#include <cstdio>
#include <thread>
#include <vector>
struct Context {JNIEnv *main_env;const char *name;bool passed=false;};
static void invoke(JNIEnv *env,void *data) {
 auto &context=*static_cast<Context *>(data);
 assert(env && env!=context.main_env);
 JNIEnv *attached=nullptr;JavaVM *vm=nullptr;assert(env->GetJavaVM(&vm)==JNI_OK);
 assert(vm->GetEnv(reinterpret_cast<void **>(&attached),JNI_VERSION_1_8)==JNI_OK && attached==env);
 std::this_thread::sleep_for(std::chrono::milliseconds(100));
 jclass type=env->FindClass(context.name);
 if(type) {
  jmethodID method=env->GetStaticMethodID(type,"main","([Ljava/lang/String;)V");
  jclass string=env->FindClass("java/lang/String");
  if(method && string) {jobjectArray args=env->NewObjectArray(0,string,nullptr);if(args)env->CallStaticVoidMethod(type,method,args);}
 }
 context.passed=!env->ExceptionCheck();
 if(!context.passed){env->ExceptionDescribe();env->ExceptionClear();}
}
int main(int argc,char **argv) {
 assert(argc>=2);std::vector<JavaVMOption> options;
 for(int i=2;i<argc;++i)options.push_back({argv[i],nullptr});
 JavaVMInitArgs args{};args.version=JNI_VERSION_1_8;args.nOptions=options.size();args.options=options.data();
 JavaVM *vm=nullptr;JNIEnv *env=nullptr;assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void **>(&env),&args)==JNI_OK);
 Context context{env,argv[1]};ps5::jni_worker::Job job;
 assert(job.join()==EBUSY);assert(job.start(nullptr,invoke,&context)==EINVAL);
 assert(job.start(vm,nullptr,&context)==EINVAL);
 assert(job.start(vm,invoke,&context,1)!=0);
 assert(job.start(vm,invoke,&context)==0);assert(job.start(vm,invoke,&context)==EINVAL);
 unsigned ticks=0;
 while(!job.ready()){++ticks;std::this_thread::sleep_for(std::chrono::milliseconds(5));}
 assert(job.join()==0 && context.passed && ticks>1);
 JNIEnv *main_env=nullptr;assert(vm->GetEnv(reinterpret_cast<void **>(&main_env),JNI_VERSION_1_8)==JNI_OK && main_env==env);
 assert(env->FindClass("java/lang/String"));assert(vm->DestroyJavaVM()==JNI_OK);
 std::printf("PASS: worker attachment, distinct JNIEnv, main-loop ticks=%u, detach/join and main-thread VM destruction\n",ticks);
}
