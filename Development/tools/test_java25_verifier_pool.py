#!/usr/bin/env python3
"""Run the actual verifier scratch allocator under a constrained native budget."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/java25'
s=(ROOT/'.tools/java25/openjdk/src/java.base/share/native/libverify/check_code.c').read_text()
a=s.index('#define CCSegSize 2000');b=s.index('\n/* Get the class associated',a)
code=s[a:b]
prefix=r'''
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <setjmp.h>
#include <stddef.h>
typedef int jboolean;
typedef struct CCpool CCpool;
typedef struct {CCpool *CCroot,*CCcurrent;int CCfree_size;char *CCfree_ptr;} context_type;
static size_t live,peak;static jmp_buf exhausted;static int expected_oom;
static void CCout_of_memory(context_type *c,int site){(void)c;(void)site;assert(expected_oom);longjmp(exhausted,1);}
static void *budget_malloc(size_t n){
 if(n>512*1024 || live+n>512*1024)return NULL;
 size_t *p=malloc(n+sizeof(max_align_t));assert(p);*p=n;live+=n;if(live>peak)peak=live;return (char*)p+sizeof(max_align_t);
}
static void budget_free(void *p){if(!p)return;size_t *base=(size_t*)((char*)p-sizeof(max_align_t));live-=*base;free(base);}
#define malloc budget_malloc
#define free budget_free
'''
suffix=r'''
int main(){
 context_type c={0};CCinit(&c);size_t root=live;
#ifdef __PROSPERO__
 for(int method=0;method<600;method++){
  CCreinit(&c);assert(live==root);
  unsigned char *a=CCalloc(&c,100000,1);for(int i=0;i<100000;i++)assert(a[i]==0);memset(a,0x55,100000);
  unsigned char *b=CCalloc(&c,150000,0);memset(b,0x66,150000);
  for(int i=0;i<100000;i++)assert(a[i]==0x55);
  for(int i=0;i<100;i++){unsigned char *small=CCalloc(&c,32,1);for(int j=0;j<32;j++)assert(!small[j]);}
 }
 assert(peak<300000);CCreinit(&c);assert(live==root);
#else
 // Original desktop behavior retains oversized method blocks and exhausts
 // this same small budget; demonstrate the regression being addressed.
 expected_oom=1;
 if(!setjmp(exhausted)){for(int method=0;method<600;method++){CCreinit(&c);CCalloc(&c,100000,1);CCalloc(&c,150000,0);}assert(!"expected budget exhaustion");}
#endif
 CCdestroy(&c);assert(live==0);puts("PASS: actual verifier pool allocation/reset/cleanup with constrained native budget");
}
'''
source=WORK/'test-verifier-pool.c';source.write_text(prefix+code+suffix)
for name,flags in [('ps5',['-D__PROSPERO__']),('desktop',[])]:
    executable=WORK/('test-verifier-pool-'+name)
    subprocess.run(['clang','-std=c11','-fsanitize=address,undefined',*flags,str(source),'-o',str(executable)],check=True)
    subprocess.run([str(executable)],check=True)
