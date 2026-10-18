#!/usr/bin/env python3
"""Actual NativeLibraries JNI lookup bodies under injected name-allocation failures."""
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parents[1];w=r/'build/java25/native-library-name-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(r/'.tools/java25/openjdk/src/java.base/share/native/libjava/NativeLibraries.c').read_text()
helper=s[s.index('#ifdef __PROSPERO__'):s.index('typedef jint (JNICALL *JNI_OnLoad_t)')]
a=s.index('static void *findJniFunction(');b=s.index('\n/*',a);find=s[a:b]
a=s.index('JNIEXPORT jstring JNICALL\nJava_jdk_internal_loader_NativeLibraries_findBuiltinLib');lookup=s[a:].replace('Java_jdk_internal_loader_NativeLibraries_findBuiltinLib','Java_LibraryNameCheck_lookup')
c=w/'bridge.c';c.write_text(r'''
#include <jni.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <errno.h>
#include <sys/mman.h>
#include <unistd.h>
static int mode,calls,mapcalls,heap_live,map_live,lookups;
static void* alloc(size_t n){int call=++calls;if(mode==1||mode==2||mode==3||(mode==4&&call==2)||(mode==5&&call==1)){errno=ENOMEM;return NULL;}void*p=malloc(n);if(p)heap_live++;return p;}
static void release(void*p){if(p){heap_live--;free(p);}}
static void* map(void*p,size_t n,int prot,int flags,int fd,off_t off){int call=++mapcalls;if(mode==2||(mode==3&&call==2)){errno=ENOMEM;return MAP_FAILED;}p=mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED)map_live++;return p;}
static int unmap(void*p,size_t n){int rc=munmap(p,n);if(!rc)map_live--;return rc;}
#define malloc alloc
#define free release
#define mmap map
#define munmap unmap
#define jio_fprintf fprintf
''' +helper+r'''
#undef malloc
#undef free
#undef mmap
#undef munmap
static void*procHandle;
#define JNI_LIB_PREFIX "lib"
#define JNI_LIB_SUFFIX ".so"
static void*getProcessHandle(void){return (void*)1;}
static void*JVM_FindLibraryEntry(void*h,const char*name){assert(h==(void*)1);lookups++;return !strcmp(name,"JNI_OnLoad_management")||!strcmp(name,"JNI_OnLoad_probe")||!strcmp(name,"JNI_OnUnload_probe")||!strcmp(name,"JNI_OnLoad")?(void*)2:NULL;}
static void throw(JNIEnv*e,const char*type,const char*text){jclass c=(*e)->FindClass(e,type);if(c){(*e)->ThrowNew(e,c,text);(*e)->DeleteLocalRef(e,c);}}
static void JNU_ThrowOutOfMemoryError(JNIEnv*e,const char*t){throw(e,"java/lang/OutOfMemoryError",t);}
static void JNU_ThrowInternalError(JNIEnv*e,const char*t){throw(e,"java/lang/InternalError",t);}
static const char*JNU_GetStringPlatformChars(JNIEnv*e,jstring s,void*p){(void)p;return (*e)->GetStringUTFChars(e,s,NULL);}
static void JNU_ReleaseStringPlatformChars(JNIEnv*e,jstring s,const char*p){(*e)->ReleaseStringUTFChars(e,s,p);}
static jstring JNU_NewStringPlatform(JNIEnv*e,const char*s){if(mode==6){JNU_ThrowOutOfMemoryError(e,"injected Java string failure");return NULL;}return (*e)->NewStringUTF(e,s);}
''' +find+'\n'+lookup+r'''
JNIEXPORT void JNICALL Java_LibraryNameCheck_config(JNIEnv*e,jclass c,jint m){(void)e;(void)c;assert(heap_live==0&&map_live==0);mode=m;calls=mapcalls=lookups=0;}
JNIEXPORT void JNICALL Java_LibraryNameCheck_clean(JNIEnv*e,jclass c){(void)e;(void)c;assert(heap_live==0&&map_live==0);}
JNIEXPORT void JNICALL Java_LibraryNameCheck_symbols(JNIEnv*e,jclass c){(void)c;assert(findJniFunction(e,(void*)1,"probe",JNI_FALSE)==(void*)2);if((*e)->ExceptionCheck(e))return;assert(findJniFunction(e,(void*)1,NULL,JNI_TRUE)==(void*)2);}
JNIEXPORT jboolean JNICALL Java_LibraryNameCheck_usedMap(JNIEnv*e,jclass c){(void)e;(void)c;return mapcalls>0;}
''')
j=w/'LibraryNameCheck.java';j.write_text(r'''
public class LibraryNameCheck {
 static native String lookup(String name);static native void config(int mode);static native void clean();static native void symbols();static native boolean usedMap();
 static void expect(String name,String expected){String actual=lookup(name);if(!java.util.Objects.equals(actual,expected))throw new AssertionError(name+" -> "+actual);clean();}
 public static void main(String[] args){System.load(args[0]);boolean ps5=Boolean.parseBoolean(args[1]);
  if(!ps5){config(1);try{lookup("libmanagement.so");throw new AssertionError("Desktop denial accepted");}catch(OutOfMemoryError expected){}clean();System.out.println("PASS: unchanged desktop body reproduces bare native-name OutOfMemoryError");return;}
  for(int mode:new int[]{0,1,4,5}){config(mode);expect("libmanagement.so","management");if(mode!=0&&!usedMap())throw new AssertionError("Mapping fallback not exercised");config(mode);expect("libmissing.so",null);}
  for(int mode:new int[]{2,3,6}){config(mode);try{lookup("libmanagement.so");throw new AssertionError("Fault accepted "+mode);}catch(OutOfMemoryError expected){}clean();}
  config(0);try{lookup(null);throw new AssertionError("Null accepted");}catch(InternalError expected){}clean();expect(".so",null);expect("lib"+"x".repeat(10000)+".so",null);
  for(int i=0;i<512;i++){config(1);expect("libmanagement.so","management");symbols();clean();}
  config(0);expect("libprobe.so","probe");
  System.out.println("PASS: actual JNI lookup/symbol construction, libc and mapped paths, first/second allocation/map faults, Java-string failure, unknown/short/oversized/null, OnLoad/OnUnload/native names and512 repeated lifetimes without leaks; -Xcheck:jni/UBSan");
 }
}
''')
subprocess.run([str(jdk/'bin/javac'),str(j)],check=True)
for ps5 in [True,False]:
 lib=w/('ps5.dylib' if ps5 else 'desktop.dylib')
 subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE',*(['-D__PROSPERO__=1'] if ps5 else []),'-O1','-g','-fsanitize=undefined','-dynamiclib','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(c),'-o',str(lib)],check=True)
 subprocess.run([str(jdk/'bin/java'),'-Xmixed','-XX:TieredStopAtLevel=1','--enable-native-access=ALL-UNNAMED','-Xcheck:jni','-cp',str(w),'LibraryNameCheck',str(lib),str(ps5).lower()],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0:halt_on_error=1'})
