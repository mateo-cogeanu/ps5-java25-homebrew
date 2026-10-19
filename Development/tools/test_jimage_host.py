#!/usr/bin/env python3
"""Compile the actual patched JIMAGE reader and inject host mapping failures."""
from pathlib import Path
import os
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'.tools/java25/openjdk'
work=ROOT/'build/java25'
share=source/'src/java.base/share/native/libjimage'
jdk=Path(os.environ.get('JAVA25_BOOT_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
base=['/usr/bin/clang++','-std=c++14','-O1','-g','-fsanitize=address,undefined','-D__PROSPERO__']
for path in [share,source/'src/java.base/share/native/libjava',source/'src/java.base/unix/native/libjava',source/'src/hotspot/share/include',source/'src/hotspot/os/posix/include',source/'build/ps5-bootstrap/support/modules_include/java.base',ROOT/'build/native']:
    base+=['-I',str(path)]
# Build the actual native image inflater, not the host JDK's libzip.
zipbase=source/'src/java.base/share/native/libzip'
body=(zipbase/'zip_util.c').read_text();a=body.index('JNIEXPORT jboolean\nZIP_InflateFully');b=body.index('\nstatic voidpf tracking_zlib_alloc',a)
fixture=r"""
#include <jni.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <errno.h>
#include <assert.h>
#include <zlib.h>
static int deny,budget=-1,live,maps;
static void *model_malloc(size_t n){if(deny){errno=ENOMEM;return NULL;}return malloc(n);}
static void *model_map(void*p,size_t n,int prot,int flags,int fd,off_t o){assert(fd==-1&&n%16384==0);if(!budget){errno=ENOMEM;return MAP_FAILED;}if(budget>0)--budget;p=mmap(p,n,prot,flags,fd,o);if(p!=MAP_FAILED){live++;maps++;}return p;}
static int model_unmap(void*p,size_t n){int rc=munmap(p,n);if(!rc)--live;return rc;}
#define malloc model_malloc
#define mmap model_map
#define munmap model_unmap
#include "ps5ZipAlloc.h"
#undef malloc
#undef mmap
#undef munmap
void zip_test_mode(int d,int b){deny=d;budget=b;}
int zip_test_live(void){return live;}
int zip_test_maps(void){return maps;}
"""
(work/'host-jimage-zip.c').write_text(fixture+body[a:b])
subprocess.run(['/usr/bin/clang','-O1','-g','-fsanitize=address,undefined','-D__PROSPERO__','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),'-I'+str(zipbase),'-c',str(work/'host-jimage-zip.c'),'-o',str(work/'host-jimage-zip.o')],check=True)
subprocess.run(base+['-DNDEBUG','-Dmmap=ps5_test_mmap','-c',str(source/'src/java.base/unix/native/libjimage/osSupport_unix.cpp'),'-o',str(work/'host-jimage-os.o')],check=True)
# Inject failures only into temporary image-resource buffers, independently
# from the zlib allocator and the resident image mapping.
(work/'host-image-buffer-test.hpp').write_text(r"""
#include <stddef.h>
#include <sys/mman.h>
extern "C" void* image_test_malloc(size_t);
extern "C" void image_test_free(void*);
extern "C" void* image_test_map(void*,size_t,int,int,int,off_t);
extern "C" int image_test_unmap(void*,size_t);
#define IMAGE_BUFFER_MALLOC image_test_malloc
#define IMAGE_BUFFER_FREE image_test_free
#define IMAGE_BUFFER_MMAP image_test_map
#define IMAGE_BUFFER_MUNMAP image_test_unmap
""")
engine=[]
for name in ['endian.cpp','imageDecompressor.cpp','imageFile.cpp','jimage.cpp']:
    obj=work/('host-'+name+'.o');subprocess.run(base+['-DNDEBUG','-include',str(work/'host-image-buffer-test.hpp'),'-c',str(share/name),'-o',str(obj)],check=True);engine.append(str(obj))
subprocess.run(base+[str(ROOT/'tools/test_jimage.cpp'),*engine,str(work/'host-jimage-os.o'),'-L'+str(jdk/'lib/server'),'-Wl,-rpath,'+str(jdk/'lib/server'),'-ljvm',str(work/'host-jimage-zip.o'),'-lz','-o',str(work/'test-jimage')],check=True)
with tempfile.TemporaryDirectory(prefix='ps5-jimage-identity-') as expected:
    subprocess.run([str(jdk/'bin/jimage'),'extract','--dir',expected,str(work/'boot-image/lib/modules')],check=True)
    subprocess.run([str(work/'test-jimage'),expected],cwd=ROOT,check=True,timeout=20)
