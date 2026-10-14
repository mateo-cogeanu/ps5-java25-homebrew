#!/usr/bin/env python3
"""Build the deterministic unsigned Java 25 JAR for the console probe."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/java25/startup-assets/java25/jars/probe.jar')
    args=parser.parse_args()
    classes=ROOT/'build/java25/jar-payload-classes'
    if classes.exists(): shutil.rmtree(classes)
    classes.mkdir(parents=True)
    subprocess.run(['/opt/homebrew/opt/openjdk@25/bin/javac','--release','25','-d',str(classes),
                    str(ROOT/'java25/tests/ps5probe/JarHello25.java')],check=True)
    bytecode=(classes/'ps5probe/JarHello25.class').read_bytes()
    assert bytecode[:4]==b'\xca\xfe\xba\xbe' and int.from_bytes(bytecode[6:8],'big')==69
    entries=[('META-INF/MANIFEST.MF',b'Manifest-Version: 1.0\r\nImplementation-Title: PS5 Java 25 probe\r\n\r\n',zipfile.ZIP_DEFLATED),
             ('ps5probe/JarHello25.class',bytecode,zipfile.ZIP_DEFLATED),
             ('ps5probe/message.txt','café / 日本語 / 🎮\n'.encode(),zipfile.ZIP_DEFLATED),
             ('fixtures/stored.txt',b'ZIP_STORED_OK\n',zipfile.ZIP_STORED),
             ('fixtures/deflated.bin',bytes((i*31+7)&255 for i in range(65536)),zipfile.ZIP_DEFLATED)]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w') as archive:
        for name,data,method in entries:
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=method;info.external_attr=0o100600<<16
            archive.writestr(info,data)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None and len(archive.infolist())==5
    report={'entries':[name for name,_,_ in entries],'payload_class_major':69,
            'payload_available_as_loose_class':False,'signed':False,'console_validation':'pending'}
    args.output.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Built ZIP/JAR fixture:',args.output)

if __name__=='__main__':main()
