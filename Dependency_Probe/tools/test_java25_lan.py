#!/usr/bin/env python3
"""Host smoke checks for packaged LAN/DNS fixtures; helper must be running."""
from pathlib import Path
import argparse
import subprocess
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config',type=Path,default=ROOT/'build/java25/lan-assets/java25/probe.properties')
args=parser.parse_args()
classes=ROOT/'build/java25/lan-assets/java25/classes'
base=['/opt/homebrew/opt/openjdk@25/bin/java','-Xint','-Xms16m','-Xmx128m',
      '-Djava.net.preferIPv4Stack=true','-cp',str(classes)]
for fixture in ['Lan25','Dns25']:
    result=subprocess.run([*base,'-Dps5.probe.config='+str(args.config.resolve()),fixture],
                          text=True,capture_output=True,timeout=25)
    assert result.returncode==0,result.stdout+result.stderr
    assert ('JAVA_LAN_OK' if fixture=='Lan25' else 'JAVA_DNS_OK') in result.stdout
    print('PASS: actual packaged '+fixture+' on host')
work=ROOT/'build/java25/lan-host-test';work.mkdir(parents=True,exist_ok=True)
invalid=work/'loopback.properties';invalid.write_text('lan.host=127.0.0.1\nlan.port=38025\n')
result=subprocess.run([*base,'-Dps5.probe.config='+str(invalid),'Lan25'],text=True,capture_output=True,timeout=10)
assert result.returncode!=0 and "another device's address" in result.stderr
print('PASS: console LAN fixture rejects loopback configuration')
