#!/usr/bin/env python3
"""Exercise actual PS5 stream-path and unavailable-mount native bodies with JNI.

The platform-string transport uses host JNI UTF transport for ASCII fixtures;
mount syscalls are injected, never run on the host. This is not console proof.
"""
from pathlib import Path
import os, subprocess
r=Path(__file__).resolve().parents[1]
jdk=Path(os.environ.get('JAVA25_BOOT_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
w=r/'build/java25/ps5-filesystem-test';w.mkdir(parents=True,exist_ok=True)
for p in ['cwd','root','root/sub']:(w/p).mkdir(exist_ok=True)
def body(s,mark):
 a=s.index(mark);b=s.index('{',a);depth=1;i=b+1
 while depth:
  if s[i]=='{':depth+=1
  if s[i]=='}':depth-=1
  i+=1
 return s[a:i]
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libjava/io_util_md.c').read_text()
helper=body(s,'static jstring ps5_io_absolute_path')
handle=body(s,'handleOpen(')
opened=body(s,'fileOpen(')
m=(r/'.tools/java25/openjdk/src/java.base/bsd/native/libnio/fs/BsdNativeDispatcher.c').read_text()
mount=body(m,'Java_sun_nio_fs_BsdNativeDispatcher_getfsstat(')
end=body(m,'Java_sun_nio_fs_BsdNativeDispatcher_endfsstat(')
c=w/'test.c';c.write_text(r'''
#include <jni.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static jfieldID IO_fd_fdID,IO_append_fdID;
typedef int FD;
#define RESTARTABLE(cmd,result) do{result=(cmd);}while(result<0&&errno==EINTR)
static jobject JNU_NewObjectByName(JNIEnv *e,const char *name,const char *sig,jobject arg){jclass c=(*e)->FindClass(e,name);if(!c)return NULL;jmethodID id=(*e)->GetMethodID(e,c,"<init>",sig);jobject r=id?(*e)->NewObject(e,c,id,arg):NULL;(*e)->DeleteLocalRef(e,c);return r;}
static jvalue JNU_CallMethodByName(JNIEnv *e,void *unused,jobject o,const char *name,const char *sig){(void)unused;jvalue r={0};jclass c=(*e)->GetObjectClass(e,o);if(!c)return r;jmethodID id=(*e)->GetMethodID(e,c,name,sig);if(id)r.l=(*e)->CallObjectMethod(e,o,id);(*e)->DeleteLocalRef(e,c);return r;}
static void throw_named(JNIEnv*e,const char*n,const char*m){jclass c=(*e)->FindClass(e,n);if(c){(*e)->ThrowNew(e,c,m);(*e)->DeleteLocalRef(e,c);}}
static void throwFileNotFoundException(JNIEnv*e,jstring p){(void)p;throw_named(e,"java/io/FileNotFoundException",strerror(errno));}
#define WITH_PLATFORM_STRING(e,value,name) { jstring saved_string=(value);const char *name=(*(e))->GetStringUTFChars(e,saved_string,NULL);if(name){
#define END_PLATFORM_STRING(e,name) if(name)(*(e))->ReleaseStringUTFChars(e,saved_string,name);}}
''' + '\n#ifdef __PROSPERO__\n'+helper+'\n#endif\nFD\n'+handle+'\nvoid\n'+opened+r'''
JNIEXPORT void JNICALL Java_Ps5FsCheck_open(JNIEnv*e,jobject self,jstring path,jint mode){
 jclass c=(*e)->GetObjectClass(e,self);assert(c);
 jfieldID field=(*e)->GetFieldID(e,c,"descriptor","Ljava/io/FileDescriptor;");assert(field);
 jclass f=(*e)->FindClass(e,"java/io/FileDescriptor");assert(f);
 IO_fd_fdID=(*e)->GetFieldID(e,f,"fd","I");assert(IO_fd_fdID);
 IO_append_fdID=(*e)->GetFieldID(e,f,"append","Z");assert(IO_append_fdID);
 int flags=mode==0?O_RDONLY:mode==1?O_WRONLY|O_CREAT|O_TRUNC:mode==2?O_WRONLY|O_CREAT|O_APPEND:O_RDWR|O_CREAT;
 fileOpen(e,self,path,field,flags);
 (*e)->DeleteLocalRef(e,f);(*e)->DeleteLocalRef(e,c);
}
struct statfs { int dummy; };
struct fsstat_iter {struct statfs *buf;int pos,nentries;};
#define MNT_NOWAIT 2
#define MNT_WAIT 1
#define jlong_to_ptr(v) ((void*)(intptr_t)(v))
#include <stdint.h>
static int calls,allocs,live,scenario,notes;
static void *count_malloc(size_t n){allocs++;if(scenario==3)return NULL;void*p=malloc(n);if(p)live++;return p;}
static void count_free(void*p){if(p){live--;free(p);}}
static int fake_getfsstat(struct statfs*p,size_t n,int flags){calls++;if(scenario==1){errno=EACCES;return -1;}if(scenario==2&&p){errno=EIO;return -1;}if(!p){assert(!n&&flags==MNT_NOWAIT);return 1;}assert(n==sizeof(*p)&&flags==MNT_WAIT);p->dummy=7;return 1;}
void ps5_vm_trace(const char *s){assert(strstr(s,"getfsstat ENOSYS"));notes++;}
static void throwUnixException(JNIEnv*e,int err){char m[32];snprintf(m,sizeof(m),"errno=%d",err);throw_named(e,"java/io/IOException",m);}
static void JNU_ThrowOutOfMemoryError(JNIEnv*e,const char*m){throw_named(e,"java/lang/OutOfMemoryError",m);}
#define malloc count_malloc
#define free count_free
#define getfsstat fake_getfsstat
jlong
''' +mount+'\nvoid\n'+end+r'''
#undef malloc
#undef free
JNIEXPORT void JNICALL Java_Ps5FsCheck_mount(JNIEnv*e,jclass c,jint value){
 calls=allocs=notes=0;scenario=value;
 jlong iter=Java_sun_nio_fs_BsdNativeDispatcher_getfsstat(e,c);
 if(iter)Java_sun_nio_fs_BsdNativeDispatcher_endfsstat(e,c,iter);
 assert(!live);
#ifdef __PROSPERO__
 assert(!calls&&!allocs&&!notes);
#else
 assert(!notes&&allocs>=1);if(value!=3)assert(calls>=1);
#endif
}
''')
java=w/'Ps5FsCheck.java';java.write_text(r'''
import java.io.*;
import java.nio.file.*;
public class Ps5FsCheck {
 private final FileDescriptor descriptor=new FileDescriptor();
 private native void open(String path,int mode) throws FileNotFoundException;
 private static native void mount(int mode) throws IOException;
 static void write(String path,int mode,String text)throws Exception {var o=new Ps5FsCheck();o.open(path,mode);try(var f=new FileOutputStream(o.descriptor)){f.write(text.getBytes());}}
 static String read(String path)throws Exception {var o=new Ps5FsCheck();o.open(path,0);try(var f=new FileInputStream(o.descriptor)){return new String(f.readAllBytes());}}
 public static void main(String[] args)throws Exception {
  System.load(args[0]);boolean ps5=Boolean.parseBoolean(args[1]);Path work=Path.of(args[2]);Path actual=work.resolve(ps5?"root":"cwd");
  write("stream.txt",1,"first");write("stream.txt",2,"+append");
  if(!read("stream.txt").equals("first+append"))throw new AssertionError("read/append");
  if(!Files.readString(actual.resolve("stream.txt")).equals("first+append"))throw new AssertionError("cwd mismatch");
  write("sub/../nested.txt",1,"nested");
  if(!Files.readString(actual.resolve("nested.txt")).equals("nested"))throw new AssertionError("parent traversal");
  Path abs=work.resolve("absolute.txt");write(abs.toString(),1,"absolute");
  if(!Files.readString(abs).equals("absolute"))throw new AssertionError("absolute");
  var both=new Ps5FsCheck();both.open("rw.txt",3);try(var f=new FileOutputStream(both.descriptor)){f.write(42);}
  if(Files.readAllBytes(actual.resolve("rw.txt"))[0]!=42)throw new AssertionError("rw");
  for(String path:new String[]{"","missing-parent/file"}){
   try{write(path,1,"bad");throw new AssertionError("accepted invalid path");}catch(FileNotFoundException expected){}
  }
  for(int mode=0;mode<4;mode++){
   try{mount(mode);if(ps5||mode!=0)throw new AssertionError("mount accepted");}
   catch(IOException error){String expected="errno="+(ps5?78:mode==1?13:5);if(!expected.equals(error.getMessage()))throw new AssertionError(error);}
   catch(OutOfMemoryError error){if(ps5||mode!=3)throw error;}
  }
  System.out.println("PASS: actual stream fileOpen/handleOpen + real JNI File absolute resolution, cwd differs from user.dir, relative/absolute/read/write/append/rw/dot-parent/empty/missing-parent errors; actual mount body zero syscall/allocation ENOSYS or desktop query/error/cleanup, PS5="+ps5);
 }
}
''')
(w/'cwd/sub').mkdir(exist_ok=True)
subprocess.run([str(jdk/'bin/javac'),str(java)],check=True)
for ps5 in [True,False]:
 lib=w/('ps5.dylib' if ps5 else 'desktop.dylib')
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-fsanitize=undefined','-dynamiclib',*(['-D__PROSPERO__=1'] if ps5 else []),'-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(c),'-o',str(lib)],check=True)
 subprocess.run([str(jdk/'bin/java'),'--enable-native-access=ALL-UNNAMED','-Xcheck:jni','-Duser.dir='+str(w/'root'),'-cp',str(w),'Ps5FsCheck',str(lib),str(ps5).lower(),str(w)],cwd=w/'cwd',check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0:halt_on_error=1'})
