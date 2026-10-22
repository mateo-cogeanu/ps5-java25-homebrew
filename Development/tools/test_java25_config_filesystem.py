#!/usr/bin/env python3
"""Actual file-statistics JNI and canonicalizer with injected sandbox refusals."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/config-filesystem-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');src=r/'.tools/java25/openjdk/src/java.base/unix/native'
s=(src/'libnio/fs/UnixNativeDispatcher.c').read_text();a=s.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_statvfs0');b=s.index('\nJNIEXPORT',a);stats=s[a:b]
owners=''
for name in ['chown0','lchown0','fchown0']:
 a=s.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_'+name);b=s.index('\nJNIEXPORT',a);owners+=s[a:b]+'\n'
xattrs=''
for name,kind in [('fgetxattr0','jint'),('fsetxattr0','void'),('fremovexattr0','void'),('flistxattr','jint')]:
 a=s.index('JNIEXPORT '+kind+' JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_'+name);b=s.find('\nJNIEXPORT',a)
 if b<0:b=len(s)
 xattrs+=s[a:b]+'\n'
a=s.index('#ifdef __PROSPERO__\n// The title SDK exposes timeval APIs');b=s.index('\nJNIEXPORT jlong JNICALL',a);timestamps=s[a:b]
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
#include <sys/time.h>
#include "ps5Realpath.h"
#include "path_util.h"
static int mode=0,statmode=0,statcalls=0,ownership_denials=0,xattr_denials=0;
#undef PS5_REALPATH_NOTE
#define PS5_REALPATH_NOTE(phase,path) do{(void)path;if(strstr(phase,"ownership"))ownership_denials++;if(strstr(phase,"extended attributes"))xattr_denials++;}while(0)
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
'''+stats+owners+xattrs+timestamps+r'''
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
JNIEXPORT jint JNICALL Java_ConfigFs_unavailableError(JNIEnv*env,jclass cls){(void)env;(void)cls;return ENOSYS;}
JNIEXPORT jint JNICALL Java_ConfigFs_xattrError(JNIEnv*env,jclass cls){(void)env;(void)cls;return ENOTSUP;}
JNIEXPORT jint JNICALL Java_ConfigFs_xattrDenials(JNIEnv*env,jclass cls){(void)env;(void)cls;return xattr_denials;}
JNIEXPORT jint JNICALL Java_ConfigFs_deniedError(JNIEnv*env,jclass cls){(void)env;(void)cls;return EPERM;}
JNIEXPORT jint JNICALL Java_ConfigFs_denials(JNIEnv*env,jclass cls){(void)env;(void)cls;return ownership_denials;}
JNIEXPORT jint JNICALL Java_ConfigFs_calls(JNIEnv*env,jclass cls){(void)env;(void)cls;return statcalls;}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*vm,void*reserved){(void)reserved;JNIEnv*env=0;if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_8))return JNI_ERR;
 jclass attrs=(*env)->FindClass(env,"sun/nio/fs/UnixFileStoreAttributes");if(!attrs)return JNI_ERR;
 attrs_f_frsize=(*env)->GetFieldID(env,attrs,"f_frsize","J");attrs_f_blocks=(*env)->GetFieldID(env,attrs,"f_blocks","J");attrs_f_bfree=(*env)->GetFieldID(env,attrs,"f_bfree","J");attrs_f_bavail=(*env)->GetFieldID(env,attrs,"f_bavail","J");if((*env)->ExceptionCheck(env))return JNI_ERR;
 jclass io=(*env)->FindClass(env,"java/io/UnixFileSystem");if(!io)return JNI_ERR;JNINativeMethod cm={"canonicalize0","(Ljava/lang/String;)Ljava/lang/String;",(void*)Java_ConfigFs_canonical};if((*env)->RegisterNatives(env,io,&cm,1))return JNI_ERR;JNINativeMethod sm={"getSpace0","(Ljava/io/File;I)J",(void*)Java_java_io_UnixFileSystem_getSpace0};if((*env)->RegisterNatives(env,io,&sm,1))return JNI_ERR;
 jclass dispatcher=(*env)->FindClass(env,"sun/nio/fs/UnixNativeDispatcher");if(!dispatcher)return JNI_ERR;
 JNINativeMethod m={"statvfs0","(JLsun/nio/fs/UnixFileStoreAttributes;)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_statvfs0};if((*env)->RegisterNatives(env,dispatcher,&m,1))return JNI_ERR;
 JNINativeMethod owners[]={
 {"chown0","(JII)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_chown0},
 {"lchown0","(JII)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_lchown0},
 {"fchown0","(III)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_fchown0}};
 if((*env)->RegisterNatives(env,dispatcher,owners,3))return JNI_ERR;
 JNINativeMethod xattrs[]={
 {"fgetxattr0","(IJJI)I",(void*)Java_sun_nio_fs_UnixNativeDispatcher_fgetxattr0},
 {"fsetxattr0","(IJJI)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_fsetxattr0},
 {"fremovexattr0","(IJ)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_fremovexattr0},
 {"flistxattr","(IJI)I",(void*)Java_sun_nio_fs_UnixNativeDispatcher_flistxattr}};
 if((*env)->RegisterNatives(env,dispatcher,xattrs,4))return JNI_ERR;
 JNINativeMethod times[]={
 {"futimens0","(IJJ)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_futimens0},
 {"utimensat0","(IJJJI)V",(void*)Java_sun_nio_fs_UnixNativeDispatcher_utimensat0}};
 if((*env)->RegisterNatives(env,dispatcher,times,2))return JNI_ERR;return JNI_VERSION_1_8;}
'''
(w/'test.c').write_text(c)
(w/'ConfigFs.java').write_text(r'''
import java.nio.file.*;import java.lang.reflect.*;import java.io.*;
public class ConfigFs {
 static native String canonical(String path)throws IOException;
 static native void modes(int realpath,int stat);
 static native boolean statsMatch(Object attrs);
 static native int calls();
 static native int denials();
 static native int deniedError();
 static native int xattrError();
 static native int xattrDenials();
 static native int unavailableError();
 static void fail(Path p)throws Exception{try{canonical(p.toString());throw new AssertionError("accepted "+p);}catch(IOException expected){}}
 public static void main(String[]args)throws Exception{
  System.load(args[0]);boolean ps5=args.length>1&&args[1].equals("ps5");
  Path nativeRoot=Files.createTempDirectory("ps5-config-fs-").toRealPath();
  if(ps5)System.setProperty("os.name","PS5");
  var ctor=Class.forName("sun.nio.fs.BsdFileSystemProvider").getDeclaredConstructor();ctor.setAccessible(true);
  var provider=(java.nio.file.spi.FileSystemProvider)ctor.newInstance();var fs=provider.getFileSystem(java.net.URI.create("file:///"));
  Path root=fs.getPath(nativeRoot.toString()).toRealPath();
  if(fs.supportedFileAttributeViews().contains("user")==ps5)throw new AssertionError("BSD user-view advertisement");
  if((provider.getFileAttributeView(root,java.nio.file.attribute.UserDefinedFileAttributeView.class)==null)!=ps5)throw new AssertionError("BSD typed-view capability");
  Method dynamic=provider.getClass().getDeclaredMethod("getFileAttributeView",Path.class,String.class,LinkOption[].class);dynamic.setAccessible(true);
  if((dynamic.invoke(provider,root,"user",new LinkOption[0])==null)!=ps5)throw new AssertionError("BSD dynamic-view capability");Path dir=Files.createDirectory(root.resolve("dir")),file=Files.writeString(dir.resolve("a.yml"),"hello config");
  Class<?> up=Class.forName("sun.nio.fs.UnixPath"),attrs=Class.forName("sun.nio.fs.UnixFileStoreAttributes");Method get=attrs.getDeclaredMethod("get",up);get.setAccessible(true);
  modes(0,0);if((new File(file.toString())).getTotalSpace()!=0||(new File(file.toString())).getFreeSpace()!=0||(new File(file.toString())).getUsableSpace()!=0||calls()!=0)throw new AssertionError("unavailable File capacity must not call native statfs");
  for(Path probe:new Path[]{file,root.resolve("missing")})try{get.invoke(null,probe);throw new AssertionError("NIO capacity must report unavailable");}catch(InvocationTargetException expected){if(!expected.getCause().getClass().getName().equals("sun.nio.fs.UnixException"))throw expected;Method errno=expected.getCause().getClass().getDeclaredMethod("errno");errno.setAccessible(true);if(((Integer)errno.invoke(expected.getCause()))!=unavailableError())throw new AssertionError("wrong unavailable error");}
  if(calls()!=0)throw new AssertionError("unsupported NIO stats invoked native statfs");
  modes(1,0);if(!canonical(file.toString()).equals(file.toString()))throw new AssertionError("file fallback");
  Path missing=dir.resolve("new/config.yml");if(!(new File(missing.toString())).getCanonicalPath().equals(missing.toString()))throw new AssertionError("File canonical API");if(!canonical(missing.toString()).equals(missing.toString()))throw new AssertionError("missing config tail");
  if(!canonical(dir.resolve("../dir/a.yml").toString()).equals(file.toString()))throw new AssertionError("parent walk");
  Path link=Files.createSymbolicLink(root.resolve("link"),dir);fail(link.resolve("a.yml"));fail(root.resolve("broken-link"));
  Files.createSymbolicLink(root.resolve("broken-link"),root.resolve("absent"));fail(root.resolve("broken-link"));
  modes(2,0);fail(file);modes(0,0);if(!canonical(link.resolve("a.yml").toString()).equals(file.toString()))throw new AssertionError("native symlink behavior");
  var stamp=java.nio.file.attribute.FileTime.from(1700000000123456L,java.util.concurrent.TimeUnit.MICROSECONDS);
  Files.setLastModifiedTime(file,stamp);
  if(!Files.getLastModifiedTime(file).equals(stamp))throw new AssertionError("real timestamp write");
  // Real NIO copy/replace of configuration data uses the actual hooked stat JNI.
  for(int i=0;i<20;i++){Path copy=dir.resolve("copy.yml");Files.copy(file,copy,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.COPY_ATTRIBUTES);if(!Files.readString(copy).equals("hello config"))throw new AssertionError("copy bytes");if(!Files.getLastModifiedTime(copy).equals(stamp))throw new AssertionError("copy timestamp");}
  if(calls()!=0)throw new AssertionError("NIO copies queried raw statfs");
  if(denials()<20)throw new AssertionError("COPY_ATTRIBUTES did not exercise denied ownership");
  Class<?> dispatcher=Class.forName("sun.nio.fs.UnixNativeDispatcher");
  for(String name:new String[]{"chown0","lchown0","fchown0"}){
   boolean fd=name.equals("fchown0");Method change=dispatcher.getDeclaredMethod(name,fd?int.class:long.class,int.class,int.class);change.setAccessible(true);
   Object first=fd?(Object)Integer.valueOf(-1):(Object)Long.valueOf(0);
   try{change.invoke(null,first,0,0);throw new AssertionError("false ownership success");}catch(InvocationTargetException expected){Method errno=expected.getCause().getClass().getDeclaredMethod("errno");errno.setAccessible(true);if(((Integer)errno.invoke(expected.getCause()))!=deniedError())throw new AssertionError("ownership error differs fromEPERM");}
  }

  if(ps5?xattrDenials()!=0:xattrDenials()<20)throw new AssertionError("BSD extended-attribute copy capability, ps5="+ps5+" denials="+xattrDenials());
  for(String name:new String[]{"fgetxattr0","fsetxattr0","fremovexattr0","flistxattr"}){
   Class<?>[] types=name.equals("fremovexattr0")?new Class<?>[]{int.class,long.class}:name.equals("flistxattr")?new Class<?>[]{int.class,long.class,int.class}:new Class<?>[]{int.class,long.class,long.class,int.class};
   Object[] values=name.equals("fremovexattr0")?new Object[]{-1,0L}:name.equals("flistxattr")?new Object[]{-1,0L,0}:new Object[]{-1,0L,0L,0};
   Method action=dispatcher.getDeclaredMethod(name,types);action.setAccessible(true);
   try{action.invoke(null,values);throw new AssertionError("false xattr success");}catch(InvocationTargetException expected){Method errno=expected.getCause().getClass().getDeclaredMethod("errno");errno.setAccessible(true);if(((Integer)errno.invoke(expected.getCause()))!=xattrError())throw new AssertionError("xattr error differs fromENOTSUP");}
  }
  var userView=Files.getFileAttributeView(file,java.nio.file.attribute.UserDefinedFileAttributeView.class);
  if(userView!=null)try{userView.list();throw new AssertionError("xattrs falsely reported empty");}catch(IOException expected){}
  if(ps5)try{Files.setAttribute(file,"user:probe",new byte[]{1});throw new AssertionError("unsupported user write falsely succeeded");}catch(UnsupportedOperationException expected){}
  try{Files.setOwner(file,Files.getOwner(file));throw new AssertionError("explicit ownership operation falsely succeeded");}catch(IOException expected){}
  if(!Files.readString(file).equals("hello config"))throw new AssertionError("ownership operation changed data");
  try{Files.copy(root.resolve("absent-source"),root.resolve("bad-copy"));throw new AssertionError("missing source accepted");}catch(NoSuchFileException expected){}
  try{Files.copy(file,root.resolve("missing-parent/bad-copy"));throw new AssertionError("missing parent accepted");}catch(NoSuchFileException expected){}
  System.out.println("PASS actual unavailable File/NIO capacity JNI in real JVM, zero native statfs calls and COPY_ATTRIBUTES config copies with actual EPERM ownership and existing Java buffer fallback; explicit ownership IOException;4xattr ENOTSUP entries/optionalcopy/no fake empty-list; actual JDK canonicalizer+descriptor walker for EPERM existing/missing-tail/dot-parent/symlink refusal/native-links/EIO. actual timeval timestamp JNI registered, real FileTime write and20copy timestamps exact; XcheckJNI/UBSan; target behavior pending.");
 }
}
''')
# A missing ordinary file is valid for File.getCanonicalPath, unlike toRealPath.
p=w/'ConfigFs.java';s=p.read_text().replace('fail(link.resolve("a.yml"));fail(root.resolve("broken-link"));','fail(link.resolve("a.yml"));');p.write_text(s)
lib=w/'libtest.dylib'
subprocess.run(['clang','-dynamiclib','-O1','-g','-fsanitize=undefined','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(src/'libnio/fs'),'-I'+str(src/'libjava'),str(w/'test.c'),str(src/'libjava/path_util.c'),'-o',str(lib)],check=True)
patchsrc=w/'bsd-src/sun/nio/fs';patchsrc.mkdir(parents=True,exist_ok=True)
for name in ['BsdFileSystem.java','BsdFileSystemProvider.java']:
 (patchsrc/name).write_text((r/'.tools/java25/openjdk/src/java.base/bsd/classes/sun/nio/fs'/name).read_text())
(patchsrc/'UnixUserDefinedFileAttributeView.java').write_text((r/'.tools/java25/openjdk/src/java.base/unix/classes/sun/nio/fs/UnixUserDefinedFileAttributeView.java').read_text())
(patchsrc/'BsdUserDefinedFileAttributeView.java').write_text((r/'.tools/java25/openjdk/src/java.base/bsd/classes/sun/nio/fs/BsdUserDefinedFileAttributeView.java').read_text())
patchclasses=w/'bsd-classes';patchclasses.mkdir(exist_ok=True)
subprocess.run([str(jdk/'bin/javac'),'--patch-module','java.base='+str(w/'bsd-src'),'-d',str(patchclasses),*[str(patchsrc/name) for name in ['BsdFileSystem.java','BsdFileSystemProvider.java','UnixUserDefinedFileAttributeView.java','BsdUserDefinedFileAttributeView.java']]],check=True)
subprocess.run([str(jdk/'bin/javac'),str(w/'ConfigFs.java')],check=True)
for mode in ['control','ps5']:
 subprocess.run([str(jdk/'bin/java'),'--patch-module','java.base='+str(patchclasses),*(['-Dos.name=PS5'] if mode=='ps5' else []),'-Xcheck:jni','--enable-native-access=ALL-UNNAMED','--add-opens=java.base/sun.nio.fs=ALL-UNNAMED','-cp',str(w),'ConfigFs',str(lib),mode],check=True,timeout=60)
