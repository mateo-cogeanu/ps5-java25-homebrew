/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <jni.h>
#include <cstddef>
namespace ps5_lts_probe {
inline jint JNICALL multiply(JNIEnv*, jclass, jint a, jint b) { return a * b; }
// Returns zero on success, retaining the actual Java exception on failure.
inline int run(JNIEnv*env, const unsigned char*bytes, size_t size) {
 if(!bytes||size<8||size>65536||bytes[0]!=0xca||bytes[1]!=0xfe||bytes[2]!=0xba||bytes[3]!=0xbe||bytes[6]!=0||bytes[7]!=61)return -1701;
 jclass loader_class=env->FindClass("java/lang/ClassLoader");
 if(!loader_class)return -1702;
 jmethodID getter=env->GetStaticMethodID(loader_class,"getSystemClassLoader","()Ljava/lang/ClassLoader;");
 if(!getter){env->DeleteLocalRef(loader_class);return -1703;}
 jobject loader=env->CallStaticObjectMethod(loader_class,getter);
 env->DeleteLocalRef(loader_class);
 if(env->ExceptionCheck()||!loader)return -1704;
 jclass test=env->DefineClass("HelloLts",loader,reinterpret_cast<const jbyte*>(bytes),static_cast<jsize>(size));
 env->DeleteLocalRef(loader);
 if(!test||env->ExceptionCheck())return -1705;
 JNINativeMethod native{const_cast<char*>("nativeMultiply"),const_cast<char*>("(II)I"),reinterpret_cast<void*>(&multiply)};
 if(env->RegisterNatives(test,&native,1)!=JNI_OK){env->DeleteLocalRef(test);return -1706;}
 jmethodID method=env->GetStaticMethodID(test,"run","()I");
 if(!method){env->DeleteLocalRef(test);return -1707;}
 jint answer=env->CallStaticIntMethod(test,method);
 bool failed=env->ExceptionCheck();
 env->DeleteLocalRef(test);
 return failed?-1708:answer==17?0:-1709;
}
}
