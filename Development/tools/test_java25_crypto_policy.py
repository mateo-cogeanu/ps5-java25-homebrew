#!/usr/bin/env python3
"""Real JNI regression: deny policy metadata and test actual JCE parsing."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
WORK=ROOT/'build/java25/crypto-policy-test'
source=WORK/'src/javax/crypto/JceSecurity.java';source.parent.mkdir(parents=True,exist_ok=True)
source.write_text((ROOT/'.tools/java25/openjdk/src/java.base/share/classes/javax/crypto/JceSecurity.java.template').read_text().replace('@@JCE_DEFAULT_POLICY@@','unlimited'))
patch=WORK/'patch';patch.mkdir(exist_ok=True)
subprocess.run([str(JDK/'bin/javac'),'--patch-module','java.base='+str(WORK/'src'),'-d',str(patch),str(source)],check=True)
classes=WORK/'classes';classes.mkdir(exist_ok=True)
probe=WORK/'CryptoProbe.java';probe.write_text('public class CryptoProbe { public static int check() throws Exception { return javax.crypto.Cipher.getMaxAllowedKeyLength("AES"); } }')
subprocess.run([str(JDK/'bin/javac'),'-d',str(classes),str(probe)],check=True)
program=r'''
#include <jni.h>
#include <dlfcn.h>
#include <cassert>
#include <cstdio>
#include <string>
static int metadata=0;
static jint (*real_stat)(JNIEnv*,jclass,jlong,jobject);
static jint (*real_access)(JNIEnv*,jclass,jlong,jint);
static jlong (*real_directory)(JNIEnv*,jclass,jlong);
static jint (*real_open)(JNIEnv*,jclass,jlong,jint,jint);
static bool policy_path(jlong path) {
 return std::string(reinterpret_cast<const char*>(path)).find("/conf/security/policy/")!=std::string::npos;
}
static void fail(JNIEnv *env,int code) {
 jclass type=env->FindClass("sun/nio/fs/UnixException");
 jmethodID constructor=env->GetMethodID(type,"<init>","(I)V");
 env->Throw(static_cast<jthrowable>(env->NewObject(type,constructor,code)));
}
jint stat_denied(JNIEnv *env,jclass type,jlong path,jobject attrs) {if(policy_path(path)){++metadata;return 1;}return real_stat(env,type,path,attrs);}
jint access_denied(JNIEnv *env,jclass type,jlong path,jint mode) {if(policy_path(path)){++metadata;return 1;}return real_access(env,type,path,mode);}
jlong directory_denied(JNIEnv *env,jclass type,jlong path) {if(policy_path(path)){++metadata;fail(env,1);return 0;}return real_directory(env,type,path);}
jint file_missing(JNIEnv *env,jclass type,jlong path,jint flags,jint mode) {if(policy_path(path)){fail(env,2);return -1;}return real_open(env,type,path,flags,mode);}
int main(int argc,char **argv) {
 assert(argc==6);
 void *library=dlopen(argv[4],RTLD_NOW);assert(library);
 real_stat=reinterpret_cast<decltype(real_stat)>(dlsym(library,"Java_sun_nio_fs_UnixNativeDispatcher_stat0"));
 real_access=reinterpret_cast<decltype(real_access)>(dlsym(library,"Java_sun_nio_fs_UnixNativeDispatcher_access0"));
 real_directory=reinterpret_cast<decltype(real_directory)>(dlsym(library,"Java_sun_nio_fs_UnixNativeDispatcher_opendir0"));
 real_open=reinterpret_cast<decltype(real_open)>(dlsym(library,"Java_sun_nio_fs_UnixNativeDispatcher_open0"));
 assert(real_stat&&real_access&&real_directory&&real_open);std::string mode=argv[2],policy=argv[3];
 std::string patch="--patch-module=java.base="+std::string(argv[1]);
 std::string sandbox="-Dsun.nio.fs.ps5Sandbox="+std::string(mode=="normal"?"false":"true");
 std::string classpath="-Djava.class.path="+std::string(argv[5]);
 JavaVMOption opts[]={{patch.data(),nullptr},{sandbox.data(),nullptr},{const_cast<char*>("-Xint"),nullptr},{classpath.data(),nullptr}};
 JavaVMInitArgs args{};args.version=JNI_VERSION_24;args.nOptions=4;args.options=opts;
 JavaVM *vm=nullptr;JNIEnv *env=nullptr;
 assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void**>(&env),&args)==JNI_OK);
 // Warm security configuration before denying metadata. Test only JCE loading.
 jclass security=env->FindClass("java/security/Security");
 jmethodID set=env->GetStaticMethodID(security,"setProperty","(Ljava/lang/String;Ljava/lang/String;)V");
 env->CallStaticVoidMethod(security,set,env->NewStringUTF("crypto.policy"),env->NewStringUTF(policy.c_str()));
 assert(!env->ExceptionCheck());
 jclass dispatcher=env->FindClass("sun/nio/fs/UnixNativeDispatcher");assert(dispatcher);
 JNINativeMethod hooks[]={
  {const_cast<char*>("stat0"),const_cast<char*>("(JLsun/nio/fs/UnixFileAttributes;)I"),reinterpret_cast<void*>(&stat_denied)},
  {const_cast<char*>("access0"),const_cast<char*>("(JI)I"),reinterpret_cast<void*>(&access_denied)},
  {const_cast<char*>("opendir0"),const_cast<char*>("(J)J"),reinterpret_cast<void*>(&directory_denied)}};
 assert(env->RegisterNatives(dispatcher,hooks,3)==JNI_OK);
 if(mode=="missing") {
  JNINativeMethod missing={const_cast<char*>("open0"),const_cast<char*>("(JII)I"),reinterpret_cast<void*>(&file_missing)};
  assert(env->RegisterNatives(dispatcher,&missing,1)==JNI_OK);
 }
 jclass cipher=env->FindClass("CryptoProbe");
 jmethodID max=cipher&&!env->ExceptionCheck()?env->GetStaticMethodID(cipher,"check","()I"):nullptr;
 jint length=max&&!env->ExceptionCheck()?env->CallStaticIntMethod(cipher,max):0;
 bool succeeds=mode=="sandbox"&&(policy=="unlimited"||policy=="limited");
 if(succeeds) {
  if(env->ExceptionCheck()){env->ExceptionDescribe();return 1;}
  assert(length==(policy=="limited"?128:2147483647));assert(metadata==0);
  std::printf("PASS: %s real policy parsed with metadata/enumeration denied, AES limit=%d\n",policy.c_str(),length);
 } else {
  assert(env->ExceptionCheck());env->ExceptionClear();
  if(mode=="normal")assert(metadata>0);
  std::printf("PASS: %s / %s rejects policy loading failure\n",mode.c_str(),policy.c_str());
 }
 assert(vm->DestroyJavaVM()==JNI_OK);
}
'''
path=WORK/'test-crypto-policy.cpp';path.write_text(program);exe=WORK/'test-crypto-policy'
subprocess.run(['/usr/bin/clang++','-std=c++20','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(path),'-L'+str(JDK/'lib/server'),'-ljvm','-Wl,-rpath,'+str(JDK/'lib/server'),'-o',str(exe)],check=True)
for mode,policy in [('normal','unlimited'),('sandbox','unlimited'),('sandbox','limited'),('missing','unlimited'),('sandbox','custom')]:
 subprocess.run([str(exe),str(patch),mode,policy,str(JDK/'lib/libnio.dylib'),str(classes)],check=True,timeout=30)
