#!/usr/bin/env python3
"""Execute actual ChunkPool paths with tracked allocations and injected refusal."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/arena-pool-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/java25/openjdk/src/hotspot/share/memory/arena.cpp').read_text();a=s.index('class ChunkPool {');b=s.index('\nstatic bool on_compiler_thread',a);pool=s[a:b].replace('class ChunkPool {','class ChunkPool {\npublic:')
a=s.index('Chunk* ChunkPool::allocate_chunk(');b=s.index('\nvoid ChunkPool::deallocate_chunk',a);allocate=s[a:b]
a=s.index('void ChunkPool::deallocate_chunk(');b=s.index('\nclass ChunkPoolCleaner',a);deallocate=s[a:b]
c=w/'test.cpp';c.write_text(r'''
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <cassert>
#include <new>
#include <mutex>
#include <thread>
#include <vector>
#include <atomic>
#include <stdexcept>
#include <cstdint>
static std::recursive_mutex mutex;
static thread_local int locked=0;
struct ChunkPoolLocker{ChunkPoolLocker(){mutex.lock();locked++;}~ChunkPoolLocker(){locked--;mutex.unlock();}};
static std::atomic<int> live{0},refuse{0};
static bool fail_all=false;
namespace os{void*malloc(size_t n,int,int){if(fail_all)return nullptr;if(refuse>0){--refuse;return nullptr;}void*p=std::malloc(n);if(p)live++;return p;}void free(void*p){assert(locked);if(p){live--;std::free(p);}}}
struct NativeHeapTrimmer{struct SuspendMark{SuspendMark(const char*){}};};
struct Chunk{Chunk*_next;size_t _length;uint64_t _stamp;static constexpr size_t tiny_size=216,init_size=984,medium_size=10200,size=32640;Chunk(size_t n):_next(nullptr),_length(n),_stamp(0){}Chunk*next(){return _next;}void set_next(Chunk*p){_next=p;}size_t length(){return _length;}uint64_t stamp(){return _stamp;}void set_stamp(uint64_t s){_stamp=s;}};
struct Arena{int get_tag(){return 0;}};
struct CompilationMemoryStatistic{static bool enabled(){return false;}static void on_arena_chunk_allocation(size_t,int,uint64_t*){}static void on_arena_chunk_deallocation(size_t,uint64_t){}};
static bool on_compiler_thread(){return false;}
#undef assert
#define assert(v,...) ((v)?(void)0:std::abort())
#define ARENA_AMALLOC_ALIGNMENT 8
#define ARENA_ALIGN(n) (((n)+7)&~size_t(7))
#define is_aligned(n,a) ((uintptr_t)(n)%(a)==0)
#define mtChunk 0
#define CALLER_PC 0
#define OOM_MALLOC_ERROR 0
struct AllocFailStrategy{static constexpr int EXIT_OOM=1;};using AllocFailType=int;
static void vm_exit_out_of_memory(size_t,int,const char*){throw std::runtime_error("real allocation refusal");}
''' +pool+allocate+deallocate+r'''
int main(){
 Arena arena;
 // A compilation's burst is returned; PS5 retains at most eight of each size.
 for(size_t size:{Chunk::tiny_size,Chunk::init_size,Chunk::medium_size,Chunk::size}){
  std::vector<Chunk*> chunks;for(int i=0;i<128;i++)chunks.push_back(ChunkPool::allocate_chunk(&arena,size,1));
  for(auto*p:chunks)ChunkPool::deallocate_chunk(p);
 }
#ifdef __PROSPERO__
 assert(live==32);
#else
 assert(live==512);
#endif
 ChunkPool::clean();assert(live==0);
 // Allocation of another size fails while unused chunks remain in a pool.
 auto*cached=ChunkPool::allocate_chunk(&arena,Chunk::size,1);ChunkPool::deallocate_chunk(cached);refuse=1;
#ifdef __PROSPERO__
 auto*p=ChunkPool::allocate_chunk(&arena,Chunk::init_size,1);assert(live==1);ChunkPool::deallocate_chunk(p);
#else
 try{ChunkPool::allocate_chunk(&arena,Chunk::init_size,1);std::abort();}catch(const std::runtime_error&){}assert(live==1);
#endif
 ChunkPool::clean();assert(live==0);
 auto*active=ChunkPool::allocate_chunk(&arena,Chunk::size,1);memset((char*)active+ARENA_ALIGN(sizeof(Chunk)),0x47,Chunk::size);
 fail_all=true;try{ChunkPool::allocate_chunk(&arena,Chunk::medium_size,1);std::abort();}catch(const std::runtime_error&){}fail_all=false;
 assert(live==1&&*((unsigned char*)active+ARENA_ALIGN(sizeof(Chunk)))==0x47);ChunkPool::deallocate_chunk(active);ChunkPool::clean();assert(live==0);
 std::vector<std::thread> threads;for(int t=0;t<4;t++)threads.emplace_back([&]{for(int i=0;i<1000;i++){auto*p=ChunkPool::allocate_chunk(&arena,Chunk::size,1);ChunkPool::deallocate_chunk(p);}});for(auto&t:threads)t.join();ChunkPool::clean();assert(live==0);
 puts("PASS: actual arena pools burst retention/cleanup, allocation refusal/retry, live-chunk preservation and4000 concurrent lifetimes; ASan/UBSan; desktop control retained");
}
''')
for ps5 in [True,False]:
 exe=w/('ps5' if ps5 else 'desktop');subprocess.run(['clang++','-std=c++17','-pthread','-O1','-g','-fsanitize=address,undefined',*(['-D__PROSPERO__=1'] if ps5 else []),str(c),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
