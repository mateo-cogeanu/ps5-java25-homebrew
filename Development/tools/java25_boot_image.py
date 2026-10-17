#!/usr/bin/env python3
"""Build a classes/resources-only core image with the host JDK's image tools.

The stock host jlink rejects BSD JMOD target tags. The temporary JMOD uses
an accepted tag solely to encode architecture-independent target-built
classes/resources; no host or Linux native binaries are included in it.
The PS5 native libraries are added separately by the startup packager.
"""
from pathlib import Path
import os
import subprocess
import shutil
import json
import argparse
import re
import hashlib
import tempfile
import zipfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--modules',default='java.base',help='Comma-separated target-built modules to include')
args=parser.parse_args()
requested=args.modules.split(',')
if any(not re.fullmatch(r'[a-z][a-z0-9_.]*',name) for name in requested):parser.error('Invalid module name')
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/java25'
BUILD=ROOT/'.tools/java25/openjdk/build/ps5-bootstrap'
JDK=Path(os.environ.get('JAVA25_BOOT_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
classes=BUILD/'jdk/modules/java.base'
if not (classes/'java/lang/Object.class').exists():
    raise SystemExit('Build java.base first')
# Generate target security configuration and other java.base runtime data.
# Raw java.security source is a template; the target build resolves providers
# and platform conditionals before it is packaged.
build_env=dict(os.environ)
build_env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config')
source=ROOT/'.tools/java25/openjdk'
# Java compilation alone omits generated resources (notably JFR metadata.bin).
# Run the target generators for each requested module that supplies one.
gendata=[name+'-gendata' for name in dict.fromkeys(['java.base',*requested])
         if (source/'make/modules'/name/'Gendata.gmk').is_file()]
subprocess.run(['gmake','-C',str(source),'CONF=ps5-bootstrap',*gendata,
                *[name+'-java' for name in requested if name!='java.base']],env=build_env,check=True)
required_resources={'jdk.jfr':['jdk/jfr/internal/types/metadata.bin']}
resource_hashes={}
for name, resources in required_resources.items():
    if name not in requested:continue
    for resource in resources:
        data=(BUILD/'jdk/modules'/name/resource).read_bytes()
        if not data:raise SystemExit('Empty target resource: '+name+'/'+resource)
        resource_hashes[name+'/'+resource]=hashlib.sha256(data).hexdigest()
conf=BUILD/'support/modules_conf/java.base'
security=conf/'security/java.security'
if not security.is_file() or b'security.provider.tbd' in security.read_bytes():
    raise SystemExit('Missing or unprocessed target java.security configuration')
image=WORK/'boot-image' 
jmods=WORK/'boot-jmods'
jmods.mkdir(parents=True,exist_ok=True)
for old in jmods.glob('*.jmod'):old.unlink()
# Additional modules are target-built Java classes; never borrow host modules.
modules=[BUILD/'jdk/modules/java.base'] if requested==['java.base'] else sorted((BUILD/'jdk/modules').iterdir())
for directory in modules:
    if not (directory/'module-info.class').is_file():continue
    target_conf=BUILD/'support/modules_conf'/directory.name
    options=['--config',str(target_conf)] if target_conf.is_dir() else []
    subprocess.run([str(JDK/'bin/jmod'),'create','--class-path',str(directory),'--module-version','25.0.4',
        '--target-platform','linux-amd64',*options,str(jmods/(directory.name+'.jmod'))],check=True)
for name in requested:
    if not (jmods/(name+'.jmod')).is_file():raise SystemExit('Requested module not target-built: '+name)
for resource, digest in resource_hashes.items():
    name, path=resource.split('/',1)
    with zipfile.ZipFile(jmods/(name+'.jmod')) as archive:
        if hashlib.sha256(archive.read('classes/'+path)).hexdigest()!=digest:
            raise SystemExit('Target resource differs in JMOD: '+resource)
if image.exists(): shutil.rmtree(image)
subprocess.run([str(JDK/'bin/jlink'),'--module-path',str(jmods),'--add-modules',args.modules,
                '--output',str(image),'--strip-debug','--no-header-files','--no-man-pages'],check=True)
# Runtime data is required by java.time, legacy timezone APIs and TLS.
# jmod classes/config alone do not include these target-generated data files.
libs=BUILD/'support/modules_libs/java.base'
shutil.copy2(libs/'tzdb.dat',image/'lib/tzdb.dat')
(image/'lib/security').mkdir(exist_ok=True)
shutil.copy2(libs/'security/cacerts',image/'lib/security/cacerts')
release=(image/'release').read_text()
included=re.search(r'^MODULES="([^"]+)"',release,re.M).group(1).split()
if any(not (jmods/(name+'.jmod')).is_file() for name in included):
    raise SystemExit('Image included a module not supplied by the target build')
if (image/'bin').exists():
    raise SystemExit('Unexpected native launcher in class-only boot image')
# Verify the linked image itself, not just its source directory/JMOD.
with tempfile.TemporaryDirectory(prefix='ps5-image-resources-') as output:
    for resource,digest in resource_hashes.items():
        subprocess.run([str(JDK/'bin/jimage'),'extract','--include','glob:/'+resource,
                        '--dir',output,str(image/'lib/modules')],check=True)
        if hashlib.sha256((Path(output)/resource).read_bytes()).hexdigest()!=digest:
            raise SystemExit('Target resource differs in linked image: '+resource)
report={'input':'PS5/FreeBSD cross-build target module classes/resources',
        'host_tool_jmod_transport_tag':'linux-amd64; host jlink rejects BSD tags',
        'included_linux_or_host_native_binaries':False,
        'requested_target_modules':requested,
        'included_target_modules':included,
        'target_gendata_targets':gendata,
        'verified_generated_resource_sha256':resource_hashes,
        'runtime_data':'target-generated tzdb.dat and security/cacerts',
        'runtime_configuration':'target-generated java.base conf including java.security, crypto policies and net.properties',
        'output':'build/java25/boot-image/lib/modules',
        'console_validation':'pending; native runtime packaged separately'}
(WORK/'boot-image-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built target core class image:',image/'lib/modules')
