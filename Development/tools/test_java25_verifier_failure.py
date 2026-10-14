#!/usr/bin/env python3
"""Exercise real verifier OOM formatter/longjmp with minimal context/JNI stubs."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'build/java25';JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(ROOT/'.tools/java25/openjdk/src/java.base/share/native/libverify/check_code.c').read_text();a=s.index('static void\nCCout_of_memory(context_type *context, int site)');b=s.index('\nstatic void\nCFerror',a);function=s[a:b]
prefix=r'''
#include <jni.h>
#include <setjmp.h>
#include <errno.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <assert.h>
#define CC_OutOfMemory 2
static jboolean pending=JNI_FALSE;
static jboolean exception_check(JNIEnv *env){(void)env;errno=EIO;return pending;}
typedef struct {JNIEnv *env;char *message;int message_buf_len,err_code;jmp_buf jump_buffer;} context_type;
static int print_CCerror_info(context_type *c){return snprintf(c->message,c->message_buf_len,"(class: Probe) ");}
static int jio_snprintf(char *p,size_t size,const char *format,...){va_list args;va_start(args,format);int n=vsnprintf(p,size,format,args);va_end(args);return n;}
'''
suffix=r'''
int main(){
 struct JNINativeInterface_ table={0};table.ExceptionCheck=exception_check;JNIEnv env=&table;
 context_type c={0};char text[256];c.env=&env;c.message=text;c.message_buf_len=sizeof(text);
 for(int i=0;i<2;i++){
  pending=i?JNI_TRUE:JNI_FALSE;errno=ENOMEM;
  if(setjmp(c.jump_buffer)==0)CCout_of_memory(&c,1234);
  assert(c.err_code==2 && errno==ENOMEM);
#ifdef __PROSPERO__
  assert(strstr(text,"site=1234")&&strstr(text,i?"JNI-pending=1":"JNI-pending=0"));
#else
  assert(strcmp(text,"(class: Probe) ")==0);
#endif
 }
 char guarded[9];memset(guarded,'Z',sizeof(guarded));c.message=guarded;c.message_buf_len=8;
 if(setjmp(c.jump_buffer)==0)CCout_of_memory(&c,5678);
 assert(guarded[8]=='Z'&&guarded[7]==0&&c.err_code==2);
 puts("PASS: real verifier OOM path retains result/errno, bounded diagnostic and JNI-pending state");
}
'''
cpp=WORK/'test-verifier-oom.c';cpp.write_text(prefix+function+suffix)
for name,flags in [('ps5',['-D__PROSPERO__']),('desktop',[])]:
 exe=WORK/('test-verifier-oom-'+name)
 subprocess.run(['/usr/bin/clang','-std=c11','-fsanitize=address,undefined','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),*flags,str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
