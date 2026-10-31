#!/usr/bin/env python3
"""Build opt-in LLVM18 exception globals using compiler TLS, without SDK key setters."""
import argparse, hashlib, json, subprocess, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'cxa_exception_storage.cpp':'1c5b4749dc742e8005968930744339c0969eed00b22fbfb735b2651f271aad61','cxa_exception.h':'ad8872f7f3850c7f948ec2e3b14a8b08a39ac95a64b01867f684103c874504cd'}
BASE='https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-18.1.8/libcxxabi/src/'
def build(output, sdk, cxx, nm):
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 source=ROOT/'.tools/cxxabi-18.1.8';source.mkdir(parents=True,exist_ok=True)
 for name,digest in PINS.items():
  p=source/name
  if not p.exists():p.write_bytes(urllib.request.urlopen(BASE+name,timeout=30).read())
  if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('Pinned LLVM source mismatch: '+name)
 flags=['-target','x86_64-sie-ps5','-std=c++14','-isysroot',str(sdk),'-isystem',str(sdk/'target/include/c++/v1'),'-isystem',str(sdk/'target/include'),'-fvisibility-nodllstorageclass=default','-femulated-tls','-DHAS_THREAD_LOCAL','-O2','-fno-stack-protector']
 subprocess.run([str(cxx),*flags,'-c',str(source/'cxa_exception_storage.cpp'),'-o',str(output)],check=True)
 symbols=subprocess.check_output([str(nm),str(output)],text=True)
 if 'pthread_'in symbols or '__emutls_get_address'not in symbols:raise ValueError('Unexpected exception globals TLS provider')
 for name in ['__cxa_get_globals','__cxa_get_globals_fast']:
  if ' T '+name+'\n'not in symbols:raise ValueError('Missing '+name)
 output.with_suffix('.json').write_text(json.dumps({'llvm':'18.1.8','source_sha256':PINS,'object_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'policy':'Explicit consumer link only; upstream HAS_THREAD_LOCAL branch; existing compiler TLS allocation/lifecycle policy; no default SDK/archive changes','console':'PS5 exception recovery, voice chat, world/save and endurance pending'},indent=2)+'\n')
 return output
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True);p.add_argument('--cxx',type=Path,required=True);p.add_argument('--nm',type=Path,required=True);a=p.parse_args();print(build(a.output,a.sdk,a.cxx,a.nm))
