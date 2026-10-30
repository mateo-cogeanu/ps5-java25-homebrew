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


def read_aliases(values, names):
    """Explicit build-time aliases share a resident group's symbols and lifetime."""
    result = {}; used = set(names)
    for value in values:
        pair = value.split('=')
        if len(pair) != 2:
            raise ValueError('Resident alias requires alias=library')
        alias, target = pair
        if len(alias)>96 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)*', alias) or alias in used or target not in names:
            raise ValueError('Invalid, duplicate or unknown resident alias')
        used.add(alias); result[alias] = target
    return result


def read_alias_symbols(values, aliases):
    """Opt-in lookup overrides on an explicit alias, within its existing group."""
    result = {}
    for value in values:
        match = re.fullmatch(r'([^:=]+):([A-Za-z_][A-Za-z0-9_]*)=([A-Za-z_][A-Za-z0-9_]*)', value)
        if not match or match[1] not in aliases:
            raise ValueError('Alias symbol requires known_alias:export=resident_symbol')
        alias, export, replacement = match.groups()
        if export.startswith(('JNI_', 'JVM_', 'Java_')) or replacement.startswith(('JNI_', 'JVM_', 'Java_')):
            raise ValueError('Alias symbol override cannot change JNI/JVM lifecycle or entrypoints')
        group = result.setdefault(alias, {})
        if export in group:
            raise ValueError('Duplicate alias symbol override')
        group[export] = replacement
    return result


def alias_symbol_entries(entries, overrides):
    """Copy a generated alias table, resolving only actual exports of its group."""
    addresses = {}
    for entry in entries:
        match = re.fullmatch(r'\{"([A-Za-z_][A-Za-z0-9_]*)", reinterpret_cast<void \*>\(&([A-Za-z_][A-Za-z0-9_]*)\)\}', entry)
        if not match:
            raise ValueError('Invalid generated resident table entry')
        addresses[match[1]] = match[2]
    if any(export not in addresses or replacement not in addresses for export, replacement in overrides.items()):
        raise ValueError('Alias symbol override must name two actual exports in the same resident group')
    result = []
    for entry in entries:
        name = entry.split('"', 2)[1]
        if name in overrides:
            result.append('{"'+name+'", reinterpret_cast<void *>(&'+addresses[overrides[name]]+')}')
        else:
            result.append(entry)
    return result
