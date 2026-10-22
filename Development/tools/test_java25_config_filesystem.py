#!/usr/bin/env python3
"""Actual file-statistics JNI and canonicalizer with injected sandbox refusals."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/config-filesystem-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');src=r/'.tools/java25/openjdk/src/java.base/unix/native'
s=(src/'libnio/fs/UnixNativeDispatcher.c').read_text();a=s.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_statvfs0');b=s.index('\nJNIEXPORT',a);stats=s[a:b]
s=(src/'libjava/UnixFileSystem_md.c').read_text();a=s.index('JNIEXPORT jlong JNICALL\nJava_java_io_UnixFileSystem_getSpace0');b=s.index('\nJNIEXPORT',a);space=s[a:b]
s=(src/'libjava/canonicalize_md.c').read_text();a=s.index('static char *ps5_canonical_realpath');b=s.index('\n#endif',a);wrapper=s[a:b].replace('= realpath(path, resolved)', '= selected_realpath(path, resolved)',1);a=s.index('JNIEXPORT int\nJDK_Canonicalize');canonical=s[a:]
c=r'''
#define __PROSPERO__ 1
#include <jni.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <sys/mount.h>
#include "ps5Realpath.h"
#include "path_util.h"
static int mode=0,statmode=0,statcalls=0;
static struct statfs laststat;
static char* selected_realpath(const char*p,char*out){if(mode){errno=mode==1?EPERM:EIO;return NULL;}return realpath(p,out);}
static int selected_statfs(const char*p,struct statfs*out){++statcalls;if(statmode==1){statmode=0;errno=EINTR;return -1;}if(statmode==2){errno=EACCES;return -1;}int n=statfs(p,out);if(!n)laststat=*out;return n;}
'''+wrapper+'\n'+canonical+r'''
#undef realpath
static jfieldID attrs_f_frsize,attrs_f_blocks,attrs_f_bfree,attrs_f_bavail;
static void throwUnixException(JNIEnv*env,int error){jclass c=(*env)->FindClass(env,"sun/nio/fs/UnixException");if(!c)return;jmethodID m=(*env)->GetMethodID(env,c,"<init>","(I)V");if(!m)return;jobject e=(*env)->NewObject(env,c,m,error);if(e)(*env)->Throw(env,(jthrowable)e);}
#define __PROSPERO__ 1
#define jlong_to_ptr(n) ((void*)(intptr_t)(n))
#define long_to_jlong(n) ((jlong)(n))
#define RESTARTABLE(cmd,result) do{result=(cmd);}while(result==-1&&errno==EINTR)
#define statfs(...) selected_statfs(__VA_ARGS__)
'''+stats+r'''
#define jlong_mul(a,b) ((jlong)((uint64_t)(a)*(uint64_t)(b)))
#define java_io_FileSystem_SPACE_TOTAL 0
#define java_io_FileSystem_SPACE_FREE 1
#define java_io_FileSystem_SPACE_USABLE 2
#define WITH_FIELD_PLATFORM_STRING(e,f,field,path) {jclass fc=(*e)->GetObjectClass(e,f);if(!fc)return 0;jfieldID pf=(*e)->GetFieldID(e,fc,"path","Ljava/lang/String;");if(!pf)return 0;jstring ss=(jstring)(*e)->GetObjectField(e,f,pf);if((*e)->ExceptionCheck(e))return 0;const char*path=(*e)->GetStringUTFChars(e,ss,0);if(path){
#define END_PLATFORM_STRING(e,path) (*e)->ReleaseStringUTFChars(e,ss,path);}}
'''+space+r'''
#undef statfs
JNIEXPORT jstring JNICALL Java_ConfigFs_canonical(JNIEnv*env,jclass cls,jstring input){(void)cls;char out[PATH_MAX];const char*p=(*env)->GetStringUTFChars(env,input,0);if(!p)return NULL;int n=JDK_Canonicalize(p,out,sizeof(out));int e=errno;(*env)->ReleaseStringUTFChars(env,input,p);if(n<0){jclass ex=(*env)->FindClass(env,"java/io/IOException");if(ex)(*env)->ThrowNew(env,ex,strerror(e));return NULL;}return (*env)->NewStringUTF(env,out);}
JNIEXPORT void JNICALL Java_ConfigFs_modes(JNIEnv*env,jclass cls,jint a,jint b){(void)env;(void)cls;mode=a;statmode=b;statcalls=0;}
JNIEXPORT jboolean JNICALL Java_ConfigFs_statsMatch(JNIEnv*env,jclass cls,jobject obj){(void)cls;return statcalls>0&&(*env)->GetLongField(env,obj,attrs_f_frsize)==laststat.f_bsize&&(*env)->GetLongField(env,obj,attrs_f_blocks)==(jlong)laststat.f_blocks&&(*env)->GetLongField(env,obj,attrs_f_bfree)==(jlong)laststat.f_bfree&&(*env)->GetLongField(env,obj,attrs_f_bavail)==(jlong)laststat.f_bavail;}
JNIEXPORT jint JNICALL Java_ConfigFs_calls(JNIEnv*env,jclass cls){(void)env;(void)cls;return statcalls;}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*vm,void*reserved){(void)reserved;JNIEnv*env=0;if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_8))return JNI_ERR;
 jclass attrs=(*env)->FindClass(env,"sun/nio/fs/UnixFileStoreAttributes");if(!attrs)return JNI_ERR;
 attrs_f_frsize=(*env)->GetFieldID(env,attrs,"f_frsize","J");attrs_f_blocks=(*env)->GetFieldID(env,attrs,"f_blocks","J");attrs_f_bfree=(*env)->GetFieldID(env,attrs,"f_bfree","J");attrs_f_bavail=(*env)->GetFieldID(env,attrs,"f_bavail","J");if((*env)->ExceptionCheck(env))return JNI_ERR;
 jclass io=(*env)->FindClass(env,"java/io/UnixFileSystem");if(!io)return JNI_ERR;JNINativeMethod cm={"canonicalize0","(Ljava/lang/String;)Ljava/lang/String;",(void*)Java_ConfigFs_canonical};if((*env)->RegisterNatives(env,io,&cm,1))return JNI_ERR;JNINativeMethod sm={"getSpace0","(Ljava/io/File;I)J",(void*)Java_java_io_UnixFileSystem_getSpace0};if((*env)->RegisterNatives(env,io,&sm,1))return JNI_ERR;
 jclass dispatcher=(*env)->FindClass(env,"sun/nio/fs/UnixNativeDispatcher");if(!dispatcher)return JNI_ERR;
 JNINativeMethod m={"statvfs0","(JLsun/nio/fs/UnixFileStoreAttributes;)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_statvfs0};if((*env)->RegisterNatives(env,dispatcher,&m,1))return JNI_ERR;return JNI_VERSION_1_8;}
'''
(w/'test.c').write_text(c)
(w/'ConfigFs.java').write_text(r'''
import java.nio.file.*;import java.lang.reflect.*;import java.io.*;
public class ConfigFs {
 static native String canonical(String path)throws IOException;
 static native void modes(int realpath,int stat);
 static native boolean statsMatch(Object attrs);
 static native int calls();
 static void fail(Path p)throws Exception{try{canonical(p.toString());throw new AssertionError("accepted "+p);}catch(IOException expected){}}
 public static void main(String[]args)throws Exception{
  System.load(args[0]);Path root=Files.createTempDirectory("ps5-config-fs-").toRealPath();Path dir=Files.createDirectory(root.resolve("dir")),file=Files.writeString(dir.resolve("a.yml"),"hello config");
  Class<?> up=Class.forName("sun.nio.fs.UnixPath"),attrs=Class.forName("sun.nio.fs.UnixFileStoreAttributes");Method get=attrs.getDeclaredMethod("get",up);get.setAccessible(true);
  modes(0,0);long total=file.toFile().getTotalSpace(),free=file.toFile().getFreeSpace(),usable=file.toFile().getUsableSpace();if(total<=0||free<0||usable<0||free>total||usable>total)throw new AssertionError("real File space values");modes(0,2);if(file.toFile().getTotalSpace()!=0)throw new AssertionError("File stat failure");modes(0,0);
  Object value=get.invoke(null,file);if(!statsMatch(value))throw new AssertionError("real stats mismatch");
  modes(0,1);value=get.invoke(null,file);if(!statsMatch(value)||calls()!=2)throw new AssertionError("EINTR retry");
  modes(0,2);try{get.invoke(null,file);throw new AssertionError("suppressed stat error");}catch(InvocationTargetException expected){if(!expected.getCause().getClass().getName().equals("sun.nio.fs.UnixException"))throw expected;}
  modes(0,0);try{get.invoke(null,root.resolve("missing"));throw new AssertionError("missing stat accepted");}catch(InvocationTargetException expected){}
  modes(1,0);if(!canonical(file.toString()).equals(file.toString()))throw new AssertionError("file fallback");
  Path missing=dir.resolve("new/config.yml");if(!missing.toFile().getCanonicalPath().equals(missing.toString()))throw new AssertionError("File canonical API");if(!canonical(missing.toString()).equals(missing.toString()))throw new AssertionError("missing config tail");
  if(!canonical(dir.resolve("../dir/a.yml").toString()).equals(file.toString()))throw new AssertionError("parent walk");
  Path link=Files.createSymbolicLink(root.resolve("link"),dir);fail(link.resolve("a.yml"));fail(root.resolve("broken-link"));
  Files.createSymbolicLink(root.resolve("broken-link"),root.resolve("absent"));fail(root.resolve("broken-link"));
  modes(2,0);fail(file);modes(0,0);if(!canonical(link.resolve("a.yml").toString()).equals(file.toString()))throw new AssertionError("native symlink behavior");
  // Real NIO copy/replace of configuration data uses the actual hooked stat JNI.
  for(int i=0;i<20;i++){Path copy=dir.resolve("copy.yml");Files.copy(file,copy,StandardCopyOption.REPLACE_EXISTING);if(!Files.readString(copy).equals("hello config"))throw new AssertionError("copy bytes");}
  System.out.println("PASS actual File/NIO statfs JNI/real JVM fields, EINTR/error/missing paths and repeated NIO config copy; actual JDK canonicalizer+descriptor walker for EPERM existing/missing-tail/dot-parent/symlink refusal/native-links/EIO. XcheckJNI/UBSan; target behavior pending.");
 }
}
''')
# A missing ordinary file is valid for File.getCanonicalPath, unlike toRealPath.
p=w/'ConfigFs.java';s=p.read_text().replace('fail(link.resolve("a.yml"));fail(root.resolve("broken-link"));','fail(link.resolve("a.yml"));');p.write_text(s)
lib=w/'libtest.dylib'
subprocess.run(['clang','-dynamiclib','-O1','-g','-fsanitize=undefined','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(src/'libnio/fs'),'-I'+str(src/'libjava'),str(w/'test.c'),str(src/'libjava/path_util.c'),'-o',str(lib)],check=True)
subprocess.run([str(jdk/'bin/javac'),str(w/'ConfigFs.java')],check=True)
subprocess.run([str(jdk/'bin/java'),'-Xcheck:jni','--enable-native-access=ALL-UNNAMED','--add-opens=java.base/sun.nio.fs=ALL-UNNAMED','-cp',str(w),'ConfigFs',str(lib)],check=True,timeout=60)
