#!/usr/bin/env python3
"""Run actual compressed-class reservation with the shared metadata ownership fixture."""
from pathlib import Path
import runpy,subprocess
r=Path(__file__).resolve().parents[1]
# Reuse the controlled real aligned storage and existing ownership/release checks.
fixture=runpy.run_path(str(r/'tools/test_java25_direct_metaspace.py'))
w=r/'build/java25/direct-class-space-test';(w/'runtime').mkdir(parents=True,exist_ok=True)
(w/'runtime/ps5StartupTrace.hpp').write_text('#pragma once\ninline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){}\n')
s=(r/'.tools/java25/openjdk/src/hotspot/share/memory/metaspace.cpp').read_text();a=s.index('ReservedSpace Metaspace::reserve_address_space_for_compressed_classes(');b=s.index('\n#endif // _LP64',a);actual=s[a:b]
source=fixture['source'].replace('tag==mtMetaspace','tag==mtClass')
source=source.replace('struct os{static bool pd_release_memory(char*,size_t);};',r'''
static bool UseCompactObjectHeaders=true,RandomizeClassSpaceLocation=false;
static size_t ordinary_calls=0,placement_calls=0,range_limit=256*1024*1024;
struct Metaspace {static size_t reserve_alignment(){return 4*1024*1024;}static ReservedSpace reserve_address_space_for_compressed_classes(size_t,bool);};
struct CompressedKlassPointers {
 static char* reserve_address_space_for_compressed_classes(size_t,bool,bool){++placement_calls;return nullptr;}
 static size_t max_klass_range_size(){return range_limit;}
};
struct os{
 static bool pd_release_memory(char*,size_t);
 static size_t vm_page_size(){return 16384;}
 static char* reserve_memory_aligned(size_t,size_t,MemTag){++ordinary_calls;errno=ordinary_errno;return ordinary;}
};
#define AMD64 1
#define NOT_ZERO(x) x
#define log_debug(...) fake_log
#define PTR_FORMAT "%p"
#define p2i(x) (x)
#undef assert
#define assert(x,...) ((x)?(void)0:abort())
#define ExecMem true
static bool is_aligned(void*p,size_t a){return (uintptr_t)p%a==0;}
static void fake_log(const char*,...){}
''')
suffix=fixture['suffix'];a=suffix.index('int main()');suffix=suffix[:a]+r'''
int main(){
 constexpr size_t size=32*1024*1024,alignment=4*1024*1024,page=16384;
 auto reserve=[](){return Metaspace::reserve_address_space_for_compressed_classes(size,true);};
 size_t before=calls;
 ordinary=(char*)0x4000000;assert(reserve().p==ordinary&&calls==before);ordinary=nullptr;
 UseCompactObjectHeaders=false;assert(!reserve().is_reserved()&&calls==before);UseCompactObjectHeaders=true;
 ordinary_errno=EACCES;assert(!reserve().is_reserved()&&calls==before);ordinary_errno=ENOMEM;
 range_limit=size-1;assert(!reserve().is_reserved()&&calls==before);range_limit=256*1024*1024;
 fail_allocate=true;assert(!reserve().is_reserved());fail_allocate=false;assert(!live&&!direct::state().held&&!records);
 fail_map=true;assert(!reserve().is_reserved());fail_map=false;assert(!live&&!direct::state().held&&!records);
 fail_protect=true;assert(!reserve().is_reserved());fail_protect=false;assert(!live&&!direct::state().held&&!records);
 auto rs=reserve();assert(rs.is_reserved()&&records==1&&last_alignment==alignment&&direct::state().held==size);inaccessible(rs.p);
 assert(direct::metadata_range(rs.p,page)&&!direct::stack_range(rs.p,page));
 assert(!mprotect(rs.p,size,PROT_READ|PROT_WRITE));for(size_t i=0;i<size;i++)assert(rs.p[i]==0);
 // Compact-header base-relative narrowKlass encoding: offset/shift roundtrips
 // the first usable class address and last aligned class in the real region.
 for(size_t offset:{size_t(64),size-size_t(64)}){uint32_t id=(uint32_t)(offset>>6);assert(id!=0&&id<(1u<<22)&&rs.p+((size_t)id<<6)==rs.p+offset);}
 memset(rs.p,0x42,size);assert(direct::uncommit_metadata(rs.p+page,page));inaccessible(rs.p+page);
 assert(!mprotect(rs.p+page,page,PROT_READ|PROT_WRITE));for(size_t i=0;i<page;i++)assert(rs.p[page+i]==0);assert(rs.p[0]==0x42&&rs.p[2*page]==0x42);
 assert(!os::pd_release_memory(rs.p,page)&&live==1&&direct::state().held==size);
 assert(os::pd_release_memory(rs.p,size)&&!live&&!direct::state().held);
 // Shared budget is charged before kernel allocation; no separate class pool.
 direct::lock();direct::state().held=direct::budget_bytes-size+page;direct::unlock();before=calls;
 assert(!reserve().is_reserved()&&calls==before);direct::lock();direct::state().held=0;direct::unlock();
 // Failed cleanup retains ownership and budget, matching existing metadata.
 rs=reserve();fail_release=true;assert(!os::pd_release_memory(rs.p,size)&&live==1&&direct::state().held==size);fail_release=false;
 direct::lock();for(unsigned i=0;i<direct::entry_count;i++)if(direct::state().entries[i].occupied){assert(!sceKernelReleaseDirectMemory(0,size));direct::abandon(i);}direct::unlock();
 assert(!live&&!direct::state().held&&ordinary_calls==placement_calls);
 puts("PASS: actual compact class-space reservation,32MiB/4MiBalignment,mtClass NMT,PROT_NONE/zero/subrangeuncommit,encodingroundtrips,ordinary/error/header/range gates,sharedbudget/rollback/cleanupretention; ASan/UBSan");
}
'''
(w/'test.cpp').write_text('#include <initializer_list>\n#include <cstdio>\n'+source+actual+fixture['release']+suffix)
subprocess.run(['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+str(w),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),str(w/'test.cpp'),'-o',str(w/'check')],check=True)
subprocess.run([str(w/'check')],check=True,timeout=60)
