#!/usr/bin/env python3
"""Verify PS5 crash-context access cannot allocate through emulated C++ TLS."""
from pathlib import Path
import os
import subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/java25';WORK.mkdir(parents=True,exist_ok=True)
source=WORK/'test-trace-storage.cpp'
source.write_text('#define __PROSPERO__ 1\n#include "runtime/ps5StartupTrace.hpp"\nextern "C" void *probe_context(){ps5_vm_trace_io_active()=true;ps5_vm_reset_native_call_record();return ps5_vm_thread_context();}\n')
output=WORK/'test-trace-storage.ll'
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config')
subprocess.run([str(ROOT/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang++'),'-std=c++17','-O2','-I'+str(ROOT/'.tools/java25/openjdk/src/hotspot/share'),'-S','-emit-llvm',str(source),'-o',str(output)],env=env,check=True)
ir=output.read_text()
for symbol in ('__emutls','@malloc','@calloc','@realloc','__cxa_guard'):
 assert symbol not in ir,'Unsafe crash-context dependency: '+symbol
assert 'cmpxchg' in ir and '@pthread_self' in ir
print('PASS: target crash-context IR uses static storage, atomics and pthread_self; no allocator, emulated TLS or initialization guard')
