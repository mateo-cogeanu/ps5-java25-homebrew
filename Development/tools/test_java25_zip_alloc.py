#!/usr/bin/env python3
"""Run actual Inflater/Deflater JNI with forced libc failure and bounded mmap fallback."""
from pathlib import Path
import subprocess,re
r=Path(__file__).resolve().parents[1];w=r/'build/java25/zip-alloc-test';w.mkdir(parents=True,exist_ok=True);base=r/'.tools/java25/openjdk/src/java.base/share/native/libzip';headers=r/'.tools/java25/openjdk/build/ps5-bootstrap/support/headers/java.base';jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
prefix=r'''
#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <errno.h>
#include <zlib.h>
extern int zip_deny,zip_budget,zip_live;
static void*test_malloc(size_t bytes){if(zip_deny){errno=ENOMEM;return NULL;}return malloc(bytes);}
static void*test_mmap(void*a,size_t n,int p,int f,int d,off_t o){if(zip_budget==0){errno=ENOMEM;return MAP_FAILED;}if(zip_budget>0)--zip_budget;void*v=mmap(a,n,p,f,d,o);if(v!=MAP_FAILED)++zip_live;return v;}
static int test_munmap(void*p,size_t n){int e=munmap(p,n);if(e==0)--zip_live;return e;}
#define malloc test_malloc
#define mmap test_mmap
#define munmap test_munmap
#include "ps5ZipAlloc.h"
#undef malloc
#undef mmap
#undef munmap
#define __PROSPERO__ 1
#define jlong_zero 0LL
#define jlong_to_ptr(n) ((void*)(intptr_t)n)
#define ptr_to_jlong(p) ((jlong)(intptr_t)p)
#define CHECK_NULL(p) if(!(p))return
static void JNU_ThrowByName(JNIEnv*env,const char*name,const char*message){jclass t=(*env)->FindClass(env,name);if(t)(*env)->ThrowNew(env,t,message?message:"");}
#define JNU_ThrowOutOfMemoryError(e,m) JNU_ThrowByName(e,"java/lang/OutOfMemoryError",m)
#define JNU_ThrowInternalError(e,m) JNU_ThrowByName(e,"java/lang/InternalError",m)
#define JNU_ThrowIllegalArgumentException(e,m) JNU_ThrowByName(e,"java/lang/IllegalArgumentException",m)
'''
sources=[];hookparts=[]
for name in ('Inflater','Deflater'):
 s=(base/(name+'.c')).read_text()
 for include in ('jlong.h','jvm.h','jni_util.h'):s=s.replace('#include "'+include+'"','')
 p=w/(name+'.c');p.write_text(prefix+s);sources.append(str(p))
 h=(headers/('java_util_zip_'+name+'.h')).read_text()
 methods=re.findall(r'Method:\s*(\w+)\s*\* Signature:\s*(\S+).*?JNICALL\s+(Java_\w+)',h,re.S)
 assert methods
 hookparts.append('jclass '+name+'=(*env)->FindClass(env,"java/util/zip/'+name+'");\nJNINativeMethod '+name+'Hooks[]={'+','.join('{"'+m+'","'+sig+'",(void*)'+symbol+'}' for m,sig,symbol in methods)+'};\nif((*env)->RegisterNatives(env,'+name+','+name+'Hooks,sizeof('+name+'Hooks)/sizeof(JNINativeMethod)))abort();\n')
