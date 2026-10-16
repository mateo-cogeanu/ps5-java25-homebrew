/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <sys/resource.h>
#include <unistd.h>
namespace ps5::process_usage {
// Raw OS counters: do not assume ru_maxrss units or infer a container limit.
// Fixed stack storage and descriptor IO; no JVM/JNI access from the UI thread.
inline bool append(const char* path,long long elapsed) {
 int saved_errno=errno;struct rusage usage{};errno=0;
 int result=getrusage(RUSAGE_SELF,&usage),error=result ? errno : 0;
 char line[512];int length;
 if(result==0)length=std::snprintf(line,sizeof(line),"elapsed_s=%lld getrusage=0 maxrss_raw=%lld minflt=%lld majflt=%lld user_us=%lld system_us=%lld\n",elapsed,(long long)usage.ru_maxrss,(long long)usage.ru_minflt,(long long)usage.ru_majflt,(long long)usage.ru_utime.tv_sec*1000000+usage.ru_utime.tv_usec,(long long)usage.ru_stime.tv_sec*1000000+usage.ru_stime.tv_usec);
 else length=std::snprintf(line,sizeof(line),"elapsed_s=%lld getrusage=%d errno=%d counters=unavailable\n",elapsed,result,error);
 bool ok=length>0&&(size_t)length<sizeof(line);int fd=-1;
 if(ok)fd=::open(path,O_CREAT|O_WRONLY|O_APPEND,0600);
 if(fd<0)ok=false;
 size_t written=0;
 while(ok&&written<(size_t)length){ssize_t n=::write(fd,line+written,(size_t)length-written);if(n<0&&errno==EINTR)continue;if(n<=0){ok=false;break;}written+=(size_t)n;}
 if(fd>=0&&::close(fd)!=0)ok=false;
 errno=saved_errno;return ok;
}
}
