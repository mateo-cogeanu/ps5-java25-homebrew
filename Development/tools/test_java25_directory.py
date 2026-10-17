#!/usr/bin/env python3
"""Exercise actual directory helper/JNI with host enumeration and malformed PS5 records."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/directory-test';w.mkdir(parents=True,exist_ok=True);inc=r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs';jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(inc/'UnixNativeDispatcher.c').read_text()
def body(name,next_name):
 a=s.index('JNIEXPORT '+name);b=s.index('JNIEXPORT '+next_name,a);return s[a:b]
op=body('jlong JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_opendir0','jlong JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_fdopendir')
cl=body('void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_closedir','jbyteArray JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_readdir0')
rd=body('jbyteArray JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_readdir0','void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_mkdir0')
source=r'''
#include <jni.h>
#include <stdlib.h>
#include <dirent.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include "ps5Directory.h"
/* Host adapter serializes real libc dirents into the pinned PS5 wire layout. */
int sceKernelGetdents(int fd,void*bytes,int capacity){
 off_t position=lseek(fd,0,SEEK_CUR);int copy=dup(fd);if(copy<0)return -1;
 DIR*stream=fdopendir(copy);if(!stream){close(copy);return -1;}
 seekdir(stream,position);unsigned char*out=bytes;size_t used=0;struct dirent*entry;
 while((entry=readdir(stream))){size_t n=strlen(entry->d_name),len=(8+n+1+3)&~3u;
  if(used+len>(size_t)capacity){closedir(stream);errno=EIO;return -1;}
  memset(out+used,0,len);uint32_t inode=entry->d_ino?1:0;memcpy(out+used,&inode,4);out[used+4]=len&255;out[used+5]=len>>8;out[used+6]=entry->d_type;out[used+7]=n;memcpy(out+used+8,entry->d_name,n);used+=len;
 }
 int error=errno;closedir(stream);errno=error;return used;
}
int sceKernelGetdirentries(int fd,void*data,int cap,long*position){(void)position;return sceKernelGetdents(fd,data,cap);}
static void throwUnixException(JNIEnv*env,int error){jclass c=(*env)->FindClass(env,"sun/nio/fs/UnixException");jmethodID m=(*env)->GetMethodID(env,c,"<init>","(I)V");jobject e=(*env)->NewObject(env,c,m,error);(*env)->Throw(env,(jthrowable)e);}
#define jlong_to_ptr(n) ((void*)(intptr_t)(n))
#define ptr_to_jlong(n) ((jlong)(intptr_t)(n))
#define PS5_REALPATH_NOTE(phase,path) ((void)0)
#define __PROSPERO__ 1
'''+op+cl+rd+r'''
JNIEXPORT void JNICALL Java_DirectoryTest_install(JNIEnv*env,jclass c){
 jclass type=(*env)->FindClass(env,"sun/nio/fs/UnixNativeDispatcher");
 JNINativeMethod hooks[]={
 {"opendir0","(J)J",(void*)Java_sun_nio_fs_UnixNativeDispatcher_opendir0},
 {"closedir","(J)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_closedir},
 {"readdir0","(J)[B",(void*)Java_sun_nio_fs_UnixNativeDispatcher_readdir0}};
 jfieldID capability=(*env)->GetStaticFieldID(env,type,"capabilities","I");
 if(!capability)abort();jint value=(*env)->GetStaticIntField(env,type,capability);
 (*env)->SetStaticIntField(env,type,capability,value&~2);
 if((*env)->RegisterNatives(env,type,hooks,3))abort();
}
'''
p=w/'bridge.c';p.write_text(source);subprocess.run(['clang','-O1','-g','-dynamiclib','-undefined','dynamic_lookup','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(inc),str(p),'-o',str(w/'libtest.dylib')],check=True)
p=w/'DirectoryTest.java';p.write_text(r'''
import java.nio.file.*;import java.util.*;import java.io.*;
public class DirectoryTest{
 static native void install();
 public static void main(String[]args)throws Exception{
 System.load(args[0]);Path root=Files.createTempDirectory("ps5-dir-");Files.createDirectories(root.resolve("sub/deep"));Files.writeString(root.resolve("sub/deep/α.txt"),"x");Files.writeString(root.resolve("leaf"),"x");Files.createSymbolicLink(root.resolve("alias"),Path.of("sub"));install();
 try{
  try(var dir=Files.newDirectoryStream(root)){Set<String>names=new HashSet<>();for(Path p:dir)names.add(p.getFileName().toString());if(!names.equals(Set.of("sub","leaf","alias")))throw new AssertionError(names);}
  try(var dir=Files.newDirectoryStream(root.resolve("alias"))){if(!dir.iterator().next().getFileName().toString().equals("deep"))throw new AssertionError("link following");}
  try(var stream=Files.walk(root)){if(stream.count()!=6)throw new AssertionError("walk");}
  try{Files.newDirectoryStream(root.resolve("leaf"));throw new AssertionError("file accepted");}catch(NotDirectoryException expected){}
  try{Files.newDirectoryStream(root.resolve("missing"));throw new AssertionError("missing accepted");}catch(NoSuchFileException expected){}
  for(int i=0;i<256;i++)try(var dir=Files.newDirectoryStream(root)){for(Path p:dir){}}
  System.out.println("PASS: actual JNI directory open/read/close, real Files.walk, Unicode, symlink following, missing/non-directory errors and repeated cleanup");
 }finally{try(var paths=Files.walk(root)){for(Path p:paths.sorted(Comparator.reverseOrder()).toList())Files.delete(p);}}
 }
}''');subprocess.run([str(jdk/'bin/javac'),'-d',str(w),str(p)],check=True);subprocess.run([str(jdk/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-cp',str(w),'DirectoryTest',str(w/'libtest.dylib')],check=True)
p=w/'parser.c';p.write_text(r'''
#include <assert.h>
#include <stdio.h>
#include "ps5Directory.h"
static int mode=0,calls=0,alternates=0;
int sceKernelGetdents(int fd,void*out,int cap){
 ++calls;unsigned char*p=out;memset(p,0,cap);
 if(mode==9||mode==11||(mode==10&&calls>1))return (int)0x80020016u;
 if(mode==1)return (int)0x8002000du;
 if(mode==2&&calls==1)return (int)0x80020004u;
 if(mode==3)return cap+1;
 if(mode==4)return 7;
 if(mode==5){p[0]=1;p[4]=0;return 12;}
 if(mode==6){p[0]=1;p[4]=12;p[7]=3;memcpy(p+8,"a\0b",3);return 12;}
 if(mode==7){p[0]=1;p[4]=12;p[7]=3;memcpy(p+8,"abcd",4);return 12;}
 if(mode==8){p[0]=1;p[4]=32;return 12;}
 if(calls>1+(mode==2))return 0;
 p[0]=1;p[4]=12;p[7]=3;memcpy(p+8,"abc",4);return 12;
}
int sceKernelGetdirentries(int fd,void*out,int cap,long*position){
 ++alternates;(void)fd;(void)cap;(void)position;
 if(mode==11)return (int)0x8002004eu;
 unsigned char*p=out;memset(p,0,12);p[0]=1;p[4]=12;p[7]=3;memcpy(p+8,"alt",4);return 12;
}
int main(){
 for(mode=0;mode<=11;mode++){
  Ps5Directory*d=ps5_directory_open("/tmp");assert(d);calls=alternates=0;
  const char*n=ps5_directory_read(d);
  if(mode==9){assert(n&&strcmp(n,"alt")==0&&alternates==1&&d->alternate==1);}
  else if(mode==10){assert(n&&strcmp(n,"abc")==0);assert(ps5_directory_read(d)==NULL&&errno==EINVAL&&alternates==0);}
  else if(mode==11){assert(n==NULL&&errno==78&&alternates==1);}
  else if(mode==0||mode==2){assert(n&&strcmp(n,"abc")==0);assert(ps5_directory_read(d)==NULL&&errno==0);}
  else {int e=mode==1?13:EIO;assert(n==NULL&&errno==e);int before=calls;assert(ps5_directory_read(d)==NULL&&errno==e&&calls==before);}
  assert(ps5_directory_close(d)==0);
 }
 assert(ps5_directory_open("/no-such-ps5-directory-test") == NULL&&errno==ENOENT);
 puts("PASS: actual helper ASan/UBSan malformed/truncated/oversized/embedded-NUL records, encoded errors, EINTR, EOF and sticky failures");
}
''');subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined','-I'+str(inc),str(p),'-o',str(w/'parser')],check=True);subprocess.run([str(w/'parser')],check=True)
