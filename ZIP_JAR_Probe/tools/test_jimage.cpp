/* SPDX-License-Identifier: GPL-2.0-only
 * Run the actual patched image reader on the host. Inject mapping failures
 * to exercise the PS5 fallback; this is not console VM execution evidence.
 */
#include "jimage.hpp"
#include <sys/mman.h>
#include <cerrno>
#include <cassert>
#include <cstdio>
#include <vector>
static bool reject_file=false,reject_anonymous=false;
static unsigned file_mappings=0,anonymous_mappings=0;
extern "C" void *ps5_test_mmap(void *p,size_t size,int protection,int flags,int fd,off_t offset) {
 if(fd>=0) ++file_mappings; else ++anonymous_mappings;
 if((fd>=0 && reject_file)||(fd<0 && reject_anonymous)) {errno=EPERM;return MAP_FAILED;}
 return mmap(p,size,protection,flags,fd,offset);
}
void read_object() {
 jint error=0;
 auto *image=JIMAGE_Open("build/java25/boot-image/lib/modules",&error);
 assert(image);
 jlong size=0;
 auto location=JIMAGE_FindResource(image,"java.base","25","java/lang/Object.class",&size);
 assert(location && size>8);
 std::vector<unsigned char> bytes(static_cast<size_t>(size));
 assert(JIMAGE_GetResource(image,location,reinterpret_cast<char *>(bytes.data()),size)==size);
 assert(bytes[0]==0xca && bytes[1]==0xfe && bytes[2]==0xba && bytes[3]==0xbe);
 assert(bytes[6]==0 && bytes[7]==69);
 JIMAGE_Close(image);
}
int main() {
 read_object();
 reject_file=true;
 read_object();
 assert(file_mappings==0 && anonymous_mappings==2);
 reject_anonymous=true;
 jint error=0;
 assert(!JIMAGE_Open("build/java25/boot-image/lib/modules",&error));
 assert(file_mappings==0 && anonymous_mappings==3);
 std::puts("Real JIMAGE reader PASS: direct anonymous copies, zero file mappings, Java 25 Object, mapping rejection");
}
