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
#include <fstream>
#include <iterator>
#include <string>
static bool reject_file=false,reject_anonymous=false;
static unsigned file_mappings=0,anonymous_mappings=0;
extern "C" void *ps5_test_mmap(void *p,size_t size,int protection,int flags,int fd,off_t offset) {
 if(fd>=0) ++file_mappings; else ++anonymous_mappings;
 if((fd>=0 && reject_file)||(fd<0 && reject_anonymous)) {errno=EPERM;return MAP_FAILED;}
 return mmap(p,size,protection,flags,fd,offset);
}
void read_object(const char *expected_root) {
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
 const char *resources[][2]={{"java.base","java/lang/String.class"},{"java.base","java/lang/Object.class"},{"java.base","sun/security/ssl/SSLSocketImpl.class"},{"jdk.jfr","jdk/jfr/internal/types/metadata.bin"},{"java.desktop","java/awt/Color.class"}};
 for(auto &resource:resources){
  auto location=JIMAGE_FindResource(image,resource[0],"25",resource[1],&size);assert(location && size>0);
  std::vector<char> actual(static_cast<size_t>(size));assert(JIMAGE_GetResource(image,location,actual.data(),size)==size);
  std::ifstream input(std::string(expected_root)+"/"+resource[0]+"/"+resource[1],std::ios::binary);assert(input);
  std::vector<char> expected((std::istreambuf_iterator<char>(input)),{});assert(actual==expected);
 }
 JIMAGE_Close(image);
}
int main(int argc,char **argv) {
 assert(argc==2);
 read_object(argv[1]);
 reject_file=true;
 read_object(argv[1]);
 assert(file_mappings==0 && anonymous_mappings==2);
 reject_anonymous=true;
 jint error=0;
 assert(!JIMAGE_Open("build/java25/boot-image/lib/modules",&error));
 assert(file_mappings==0 && anonymous_mappings==3);
 std::puts("Real JIMAGE reader PASS: direct anonymous copies, zero file mappings, Java 25 classes/TLS/JFR/desktop byte identity, mapping rejection");
}
