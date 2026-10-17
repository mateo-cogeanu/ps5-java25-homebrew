#!/usr/bin/env python3
"""Run actual io_util.c bulk read/write bodies through real JNI and POSIX I/O."""
from pathlib import Path
import os
import subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/java25/io-scratch-test';WORK.mkdir(parents=True,exist_ok=True)
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(ROOT/'.tools/java25/openjdk/src/java.base/share/native/libjava/io_util.c').read_text()
# Preserve actual validation, allocation, JNI-copy, I/O loop and cleanup bodies.
actual=s[s.index('static int\noutOfBounds'):s.index('\nvoid\nwriteSingle')]
actual+='\n'+s[s.index('void\nwriteBytes'):s.index('\nvoid\nthrowFileNotFoundException')]
bridge=r'''
#include <jni.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <assert.h>
static int deny_heap,deny_map,fd_value,io_fail;
static long heap_live,map_live; static void *mapped_pointer; static size_t mapped_length;
static void *test_malloc(size_t n){if(deny_heap)return NULL;void *p=malloc(n);if(p)heap_live++;return p;}
static void test_free(void *p){if(p)heap_live--;free(p);}
static void *test_mmap(void *p,size_t n,int prot,int flags,int fd,off_t off){if(deny_map){errno=ENOMEM;return MAP_FAILED;}void *r=mmap(p,n,prot,flags,fd,off);if(r!=MAP_FAILED){map_live++;mapped_pointer=r;mapped_length=n;}return r;}
static int test_munmap(void *p,size_t n){assert(p==mapped_pointer&&n==mapped_length);int r=munmap(p,n);if(!r)map_live--;return r;}
static void throw_named(JNIEnv *env,const char *name,const char *message){jclass c=(*env)->FindClass(env,name);if(c)(*env)->ThrowNew(env,c,message);}
#define JNU_ThrowNullPointerException(e,m) throw_named(e,"java/lang/NullPointerException",m)
#define JNU_ThrowByName throw_named
#define JNU_ThrowOutOfMemoryError(e,m) throw_named(e,"java/lang/OutOfMemoryError",m)
#define JNU_ThrowIOException(e,m) throw_named(e,"java/io/IOException",m)
#define JNU_ThrowIOExceptionWithLastError(e,m) throw_named(e,"java/io/IOException",m)
#define IS_NULL(p) ((p)==NULL)
#define FD int
#define getFD(e,o,f) fd_value
#define BUF_SIZE 8192
#define jio_fprintf fprintf
static int io_read(int fd,void *p,int n){if(io_fail){errno=EIO;return -1;}return (int)read(fd,p,n);}
static int io_write(int fd,const void *p,int n){if(io_fail){errno=EIO;return -1;}return (int)write(fd,p,n>4096?4096:n);}
#define IO_Read io_read
#define IO_Write io_write
#define IO_Append io_write
#define malloc test_malloc
#define free test_free
#define mmap test_mmap
#define munmap test_munmap
'''
bridge+=actual+r'''
#undef malloc
#undef free
#undef mmap
#undef munmap
JNIEXPORT jint JNICALL Java_IoScratchCheck_transfer(JNIEnv *env,jclass cls,jstring path,jbyteArray data,jint off,jint len,jboolean output,jint mode){
 deny_heap=mode&1;deny_map=mode&2;io_fail=mode&4;
 const char *name=(*env)->GetStringUTFChars(env,path,NULL);if(!name)return -1;
 fd_value=open(name,output?(O_WRONLY|O_APPEND):O_RDONLY,0600);
 (*env)->ReleaseStringUTFChars(env,path,name);
 int owned=fd_value;if(mode&8)fd_value=-1;
 jint result=0;if(output)writeBytes(env,NULL,data,off,len,JNI_TRUE,NULL);else result=readBytes(env,NULL,data,off,len,NULL);
 if(owned>=0)close(owned);
 assert(heap_live==0&&map_live==0);
 return result;
}
'''
bridge+=r'''
JNIEXPORT jint JNICALL Java_IoScratchCheck_readAll(JNIEnv *env,jclass cls,jstring path,jbyteArray data,jint off,jint len,jint mode){
 deny_heap=mode&1;deny_map=mode&2;io_fail=0;
 const char* name=(*env)->GetStringUTFChars(env,path,NULL);if(!name)return -1;
 fd_value=open(name,O_RDONLY);(*env)->ReleaseStringUTFChars(env,path,name);assert(fd_value>=0);
 jint total=0;while(total<len){jint got=readBytes(env,NULL,data,off+total,len-total,NULL);if((*env)->ExceptionCheck(env))break;if(got<0)break;assert(got>0&&got<=BUF_SIZE);total+=got;}
 close(fd_value);assert(heap_live==0&&map_live==0);return total;
}
'''
bridge+=r'''
static jfieldID raf_fd,fd_number;static int raf_reads;
static jint bounded_raf_read(JNIEnv* env,jobject self,jbyteArray bytes,jint off,jint len){
 jobject fd=(*env)->GetObjectField(env,self,raf_fd);fd_value=(*env)->GetIntField(env,fd,fd_number);(*env)->DeleteLocalRef(env,fd);
 deny_heap=1;deny_map=1;io_fail=0;++raf_reads;return readBytes(env,self,bytes,off,len,NULL);
}
JNIEXPORT void JNICALL Java_IoScratchCheck_installRandomAccessReader(JNIEnv* env,jclass cls){
 jclass raf=(*env)->FindClass(env,"java/io/RandomAccessFile");jclass fd=(*env)->FindClass(env,"java/io/FileDescriptor");
 raf_fd=(*env)->GetFieldID(env,raf,"fd","Ljava/io/FileDescriptor;");fd_number=(*env)->GetFieldID(env,fd,"fd","I");
 JNINativeMethod method={"readBytes0","([BII)I",(void*)&bounded_raf_read};assert((*env)->RegisterNatives(env,raf,&method,1)==0);
}
JNIEXPORT jint JNICALL Java_IoScratchCheck_rafReads(JNIEnv* env,jclass cls){return raf_reads;}
'''
java=r'''
import java.nio.file.*;import java.util.*;import java.io.*;
public class IoScratchCheck {
 static native int transfer(String path,byte[] data,int off,int len,boolean output,int mode);
 static native int readAll(String path,byte[] data,int off,int len,int mode);
 static native void installRandomAccessReader();
 static native int rafReads();
 interface Action {void run()throws Exception;}
 static void expect(Class<? extends Throwable> type,Action a)throws Exception {try{a.run();}catch(Throwable t){if(type.isInstance(t))return;throw t;}throw new AssertionError("Expected "+type);}
 public static void main(String[] args)throws Exception {
  System.load(args[0]);Path f=Path.of(args[1]);byte[] payload=new byte[65537];new Random(42).nextBytes(payload);
  for(int mode:new int[]{0,1,3}) {
   Files.write(f,payload);byte[] out=new byte[payload.length+14];
   int n=transfer(f.toString(),out,7,payload.length,false,mode);
   if(n!=8192||!Arrays.equals(Arrays.copyOf(payload,n),Arrays.copyOfRange(out,7,7+n)))throw new AssertionError("read mismatch");
   Arrays.fill(out,(byte)0);n=readAll(f.toString(),out,7,payload.length,mode);
   if(n!=payload.length||!Arrays.equals(payload,Arrays.copyOfRange(out,7,7+n))||out[6]!=0||out[7+n]!=0)throw new AssertionError("full short-read loop mismatch");
   if(mode==3)continue; // Writes retain real allocation failure; tested below.
   Files.write(f,new byte[0]);transfer(f.toString(),out,7,payload.length,true,mode);
   if(!Arrays.equals(payload,Files.readAllBytes(f)))throw new AssertionError("partial write mismatch");
   Files.write(f,new byte[]{1,2,3});if(transfer(f.toString(),out,0,payload.length,false,mode)!=3)throw new AssertionError("short read");
   Files.write(f,new byte[0]);if(transfer(f.toString(),out,0,payload.length,false,mode)!=-1)throw new AssertionError("EOF");
  }
  for(boolean output:new boolean[]{false,true}) {
   for(int size:new int[]{0,1,8192,8193}) {Files.write(f,new byte[size]);transfer(f.toString(),new byte[size],0,size,output,3);if(size>8192)throw new AssertionError("both backends should fail");}
  }
 }
}
'''
# Boundary calls above 8192 should throw, while <=8192 never allocates.
java=java.replace('transfer(f.toString(),new byte[size],0,size,output,3);if(size>8192)throw new AssertionError("both backends should fail");','if(output&&size>8192)expect(OutOfMemoryError.class,()->transfer(f.toString(),new byte[size],0,size,output,3));else transfer(f.toString(),new byte[size],0,size,output,3);')
java=java.replace('  }\n }\n}', '''  }
  for(boolean output:new boolean[]{false,true}) {
   expect(NullPointerException.class,()->transfer(f.toString(),null,0,1,output,1));
   expect(IndexOutOfBoundsException.class,()->transfer(f.toString(),payload,-1,10,output,1));
   expect(IndexOutOfBoundsException.class,()->transfer(f.toString(),payload,1,Integer.MAX_VALUE,output,1));
   expect(IOException.class,()->transfer(f.toString(),payload,0,payload.length,output,1|8));
   expect(IOException.class,()->transfer(f.toString(),payload,0,payload.length,output,1|4));
  }
  installRandomAccessReader();Files.write(f,payload);
  try(var raf=new RandomAccessFile(f.toFile(),"r")){
   byte[] full=new byte[payload.length];raf.readFully(full);
   if(!Arrays.equals(payload,full)||raf.getFilePointer()!=payload.length)throw new AssertionError("RAF readFully position/content");
   expect(EOFException.class,()->raf.readFully(new byte[1]));
  }
  Path zip=f.resolveSibling("fixture.zip");
  try(var out=new java.util.zip.ZipOutputStream(Files.newOutputStream(zip))){out.putNextEntry(new java.util.zip.ZipEntry("payload"));out.write(payload);out.closeEntry();}
  int before=rafReads();
  try(var input=new java.util.zip.ZipFile(zip.toFile());var entry=input.getInputStream(input.getEntry("payload"))){if(!Arrays.equals(payload,entry.readAllBytes()))throw new AssertionError("real ZipFile content");}
  if(rafReads()<=before)throw new AssertionError("ZipFile did not exercise actual capped JNI read");Files.delete(zip);
  Files.delete(f);System.out.println("PASS: actual JNI bulk file I/O, libc/mmap, partial writes, bounded reads/full continuation/EOF, stack threshold, bounds/null, I/O/OOM cleanup");
 }
}''')
(WORK/'bridge.c').write_text(bridge);(WORK/'IoScratchCheck.java').write_text(java)
common=['clang','-std=c11','-fsanitize=undefined','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin')]
for ps5 in (False,True):
 lib=WORK/('io-ps5.dylib' if ps5 else 'io-host.dylib')
 subprocess.run([*common,*(['-D__PROSPERO__'] if ps5 else []),'-dynamiclib',str(WORK/'bridge.c'),'-o',str(lib)],check=True)
 subprocess.run([str(JDK/'bin/javac'),'-d',str(WORK),str(WORK/'IoScratchCheck.java')],check=True)
 # The ordinary branch intentionally cannot survive a forced malloc failure.
 if ps5: subprocess.run([str(JDK/'bin/java'),'--enable-native-access=ALL-UNNAMED','-Xcheck:jni','-cp',str(WORK),'IoScratchCheck',str(lib),str(WORK/'data.bin')],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0'})
print('PASS: non-PS5 branch compiles unchanged allocation behavior')
