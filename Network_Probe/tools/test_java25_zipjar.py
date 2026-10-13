#!/usr/bin/env python3
"""Run actual packaged Java ZIP/JAR fixtures and meaningful failure cases on host."""
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'build/java25/zipjar-assets/java25'
WORK=ROOT/'build/java25/zipjar-host-test'
WORK.mkdir(parents=True,exist_ok=True)
JAR=ASSETS/'jars/probe.jar'
CLASSES=ASSETS/'classes'
assert not (CLASSES/'ps5probe/JarHello25.class').exists()
command=['/opt/homebrew/opt/openjdk@25/bin/java','-Xint','-Xms16m','-Xmx128m',
         '-XX:+UseSerialGC','-XX:ActiveProcessorCount=2',
         '-Dsun.nio.fs.chdirAllowed=true','-Dsun.nio.fs.ps5Sandbox=true','-Duser.dir=/app0',
         '-cp',str(CLASSES)]

def run(path):
    return subprocess.run([*command,'-Dps5.probe.jar='+str(path),'ZipJar25'],text=True,capture_output=True)

success=run(JAR)
assert success.returncode==0 and 'JAVA_ZIP_JAR_OK' in success.stdout,success.stdout+success.stderr
print('PASS: real ZipFile stored/deflated bytes, JarFile manifest, JAR-defined class and UTF-8 resource')

cases=[('bad-stored.jar','fixtures/stored.txt',b'BAD_BYTES','stored ZIP entry'),
       ('bad-resource.jar','ps5probe/message.txt',b'BAD_RESOURCE','JAR class execution and UTF-8 resource')]
for name,entry,replacement,stage in cases:
    path=WORK/name
    with zipfile.ZipFile(JAR) as original, zipfile.ZipFile(path,'w') as modified:
        for info in original.infolist():
            modified.writestr(info,replacement if info.filename==entry else original.read(info.filename))
    result=run(path)
    assert result.returncode!=0 and stage in result.stderr,result.stdout+result.stderr
    assert 'JAVA_ZIP_JAR_OK' not in result.stdout
    print('PASS: failure detected at '+stage)

path=WORK/'missing-class.jar'
with zipfile.ZipFile(JAR) as original, zipfile.ZipFile(path,'w') as modified:
    for info in original.infolist():
        data=original.read(info.filename)
        if info.filename=='ps5probe/JarHello25.class':
            info.filename='ps5probe/Absent.class'
        modified.writestr(info,data)
result=run(path)
assert result.returncode!=0 and 'JAR class loader' in result.stderr and 'ClassNotFoundException' in result.stderr,result.stderr
print('PASS: missing JAR class cannot be supplied by loose class-path fallback')
