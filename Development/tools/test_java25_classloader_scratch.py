#!/usr/bin/env python3
"""Exercise actual ClassLoader.c JNI with forced heap/mapping allocation failures."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'build/java25/classloader-scratch-test';WORK.mkdir(exist_ok=True)
SRC=ROOT/'.tools/java25/openjdk/src';JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
java=r'''
import java.nio.file.*;
public class ClassLoaderMemoryCheck extends ClassLoader {
 native Class<?> define0(byte[] data,int offset,int length,boolean denyHeap,boolean denyMap,String source);
 static native Class<?> hidden0(byte[] data);
 native Class<?> direct0(java.nio.ByteBuffer data,int length,String source);
 static native long outstanding();
 static void clean(){if(outstanding()!=0)throw new AssertionError("Scratch leak");}
 public static void main(String[] args)throws Exception {
  System.load(args[0]);byte[] bytes=Files.readAllBytes(Path.of(args[1]));
  for(boolean fallback:new boolean[]{false,true}){
   Class<?> type=new ClassLoaderMemoryCheck().define0(bytes,0,bytes.length,fallback,false,"source/".repeat(200));
   if((int)type.getMethod("answer").invoke(null)!=42)throw new AssertionError("Bad class");clean();
  }
  Class<?> hidden=hidden0(bytes);if(!hidden.isHidden()||(int)hidden.getMethod("answer").invoke(null)!=42)throw new AssertionError("Hidden class failed");clean();
  var direct=java.nio.ByteBuffer.allocateDirect(bytes.length);direct.put(bytes);direct.flip();
  Class<?> directType=new ClassLoaderMemoryCheck().direct0(direct,bytes.length,"direct-source/".repeat(150));if((int)directType.getMethod("answer").invoke(null)!=42||direct.get(0)!=bytes[0])throw new AssertionError("Direct class or caller buffer failed");clean();
  try{new ClassLoaderMemoryCheck().define0(new byte[]{1,2,3},0,3,true,false,null);throw new AssertionError("Accepted invalid class");}catch(ClassFormatError expected){}clean();
  try{new ClassLoaderMemoryCheck().define0(bytes,-1,bytes.length,true,false,null);throw new AssertionError("Accepted invalid range");}catch(ArrayIndexOutOfBoundsException expected){}clean();
  try{new ClassLoaderMemoryCheck().define0(bytes,0,bytes.length,true,true,null);throw new AssertionError("Expected OOM");}catch(OutOfMemoryError expected){if(!expected.getMessage().contains("class-byte scratch"))throw expected;}clean();
  System.out.println("PASS: actual JNI class definition, heap and real mmap paths, long UTF source, valid execution, malformed/range/OOM cleanup");
 }
}
'''
bridge=r'''
#include <jni.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <sys/mman.h>
static int deny_heap,deny_map;static long heap_live,map_live;
void *test_heap_allocate(size_t size){if(deny_heap)return NULL;void *p=malloc(size);if(p)heap_live++;return p;}
void test_heap_release(void *p){if(p)heap_live--;free(p);}
void *test_map(void *p,size_t size,int prot,int flags,int fd,off_t offset){if(deny_map){errno=ENOMEM;return MAP_FAILED;}void *r=mmap(p,size,prot,flags,fd,offset);if(r!=MAP_FAILED)map_live++;return r;}
int test_unmap(void *p,size_t size){int r=munmap(p,size);if(!r)map_live--;return r;}
extern jclass Java_java_lang_ClassLoader_defineClass1(JNIEnv*,jclass,jobject,jstring,jbyteArray,jint,jint,jobject,jstring);
JNIEXPORT jclass JNICALL Java_ClassLoaderMemoryCheck_define0(JNIEnv *env,jobject loader,jbyteArray data,jint offset,jint size,jboolean heap,jboolean map,jstring source){deny_heap=heap;deny_map=map;return Java_java_lang_ClassLoader_defineClass1(env,NULL,loader,NULL,data,offset,size,NULL,source);}
extern jclass Java_java_lang_ClassLoader_defineClass0(JNIEnv*,jclass,jobject,jclass,jstring,jbyteArray,jint,jint,jobject,jboolean,jint,jobject);
extern jclass Java_java_lang_ClassLoader_defineClass2(JNIEnv*,jclass,jobject,jstring,jobject,jint,jint,jobject,jstring);
JNIEXPORT jclass JNICALL Java_ClassLoaderMemoryCheck_hidden0(JNIEnv *env,jclass type,jbyteArray data){deny_heap=1;deny_map=0;return Java_java_lang_ClassLoader_defineClass0(env,NULL,NULL,type,NULL,data,0,(*env)->GetArrayLength(env,data),NULL,JNI_FALSE,2,NULL);}
JNIEXPORT jclass JNICALL Java_ClassLoaderMemoryCheck_direct0(JNIEnv *env,jobject loader,jobject data,jint size,jstring source){deny_heap=1;deny_map=0;return Java_java_lang_ClassLoader_defineClass2(env,NULL,loader,NULL,data,0,size,NULL,source);}
JNIEXPORT jlong JNICALL Java_ClassLoaderMemoryCheck_outstanding(JNIEnv *env,jclass type){return heap_live+map_live;}
'''
(WORK/'ClassLoaderMemoryCheck.java').write_text(java);(WORK/'ClassLoaderScratchFixture.java').write_text('public class ClassLoaderScratchFixture {public static int answer(){return 42;}}\n');(WORK/'bridge.c').write_text(bridge)
incs=[JDK/'include',JDK/'include/darwin',SRC/'java.base/share/native/libjava',SRC/'java.base/unix/native/libjava',SRC/'hotspot/share/include',SRC/'hotspot/os/posix/include',ROOT/'.tools/java25/openjdk/build/ps5-bootstrap/support/headers/java.base']
common=['clang','-std=c11','-fsanitize=undefined',*['-I'+str(p) for p in incs]]
subprocess.run([*common,'-D__PROSPERO__','-Dmalloc=test_heap_allocate','-Dfree=test_heap_release','-Dmmap=test_map','-Dmunmap=test_unmap','-c',str(SRC/'java.base/share/native/libjava/ClassLoader.c'),'-o',str(WORK/'loader.o')],check=True)
subprocess.run([*common,'-c',str(WORK/'bridge.c'),'-o',str(WORK/'bridge.o')],check=True)
subprocess.run(['clang','-fsanitize=undefined','-dynamiclib','-undefined','dynamic_lookup',str(WORK/'loader.o'),str(WORK/'bridge.o'),'-o',str(WORK/'loader-check.dylib')],check=True)
subprocess.run([str(JDK/'bin/javac'),'-d',str(WORK),str(WORK/'ClassLoaderMemoryCheck.java'),str(WORK/'ClassLoaderScratchFixture.java')],check=True)
subprocess.run([str(JDK/'bin/java'),'--enable-native-access=ALL-UNNAMED','-Xverify:all','-cp',str(WORK),'ClassLoaderMemoryCheck',str(WORK/'loader-check.dylib'),str(WORK/'ClassLoaderScratchFixture.class')],check=True)
