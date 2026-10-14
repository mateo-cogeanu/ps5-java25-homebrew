#!/usr/bin/env python3
"""Real JNI regression for bundled class-path URLs with canonicalization denied."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
WORK=ROOT/'build/java25/system-classpath-test'
source=WORK/'src/jdk/internal/loader/URLClassPath.java';source.parent.mkdir(parents=True,exist_ok=True)
source.write_text((ROOT/'.tools/java25/openjdk/src/java.base/share/classes/jdk/internal/loader/URLClassPath.java').read_text())
patch=WORK/'patch';patch.mkdir(exist_ok=True)
subprocess.run([str(JDK/'bin/javac'),'--patch-module','java.base='+str(WORK/'src'),'-d',str(patch),str(source)],check=True)
program=r'''
#include <jni.h>
#include <cassert>
#include <cstdio>
#include <string>
int denied=0;
jstring deny(JNIEnv *env,jobject,jstring) {
 ++denied;env->ThrowNew(env->FindClass("java/io/IOException"),"Sandbox canonicalization denied");return nullptr;
}
int main(int argc,char **argv) {
 assert(argc==3);bool sandbox=std::string(argv[2])=="true";
 std::string patch="--patch-module=java.base="+std::string(argv[1]);
 std::string property="-Dsun.nio.fs.ps5Sandbox="+std::string(argv[2]);
 JavaVMOption opts[]={{patch.data(),nullptr},{property.data(),nullptr},{const_cast<char*>("-Xint"),nullptr}};
 JavaVMInitArgs args{};args.version=JNI_VERSION_24;args.nOptions=3;args.options=opts;
 JavaVM *vm=nullptr;JNIEnv *env=nullptr;assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void**>(&env),&args)==JNI_OK);
 jclass fs=env->FindClass("java/io/UnixFileSystem");assert(fs);
 JNINativeMethod hook={const_cast<char*>("canonicalize0"),const_cast<char*>("(Ljava/lang/String;)Ljava/lang/String;"),reinterpret_cast<void*>(&deny)};
 assert(env->RegisterNatives(fs,&hook,1)==JNI_OK);
 jclass ucp=env->FindClass("jdk/internal/loader/URLClassPath");
 jmethodID convert=env->GetStaticMethodID(ucp,"toFileURL","(Ljava/lang/String;)Ljava/net/URL;");assert(convert);
 auto url=env->CallStaticObjectMethod(ucp,convert,env->NewStringUTF("/app0/assets/java25/jars/application.jar"));
 assert(!env->ExceptionCheck());assert(sandbox?(url!=nullptr && denied==0):(url==nullptr && denied>0));
 int count=denied;
 for(const char *path:{"/app0/assets/java25/jars/../outside.jar","/tmp/outside.jar","relative.jar"}) {
  assert(!env->CallStaticObjectMethod(ucp,convert,env->NewStringUTF(path)));assert(!env->ExceptionCheck());
 }
 assert(denied==count+3);
 assert(vm->DestroyJavaVM()==JNI_OK);
 std::puts(sandbox?"PASS: bundled system-JAR URL survives denied canonicalization; other paths retain checks":"PASS: non-PS5 canonicalization failures retain normal behavior");
}
'''
p=WORK/'test-system-classpath.cpp';p.write_text(program);exe=WORK/'test-system-classpath'
subprocess.run(['/usr/bin/clang++','-std=c++20','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(p),'-L'+str(JDK/'lib/server'),'-ljvm','-Wl,-rpath,'+str(JDK/'lib/server'),'-o',str(exe)],check=True)
for flag in ['false','true']:subprocess.run([str(exe),str(patch),flag],check=True,timeout=30)
