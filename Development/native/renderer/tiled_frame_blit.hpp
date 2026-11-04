/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
namespace ps5::demo::detail {
// Same1920x1080 64KiB tile layout; copy four adjacent pixels at a time.
// No caller-visible padding, ownership, pitch or input-refusal change.
inline constexpr std::size_t active_tiled_bytes=15u*9u*65536u;
inline void blit_tiled_1080(std::uint32_t* output,const std::uint32_t* input,unsigned pitch)noexcept{
 for(unsigned by=0;by<9;by++)for(unsigned bx=0;bx<15;bx++){
  auto* tile=reinterpret_cast<unsigned char*>(output)+(by*15+bx)*65536u;
  unsigned rows=by==8?56:128;
  for(unsigned y=0;y<rows;y++){
   unsigned yo=((y<<4)&0x70u)^((y<<5)&0xf00u)^((y<<9)&0x1000u)^((y<<8)&0x4000u);
   const auto* row=input+std::size_t(by*128+y)*pitch+bx*128;
   for(unsigned x=0;x<128;x+=4){unsigned xo=((x<<5)&0x380u)^((x<<4)&0x400u)^((x<<6)&0x800u)^((x<<9)&0xa000u);std::memcpy(tile+(yo^xo),row+x,16);}
  }
 }
}
}
