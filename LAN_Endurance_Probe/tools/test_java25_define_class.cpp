/* SPDX-License-Identifier: GPL-3.0-or-later */
// Real host JVM integration; this is not PS5 execution evidence.
#include <jni.h>
#include <cassert>
#include <cstdio>
int main() {
 JavaVM* vm=nullptr;JNIEnv* env=nullptr;
 JavaVMOption options[]={{const_cast<char*>("-Xint"),nullptr},
 {const_cast<char*>("-Djava.class.path=/no/ps5/bootstrap/classes"),nullptr}};
 JavaVMInitArgs args{};args.version=JNI_VERSION_24;args.nOptions=2;args.options=options;
 assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void**>(&env),&args)==JNI_OK);
 assert(!env->FindClass("Hello25")&&env->ExceptionCheck());env->ExceptionClear();
 unsigned char bytes[64*1024];
 FILE* file=std::fopen("build/java25/startup-assets/java25/classes/Hello25.class","rb");assert(file);
 size_t size=std::fread(bytes,1,sizeof(bytes),file);assert(std::feof(file)&&!std::ferror(file)&&size>8);
 std::fclose(file);assert(bytes[6]==0&&bytes[7]==69);
 jclass loader_class=env->FindClass("java/lang/ClassLoader");assert(loader_class);
 jmethodID get_loader=env->GetStaticMethodID(loader_class,"getSystemClassLoader","()Ljava/lang/ClassLoader;");assert(get_loader);
 jobject loader=env->CallStaticObjectMethod(loader_class,get_loader);assert(loader&&!env->ExceptionCheck());
 jclass klass=env->DefineClass("Hello25",loader,reinterpret_cast<const jbyte*>(bytes),static_cast<jsize>(size));
 if(env->ExceptionCheck())env->ExceptionDescribe();assert(klass&&!env->ExceptionCheck());
 jmethodID main_method=env->GetStaticMethodID(klass,"main","([Ljava/lang/String;)V");assert(main_method);
 jclass string_class=env->FindClass("java/lang/String");assert(string_class);
 jobjectArray arguments=env->NewObjectArray(0,string_class,nullptr);assert(arguments);
 env->CallStaticVoidMethod(klass,main_method,arguments);
 if(env->ExceptionCheck())env->ExceptionDescribe();assert(!env->ExceptionCheck());
 env->DeleteLocalRef(arguments);env->DeleteLocalRef(string_class);env->DeleteLocalRef(klass);
 env->DeleteLocalRef(loader);env->DeleteLocalRef(loader_class);
 assert(vm->DestroyJavaVM()==JNI_OK);
 std::puts("PASS: unavailable class-path discovery, actual DefineClass/system loader, Hello25 Java thread and clean shutdown");
}