bridge=r'''
#include <jni.h>
#include <stdlib.h>
#include "java_util_zip_Inflater.h"
#include "java_util_zip_Deflater.h"
int zip_deny=0,zip_budget=-1,zip_live=0;
JNIEXPORT void JNICALL Java_ZipAllocTest_mode(JNIEnv*env,jclass c,jint deny,jint budget){zip_deny=deny;zip_budget=budget;}
JNIEXPORT jint JNICALL Java_ZipAllocTest_live(JNIEnv*env,jclass c){return zip_live;}
JNIEXPORT void JNICALL Java_ZipAllocTest_install(JNIEnv*env,jclass c){
'''+''.join(hookparts)+r'''
Java_java_util_zip_Inflater_initIDs(env,Inflater);
}
''';p=w/'bridge.c';p.write_text(bridge);sources.append(str(p))
subprocess.run(['clang','-O1','-g','-dynamiclib','-undefined','dynamic_lookup','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(headers),'-I'+str(base),*sources,'-lz','-o',str(w/'libtest.dylib')],check=True)
p=w/'ZipAllocTest.java';p.write_text(r'''
import java.util.*;import java.util.zip.*;import java.nio.file.*;import java.nio.*;
public class ZipAllocTest{
 static native void install();static native void mode(int deny,int budget);static native int live();
 static void roundtrip(boolean raw)throws Exception{
  byte[]input=new byte[120000],packed=new byte[121000],output=new byte[120000];new Random(37).nextBytes(input);
  int size;try(Deflater d=new Deflater(6,raw)){d.setInput(input);d.finish();size=d.deflate(packed);if(!d.finished())throw new AssertionError("deflate");}
  try(Inflater i=new Inflater(raw)){i.setInput(packed,0,size);if(i.inflate(output)!=input.length||!i.finished()||!Arrays.equals(input,output))throw new AssertionError("inflate");i.reset();}
  if(live()!=0)throw new AssertionError("mapped leak "+live());
 }
 public static void main(String[]args)throws Exception{
 System.load(args[0]);install();
 mode(0,-1);roundtrip(false);roundtrip(true);
 mode(1,-1);for(int n=0;n<64;n++){roundtrip(false);roundtrip(true);}
 Path jar=Files.createTempFile("ps5-inflate-",".zip");Files.delete(jar);
 try{
  try(var fs=FileSystems.newFileSystem(jar,Map.of("create","true"))){Files.writeString(fs.getPath("/asset"),"datapack".repeat(10000));}
  try(var fs=FileSystems.newFileSystem(jar,Map.of())){if(!Files.readString(fs.getPath("/asset")).equals("datapack".repeat(10000)))throw new AssertionError("ZipFS content");}
 }finally{Files.deleteIfExists(jar);}
 for(int budget:new int[]{0,1}){mode(1,budget);try(Inflater ignored=new Inflater()){throw new AssertionError("exhaustion accepted");}catch(OutOfMemoryError expected){}if(live()!=0)throw new AssertionError("failed init leak");}
 mode(1,2);try(Deflater ignored=new Deflater()){throw new AssertionError("deflater exhaustion accepted");}catch(OutOfMemoryError expected){}if(live()!=0)throw new AssertionError("deflater failed init leak");
 mode(1,-1);System.out.println("PASS: actual complete Inflater/Deflater JNI and zlib callbacks, native/mapped raw+wrapped128 roundtrips, real ZipFS compressed asset, allocation-budget failure cleanup and genuine OOM");
 }
}''');subprocess.run([str(jdk/'bin/javac'),'-d',str(w),str(p)],check=True);subprocess.run([str(jdk/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-cp',str(w),'ZipAllocTest',str(w/'libtest.dylib')],check=True)
# Sanitizers on the actual allocator and actual zlib under refused libc allocation.
p=w/'allocator.c';p.write_text(r'''
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <zlib.h>
static void*refuse(size_t n){(void)n;errno=ENOMEM;return NULL;}
#define malloc refuse
#include "ps5ZipAlloc.h"
#undef malloc
int main(){
 errno=EBUSY;unsigned char*p=ps5_zip_calloc(3,100);assert(p&&errno==EBUSY&&((uintptr_t)p%_Alignof(max_align_t))==0);for(int i=0;i<300;i++)assert(p[i]==0);ps5_zip_free(p);assert(errno==EBUSY);
 assert(ps5_zip_calloc(SIZE_MAX,2)==NULL&&errno==ENOMEM);assert(ps5_zip_calloc(1,SIZE_MAX)==NULL&&errno==ENOMEM);
 for(int i=0;i<1024;i++){z_stream s={0};s.zalloc=ps5_zip_zalloc;s.zfree=ps5_zip_zfree;assert(inflateInit(&s)==Z_OK);assert(inflateEnd(&s)==Z_OK);}
 return 0;
}
''');subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined','-I'+str(base),str(p),'-lz','-o',str(w/'allocator')],check=True);subprocess.run([str(w/'allocator')],check=True);print('PASS: actual allocator ASan/UBSan zeroing/alignment/overflow/errno and1024 real zlib lifetimes')
