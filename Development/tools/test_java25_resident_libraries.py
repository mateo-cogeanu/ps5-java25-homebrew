#!/usr/bin/env python3
"""Validate real target object inputs and failure boundaries for resident groups."""
from pathlib import Path
import json
import subprocess
import tempfile
from java25_resident_libraries import read_libraries, read_aliases

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

assert read_aliases(['SDL3=consumer'],{'consumer'})=={'SDL3':'consumer'}
assert read_aliases(['zstd-jni_dh-1.5.7-12=consumer'],{'consumer'})=={'zstd-jni_dh-1.5.7-12':'consumer'}
for values in [['dot..name=consumer'],['quote\"=consumer'],['bad'],['../SDL=consumer'],['SDL3=absent'],['consumer=consumer'],['SDL3=consumer','SDL3=consumer']]:
 try:read_aliases(values,{'consumer'});raise AssertionError('invalid alias accepted')
 except ValueError:pass
print('PASS explicit alias schema/known target/unique name/path rejection; no additional native objects')

from java25_resident_libraries import read_alias_symbols, alias_symbol_entries
aliases={'ConsumerAlias':'consumer'}
overrides=read_alias_symbols(['ConsumerAlias:poll=private_poll'],aliases)
entries=['{"poll", reinterpret_cast<void *>(&real_poll)}','{"private_poll", reinterpret_cast<void *>(&scoped_poll)}','{"other", reinterpret_cast<void *>(&other)}']
remapped=alias_symbol_entries(entries,overrides['ConsumerAlias'])
assert remapped[0]=='{"poll", reinterpret_cast<void *>(&scoped_poll)}'
assert entries[0]=='{"poll", reinterpret_cast<void *>(&real_poll)}' and remapped[1:]==entries[1:]
assert alias_symbol_entries(entries,{})==entries
for values in [['consumer:poll=private_poll'],['Absent:poll=private_poll'],['ConsumerAlias:poll=missing','ConsumerAlias:poll=private_poll'],['ConsumerAlias:JNI_OnLoad=private_poll'],['ConsumerAlias:poll=Java_Fake'],['ConsumerAlias:poll=bad-name'],['ConsumerAlias:poll=bad;code']]:
 try:read_alias_symbols(values,aliases);raise AssertionError('invalid override accepted')
 except ValueError:pass
for value in [{'missing':'private_poll'},{'poll':'other_library_symbol'}]:
 try:alias_symbol_entries(entries,value);raise AssertionError('unknown export accepted')
 except ValueError:pass
# Compile and call the exact generated table expressions: alias-only redirection.
with tempfile.TemporaryDirectory(prefix='alias-symbol-')as folder:
 w=Path(folder);p=w/'check.cpp'
 p.write_text('#include <cassert>\nint real_poll(){return 1;}int scoped_poll(){return 2;}int other(){return 3;}struct Symbol{const char*name;void*address;};\nstatic Symbol base[]={'+','.join(entries)+'};\nstatic Symbol alias[]={'+','.join(remapped)+'};\nint main(){assert(reinterpret_cast<int(*)()>(base[0].address)()==1);assert(reinterpret_cast<int(*)()>(alias[0].address)()==2);assert(reinterpret_cast<int(*)()>(alias[2].address)()==3);}\n')
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined',str(p),'-o',str(w/'check')],check=True)
 subprocess.run([str(w/'check')],check=True)
print('PASS opt-in alias lookup redirection: actual compiled table calls,base/default/unrelated entries preserved,knownalias/samegroup actualexports/schema/duplicate/JNIentrypoint rejection;ASanUBSan')
