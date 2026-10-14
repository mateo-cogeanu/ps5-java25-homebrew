# Embedded HotSpot setup probe

This test application embeds objects built from the FreeBSD OpenJDK 25 fork:
https://github.com/freebsd/openjdk/tree/b219cdec88ca2e165711f63b8158ab78303facc8

The upstream tag is jdk-25.0.4+7-freebsd-1. Preserve upstream copyright notices
and the accompanying LICENSE, ADDITIONAL_LICENSE_INFO and ASSEMBLY_EXCEPTION.
HotSpot files carry their own GPL-2.0 notices; Classpath exceptions apply where
the upstream file/license specifies them.

The corresponding local port source and build recipe are in this workspace:
java25/patches/, java25/probe/jni.cpp, tools/java25_source.py,
tools/java25_cc.py, tools/package_java25_jni.py and tools/package_native.py.
The pinned complete upstream source is in .tools/java25/openjdk. Rebuild with
python3 tools/java25_source.py --build-hotspot and
python3 tools/package_java25_jni.py. The native app/renderer sources and notices
are documented separately in THIRD_PARTY_NOTICES.md and GPL-3.0.txt.

These are private experimental tests, not a complete Java distribution.
PPSA99864 checks setup APIs only, with optional SDK loader callbacks absent.
PPSA99865 attempts VM creation and Hello25 using the embedded core-library
lookup adapter in tools/java25_builtin_runtime.py and class image builder
tools/java25_boot_image.py. Console VM execution is not yet established.
The core class image builder uses a temporary accepted host-jlink platform
tag to transport the cross-built classes/resources, with no Linux or host
native binaries included. HotSpot/core constructors run only after the first
selected test is displayed as RUN. See java25/README.md for current limitations.
