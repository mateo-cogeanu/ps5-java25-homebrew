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
subprocess.run(['gmake','-C',str(ROOT/'.tools/java25/openjdk'),'CONF=ps5-bootstrap','java.base-gendata'],env=build_env,check=True)
conf=BUILD/'support/modules_conf/java.base'
security=conf/'security/java.security'
if not security.is_file() or b'security.provider.tbd' in security.read_bytes():
    raise SystemExit('Missing or unprocessed target java.security configuration')
image=WORK/'boot-image' 
jmods=WORK/'boot-jmods'
jmods.mkdir(parents=True,exist_ok=True)
module=jmods/'java.base.jmod'
module.unlink(missing_ok=True)
subprocess.run([str(JDK/'bin/jmod'),'create','--class-path',str(classes),'--module-version','25.0.4',
                '--target-platform','linux-amd64','--config',str(conf),str(module)],check=True)
if image.exists(): shutil.rmtree(image)
subprocess.run([str(JDK/'bin/jlink'),'--module-path',str(jmods),'--add-modules','java.base',
                '--output',str(image),'--strip-debug','--no-header-files','--no-man-pages'],check=True)
if (image/'bin').exists():
    raise SystemExit('Unexpected native launcher in class-only boot image')
report={'input':'PS5/FreeBSD cross-build java.base classes/resources',
        'host_tool_jmod_transport_tag':'linux-amd64; host jlink rejects BSD tags',
        'included_linux_or_host_native_binaries':False,
        'runtime_configuration':'target-generated java.base conf including java.security, crypto policies and net.properties',
        'output':'build/java25/boot-image/lib/modules',
        'console_validation':'pending; native runtime packaged separately'}
(WORK/'boot-image-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built target core class image:',image/'lib/modules')
