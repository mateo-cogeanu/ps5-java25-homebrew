#!/usr/bin/env python3
"""Exercise real dependency JARs, system class path and host JNI fixture."""
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
assets=ROOT/'build/java25/dependency-assets/java25';jars=assets/'jars';classes=assets/'classes'
work=ROOT/'build/java25/dependency-host-test';work.mkdir(exist_ok=True)
subprocess.run(['/usr/bin/clang++','-std=c++20','-dynamiclib','-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(ROOT/'java25/probe/dependency_jni.cpp'),'-o',str(work/'libps5probe.dylib')],check=True)
def run(fixture,directory=jars,classpath=None,library=work,expect=None):
    cp=classpath or str(classes)+':'+str(jars/'application.jar')
    result=subprocess.run([str(JDK/'bin/java'),'-Xint','-Xms16m','-Xmx128m','-cp',cp,
        '-Dps5.probe.dependencyDir='+str(directory),'-Djava.library.path='+str(library),fixture],capture_output=True,text=True,timeout=30)
    output=result.stdout+result.stderr
    if expect:assert result.returncode!=0 and expect in output,output
    else:assert result.returncode==0 and 'JAVA_' in output,output
    return output
assert not (classes/'ps5deps').exists()
run('MultiJar25');print('PASS: manifest transitive JAR classes, ServiceLoader, UTF-8 resources, enumeration order')
run('SystemClasspath25');print('PASS: actual system class path, manifest dependencies and missing-class rejection')
run('NativeDeps25');print('PASS: real System.loadLibrary/JNI_OnLoad, native array arithmetic, exception and missing-library rejection')
with tempfile.TemporaryDirectory() as directory:
    empty=Path(directory);shutil.copy2(jars/'application.jar',empty/'application.jar')
    run('MultiJar25',directory=empty,expect='NoClassDefFoundError');print('PASS: absent transitive dependency fails')
    run('SystemClasspath25',classpath=str(classes),expect='ClassNotFoundException');print('PASS: application JAR absent from system class path fails')
    run('NativeDeps25',library=empty,expect='UnsatisfiedLinkError');print('PASS: unavailable actual JNI fixture fails loading')
