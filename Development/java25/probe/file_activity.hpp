/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <atomic>
#include <cstdio>
#include <cstring>
#include <cerrno>
namespace ps5::file_activity {
#if defined(PS5_TRACK_FILE_ACTIVITY) && PS5_TRACK_FILE_ACTIVITY
// Optional consumer instrumentation. Does not own or close recorded handles.
inline std::atomic_flag guard=ATOMIC_FLAG_INIT;
struct Entry {bool active=false;unsigned long long sequence=0;char path[112]{};};
inline Entry entries[8192];
inline unsigned long long opened=0,closed=0,failed=0,sequence=0,outside=0;
inline void lock(){while(guard.test_and_set(std::memory_order_acquire)){}}
inline void unlock(){guard.clear(std::memory_order_release);}
inline void open_result(int fd,const char *path){
 int saved=errno;lock();
 if(fd<0)failed++;
 else {opened++;if(fd<8192){auto &e=entries[fd];e.active=true;e.sequence=++sequence;std::snprintf(e.path,sizeof(e.path),"%s",path?path:"(null)");}else outside++;}
 unlock();errno=saved;
}
inline void close_result(int fd,int result){
 int saved=errno;lock();if(result==0){closed++;if(fd>=0&&fd<8192)entries[fd].active=false;}unlock();errno=saved;
}
inline int snapshot(char *text,size_t capacity){
 int saved=errno;lock();unsigned live=0;for(auto &e:entries)if(e.active)live++;
 int n=std::snprintf(text,capacity,"wrapped_open=%llu wrapped_close=%llu failed_open=%llu tracked_live=%u outside=%llu\nOnly consumer-linked open/close calls are recorded; native library internals may be absent.\n",opened,closed,failed,live,outside);
 size_t used=n>0?(size_t)n:0;unsigned shown=0;
 for(unsigned fd=0;fd<8192&&shown<24&&used<capacity;fd++)if(entries[fd].active){int length=std::snprintf(text+used,capacity-used,"fd=%u sequence=%llu path=%s\n",fd,entries[fd].sequence,entries[fd].path);if(length<0)break;used+=(size_t)length;shown++;}
 unlock();errno=saved;return used<capacity?(int)used:(int)(capacity?capacity-1:0);
}
#else
inline void open_result(int,const char*){}
inline void close_result(int,int){}
inline int snapshot(char *text,size_t capacity){int saved=errno;int n=std::snprintf(text,capacity,"File activity instrumentation is not enabled\n");errno=saved;return n;}
#endif
}
