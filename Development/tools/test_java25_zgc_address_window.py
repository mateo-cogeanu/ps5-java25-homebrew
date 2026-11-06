#!/usr/bin/env python3
"""Check the actual PS5 address selection and x86 ZGC color round trips."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
hotspot = root / ".tools/java25/openjdk/src/hotspot"
platform = (hotspot / "cpu/x86/gc/z/zAddress_x86.cpp").read_text()
platform = platform[platform.index("size_t ZPlatformAddressOffsetBits()"):platform.index("void ZGlobalsPointers::pd_set_good_masks()")]
header = (hotspot / "share/gc/z/zAddress.hpp").read_text()
constants = header[header.index("constexpr uintptr_t z_pointer_mask"):header.index("// Barrier metadata masks")]
inline = (hotspot / "share/gc/z/zAddress.inline.hpp").read_text()
x86_inline = (hotspot / "cpu/x86/gc/z/zAddress_x86.inline.hpp").read_text()

def function(text, signature):
    return re.search(re.escape(signature) + r" \{.*?\n\}", text, re.S).group()

functions = [
    function(inline, "inline constexpr int ZPointer::load_shift_lookup_index(uintptr_t value)"),
    function(x86_inline, "inline constexpr int ZPointer::load_shift_lookup(uintptr_t value)"),
    function(inline, "inline zpointer ZAddress::color(zaddress addr, uintptr_t color)"),
    function(inline, "inline zaddress ZPointer::uncolor(zpointer ptr)")
]
source = r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <algorithm>
static void verify(bool test) { assert(test); }
#undef assert
#define assert(condition, ...) verify(condition)
static bool is_power_of_2(size_t n) { return n && !(n & (n - 1)); }
static size_t log2i_exact(size_t value) { verify(is_power_of_2(value)); return __builtin_ctzll(value); }
template<class T> static T clamp(T value, T low, T high) { return std::max(low, std::min(high, value)); }
static size_t requested;
class ZGlobalsPointers {
 public:
  static size_t min_address_offset_request() { return requested; }
};
using zaddress = uintptr_t;
using zpointer = uintptr_t;
static uintptr_t untype(uintptr_t p) { return p; }
static uintptr_t to_zpointer(uintptr_t p) { return p; }
static uintptr_t to_zaddress(uintptr_t p) { return p; }
static bool is_null_any(uintptr_t p) { return !p; }
class ZPointer {
 public:
  static constexpr int load_shift_lookup_index(uintptr_t);
  static constexpr int load_shift_lookup(uintptr_t);
  static bool is_load_good(uintptr_t) { return true; }
  static uintptr_t uncolor(uintptr_t);
};
class ZAddress {
 public:
  static uintptr_t color(uintptr_t, uintptr_t);
};
'''
source += constants + platform + chr(10).join(functions)
source += r'''
int main() {
  for (size_t bits = 35; bits <= 37; ++bits) {
    requested = uintptr_t(1) << bits;
#ifdef __PROSPERO__
    verify(ZPlatformAddressOffsetBits() == bits);
    verify(ZPlatformAddressHeapBaseShift() == bits);
#else
    verify(ZPlatformAddressOffsetBits() == 42);
    verify(ZPlatformAddressHeapBaseShift() == 42);
#endif
    uintptr_t base = uintptr_t(1) << bits;
    for (uintptr_t offset : {uintptr_t(0), uintptr_t(8), base / 2, base - 8}) {
      uintptr_t address = base + offset;
      verify((address & (base - 1)) == offset);
      for (unsigned phase = 0; phase < 4; ++phase) {
        for (unsigned metadata = 0; metadata < 256; ++metadata) {
          uintptr_t color = (uintptr_t(1) << (ZPointerRemappedShift + phase)) |
                            (uintptr_t(metadata) << 4);
          auto pointer = ZAddress::color(address, color);
          verify(ZPointer::uncolor(pointer) == address);
        }
      }
    }
  }
}
'''
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    (work / "test.cpp").write_text(source)
    for name, flags in (("ps5", ["-D__PROSPERO__"]), ("desktop", [])):
        subprocess.run([
            "clang++", "-std=c++17", "-O1", "-g", "-fsanitize=address,undefined",
            *flags, str(work / "test.cpp"), "-o", str(work / name)
        ], check=True)
        subprocess.run([str(work / name)], check=True)
print("PASS actual ZGC address selection and color/uncolor arithmetic: PS5 windows, all four remap phases, metadata combinations, boundaries and desktop defaults; console barriers pending")
