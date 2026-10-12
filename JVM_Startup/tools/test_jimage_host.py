#!/usr/bin/env python3
"""Compile the actual patched JIMAGE reader and inject host mapping failures."""
from pathlib import Path
import os
import subprocess
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'.tools/java25/openjdk'
work=ROOT/'build/java25'
share=source/'src/java.base/share/native/libjimage'
jdk=Path(os.environ.get('JAVA25_BOOT_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
base=['/usr/bin/clang++','-std=c++14','-O2','-D__PROSPERO__']
for path in [share,source/'src/java.base/share/native/libjava',source/'src/java.base/unix/native/libjava',source/'src/hotspot/share/include',source/'src/hotspot/os/posix/include',source/'build/ps5-bootstrap/support/modules_include/java.base',ROOT/'build/native']:
    base+=['-I',str(path)]
subprocess.run(base+['-DNDEBUG','-Dmmap=ps5_test_mmap','-c',str(source/'src/java.base/unix/native/libjimage/osSupport_unix.cpp'),'-o',str(work/'host-jimage-os.o')],check=True)
subprocess.run(base+[str(ROOT/'tools/test_jimage.cpp'),*[str(share/name) for name in ['endian.cpp','imageDecompressor.cpp','imageFile.cpp','jimage.cpp']],str(work/'host-jimage-os.o'),'-L'+str(jdk/'lib/server'),'-Wl,-rpath,'+str(jdk/'lib/server'),'-ljvm','-o',str(work/'test-jimage')],check=True)
subprocess.run([str(work/'test-jimage')],cwd=ROOT,check=True,timeout=20)
