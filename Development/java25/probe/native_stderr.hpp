/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <unistd.h>

namespace ps5::native_stderr {
// Title-lifetime capture of real native stderr, including direct descriptor2
// writes. Call once before native services start; caller supplies the path.
// A failed open/dup leaves descriptor2 unchanged. No change to stdout/Java streams.
inline int begin(const char *path) {
 int saved=errno,fd;
 do{fd=::open(path,O_CREAT|O_WRONLY|O_APPEND,0600);}while(fd<0&&errno==EINTR);
 if(fd<0)return errno;
 int result;
 do{result=::dup2(fd,STDERR_FILENO);}while(result<0&&errno==EINTR);
 int error=result<0?errno:0;
 if(fd!=STDERR_FILENO)(void)::close(fd);
 if(error){errno=error;return error;}
 // Native error lines must survive process exit without a stdio flush.
 if(std::setvbuf(stderr,nullptr,_IONBF,0)!=0){errno=EIO;return EIO;}
 errno=saved;return 0;
}
}
