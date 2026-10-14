#!/usr/bin/env python3
"""Compile the real Settings header with host stubs for unrelated VM types.
Checks reservation granularity, root alignment and unchanged non-PS5 defaults.
This is a settings/pressure model test, not console VM execution.
"""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/java25/metaspace-settings-test';WORK.mkdir(parents=True,exist_ok=True)
headers={
 'memory/allStatic.hpp':'#pragma once\nclass AllStatic {};\n',
 'memory/metaspace/chunklevel.hpp':'#pragma once\n#include <cstddef>\nnamespace metaspace { namespace chunklevel { constexpr std::size_t MAX_CHUNK_WORD_SIZE=2*1024*1024; }}\n',
 'utilities/globalDefinitions.hpp':'#pragma once\n#include <cstddef>\nconstexpr std::size_t K=1024, BytesPerWord=8;\nclass outputStream;\n#if TEST_LP64\n#define LP64_ONLY(x) x\n#define NOT_LP64(x)\n#else\n#define LP64_ONLY(x)\n#define NOT_LP64(x) x\n#endif\n'}
for name,text in headers.items():
 p=WORK/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
header=ROOT/'.tools/java25/openjdk/src/hotspot/share/memory/metaspace/metaspaceSettings.hpp'
source=WORK/'test.cpp';source.write_text('#include "'+str(header)+'"\n'+r'''
#include <cassert>
int main(){
 const auto root=metaspace::chunklevel::MAX_CHUNK_WORD_SIZE;
 const auto node=metaspace::Settings::virtual_space_node_default_word_size();
 const auto alignment=metaspace::Settings::virtual_space_node_reserve_alignment_words();
 assert(node==root*EXPECTED_ROOTS && alignment==root && node%root==0);
 assert(metaspace::Settings::commit_granule_bytes()==64*K);
#ifdef __PROSPERO__
 // A 48 MiB reservation budget cannot fit the desktop 64 MiB node (or
 // 80 MiB alignment fallback). Two incremental 16 MiB nodes fit, including
 // transient one-root over-reservation while aligning the second node.
 const auto budget=48*1024*1024UL;
 assert(4*root*BytesPerWord>budget);
 assert((node+alignment)*BytesPerWord<=budget);
 assert((2*node+alignment)*BytesPerWord<=budget);
#endif
}
''')
for name,flags in [('ps5',['-D__PROSPERO__','-DTEST_LP64=1','-DEXPECTED_ROOTS=1']),('bsd64',['-DTEST_LP64=1','-DEXPECTED_ROOTS=4']),('bsd32',['-DTEST_LP64=0','-DEXPECTED_ROOTS=1'])]:
 exe=WORK/name
 subprocess.run(['/usr/bin/clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(WORK),*flags,str(source),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
 print('PASS:',name,'actual metaspace Settings header, root alignment and reservation model')
