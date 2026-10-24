/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace ps5::log_retention {
// Explicit caller-selected diagnostic file only. Call before opening its writer.
// Read the retained tail completely before truncating, so read failures leave
// the file intact. Reuse its inode and free old blocks before rewriting: a temp
// file/rename rotation would require extra storage when the volume is full.
// After truncation a failed write may leave a partial tail; callers must stop
// and report the failure. Never apply this helper to world/save/user data.
inline bool retain_tail(const char* path, char* scratch, size_t capacity) {
 if(!scratch || !capacity){errno=EINVAL;return false;}
 int fd;
 do{fd=::open(path,O_RDWR);}while(fd<0 && errno==EINTR);
 if(fd<0)return errno==ENOENT;
 struct stat info{};
 int error=0;
 if(::fstat(fd,&info)!=0)error=errno;
 else if(!S_ISREG(info.st_mode)||info.st_size<0)error=EINVAL;
 else if(static_cast<unsigned long long>(info.st_size)>capacity) {
  size_t offset=0;
  if(::lseek(fd,info.st_size-static_cast<off_t>(capacity),SEEK_SET)<0)error=errno;
  while(!error && offset<capacity) {
   ssize_t n=::read(fd,scratch+offset,capacity-offset);
   if(n<0 && errno==EINTR)continue;
   if(n<=0){error=n<0?errno:EIO;break;}
   offset+=static_cast<size_t>(n);
  }
  if(!error && ::ftruncate(fd,0)!=0)error=errno;
  if(!error && ::lseek(fd,0,SEEK_SET)<0)error=errno;
  offset=0;
  while(!error && offset<capacity) {
   ssize_t n=::write(fd,scratch+offset,capacity-offset);
   if(n<0 && errno==EINTR)continue;
   if(n<=0){error=n<0?errno:EIO;break;}
   offset+=static_cast<size_t>(n);
  }
 }
 if(::close(fd)!=0 && !error)error=errno;
 if(error){errno=error;return false;}
 return true;
}
}
