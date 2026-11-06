#!/usr/bin/env python3
"""Check the actual allocator trace hook without suppressing failure evidence."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
text=(root/".tools/java25/openjdk/src/hotspot/share/runtime/ps5NativeHeap.hpp").read_text()
body=text[text.index("inline void note("):text.index("// At most one empty slab")]
source=r'''
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
static unsigned interval;
static std::atomic<unsigned> writes{0}, reports{0};
static unsigned* ps5_vm_metadata_interval() { return &interval; }
static size_t libc_held() { return 0; }
constexpr size_t libc_budget=2*1024*1024;
namespace ps5_native_direct { static void report() { ++reports; } }
static void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long) { ++writes; }
'''
source+=body
source+=r'''
int main() {
 note("test",1,1,0);
 assert(writes==2&&reports==1);
 interval=4096;
 unsigned before=writes;
 for(unsigned i=0;i<8192;++i)note("test",1,1,0);
 assert(writes-before==4);
 before=writes;
 for(unsigned i=0;i<100;++i)note("failure",1,0,12);
 assert(writes-before==200);
 std::vector<std::thread> workers;
 before=writes;
 for(unsigned t=0;t<4;++t)workers.emplace_back([]{
   for(unsigned i=0;i<4096;++i)note("success",1,1,0);
 });
 for(auto& worker:workers)worker.join();
 assert(writes-before==8);
 interval=0;
 before=writes;
 for(unsigned i=0;i<10;++i)note("default",1,1,0);
 assert(writes-before==20);
}
'''
with tempfile.TemporaryDirectory() as directory:
    p=Path(directory)
    (p/"test.cpp").write_text(source)
    subprocess.run(["clang++","-std=c++17","-O1","-g","-pthread",
                    "-fsanitize=address,undefined",str(p/"test.cpp"),"-o",str(p/"test")],check=True)
    subprocess.run([str(p/"test")],check=True)
print("PASS actual allocator trace hook: default output, first/periodic successes, all failures and concurrent event accounting; ASan/UBSan")
