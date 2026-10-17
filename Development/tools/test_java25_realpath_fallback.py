#!/usr/bin/env python3
"""Run actual JNI realpath and descriptor walk through a real host JVM and ZipFS."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/realpath-test';w.mkdir(parents=True,exist_ok=True);jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs/UnixNativeDispatcher.c').read_text();a=s.index('JNIEXPORT jbyteArray JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_realpath0');b=s.index('JNIEXPORT jint JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_access0',a);actual=s[a:b]
p=w/'native.c';p.write_text(r'''
#include <jni.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include "ps5Realpath.h"
static int mode=1;
static char* selected_realpath(const char*p,char*out){if(mode){errno=mode==1?EPERM:EACCES;return NULL;}return realpath(p,out);}
static void throwUnixException(JNIEnv*env,int error){jclass c=(*env)->FindClass(env,"sun/nio/fs/UnixException");jmethodID m=(*env)->GetMethodID(env,c,"<init>","(I)V");jobject e=(*env)->NewObject(env,c,m,error);(*env)->Throw(env,(jthrowable)e);}
#define jlong_to_ptr(n) ((void*)(intptr_t)(n))
#define __PROSPERO__ 1
#define realpath selected_realpath
'''+actual+r'''
#undef realpath
JNIEXPORT void JNICALL Java_RealpathTest_install(JNIEnv*env,jclass c){
 jclass type=(*env)->FindClass(env,"sun/nio/fs/UnixNativeDispatcher");
 JNINativeMethod hook={"realpath0","(J)[B",(void*)Java_sun_nio_fs_UnixNativeDispatcher_realpath0};
 if((*env)->RegisterNatives(env,type,&hook,1))abort();
}
JNIEXPORT void JNICALL Java_RealpathTest_mode(JNIEnv*env,jclass c,jint value){mode=value;}
''')
p.write_text(p.read_text().replace('#include <jni.h>','#include <jni.h>\n#include <stdint.h>'))
subprocess.run(['/usr/bin/clang','-std=c11','-O1','-g','-dynamiclib','-undefined','dynamic_lookup','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs'),str(p),'-o',str(w/'libtest.dylib')],check=True)
p=w/'RealpathTest.java';p.write_text(r'''
import java.nio.file.*;import java.util.*;import java.io.*;
public class RealpathTest {
 static native void install();static native void mode(int value);
 public static void main(String[]args)throws Exception {
  System.load(args[0]);Path root=Files.createTempDirectory("ps5-realpath-").toRealPath();Path file=Files.writeString(root.resolve("file"),"hello");Files.createDirectory(root.resolve("dir"));Files.createSymbolicLink(root.resolve("link"),Path.of("dir"));Files.createSymbolicLink(root.resolve("broken"),Path.of("missing"));
  install();
  try {
   if(!file.toRealPath().equals(file)||!root.resolve("dir/../file").toRealPath().equals(file)||!Path.of("/").toRealPath().equals(Path.of("/")))throw new AssertionError("canonical name");
   for(String path:List.of("missing","missing/../file","file/../file","link","link/../file","broken")){
    try{root.resolve(path).toRealPath();throw new AssertionError("accepted "+path);}catch(IOException expected){}
   }
   Path jar=root.resolve("assets.zip");try(var fs=FileSystems.newFileSystem(jar,Map.of("create","true"))){Files.writeString(fs.getPath("/asset"),"zip-ok");}
   try(var fs=FileSystems.newFileSystem(jar,Map.of())){if(!Files.readString(fs.getPath("/asset")).equals("zip-ok"))throw new AssertionError("ZipFS data");}
   for(int i=0;i<512;i++)if(!file.toRealPath().equals(file))throw new AssertionError("repeated lookup");
   mode(2);try{file.toRealPath();throw new AssertionError("non-EPERM error ignored");}catch(AccessDeniedException expected){}
   mode(0);if(!root.resolve("link").toRealPath().equals(root.resolve("dir")))throw new AssertionError("native link resolution altered");
   System.out.println("PASS: actual JNI realpath in host JVM; descriptor canonicalization, dot/parent, missing components, file/parent, symlink refusal, native links unchanged, repeated lookup and real ZipFS mount/read");
  }finally{mode(0);try(var paths=Files.walk(root)){for(Path path:paths.sorted(Comparator.reverseOrder()).toList())Files.delete(path);}}
 }
}''');subprocess.run([str(jdk/'bin/javac'),'-d',str(w),str(p)],check=True);subprocess.run([str(jdk/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-cp',str(w),'RealpathTest',str(w/'libtest.dylib')],check=True)
p=w/'walk.cpp';p.write_text(r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <filesystem>
#include <sys/stat.h>
#include <sys/resource.h>
#include "ps5Realpath.h"
int main(){
 char temporary[]="/tmp/ps5-path-walk-XXXXXX",rootbuf[PATH_MAX+1],out[PATH_MAX+1];assert(mkdtemp(temporary));assert(realpath(temporary,rootbuf));std::string root=rootbuf,file=root+"/file",dir=root+"/dir";
 assert(mkdir(dir.c_str(),0700)==0);int fd=open(file.c_str(),O_CREAT|O_WRONLY,0600);assert(fd>=0&&close(fd)==0);assert(symlink("dir",(root+"/link").c_str())==0);
 assert(ps5_descriptor_realpath((root+"/dir/../file").c_str(),out)==0&&out==file);
 assert(ps5_descriptor_realpath((file+"/").c_str(),out)==-1&&errno==ENOTDIR);
 assert(ps5_descriptor_realpath((root+"/missing/../file").c_str(),out)==-1&&errno==ENOENT);
 assert(ps5_descriptor_realpath((root+"/link/../file").c_str(),out)==-1);
 assert(ps5_descriptor_realpath("relative",out)==-1&&errno==EINVAL);
 assert(ps5_descriptor_realpath((root+"/"+std::string(NAME_MAX+1,'a')).c_str(),out)==-1&&errno==ENAMETOOLONG);
 assert(ps5_descriptor_realpath(("/"+std::string(PATH_MAX+1,'a')).c_str(),out)==-1&&errno==ENAMETOOLONG);
 rlimit original;assert(getrlimit(RLIMIT_NOFILE,&original)==0);rlimit limited=original;if(limited.rlim_cur>64)limited.rlim_cur=64;assert(setrlimit(RLIMIT_NOFILE,&limited)==0);
 for(int i=0;i<2000;++i){assert(ps5_descriptor_realpath(file.c_str(),out)==0);assert(ps5_descriptor_realpath((root+"/missing").c_str(),out)==-1&&errno==ENOENT);}
 assert(setrlimit(RLIMIT_NOFILE,&original)==0);std::filesystem::remove_all(root);
 puts("PASS: actual descriptor walk ASan/UBSan, trailing slash, unelided missing/link components, path/name limits and 4000 successful/failed walks under 64-fd limit");
}
''');subprocess.run(['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+str(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs'),str(p),'-o',str(w/'walk')],check=True);subprocess.run([str(w/'walk')],check=True)
