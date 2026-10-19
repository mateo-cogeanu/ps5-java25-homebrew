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
#include <zlib.h>
#include <cstring>
extern "C" void zip_test_mode(int,int);
extern "C" int zip_test_live();
extern "C" int zip_test_maps();
extern "C" jboolean ZIP_InflateFully(void*,jlong,void*,jlong,char**);
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
 const char *resources[][2]={{"java.base","java/lang/String.class"},{"java.base","java/lang/Object.class"},{"java.base","sun/security/ssl/SSLSocketImpl.class"},{"java.base","sun/security/ssl/DTLSInputRecord.class"},{"jdk.jfr","jdk/jfr/internal/types/metadata.bin"},{"java.desktop","java/awt/Color.class"}};
 for(auto &resource:resources){
  auto location=JIMAGE_FindResource(image,resource[0],"25",resource[1],&size);assert(location && size>0);
  std::vector<char> actual(static_cast<size_t>(size));assert(JIMAGE_GetResource(image,location,actual.data(),size)==size);
  std::ifstream input(std::string(expected_root)+"/"+resource[0]+"/"+resource[1],std::ios::binary);assert(input);
  std::vector<char> expected((std::istreambuf_iterator<char>(input)),{});assert(actual==expected);
 }
 JIMAGE_Close(image);
}
void test_inflater() {
 std::vector<unsigned char> input(50000);for(size_t i=0;i<input.size();i++)input[i]=(i*31+i/101)&255;
 uLongf n=compressBound(input.size());std::vector<unsigned char> compressed(n);assert(compress2(compressed.data(),&n,input.data(),input.size(),6)==Z_OK);compressed.resize(n);
 std::vector<unsigned char> output(input.size());char *error=nullptr;
 for(int denied=0;denied<2;denied++) {zip_test_mode(denied,-1);assert(ZIP_InflateFully(compressed.data(),n,output.data(),output.size(),&error));assert(output==input);assert(zip_test_live()==0);}
 zip_test_mode(1,0);assert(!ZIP_InflateFully(compressed.data(),n,output.data(),output.size(),&error));assert(error&&zip_test_live()==0);
 zip_test_mode(1,-1);assert(!ZIP_InflateFully(compressed.data(),n-2,output.data(),output.size(),&error));assert(error&&zip_test_live()==0);
 compressed[0]^=255;assert(!ZIP_InflateFully(compressed.data(),n,output.data(),output.size(),&error));assert(error&&zip_test_live()==0);compressed[0]^=255;
 assert(!ZIP_InflateFully(compressed.data(),n,output.data(),output.size()-1,&error));assert(error&&zip_test_live()==0);
 zip_test_mode(0,-1);
}
int main(int argc,char **argv) {
 assert(argc==2);
 test_inflater();
 read_object(argv[1]);
 reject_file=true;
 read_object(argv[1]);
 assert(file_mappings==0 && anonymous_mappings==2);
 zip_test_mode(1,-1);read_object(argv[1]);assert(zip_test_maps()>0&&zip_test_live()==0);
 jint image_error=0;auto *image=JIMAGE_Open("build/java25/boot-image/lib/modules",&image_error);assert(image);
 jlong bytes=0;auto location=JIMAGE_FindResource(image,"java.base","25","sun/security/ssl/DTLSInputRecord.class",&bytes);assert(location);
 std::vector<char> buffer(bytes,0x5a);zip_test_mode(1,0);assert(JIMAGE_GetResource(image,location,buffer.data(),bytes)==0);
 for(char b:buffer)assert(b==0x5a);assert(zip_test_live()==0);
 zip_test_mode(1,-1);assert(JIMAGE_GetResource(image,location,buffer.data(),bytes)==bytes);assert((unsigned char)buffer[0]==0xca);assert(zip_test_live()==0);JIMAGE_Close(image);
 assert(file_mappings==0 && anonymous_mappings==4);
 reject_anonymous=true;
 jint error=0;
 assert(!JIMAGE_Open("build/java25/boot-image/lib/modules",&error));
 assert(file_mappings==0 && anonymous_mappings==5);
 std::puts("Real JIMAGE reader PASS: direct anonymous copies, zero file mappings, actual ZIP allocator fallback/failure/truncated/corrupt controls; DTLS/classes/TLS/JFR/desktop identity; failed decode returns0 without publishing bytes; mapping rejection");
}
