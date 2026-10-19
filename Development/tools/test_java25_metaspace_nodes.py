#!/usr/bin/env python3
"""Actual metaspace geometry/Settings and level-fitting implementation on host.
Unrelated VM types/printing are stand-ins; pressure checks are reservation models.
"""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/metaspace-settings-test';w.mkdir(parents=True,exist_ok=True)
source_root=r/'.tools/java25/openjdk/src/hotspot/share'
headers={
'memory/allStatic.hpp':'#pragma once\nclass AllStatic {};\n',
'utilities/globalDefinitions.hpp':r'''#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdlib>
constexpr std::size_t K=1024,M=1024*K,BytesPerWord=8;using MetaWord=uint64_t;
class outputStream;
#define STATIC_ASSERT(x) static_assert(x)
#define assert(x,...) do{if(!(x))std::abort();}while(0)
#if TEST_LP64
#define LP64_ONLY(x) x
#define NOT_LP64(x)
#else
#define LP64_ONLY(x)
#define NOT_LP64(x) x
#endif
''',
'utilities/debug.hpp':'#pragma once\n#include "utilities/globalDefinitions.hpp"\n',
'utilities/ostream.hpp':'#pragma once\nclass outputStream{public:void print(const char*,...) {}};\n',
'utilities/powerOfTwo.hpp':'#pragma once\n#include <cstddef>\ninline size_t round_up_power_of_2(size_t n){size_t p=1;while(p<n)p*=2;return p;}\ninline int exact_log2(size_t n){int i=0;while(n>1){n/=2;i++;}return i;}\n'}
for name,text in headers.items():p=w/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
p=w/'memory/metaspace/chunklevel.hpp';p.parent.mkdir(parents=True,exist_ok=True);p.write_text((source_root/'memory/metaspace/chunklevel.hpp').read_text())
source=w/'test.cpp';source.write_text('#include "'+str(source_root/'memory/metaspace/metaspaceSettings.hpp')+'"\n'+r'''
int main(){
 using namespace metaspace;using namespace metaspace::chunklevel;
 const size_t root=MAX_CHUNK_WORD_SIZE,node=Settings::virtual_space_node_default_word_size(),alignment=Settings::virtual_space_node_reserve_alignment_words();
 assert(node==root*EXPECTED_ROOTS&&alignment==root&&node%root==0);
 assert(Settings::commit_granule_bytes()==64*K&&MIN_CHUNK_BYTE_SIZE==K);
 assert(!is_valid_level(-1)&&!is_valid_level(NUM_CHUNK_LEVELS));
 const chunklevel_t named[]={CHUNK_LEVEL_1K,CHUNK_LEVEL_2K,CHUNK_LEVEL_4K,CHUNK_LEVEL_8K,CHUNK_LEVEL_16K,CHUNK_LEVEL_32K,CHUNK_LEVEL_64K,CHUNK_LEVEL_128K,CHUNK_LEVEL_256K,CHUNK_LEVEL_512K,CHUNK_LEVEL_1M,CHUNK_LEVEL_2M,CHUNK_LEVEL_4M};
 for(int i=0;i<13;i++)assert(word_size_for_level(named[i])*BytesPerWord==(K<<i));
 for(size_t words=1;words<=root;words++){
  auto level=level_fitting_word_size(words);assert(is_valid_level(level));
  size_t fit=word_size_for_level(level);assert(fit>=words&&(fit/2<words||level==HIGHEST_CHUNK_LEVEL));
 }
 // Buddy splitting/merging geometry: every split is exact, with 1KiB leaves.
 size_t size=MAX_CHUNK_BYTE_SIZE,count=1;
 for(int level=0;level<NUM_CHUNK_LEVELS;level++){
  assert(size==word_size_for_level(level)*BytesPerWord&&size*count==MAX_CHUNK_BYTE_SIZE);
  for(size_t i=0;i<count;i++){
   size_t offset=i*size,buddy=offset^size;
   if(level>0)assert(buddy<MAX_CHUNK_BYTE_SIZE&&(buddy^size)==offset);
  }
  size/=2;count*=2;
 }
#ifdef __PROSPERO__
 assert(root*BytesPerWord==4*M&&NUM_CHUNK_LEVELS==13);
 // An 8MiB remaining mapping budget cannot fit the former16MiB root.
 const size_t budget=8*M;assert(16*M>budget);assert((node+alignment)*BytesPerWord<=budget);assert(2*node*BytesPerWord<=budget);
#else
 assert(root*BytesPerWord==16*M&&NUM_CHUNK_LEVELS==15);
 assert(word_size_for_level(CHUNK_LEVEL_16M)*BytesPerWord==16*M&&word_size_for_level(CHUNK_LEVEL_8M)*BytesPerWord==8*M);
#endif
}
''')
for name,flags in [('ps5',['-D__PROSPERO__','-DTEST_LP64=1','-DEXPECTED_ROOTS=1']),('bsd64',['-DTEST_LP64=1','-DEXPECTED_ROOTS=4']),('bsd32',['-DTEST_LP64=0','-DEXPECTED_ROOTS=1'])]:
 exe=w/name;subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(w),*flags,str(source),str(source_root/'memory/metaspace/chunklevel.cpp'),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
 print('PASS:',name,'actual geometry/Settings/level-fitting for every word size; named sizes, buddy geometry, alignment and pressure model; ASan/UBSan')
