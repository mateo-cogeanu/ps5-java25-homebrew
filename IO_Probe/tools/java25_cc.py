#!/usr/bin/env python3
"""Route HotSpot's C-driver C++ compilations through the SDK's C++ driver.

The SDK C wrapper puts C headers before any later user-supplied -isystem path.
Using the C++ wrapper keeps libc++ wrapper headers ahead of the C headers.
"""
import os
from pathlib import Path
import sys

sdk = Path(__file__).resolve().parents[1] / ".tools/native-sdk/ps5-payload-sdk/bin"
arguments = sys.argv[1:]
cxx = any(argument.startswith("-std=c++") or argument.startswith("-std=gnu++")
          or argument in ("c++", "c++-header")
          or argument.endswith((".cpp", ".cc", ".cxx", ".hpp")) for argument in arguments)
driver = str(sdk / ("prospero-clang++" if cxx else "prospero-clang"))
os.execv(driver, [driver, *arguments])
