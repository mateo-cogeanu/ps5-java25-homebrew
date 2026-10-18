#!/usr/bin/env python3
"""Actual C1 execution gate: compiled integer correctness and refusal controls."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/bin')
with tempfile.TemporaryDirectory() as temporary:
    work=Path(temporary);log=work/'jit.log'
    subprocess.run([str(JDK/'javac'),'-d',str(work),str(ROOT/'java25/tests/ps5probe/JitWarmup25.java')],check=True)
    common=[str(JDK/'java'),'-XX:ReservedCodeCacheSize=8m','-Dps5.probe.jitLog='+str(log),'-cp',str(work)]
    result=subprocess.run(common+['-Xint','ps5probe.JitWarmup25'],capture_output=True,text=True)
    assert result.returncode and 'C1 gate requires' in result.stderr,result
    flags=['-Xmixed','-XX:TieredStopAtLevel=1','-XX:CICompilerCount=1']
    result=subprocess.run(common+flags+['-Xlog:jit+compilation=debug:file='+str(log)+':uptime,level,tags:filecount=0','ps5probe.JitWarmup25'],capture_output=True,text=True,timeout=45)
    assert result.returncode==0 and 'JIT_WARMUP_OK level=1' in result.stdout,result
    assert 'ps5probe.JitWarmup25::kernel' in log.read_text()
    result=subprocess.run(common+flags+['ps5probe.JitWarmup25'],capture_output=True,text=True,timeout=45)
    assert result.returncode and 'require fresh VM/session' in result.stderr,result
    log.unlink()
    result=subprocess.run(common+flags+['ps5probe.JitWarmup25'],capture_output=True,text=True,timeout=45)
    assert result.returncode and 'No current-run level-1 kernel compilation' in result.stderr,result
print('PASS: actual C1 compilation and 40960+ checked results; interpreter, stale-log and missing-log controls reject')
