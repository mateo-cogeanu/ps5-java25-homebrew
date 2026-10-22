#!/usr/bin/env python3
"""Validate real target object inputs and failure boundaries for resident groups."""
from pathlib import Path
import json
import subprocess
import tempfile
from java25_resident_libraries import read_libraries

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='resident-inputs-')as folder:
 w=Path(folder);(w/'lib.c').write_text('int consumer_export(void){return 17;}\n')
 subprocess.run(['/opt/homebrew/opt/llvm/bin/clang','-target','x86_64-sie-ps5','-c',str(w/'lib.c'),'-o',str(w/'lib.o')],check=True)
 manifest=w/'libraries.json'
 def check(rows,valid):
  manifest.write_text(json.dumps(rows))
  try:
   result=read_libraries(manifest,['java','jvm','management','ps5probe'])
   if not valid:raise AssertionError('invalid library input accepted')
   assert result[0][0]=='consumer'and result[0][1]==[(w/'lib.o').resolve()]
  except ValueError:
   if valid:raise
 good={'name':'consumer','objects':[str(w/'lib.o')]};check([good],True)
 for rows in [[{**good,'name':'java'}],[good,good],[{**good,'name':'../consumer'}],[{**good,'objects':[]}],[{**good,'objects':['relative.o']}],[{**good,'objects':[str(w/'lib.o')]*2}],[{**good,'extra':True}],{'name':'consumer'}]:check(rows,False)
 (w/'not-elf.o').write_bytes(b'not an ELF object')
 check([{**good,'objects':[str(w/'not-elf.o')]}],False)
 # A real ELF shared object must not be accepted as a relocatable input.
 data=bytearray((w/'lib.o').read_bytes());data[16:18]=(3).to_bytes(2,'little');(w/'shared.o').write_bytes(data)
 check([{**good,'objects':[str(w/'shared.o')]}],False)
 # Test the full generator's lifecycle guard with a real constructor section.
 (w/'ctor.c').write_text('int n; __attribute__((constructor)) void ctor(void){n=17;}\n')
 subprocess.run(['/opt/homebrew/opt/llvm/bin/clang','-target','x86_64-sie-ps5','-c',str(w/'ctor.c'),'-o',str(w/'ctor.o')],check=True)
 manifest.write_text(json.dumps([{'name':'constructor_probe','objects':[str(w/'ctor.o')]}]))
 rejected=subprocess.run(['python3',str(ROOT/'tools/java25_builtin_runtime.py'),'--external-libraries',str(manifest)],capture_output=True,text=True)
 assert rejected.returncode!=0 and 'constructors require an explicit lifecycle port' in rejected.stderr,(rejected.stdout,rejected.stderr)
 print('PASS actual PS5 object validation, reserved/duplicate/unsafe names, absolute/nonempty/unique object paths, schema, malformed/shared ELF and real constructor-section rejection')
