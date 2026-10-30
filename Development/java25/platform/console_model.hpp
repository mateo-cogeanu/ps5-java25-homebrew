/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstddef>
#include <cstring>
namespace ps5::console {
enum class Model { unknown, standard, pro };
enum class Status { unavailable, failed, malformed, unrecognized, recognized };
struct Result { Model model=Model::unknown; Status status=Status::unavailable; int native_result=0; };
using Query=int(*)(char*);
// Only documented retail CFI families. Unknown revisions/devkits stay unknown.
inline Model classify(const char* text,std::size_t capacity) {
 if(!text)return Model::unknown;
 const char* end=static_cast<const char*>(std::memchr(text,0,capacity));
 if(!end)return Model::unknown;
 std::size_t n=static_cast<std::size_t>(end-text);
 if(n<8||n>13||std::memcmp(text,"CFI-",4))return Model::unknown;
 for(unsigned i=4;i<8;i++)if(text[i]<'0'||text[i]>'9')return Model::unknown;
 std::size_t i=8;
 if(i<n&&(text[i]=='A'||text[i]=='B'))i++;
 if(i<n&&text[i]=='-')i++;
 if(i<n){if(n-i!=2||text[i]<'0'||text[i]>'9'||text[i+1]<'0'||text[i+1]>'9')return Model::unknown;i+=2;}
 if(i!=n||text[n-1]=='-')return Model::unknown;
 if(text[4]=='7'&&(text[5]=='0'||text[5]=='1'))return Model::pro;
 if((text[4]=='1'&&(text[5]>='0'&&text[5]<='2'))||(text[4]=='2'&&(text[5]=='0'||text[5]=='1')))return Model::standard;
 return Model::unknown;
}
inline Result read(Query query) {
 Result out;if(!query)return out;
 // The pinned SDK hwinfo example uses 1000 bytes for this unsized native ABI.
 // Do not shrink this buffer. Never copy/log the raw response or call serial APIs.
 char text[1000];std::memset(text,0xff,sizeof(text));
 out.native_result=query(text);
 if(out.native_result!=0){out.status=Status::failed;return out;}
 if(!std::memchr(text,0,sizeof(text))){out.status=Status::malformed;return out;}
 out.model=classify(text,sizeof(text));
 out.status=out.model==Model::unknown?Status::unrecognized:Status::recognized;
 return out;
}
inline const char* name(Model model) {
 switch(model){case Model::standard:return "PlayStation 5";case Model::pro:return "PlayStation 5 Pro";default:return "PlayStation 5 (model unknown)";}
}
}
