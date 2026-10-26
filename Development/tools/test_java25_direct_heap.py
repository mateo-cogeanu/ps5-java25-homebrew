#!/usr/bin/env python3
"""Exercise actual heap reservation/ownership with fault-controlled kernel calls."""
from pathlib import Path
import runpy,subprocess
r=Path(__file__).resolve().parents[1]
f=runpy.run_path(str(r/'tools/test_java25_direct_metaspace.py'))
w=r/'build/java25/direct-heap-test';(w/'runtime').mkdir(parents=True,exist_ok=True)
(w/'runtime/ps5StartupTrace.hpp').write_text('#pragma once\ninline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){}\n')
source=f['source'].replace('tag==mtMetaspace','tag==mtJavaHeap')
source=source.replace('struct os{static bool pd_release_memory(char*,size_t);};','struct os{static bool pd_release_memory(char*,size_t);static bool pd_uncommit_memory(char*,size_t,bool);};')
s=(r/'.tools/java25/openjdk/src/hotspot/os/bsd/os_bsd.cpp').read_text();uncommit=s[s.index('bool os::pd_uncommit_memory('):s.index('\nbool os::pd_create_stack_guard_pages(')]
# Keep the actual PS5 ownership dispatch,stub only ordinary fallback branches.
uncommit=uncommit[:uncommit.index('  if (exec)')]+ '  return false;\n}\n'
suffix=f['suffix'];suffix=suffix[:suffix.index('int main()')]+r'''
int main(){
 constexpr size_t size=768*1024*1024,alignment=4*1024*1024,page=16384;size_t before=calls;
 auto reserve=[](size_t n){return MemoryReserver::reserve_memory(nullptr,n,alignment,page,false,mtJavaHeap);};
 assert(!reserve(size).is_reserved()&&calls==before);UseCompressedOops=false;
 assert(!MemoryReserver::reserve_memory((char*)0x4000000,size,alignment,page,false,mtJavaHeap).is_reserved());
 assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,true,mtJavaHeap).is_reserved());
 ordinary_errno=EACCES;assert(!reserve(size).is_reserved()&&calls==before);ordinary_errno=ENOMEM;
 ordinary=(char*)0x4000000;assert(reserve(size).p==ordinary&&calls==before);ordinary=nullptr;
 fail_allocate=true;assert(!reserve(size).is_reserved());fail_allocate=false;assert(!live&&!direct::state().held&&!direct::state().heap_held);
 fail_map=true;assert(!reserve(size).is_reserved());fail_map=false;assert(!live&&!direct::state().held&&!direct::state().heap_held);
 fail_protect=true;assert(!reserve(size).is_reserved());fail_protect=false;assert(!live&&!direct::state().held&&!direct::state().heap_held);
 auto rs=reserve(size);assert(rs.is_reserved()&&records==1&&last_alignment==alignment&&direct::state().heap_held==size);
 inaccessible(rs.p);assert(direct::heap_range(rs.p,page)&&direct::heap_range(rs.p+size-page,page));
 assert(!direct::metadata_range(rs.p,page)&&!direct::stack_range(rs.p,page));
 assert(!direct::heap_range(rs.p+size-page,2*page)&&!direct::heap_range((void*)(UINTPTR_MAX-100),200));
 assert(!mprotect(rs.p,size,PROT_READ|PROT_WRITE));for(size_t i=0;i<size;++i)assert(rs.p[i]==0);memset(rs.p,0x42,size);
 assert(os::pd_uncommit_memory(rs.p+page,page,false));inaccessible(rs.p+page);
 assert(!mprotect(rs.p+page,page,PROT_READ|PROT_WRITE));for(size_t i=0;i<page;++i)assert(rs.p[page+i]==0);
 assert(rs.p[0]==0x42&&rs.p[2*page]==0x42&&direct::state().heap_held==size);
 assert(!os::pd_release_memory(rs.p,page));assert(!os::pd_release_memory(rs.p+page,page));assert(live==1&&direct::state().heap_held==size);
 assert(os::pd_release_memory(rs.p,size)&&!live&&!direct::state().held&&!direct::state().heap_held);
 // Exhausted native budget cannot consume/deny the separately bounded heap budget.
 direct::state().held=direct::budget_bytes;before=calls;
 assert(direct::map(page)==MAP_FAILED&&calls==before);
 rs=reserve(alignment);assert(rs.is_reserved()&&direct::state().heap_held==alignment);
 assert(os::pd_release_memory(rs.p,alignment));assert(direct::state().held==direct::budget_bytes);direct::state().held=0;
 assert(!reserve(direct::heap_budget_bytes+alignment).is_reserved());
 direct::state().heap_held=direct::heap_budget_bytes;direct::state().held=direct::heap_budget_bytes;before=calls;
 assert(!reserve(alignment).is_reserved()&&calls==before);direct::state().heap_held=direct::state().held=0;
 rs=reserve(alignment);fail_release=true;assert(!os::pd_release_memory(rs.p,alignment)&&live==1&&direct::state().heap_held==alignment);fail_release=false;
 direct::lock();for(unsigned i=0;i<direct::entry_count;i++)if(direct::state().entries[i].occupied){assert(!sceKernelReleaseDirectMemory(0,alignment));direct::abandon(i);}direct::unlock();
 assert(!live&&!direct::state().heap_held&&!direct::state().held);
 puts("PASS actual uncompressed heap reservation:768MiB/alignment,zero/PROT_NONE/subrange uncommit+recommit,adjacent preservation,whole/interior release guards,NMT,compressed/fixed/exec/error gates,ordinary success,rollback and cleanup retention,separate768MiBheap/256MiBnative budgets;ASan/UBSan OS fixtures,not PS5 acceptance");
}
'''
(w/'test.cpp').write_text('#include <initializer_list>\n#include <cstdio>\n'+source+f['reserve']+f['release']+uncommit+suffix)
subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+str(w),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),str(w/'test.cpp'),'-o',str(w/'check')],check=True)
subprocess.run([str(w/'check')],check=True,timeout=60)
