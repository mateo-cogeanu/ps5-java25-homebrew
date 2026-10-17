#!/usr/bin/env python3
"""Register actual patched access0 in a real JVM with injected native EPERM."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/access-test';w.mkdir(parents=True,exist_ok=True);jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs/UnixNativeDispatcher.c').read_text();a=s.index('JNIEXPORT jint JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_access0');b=s.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_statvfs0',a)
p=w/'bridge.c';p.write_text(r'''
#include <jni.h>
#include <stdint.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
static int denial=EPERM;
static int native_access(const char*p,int mode){if(!denial)return access(p,mode);errno=denial;return -1;}
#define access native_access
#define __PROSPERO__ 1
#define PS5_REALPATH_NOTE(phase,path) ((void)0)
#define RESTARTABLE(call,result) do{result=(call);}while(result==-1&&errno==EINTR)
#define jlong_to_ptr(n) ((void*)(intptr_t)n)
'''+s[a:b]+r'''
JNIEXPORT void JNICALL Java_AccessTest_install(JNIEnv*env,jclass c){jclass t=(*env)->FindClass(env,"sun/nio/fs/UnixNativeDispatcher");JNINativeMethod hook={"access0","(JI)I",(void*)Java_sun_nio_fs_UnixNativeDispatcher_access0};if((*env)->RegisterNatives(env,t,&hook,1))abort();}
JNIEXPORT void JNICALL Java_AccessTest_denial(JNIEnv*env,jclass c,jint value){denial=value;}
''');subprocess.run(['clang','-O1','-g','-dynamiclib','-undefined','dynamic_lookup','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(p),'-o',str(w/'libtest.dylib')],check=True)
p=w/'AccessTest.java';p.write_text(r'''
import java.nio.file.*;import java.io.*;import java.util.*;
public class AccessTest{
 static native void install();static native void denial(int n);
 public static void main(String[]args)throws Exception{
 System.load(args[0]);Path root=Files.createTempDirectory("ps5-access-");Path file=Files.writeString(root.resolve("file"),"unchanged");Path jar=root.resolve("asset.zip");try(var z=FileSystems.newFileSystem(jar,Map.of("create","true"))){Files.writeString(z.getPath("/version.json"),"ok");}install();
 try{
 if(!Files.isReadable(file)||!Files.isWritable(file)||Files.isExecutable(file)||!Files.exists(file)||Files.exists(root.resolve("missing")))throw new AssertionError("operation checks");
 file.getFileSystem().provider().checkAccess(file,AccessMode.READ,AccessMode.WRITE);
 for(int i=0;i<1024;i++)if(!Files.isReadable(file))throw new AssertionError("repeat");
 if(!Files.readString(file).equals("unchanged"))throw new AssertionError("modified");
 try(var z=FileSystems.newFileSystem(jar,Map.of())){if(!Files.readString(z.getPath("/version.json")).equals("ok"))throw new AssertionError("ZipFS");}
 denial(13);if(Files.isReadable(file))throw new AssertionError("EACCES overridden");
 denial(0);if(!Files.isReadable(file))throw new AssertionError("native success");
 System.out.println("PASS: actual JNI access0, genuine read/write/existence, no execute inference, ENOENT/EACCES, unchanged content, repeated cleanup and actual ZipFS mount/read with access EPERM");
 }finally{denial(0);Files.delete(jar);Files.delete(file);Files.delete(root);}
 }
}''');subprocess.run([str(jdk/'bin/javac'),'-d',str(w),str(p)],check=True);subprocess.run([str(jdk/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-cp',str(w),'AccessTest',str(w/'libtest.dylib')],check=True)
