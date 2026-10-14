/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <jni.h>
#ifndef PS5_EMBEDDED_FIXTURE
#define PS5_FIXTURE_LOAD JNI_OnLoad
#else
#define PS5_FIXTURE_LOAD ps5_ps5probe_JNI_OnLoad
#endif
extern "C" JNIEXPORT jint JNICALL PS5_FIXTURE_LOAD(JavaVM *vm,void *) {
 JNIEnv *env=nullptr;
 return vm->GetEnv(reinterpret_cast<void **>(&env),JNI_VERSION_1_8)==JNI_OK?JNI_VERSION_1_8:JNI_ERR;
}
extern "C" JNIEXPORT jlong JNICALL Java_ps5deps_NativeMath_sum(JNIEnv *env,jclass,jbyteArray array) {
 if(!array) {jclass type=env->FindClass("java/lang/NullPointerException");if(type)env->ThrowNew(type,"NativeMath.sum bytes");return 0;}
 jsize length=env->GetArrayLength(array);jlong result=0;jbyte chunk[256];
 for(jsize offset=0;offset<length;offset+=256) {
  jsize count=length-offset;if(count>256)count=256;
  env->GetByteArrayRegion(array,offset,count,chunk);if(env->ExceptionCheck())return 0;
  for(jsize i=0;i<count;i++)result+=static_cast<unsigned char>(chunk[i])*static_cast<jlong>(offset+i+1);
 }
 return result;
}
