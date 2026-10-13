PS5_PAYLOAD_SDK ?= $(CURDIR)/.tools/ps5-payload-sdk
LLVM_CONFIG ?= /opt/homebrew/opt/llvm/bin/llvm-config
export LLVM_CONFIG
include $(PS5_PAYLOAD_SDK)/toolchain/prospero.mk

CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror
ELF := build/controller-tester.elf

.PHONY: all clean package java25-probe java25-runtime-probe java25-jni-probe java25-startup
all: $(ELF)

build/payload.x: tools/linker_layout.py $(PS5_PAYLOAD_SDK)/ldscripts/elf_x86_64.x
	mkdir -p build
	python3 tools/linker_layout.py $(PS5_PAYLOAD_SDK)/ldscripts/elf_x86_64.x $@

$(ELF): src/main.c src/pad.h build/payload.x
	mkdir -p build
	$(CC) $(CFLAGS) src/main.c -Wl,-T,build/payload.x -lScePad -lSceUserService -o $@

clean:
	rm -f $(ELF)

package:
	python3 tools/package_native.py

java25-probe:
	python3 tools/package_native.py --source java25/probe/main.cpp --param java25/probe/param.json

java25-runtime-probe:
	python3 tools/package_native.py --source java25/probe/runtime.cpp --param java25/probe/runtime-param.json

java25-jni-probe:
	python3 tools/package_java25_jni.py

java25-startup:
	python3 tools/package_java25_jni.py --startup
