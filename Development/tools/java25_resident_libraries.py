#!/usr/bin/env python3
"""Validate external consumer-owned resident native objects for JNI packaging."""
import json
from pathlib import Path
import re
import struct


def read_libraries(path, reserved):
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError('Resident libraries must be a JSON list')
    names = set(reserved)
    result = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'name', 'objects'}:
            raise ValueError('Resident library requires only name and objects')
        name, objects = row['name'], row['objects']
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', name) or name in names:
            raise ValueError('Invalid, duplicate or reserved resident library name')
        if not isinstance(objects, list) or not objects:
            raise ValueError('Resident library requires a nonempty object list')
        checked = []
        for value in objects:
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise ValueError('Resident object path must be absolute')
            source = Path(value).resolve();data = source.read_bytes()
            if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<HH', data, 16) != (1, 62):
                raise ValueError('Resident input must be an ELF64 little-endian x86_64 relocatable object: ' + str(source))
            if source in checked:
                raise ValueError('Duplicate resident object')
            checked.append(source)
        names.add(name);result.append((name, checked))
    return result
