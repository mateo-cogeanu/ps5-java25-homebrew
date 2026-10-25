/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <unistd.h>

namespace ps5::native_stderr {
// Title-lifetime native FILE stderr capture,called before native services start.
// PS5 title sandbox refuses dup2 with EPERM. Publish a fully configured stream
// instead;raw descriptor2 writes deliberately retain their original destination.
// Open/fdopen/setvbuf failure preserves the previous stderr pointer.
inline int begin(const char *path) {
 int saved=errno,fd;
 do{fd=::open(path,O_CREAT|O_WRONLY|O_APPEND,0600);}while(fd<0&&errno==EINTR);
 if(fd<0)return errno;
 FILE *stream=::fdopen(fd,"a");
 if(!stream){int error=errno?errno:EIO;(void)::close(fd);errno=error;return error;}
 if(std::setvbuf(stream,nullptr,_IONBF,0)!=0){(void)std::fclose(stream);errno=EIO;return EIO;}
 (void)std::fflush(stderr);
 stderr=stream; // Existing descriptor2/old stream remain owned;do not close them.
 errno=saved;return 0;
}
}
