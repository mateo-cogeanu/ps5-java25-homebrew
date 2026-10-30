#!/usr/bin/env python3
"""Retire only byte-verified frozen runtime snapshots after archive publication."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def retire_runtime_snapshots(root, checkout, pin):
    names = pin['runtime_snapshots']
    for name in names:
        if Path(name).name != name or name in {'.', '..', 'Development'}:
            raise ValueError('Unsafe archive snapshot path')
    present = [name for name in names if (checkout / name).exists()]
    if not present:
        return []
    archive = root / '.tools/github-publish/history-verified'
    if not (archive / '.git').is_dir():
        subprocess.run(['git', 'clone', '--no-checkout', pin['repository'] + '.git', str(archive)], check=True)
    elif subprocess.check_output(['git', 'status', '--porcelain'], cwd=archive):
        raise RuntimeError('Archive verification cache has local changes; preserve them before continuing')
    subprocess.run(['git', 'fetch', 'origin', pin['commit']], cwd=archive, check=True)
    subprocess.run(['git', 'checkout', '--detach', pin['commit']], cwd=archive, check=True)
    data = (archive / 'manifest.json').read_bytes()
    if hashlib.sha256(data).hexdigest() != pin['manifest_sha256']:
        raise RuntimeError('Pinned archive manifest checksum mismatch')
    manifest = json.loads(data)
    expected = {}
    for entry in manifest['files']:
        path = archive / entry['destination']
        if (path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']
                or path.stat().st_size != entry['bytes']
                or bool(path.stat().st_mode & 0o111) != (entry['git_mode'] == '100755')):
            raise RuntimeError('Archive content differs from manifest: ' + entry['destination'])
        if entry['destination'].startswith('runtime/') and entry['original_path'].split('/')[0] in present:
            expected[entry['original_path']] = entry
    actual = {p.relative_to(checkout).as_posix() for name in present
              for p in (checkout / name).rglob('*') if p.is_file() or p.is_symlink()}
    if actual != set(expected):
        raise RuntimeError('Frozen snapshot contains missing or additional local files; refusing removal')
    for name, entry in expected.items():
        path = checkout / name
        if (path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']
                or bool(path.stat().st_mode & 0o111) != (entry['git_mode'] == '100755')):
            raise RuntimeError('Frozen snapshot changed locally; refusing removal: ' + name)
    # Every original has been checked before the first removal. Git history and
    # the independently fetched archive remain recovery paths.
    for name in present:
        shutil.rmtree(checkout / name)
    return present
