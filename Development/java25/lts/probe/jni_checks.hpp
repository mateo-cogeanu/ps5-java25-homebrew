/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <jni.h>
#include <cstddef>
namespace ps5_lts_probe {
inline jint JNICALL multiply(JNIEnv*, jclass, jint a, jint b) { return a * b; }
// Returns zero on success, retaining the actual Java exception on failure.
inline int run(JNIEnv*env, const unsigned char*bytes, size_t size,
               void(*trace)(const char*)=nullptr, int(*on_class)(JNIEnv*,jclass)=nullptr) {
 if(!bytes||size<8||size>65536||bytes[0]!=0xca||bytes[1]!=0xfe||bytes[2]!=0xba||bytes[3]!=0xbe||bytes[6]!=0||bytes[7]!=61)return -1701;
 if(trace)trace("JNI: find ClassLoader");
 jclass loader_class=env->FindClass("java/lang/ClassLoader");
 if(!loader_class)return -1702;
 if(trace)trace("JNI: get system loader method");
 jmethodID getter=env->GetStaticMethodID(loader_class,"getSystemClassLoader","()Ljava/lang/ClassLoader;");
 if(!getter){env->DeleteLocalRef(loader_class);return -1703;}
 if(trace)trace("JNI: obtain system loader");
 jobject loader=env->CallStaticObjectMethod(loader_class,getter);
 env->DeleteLocalRef(loader_class);
 if(env->ExceptionCheck()||!loader)return -1704;
 if(trace)trace("JNI: define consumer probe class");
 jclass test=env->DefineClass("HelloLts",loader,reinterpret_cast<const jbyte*>(bytes),static_cast<jsize>(size));
 env->DeleteLocalRef(loader);
 if(!test||env->ExceptionCheck())return -1705;
 if(trace)trace("JNI: register original multiply");
 JNINativeMethod native{const_cast<char*>("nativeMultiply"),const_cast<char*>("(II)I"),reinterpret_cast<void*>(&multiply)};
 if(env->RegisterNatives(test,&native,1)!=JNI_OK){env->DeleteLocalRef(test);return -1706;}
 if(trace)trace("JNI: resolve consumer run method");
 if(trace&&on_class)trace("JNI: register consumer diagnostic native");
 if(on_class){int rc=on_class(env,test);if(rc){env->DeleteLocalRef(test);return rc;}}
 jmethodID method=env->GetStaticMethodID(test,"run","()I");
 if(!method){env->DeleteLocalRef(test);return -1707;}
 if(trace)trace("JNI: invoke consumer run");
 jint answer=env->CallStaticIntMethod(test,method);
 if(trace)trace("JNI: consumer run returned");
 bool failed=env->ExceptionCheck();
 env->DeleteLocalRef(test);
 return failed?-1708:answer==17?0:-1709;
}
}
