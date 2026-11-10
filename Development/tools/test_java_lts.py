#!/usr/bin/env python3
"""Offline LTS source-preservation, ordered patch and boot pin failure controls."""
import hashlib
from pathlib import Path
import subprocess
import tempfile

from java_lts import ROOT, apply_patches, pinned_download, sha, verify_boot


def reject(action, expected=ValueError):
    try:
        action()
    except expected:
        return
    raise AssertionError('Invalid LTS input accepted')


def main():
    if not __debug__:
        raise RuntimeError('Run LTS checks without Python optimization')
    with tempfile.TemporaryDirectory(prefix='java-lts-check-') as folder:
        work = Path(folder)
        source = work / 'source'
        source.mkdir()
        subprocess.run(['git', 'init', '-q', str(source)], check=True)
        original = source / 'probe.txt'
        original.write_text('original\n')
        subprocess.run(['git', 'add', 'probe.txt'], cwd=source, check=True)
        patch = work / 'port.patch'
        patch.write_text('--- a/probe.txt\n+++ b/probe.txt\n@@ -1 +1 @@\n-original\n+ported\n')
        assert apply_patches(source, [patch]) == 'applied'
        assert original.read_text() == 'ported\n'
        assert apply_patches(source, [patch]) == 'already applied'
        original.write_text('maintainer edit\n')
        before = sha(original)
        reject(lambda: apply_patches(source, [patch]))
        assert sha(original) == before
        data = b'original boot archive fixture'
        archive = work / 'boot.tar.gz'
        pin = {'url': 'https://example.invalid/no-network', 'size': len(data),
               'sha256': hashlib.sha256(data).hexdigest()}
        reject(lambda: pinned_download(pin, archive), FileNotFoundError)
        archive.write_bytes(data)
        pinned_download(pin, archive)
        archive.write_bytes(b'corrupt cached archive')
        reject(lambda: pinned_download(pin, archive))
        assert archive.read_bytes() == b'corrupt cached archive'
        reject(lambda: verify_boot(work / 'missing-jdk', 17))
    # Reproduce each canonical patch set against its pinned upstream preimages.
    # This optional cache-aware section is read-only; no source cache mutation.
    for major in (17, 21):
        source = ROOT / ('.tools/java' + str(major) + '/openjdk')
        if not (source / '.git').exists():
            continue
        patches = sorted((ROOT / ('java25/lts/' + str(major) + '/patches')).glob('*.patch'))
        with tempfile.TemporaryDirectory(prefix='java-lts-preimages-') as folder:
            preimages = Path(folder)
            subprocess.run(['git', 'init', '-q', str(preimages)], check=True)
            created = set()
            for patch in patches:
                lines = patch.read_text().splitlines()
                for line, following in zip(lines, lines[1:]):
                    if line == '--- /dev/null' and following.startswith('+++ b/'):
                        created.add(following.removeprefix('+++ b/'))
                    if line.startswith('--- a/'):
                        name = line.removeprefix('--- a/')
                        if name in created:
                            continue
                        target = preimages / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=source))
            assert apply_patches(preimages, patches) == 'applied'
            assert apply_patches(preimages, patches) == 'already applied'
        print('PASS pinned Java', major, 'original preimages, complete patch application/idempotence')
    print('PASS offline LTS patch conflict/source preservation, missing/corrupt boot refusal and incomplete JDK refusal')


if __name__ == '__main__':
    main()
