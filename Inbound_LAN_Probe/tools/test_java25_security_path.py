#!/usr/bin/env python3
"""Real host JNI regression: deny realpath, exercise the patched Security class."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
WORK=ROOT/'build/java25/security-path-test'
source=WORK/'src/java/security/Security.java';source.parent.mkdir(parents=True,exist_ok=True)
source.write_text((ROOT/'.tools/java25/openjdk/src/java.base/share/classes/java/security/Security.java').read_text())
patch=WORK/'patch';patch.mkdir(exist_ok=True)
subprocess.run([str(JDK/'bin/javac'),'--patch-module','java.base='+str(WORK/'src'),'-d',str(patch),str(source)],check=True)
program=r'''
#include <jni.h>
#include <cassert>
#include <cstdio>
#include <string>
static int denied=0;
jbyteArray deny_realpath(JNIEnv *env,jclass,jlong) {
 ++denied;
 jclass error=env->FindClass("sun/nio/fs/UnixException");
 jmethodID constructor=env->GetMethodID(error,"<init>","(I)V");
 jobject exception=env->NewObject(error,constructor,1);
 env->Throw(static_cast<jthrowable>(exception));return nullptr;
}
int main(int argc,char **argv) {
 assert(argc==3);bool sandbox=std::string(argv[2])=="true";
 std::string patch="--patch-module=java.base="+std::string(argv[1]);
 std::string policy="-Dsun.nio.fs.ps5Sandbox="+std::string(argv[2]);
 JavaVMOption opts[]={{patch.data(),nullptr},{policy.data(),nullptr},{const_cast<char*>("-Xint"),nullptr}};
 JavaVMInitArgs args{};args.version=JNI_VERSION_24;args.nOptions=3;args.options=opts;
 JavaVM *vm=nullptr;JNIEnv *env=nullptr;
 assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void**>(&env),&args)==JNI_OK);
 jclass dispatcher=env->FindClass("sun/nio/fs/UnixNativeDispatcher");assert(dispatcher);
 JNINativeMethod hook={const_cast<char*>("realpath0"),const_cast<char*>("(J)[B"),reinterpret_cast<void*>(&deny_realpath)};
 assert(env->RegisterNatives(dispatcher,&hook,1)==JNI_OK);
 jclass security=env->FindClass("java/security/Security");
 jmethodID get=security&&!env->ExceptionCheck()?env->GetStaticMethodID(security,"getProperty","(Ljava/lang/String;)Ljava/lang/String;"):nullptr;
 jstring value=get&&!env->ExceptionCheck()?static_cast<jstring>(env->CallStaticObjectMethod(security,get,env->NewStringUTF("security.provider.1"))):nullptr;
 if(sandbox) {
  if(env->ExceptionCheck()) {env->ExceptionDescribe();return 1;}
  assert(value && denied==0);
  const char *utf=env->GetStringUTFChars(value,nullptr);
  assert(std::string(utf)=="SUN");env->ReleaseStringUTFChars(value,utf);
  // Extra-file loading still canonicalizes. No global realpath bypass.
  jclass loader=env->FindClass("java/security/Security$SecPropLoader");
  jmethodID load=env->GetStaticMethodID(loader,"loadExtraFromPath","(Ljava/lang/String;Ljava/security/Security$SecPropLoader$LoadingMode;)Ljava/lang/Exception;");
  jclass mode=env->FindClass("java/security/Security$SecPropLoader$LoadingMode");
  jfieldID append=env->GetStaticFieldID(mode,"APPEND","Ljava/security/Security$SecPropLoader$LoadingMode;");
  jclass system=env->FindClass("java/lang/System");
  jmethodID property=env->GetStaticMethodID(system,"getProperty","(Ljava/lang/String;)Ljava/lang/String;");
  jstring home=static_cast<jstring>(env->CallStaticObjectMethod(system,property,env->NewStringUTF("java.home")));
  const char *home_utf=env->GetStringUTFChars(home,nullptr);
  std::string extra=std::string(home_utf)+"/conf/net.properties";
  env->ReleaseStringUTFChars(home,home_utf);
  assert(load && append && !env->ExceptionCheck());
  jobject error=env->CallStaticObjectMethod(loader,load,env->NewStringUTF(extra.c_str()),env->GetStaticObjectField(mode,append));
  assert(env->ExceptionCheck() && !error && denied>0);
  env->ExceptionClear();
  std::puts("PASS: bundled master loads with realpath denied; extra config still rejects denial");
 } else {
  assert(env->ExceptionCheck() && denied>0);
  env->ExceptionClear();
  std::puts("PASS: normal policy retains the original realpath failure");
 }
 assert(vm->DestroyJavaVM()==JNI_OK);
}
'''
path=WORK/'test-security-path.cpp';path.write_text(program);exe=WORK/'test-security-path'
subprocess.run(['/usr/bin/clang++','-std=c++20','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(path),
 '-L'+str(JDK/'lib/server'),'-ljvm','-Wl,-rpath,'+str(JDK/'lib/server'),'-o',str(exe)],check=True)
for enabled in ['false','true']:
 subprocess.run([str(exe),str(patch),enabled],check=True,timeout=30)
