#!/usr/bin/env python3
"""Actual JNI platform-string conversions with forced native allocation refusal."""
from pathlib import Path
import os,re,subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'build/java25/platform-string-test';WORK.mkdir(parents=True,exist_ok=True)
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(ROOT/'.tools/java25/openjdk/src/java.base/share/native/libjava/jni_util.c').read_text()
def function(name):
 m=re.search(r'(?:static |JNIEXPORT )?(?:const char\s*\*|void)(?:\s+JNICALL)?\s*\n?'+name+r'\([^;]+?\)\s*\{',s);assert m,name
 start=m.start();pos=m.end();depth=1
 # Selected native functions have no brace characters in string literals.
 while depth:
  c=s[pos];depth+=(c=='{')-(c=='}');pos+=1
 return s[start:pos]+'\n'
helper=s[s.index('#ifdef __PROSPERO__\ntypedef union'):s.index('/* Due to a bug')]
helper='''
int JNU_PS5DirectScratchEnabled(void){return 0;}
size_t sceKernelGetDirectMemorySize(void){return 0;}
int sceKernelAllocateDirectMemory(int64_t a,int64_t b,size_t c,size_t d,int e,int64_t*f){return -1;}
int sceKernelMapDirectMemory(void**a,size_t b,int c,int d,int64_t e,size_t f){return -1;}
int sceKernelMunmap(void*a,size_t b){return -1;}
int sceKernelReleaseDirectMemory(int64_t a,size_t b){return -1;}
''' + (ROOT/'.tools/java25/openjdk/src/java.base/share/native/libjava/ps5_core_direct_scratch.h').read_text() + helper
macro=s[s.index('#define MALLOC_MIN4'):s.index('\n\n/**')]
bridge=r'''
#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdint.h>
#include <limits.h>
#include <errno.h>
#include <sys/mman.h>
#include <unistd.h>
#include <assert.h>
static int deny_heap,deny_map;static long heap_live,map_live;static void *map_address;static size_t map_length;
static void *test_malloc(size_t n){if(deny_heap)return NULL;void *p=malloc(n);if(p)heap_live++;return p;}
static void test_free(void *p){if(p)heap_live--;free(p);}
static void *test_map(void *p,size_t n,int prot,int flags,int fd,off_t off){if(deny_map){errno=ENOMEM;return MAP_FAILED;}void *r=mmap(p,n,prot,flags,fd,off);if(r!=MAP_FAILED){map_live++;map_address=r;map_length=n;}return r;}
static int test_unmap(void *p,size_t n){assert(p==map_address&&n==map_length);int r=munmap(p,n);if(!r)map_live--;return r;}
static void throw_named(JNIEnv *env,const char *name,const char *msg){jclass c=(*env)->FindClass(env,name);if(c)(*env)->ThrowNew(env,c,msg);}
#define JNU_ThrowOutOfMemoryError(e,m) throw_named(e,"java/lang/OutOfMemoryError",m)
#define JNU_ThrowIllegalArgumentException(e,m) throw_named(e,"java/lang/IllegalArgumentException",m)
#define jio_fprintf fprintf
#define java_lang_String_LATIN1 0
#define malloc test_malloc
#define free test_free
#define mmap test_map
#define munmap test_unmap
static jmethodID String_getBytes_ID;static jfieldID String_coder_ID,String_value_ID;static jobject jnuCharset;
'''+helper+macro+'\n'
for name in ['getString8859_1Chars','getString646_USChars','getStringCp1252Chars','getStringBytes','getStringUTF8','JNU_ReleaseStringPlatformChars']:bridge+=function(name)
bridge+=r'''
JNIEXPORT jbyteArray JNICALL Java_PlatformStringCheck_convert(JNIEnv *env,jclass cls,jstring value,jint kind,jboolean strict,jint mode,jint length){
 jclass str=(*env)->FindClass(env,"java/lang/String");
 String_coder_ID=(*env)->GetFieldID(env,str,"coder","B");String_value_ID=(*env)->GetFieldID(env,str,"value","[B");
 String_getBytes_ID=(*env)->GetMethodID(env,str,"getBytes","(Ljava/nio/charset/Charset;)[B");
 jclass cs=(*env)->FindClass(env,"java/nio/charset/StandardCharsets");jfieldID utf=(*env)->GetStaticFieldID(env,cs,"UTF_8","Ljava/nio/charset/Charset;");jnuCharset=(*env)->GetStaticObjectField(env,cs,utf);
 deny_heap=mode&1;deny_map=mode&2;
 const char *p=kind==0?getStringUTF8(env,value,strict):kind==1?getString8859_1Chars(env,value,strict):kind==2?getString646_USChars(env,value,strict):kind==3?getStringCp1252Chars(env,value,strict):getStringBytes(env,value,strict);
 jbyteArray result=NULL;
 if(p){assert(p[length]==0);result=(*env)->NewByteArray(env,length);if(result)(*env)->SetByteArrayRegion(env,result,0,length,(const jbyte*)p);errno=EACCES;JNU_ReleaseStringPlatformChars(env,value,p);assert(errno==EACCES);}
 assert(heap_live==0&&map_live==0);return result;
}
JNIEXPORT void JNICALL Java_PlatformStringCheck_limits(JNIEnv *env,jclass cls){
 assert(MALLOC_MIN4(-1)==NULL);assert(MALLOC_MIN4(INT_MAX)==NULL);
#ifdef __PROSPERO__
 assert(platform_string_allocate(SIZE_MAX)==NULL);
#endif
}
'''
java=r'''
import java.nio.charset.*;import java.util.*;
public class PlatformStringCheck {
 static native byte[] convert(String value,int kind,boolean strict,int mode,int length);
 static native void limits();
 static byte[] legacy(String value,Charset cs){var bytes=new java.io.ByteArrayOutputStream();for(char c:value.toCharArray())bytes.writeBytes(String.valueOf(c).getBytes(cs));return bytes.toByteArray();}
 interface Action{void run();}static void expect(Class<? extends Throwable> type,Action a){try{a.run();}catch(Throwable t){if(type.isInstance(t))return;throw t;}throw new AssertionError(type);}
 public static void main(String[] args){System.load(args[0]);limits();
  for(int mode:new int[]{0,1})for(boolean strict:new boolean[]{false,true})for(int kind=0;kind<5;kind++) {
   Charset cs=kind==1?StandardCharsets.ISO_8859_1:kind==2?StandardCharsets.US_ASCII:kind==3?Charset.forName("windows-1252"):StandardCharsets.UTF_8;
   for(String value:new String[]{"","/app/assets/java25/conf/logging.properties","café","€日本語😀","path/".repeat(5000)}) {
    byte[] expected=(kind>=1&&kind<=3)?legacy(value,cs):value.getBytes(cs),got=convert(value,kind,strict,mode,expected.length);
    if(!Arrays.equals(expected,got))throw new AssertionError("encoding "+kind+" mode "+mode);
   }
   final int k=kind;
   expect(IllegalArgumentException.class,()->convert("bad\0path",k,true,mode,8));
   if(kind==0||kind==4)expect(IllegalArgumentException.class,()->convert("日本\0path",k,true,mode,11));
   byte[] zero="a\0b".getBytes(cs);if(!Arrays.equals(zero,convert("a\0b",kind,false,mode,zero.length)))throw new AssertionError("permissive NUL");
  }
  for(int kind=0;kind<5;kind++){final int k=kind;expect(OutOfMemoryError.class,()->convert("path",k,true,3,4));}
  System.out.println("PASS: actual JNI platform-string conversion, UTF-8 Latin1/non-Latin1, charset paths, libc/mmap, long/empty/NUL strings, allocation failure, bounds and matching release");
 }
}
'''
(WORK/'bridge.c').write_text(bridge);(WORK/'PlatformStringCheck.java').write_text(java)
common=['clang','-std=c11','-fsanitize=undefined','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin')]
for ps5 in [False,True]:
 lib=WORK/('string-ps5.dylib' if ps5 else 'string-host.dylib');subprocess.run([*common,*(['-D__PROSPERO__'] if ps5 else []),'-dynamiclib',str(WORK/'bridge.c'),'-o',str(lib)],check=True)
 if ps5:
  subprocess.run([str(JDK/'bin/javac'),'-d',str(WORK),str(WORK/'PlatformStringCheck.java')],check=True)
  subprocess.run([str(JDK/'bin/java'),'--enable-native-access=ALL-UNNAMED','-Xcheck:jni','-cp',str(WORK),'PlatformStringCheck',str(lib)],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0'})
print('PASS: ordinary platform branch compiles')
