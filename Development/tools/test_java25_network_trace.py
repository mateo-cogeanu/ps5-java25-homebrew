#!/usr/bin/env python3
"""Test actual probe callback with real host JNI and packaged networking bytecode."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
WORK=ROOT/'build/java25'
s=(ROOT/'java25/probe/network.cpp').read_text()
callback=s[s.index('void network_checkpoint('):s.index('int vm_print(')]
program=r'''
#include <jni.h>
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>
static std::vector<std::string> stages;
void log_stage(const char *stage){stages.emplace_back(stage);}
'''+callback+r'''
int main(int argc,char **argv){
 assert(argc==2);
 std::string path="-Djava.class.path="+std::string(argv[1]);
 JavaVMOption options[]={ {path.data(),nullptr},
  {const_cast<char*>("-Xint"),nullptr},
  {const_cast<char*>("-Djava.net.preferIPv4Stack=true"),nullptr},
  {const_cast<char*>("-Dps5.probe.networkTrace=true"),nullptr} };
 JavaVMInitArgs args{};args.version=JNI_VERSION_24;args.nOptions=4;args.options=options;
 JavaVM *vm=nullptr;JNIEnv *env=nullptr;
 assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void**>(&env),&args)==JNI_OK);
 jclass fixture=env->FindClass("Network25");assert(fixture);
 JNINativeMethod method={const_cast<char*>("checkpoint"),const_cast<char*>("(Ljava/lang/String;)V"),reinterpret_cast<void*>(&network_checkpoint)};
 assert(env->RegisterNatives(fixture,&method,1)==JNI_OK);
 jmethodID main=env->GetStaticMethodID(fixture,"main","([Ljava/lang/String;)V");assert(main);
 jclass strings=env->FindClass("java/lang/String");
 jobjectArray parameters=env->NewObjectArray(0,strings,nullptr);
 env->CallStaticVoidMethod(fixture,main,parameters);
 if(env->ExceptionCheck()){env->ExceptionDescribe();return 1;}
 assert((stages==std::vector<std::string>{"Network: numeric IPv4 loopback","Network: TCP client/server echo","Network: UDP two-way datagrams","Network: NIO channels and selector"}));
 assert(vm->DestroyJavaVM()==JNI_OK);
 std::puts("PASS: real JNI trace registration and four networking stage callbacks");
}
'''
path=WORK/'test-network-trace.cpp';path.write_text(program)
exe=WORK/'test-network-trace'
subprocess.run(['/usr/bin/clang++','-std=c++20','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(path),
                '-L'+str(JDK/'lib/server'),'-ljvm','-Wl,-rpath,'+str(JDK/'lib/server'),'-o',str(exe)],check=True)
subprocess.run([str(exe),str(WORK/'network-assets/java25/classes')],check=True,timeout=60)
