#!/usr/bin/env python3
"""Force the genuine freshly built JNA JNI; packaged host-native fallback forbidden."""
from pathlib import Path
import argparse,hashlib,json,subprocess,urllib.request,zipfile
from java25_jna import build,ROOT,JDK
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jna-jar',type=Path,required=True);a=p.parse_args();jar=a.jna_jar.resolve()
# Actual publisher snapshot6 pin, not a locally built replacement Java library.
assert jar.stat().st_size==1950853 and hashlib.sha1(jar.read_bytes()).hexdigest()=='ca303052cd617c1af2e2c8d344c98a706fb63143', 'Unexpected JNA artifact'
lib=build(Path('/opt/homebrew/opt/libffi/include'),host=True,offline=True)
w=ROOT/'build/java25/jna-test';w.mkdir(parents=True,exist_ok=True)
subprocess.run([str(JDK/'bin/javac'),'--release','25','-cp',str(jar),'-d',str(w),str(ROOT/'java25/tests/JnaNativeProbe25.java')],check=True)
result=subprocess.run([str(JDK/'bin/java'),'-Djna.boot.library.path='+str(lib.parent),'-Djna.nosys=true','-Djna.noclasspath=true','-Djna.nounpack=true','-cp',str(w)+':'+str(jar),'JnaNativeProbe25','host'],capture_output=True,text=True,check=True,timeout=30);print(result.stdout)
with zipfile.ZipFile(jar)as z:assert 'com/sun/jna/Native.class' in z.namelist()
print('PASS original publisher JNA Java classes with forced newly built JNI; target behavior pending')
