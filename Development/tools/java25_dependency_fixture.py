#!/usr/bin/env python3
"""Build deterministic JAR-only transitive dependency and JNI fixtures."""
from pathlib import Path
import argparse
import shutil
import subprocess
import zipfile
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
classes=ROOT/'build/java25/dependency-payload-classes';shutil.rmtree(classes,ignore_errors=True);classes.mkdir(parents=True)
sources=sorted((ROOT/'java25/tests/dependencies').rglob('*.java'))
subprocess.run(['/opt/homebrew/opt/openjdk@25/bin/javac','--release','25','-d',str(classes),*[str(p) for p in sources]],check=True)
args.output.mkdir(parents=True,exist_ok=True)
def jar(name,entries):
 with zipfile.ZipFile(args.output/name,'w') as archive:
  for path,data in entries:
   info=zipfile.ZipInfo(path,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100600<<16;archive.writestr(info,data)
def bytecode(name):
 data=(classes/name).read_bytes();assert data[:4]==bytes.fromhex('cafebabe') and data[6:8]==b'\x00E';return (name,data)
manifest=lambda extra:b'Manifest-Version: 1.0\r\n'+extra+b'\r\n'
jar('application.jar',[('META-INF/MANIFEST.MF',manifest(b'Class-Path: dependency.jar api.jar\r\n')),bytecode('ps5deps/Application.class'),('order.txt',b'application\n')])
jar('dependency.jar',[('META-INF/MANIFEST.MF',manifest(b'')),bytecode('ps5deps/Engine.class'),bytecode('ps5deps/impl/GreetingImpl.class'),('META-INF/services/ps5deps.api.Greeting',b'ps5deps.impl.GreetingImpl\n'),('ps5deps/message.txt','café / 日本語 / 🎮\n'.encode()),('order.txt',b'dependency\n')])
jar('api.jar',[('META-INF/MANIFEST.MF',manifest(b'')),bytecode('ps5deps/api/Greeting.class'),('order.txt',b'api\n')])
jar('native.jar',[('META-INF/MANIFEST.MF',manifest(b'')),bytecode('ps5deps/NativeMath.class')])
print('Built four deterministic dependency/JNI JARs:',args.output)
