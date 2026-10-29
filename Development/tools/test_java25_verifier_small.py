#!/usr/bin/env python3
"""Exercise actual verifier reserve exhaustion, reuse and concurrent ownership."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1];work=root/'build/java25';work.mkdir(parents=True,exist_ok=True)
header=root/'.tools/java25/openjdk/src/java.base/share/native/libverify/ps5_verify_alloc.h'
code=r'''
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <pthread.h>
#include <stdarg.h>

static void *refuse(size_t n){(void)n;return NULL;}
#include <sys/mman.h>
static void *refuse_map(void *p,size_t n,int a,int b,int c,off_t d){(void)p;(void)n;(void)a;(void)b;(void)c;(void)d;errno=ENOMEM;return MAP_FAILED;}
#define malloc refuse
#define mmap refuse_map
#define jio_fprintf fprintf
'''.replace('#include <sys/mman.h>','#include <errno.h>\n#include <sys/mman.h>')
code+='\n#define __PROSPERO__\n#include "'+str(header)+'"\n'
code+=r'''
static void *worker(void *arg){unsigned char value=(uintptr_t)arg;for(int i=0;i<10000;i++){unsigned char *p=verify_native_allocate(24);assert(p);memset(p,value,24);for(int k=0;k<24;k++)assert(p[k]==value);verify_native_release(p);}return NULL;}
int main(void){assert(!verify_native_allocate(24));JNU_PS5SetVerifierSmallReserveEnabled(1);void *slots[16384];for(int i=0;i<16384;i++){slots[i]=verify_native_callocate(1,24);assert(slots[i]);assert(!*(unsigned char*)slots[i]);memset(slots[i],i,24);}assert(!verify_native_allocate(24));assert(!verify_native_allocate(257));assert(!verify_native_callocate(SIZE_MAX,2));for(int i=0;i<16384;i++){assert(*(unsigned char*)slots[i]==(unsigned char)i);verify_native_release(slots[i]);}pthread_t threads[8];for(uintptr_t i=0;i<8;i++)assert(!pthread_create(&threads[i],0,worker,(void*)(i+1)));for(int i=0;i<8;i++)pthread_join(threads[i],0);for(int i=0;i<512;i++)assert(!verify_small_used[i]);puts("PASS verifier reserve: default off, 16384 tiny allocations without mmap, bounded exhaustion, overflow, zeroing, reuse, 80000 concurrent cycles");}
'''
p=work/'verifier-small.c';p.write_text(code)
subprocess.run(['clang','-std=c11','-fsanitize=address,undefined','-pthread',str(p),'-o',str(work/'verifier-small')],check=True)
subprocess.run([str(work/'verifier-small')],check=True)
