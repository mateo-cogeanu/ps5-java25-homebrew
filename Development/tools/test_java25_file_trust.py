#!/usr/bin/env python3
"""Actual java.io metadata bodies, injected denied queries and real default JSSE.

Only this test JVM rebinds four java.io natives; production Java classes/TLS
are unchanged. Real file descriptors and the target cacerts supply the data.
"""
from pathlib import Path
import os,subprocess,argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-class');parser.add_argument('--class-path',default='');parser.add_argument('--run-arg',action='append',default=[]);args=parser.parse_args()
r=Path(__file__).resolve().parents[1];w=r/'build/java25/file-trust-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libjava/UnixFileSystem_md.c').read_text()
def body(mark):
 a=s.index(mark);b=s.index('{',a);depth=1;i=b+1
 while depth:
  if s[i]=='{':depth+=1
  if s[i]=='}':depth-=1
  i+=1
 return s[a:i]
helper=s[s.index('#ifdef __PROSPERO__\n/* File-based'):s.index('/* -- Attribute accessors -- */')]
c=w/'test.c';c.write_text(r'''
#include <jni.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <stdint.h>
#include <string.h>
static int stat_error=EPERM,access_error=EPERM,fail_open,fail_fstat,fail_close,opens,live;
static int injected_stat(const char*p,struct stat*s){if(stat_error){errno=stat_error;return -1;}return stat(p,s);}
static int injected_access(const char*p,int mode){if(access_error){errno=access_error;return -1;}return access(p,mode);}
static int injected_open(const char*p,int flags){assert(!(flags&(O_CREAT|O_TRUNC)));opens++;if(fail_open){errno=EACCES;return -1;}int fd=open(p,flags);if(fd>=0)live++;return fd;}
static int injected_fstat(int fd,struct stat*s){if(fail_fstat){errno=EIO;return -1;}return fstat(fd,s);}
static int injected_close(int fd){int result=close(fd);if(!result)live--;if(fail_close){errno=EIO;return -1;}return result;}
#define stat(p,s) injected_stat(p,s)
#define access(p,m) injected_access(p,m)
#define open(p,f) injected_open(p,f)
#define fstat(fd,s) injected_fstat(fd,s)
#define close(fd) injected_close(fd)
#define RESTARTABLE(cmd,result) do{result=(cmd);}while(result<0&&errno==EINTR)
#define java_io_FileSystem_BA_EXISTS 1
#define java_io_FileSystem_BA_REGULAR 2
#define java_io_FileSystem_BA_DIRECTORY 4
#define java_io_FileSystem_ACCESS_READ 4
#define java_io_FileSystem_ACCESS_WRITE 2
#define java_io_FileSystem_ACCESS_EXECUTE 1
static struct {jfieldID path;} ids;
#define WITH_FIELD_PLATFORM_STRING(e,file,field,path) for(jstring value=(jstring)(*(e))->GetObjectField(e,file,field);value!=NULL;(*(e))->DeleteLocalRef(e,value),value=NULL) for(const char*path=(*(e))->GetStringUTFChars(e,value,NULL);path!=NULL;(*(e))->ReleaseStringUTFChars(e,value,path),path=NULL)
#define END_PLATFORM_STRING(e,path)
''' +helper+'\nstatic jboolean\n'+body('statMode(')+'\njint\n'+body('Java_java_io_UnixFileSystem_getBooleanAttributes0(')+'\njboolean\n'+body('Java_java_io_UnixFileSystem_checkAccess0(')+'\njlong\n'+body('Java_java_io_UnixFileSystem_getLastModifiedTime0(')+'\njlong\n'+body('Java_java_io_UnixFileSystem_getLength0(')+r'''
JNIEXPORT void JNICALL Java_FileTrustCheck_install(JNIEnv*e,jclass c){
 (void)c;jclass f=(*e)->FindClass(e,"java/io/File");assert(f);ids.path=(*e)->GetFieldID(e,f,"path","Ljava/lang/String;");assert(ids.path);
 jclass fs=(*e)->FindClass(e,"java/io/UnixFileSystem");assert(fs);
 JNINativeMethod methods[]={
 {"getBooleanAttributes0","(Ljava/io/File;)I",(void*)Java_java_io_UnixFileSystem_getBooleanAttributes0},
 {"checkAccess0","(Ljava/io/File;I)Z",(void*)Java_java_io_UnixFileSystem_checkAccess0},
 {"getLastModifiedTime0","(Ljava/io/File;)J",(void*)Java_java_io_UnixFileSystem_getLastModifiedTime0},
 {"getLength0","(Ljava/io/File;)J",(void*)Java_java_io_UnixFileSystem_getLength0}};
 assert((*e)->RegisterNatives(e,fs,methods,4)==0);(*e)->DeleteLocalRef(e,f);(*e)->DeleteLocalRef(e,fs);
}
JNIEXPORT void JNICALL Java_FileTrustCheck_config(JNIEnv*e,jclass c,jint st,jint ac,jint op,jint fs,jint cl){(void)e;(void)c;assert(!live);stat_error=st;access_error=ac;fail_open=op;fail_fstat=fs;fail_close=cl;opens=0;}
JNIEXPORT jint JNICALL Java_FileTrustCheck_opens(JNIEnv*e,jclass c){(void)e;(void)c;assert(!live);return opens;}
''')
java=w/'FileTrustCheck.java';java.write_text(r'''
import java.io.*;
import java.nio.file.*;
import java.security.*;
import javax.net.ssl.*;
public class FileTrustCheck {
 static native void install();static native void config(int stat,int access,int open,int fstat,int close);static native int opens();
 public static void main(String[] args)throws Exception {
  System.load(args[0]);boolean ps5=Boolean.parseBoolean(args[1]);Path trust=Path.of(args[2]);
  // Establish expected target certificate count with normal real file IO first.
  KeyStore store=KeyStore.getInstance(KeyStore.getDefaultType());try(var in=Files.newInputStream(trust)){store.load(in,null);}int expected=store.size();if(expected==0)throw new AssertionError("Empty source store");
  File file=trust.toFile();long length=file.length(),modified=file.lastModified();install();
  if(ps5){
   if(!file.isFile()||!file.canRead()||file.length()!=length||file.lastModified()!=modified||opens()==0)throw new AssertionError("Descriptor metadata mismatch");
   if(file.canExecute())throw new AssertionError("Execute inferred");
   if(trust.resolveSibling("missing-cacerts").toFile().exists())throw new AssertionError("Missing file invented");
   for(int fault=0;fault<3;fault++){config(1,1,fault==0?1:0,fault==1?1:0,fault==2?1:0);if(file.isFile()||file.canRead())throw new AssertionError("Failure accepted");opens();}
   config(13,13,0,0,0);if(file.isFile()||file.canRead()||opens()!=0)throw new AssertionError("EACCES bypassed");
   config(0,0,0,0,0);if(!file.isFile()||!file.canRead()||opens()!=0)throw new AssertionError("Normal stat/access changed");
  } else {if(file.isFile()||file.canRead()||opens()!=0)throw new AssertionError("Desktop denial changed");}
  config(1,1,0,0,0);
  System.setProperty("javax.net.ssl.trustStore",trust.toString());
  TrustManagerFactory factory=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());factory.init((KeyStore)null);
  X509TrustManager manager=(X509TrustManager)factory.getTrustManagers()[0];int actual=manager.getAcceptedIssuers().length;
  if(actual!=(ps5?expected:0))throw new AssertionError("Expected "+(ps5?expected:0)+" anchors, got "+actual);
  if(ps5&&args.length>3)Class.forName(args[3]).getMethod("main",String[].class).invoke(null,(Object)java.util.Arrays.copyOfRange(args,4,args.length));
  System.out.println("PASS: actual java.io metadata natives/real descriptors, EPERM fallback vs unchanged desktop, real missing/open/fstat/close failures, no execute/EACCES inference, exact length/mtime; default JSSE anchors="+actual+" PS5="+ps5);
 }
}
''')
subprocess.run([str(jdk/'bin/javac'),str(java)],check=True)
for ps5 in [True,False]:
 lib=w/('ps5.dylib' if ps5 else 'desktop.dylib')
 subprocess.run(['clang','-std=c11','-DMACOSX=1',*(['-D__PROSPERO__=1'] if ps5 else []),'-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-fsanitize=undefined','-dynamiclib','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(c),'-o',str(lib)],check=True)
 subprocess.run([str(jdk/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-Xcheck:jni','-cp',str(w)+(os.pathsep+args.class_path if args.class_path else ''),'FileTrustCheck',str(lib),str(ps5).lower(),str(r/'build/java25/boot-image/lib/security/cacerts'),*([args.run_class,*args.run_arg] if args.run_class else [])],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0:halt_on_error=1'})
