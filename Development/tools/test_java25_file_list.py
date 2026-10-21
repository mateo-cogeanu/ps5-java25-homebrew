#!/usr/bin/env python3
"""Real File.list/listFiles with actual PS5 JNI body and resident directory parser.

Only an isolated host JVM rebinds list0; platform enumeration is injected.
"""
from pathlib import Path
import subprocess,os,argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--compile-only',action='store_true');args=parser.parse_args()
r=Path(__file__).resolve().parents[1];w=r/'build/java25/file-list-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');inc=r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs'
from java25_direct_memory_fixture import build as build_direct
direct_object=build_direct(r,w,jdk,flags=['-fsanitize=undefined'])
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libjava/UnixFileSystem_md.c').read_text();a=s.index('Java_java_io_UnixFileSystem_list0(');b=s.index('\nJNIEXPORT jboolean JNICALL',a);body='JNIEXPORT jobjectArray JNICALL\n'+s[a:b]
# Reuse the existing host-to-PS5 record serializer, not a canned Java listing.
d=(r/'tools/test_java25_directory.py').read_text();a=d.index('int sceKernelGetdents(');b=d.index('static void throwUnixException',a);adapter=d[a:b]
adapter=adapter.replace(' off_t position=', ' if(mode==2||(mode==3&&++reads>1)){errno=EIO;return (int)0x80020005u;}\n off_t position=')
c=w/'bridge.c';c.write_text(r'''
#include <jni.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
static int mode,reads,live_fds,live_maps,map_calls,desktop_calls;
extern void ps5_test_direct_mode(int);extern int ps5_test_direct_live(void);extern int ps5_test_direct_maps(void);
static int injected_open(const char*p,int flags){if(mode==1){errno=EACCES;return -1;}int fd=open(p,flags);if(fd>=0)live_fds++;return fd;}
static int injected_close(int fd){int result=close(fd);if(!result)live_fds--;if(mode==4){errno=EIO;return -1;}return result;}
static void* injected_map(void*p,size_t n,int prot,int flags,int fd,off_t off){int call=++map_calls;if(mode==7||mode==8||(mode==5&&call==1)||(mode==6&&call==2)){errno=ENOMEM;return MAP_FAILED;}p=mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED)live_maps++;return p;}
static int injected_unmap(void*p,size_t n){int result=munmap(p,n);if(!result)live_maps--;return result;}
#define open injected_open
#define close injected_close
#define mmap injected_map
#define munmap injected_unmap
#include "ps5Directory.h"
#undef open
#undef close
#undef mmap
#undef munmap
''' +adapter+r'''
static DIR* denied_opendir(const char*p){(void)p;desktop_calls++;errno=EPERM;return NULL;}
static struct {jfieldID path;} ids;
#define WITH_FIELD_PLATFORM_STRING(e,file,field,path) for(jstring value=(jstring)(*(e))->GetObjectField(e,file,field);value!=NULL;(*(e))->DeleteLocalRef(e,value),value=NULL) for(const char*path=(*(e))->GetStringUTFChars(e,value,NULL);path!=NULL;(*(e))->ReleaseStringUTFChars(e,value,path),path=NULL)
#define END_PLATFORM_STRING(e,path)
#define CHECK_NULL_RETURN(p,value) if(!(p))return value
static jclass JNU_ClassString(JNIEnv*e){return (*e)->FindClass(e,"java/lang/String");}
static jstring JNU_NewStringPlatform(JNIEnv*e,const char*s){return (*e)->NewStringUTF(e,s);}
#define newStringPlatform JNU_NewStringPlatform
static int JNU_CopyObjectArray(JNIEnv*e,jobjectArray to,jobjectArray from,int n){for(int i=0;i<n;i++){jobject value=(*e)->GetObjectArrayElement(e,from,i);(*e)->SetObjectArrayElement(e,to,i,value);(*e)->DeleteLocalRef(e,value);if((*e)->ExceptionCheck(e))return -1;}return 0;}
#define jio_fprintf fprintf
#define opendir denied_opendir
''' +body+r'''
JNIEXPORT void JNICALL Java_FileListCheck_install(JNIEnv*e,jclass c){(void)c;jclass file=(*e)->FindClass(e,"java/io/File");ids.path=(*e)->GetFieldID(e,file,"path","Ljava/lang/String;");assert(ids.path);jclass fs=(*e)->FindClass(e,"java/io/UnixFileSystem");JNINativeMethod hook={"list0","(Ljava/io/File;)[Ljava/lang/String;",(void*)Java_java_io_UnixFileSystem_list0};assert((*e)->RegisterNatives(e,fs,&hook,1)==0);}
JNIEXPORT void JNICALL Java_FileListCheck_config(JNIEnv*e,jclass c,jint fault){(void)e;(void)c;assert(!live_fds&&!live_maps&&!ps5_test_direct_live());ps5_test_direct_mode(fault==7?-1:fault==8?1:0);mode=fault;reads=map_calls=desktop_calls=0;}
JNIEXPORT void JNICALL Java_FileListCheck_clean(JNIEnv*e,jclass c){(void)e;(void)c;assert(!live_fds&&!live_maps&&!ps5_test_direct_live());
#ifdef __PROSPERO__
 assert(!desktop_calls);
#endif
}
''')
j=w/'FileListCheck.java';j.write_text(r'''
import java.io.*;import java.nio.file.*;import java.util.*;
public class FileListCheck {
 static native void install();static native void config(int fault);static native void clean();
 public static void main(String[]args)throws Exception {
  Path root=Files.createTempDirectory("ps5-file-list-"),empty=Files.createDirectory(root.resolve("empty")),entries=Files.createDirectory(root.resolve("entries"));Set<String> expected=new HashSet<>();
  for(int i=0;i<350;i++){String name="player_"+i+".dat";Files.writeString(entries.resolve(name),"fixture");expected.add(name);}
  Files.writeString(entries.resolve("α-player.dat"),"unicode");expected.add("α-player.dat");Files.createSymbolicLink(root.resolve("alias"),Path.of("entries"));
  System.load(args[0]);install();boolean ps5=Boolean.parseBoolean(args[1]);
  try {
   if(!ps5){if(entries.toFile().list()!=null)throw new AssertionError("Desktop unsupported opendir changed");clean();return;}
   if(empty.toFile().list().length!=0)throw new AssertionError("Empty is not empty");clean();
   for(int i=0;i<128;i++){config(0);String[] names=entries.toFile().list();if(names==null||!new HashSet<>(Arrays.asList(names)).equals(expected))throw new AssertionError("Names changed");File[] files=root.resolve("alias").toFile().listFiles();if(files==null||files.length!=expected.size())throw new AssertionError("listFiles/symlink");for(File f:files)if(!expected.contains(f.getName())||!f.getParentFile().equals(root.resolve("alias").toFile()))throw new AssertionError("Child path changed");clean();}
   if(root.resolve("missing").toFile().list()!=null||entries.resolve("player_0.dat").toFile().list()!=null)throw new AssertionError("Invalid directory accepted");clean();
   for(int fault=1;fault<=6;fault++){config(fault);if(entries.toFile().list()!=null)throw new AssertionError("Failure/partial listing accepted: "+fault);clean();}
   for(int i=0;i<64;i++){config(7);String[] names=entries.toFile().list();if(names==null||!new HashSet<>(Arrays.asList(names)).equals(expected))throw new AssertionError("Direct-backed names changed");clean();if(entries.toFile().listFiles((dir,name)->name.endsWith(".dat")).length!=expected.size())throw new AssertionError("Converter-style filter failed");clean();if(empty.toFile().list().length!=0)throw new AssertionError("Direct empty directory changed");clean();}
   config(8);if(entries.toFile().list()!=null)throw new AssertionError("Partial direct budget accepted");clean();
   config(0);if(entries.toFile().listFiles().length!=expected.size())throw new AssertionError("Recovery failed");clean();
   System.out.println("PASS: actual File.list/listFiles JNI, resident parser with real host enumeration;351 Unicode names/array growth, exact child paths, symlink, empty/missing/file, denied SDK opendir, open/read/partial-read/close/first-second mapping faults, recovery and256 repeated listings without fd/map leaks; forced anonymous refusal then actual shared VM bridge/ledger with real direct storage preserves listings/filters/empty, partial-budget rollback; -Xcheck:jni/UBSan. Host directory/layout adapter, not console proof.");
  }finally{config(0);try(var paths=Files.walk(root)){for(Path p:paths.sorted(Comparator.reverseOrder()).toList())Files.delete(p);}}
  if(args.length>2)Class.forName(args[2]).getMethod("main",String[].class).invoke(null,(Object)Arrays.copyOfRange(args,3,args.length));
 }
}
''')
subprocess.run([str(jdk/'bin/javac'),str(j)],check=True)
for ps5 in [True,False]:
 lib=w/('ps5.dylib' if ps5 else 'desktop.dylib')
 subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE','-DMACOSX=1',*(['-D__PROSPERO__=1'] if ps5 else []),'-O1','-g','-fsanitize=undefined','-dynamiclib','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(inc),str(c),direct_object,'-o',str(lib)],check=True)
 if args.compile_only:continue
 subprocess.run([str(jdk/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-Xcheck:jni','-cp',str(w),'FileListCheck',str(lib),str(ps5).lower()],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0:halt_on_error=1'})
