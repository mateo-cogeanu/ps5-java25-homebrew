#!/usr/bin/env python3
"""Exercise archive retirement against local Git remotes and real file changes."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from history_archive import retire_runtime_snapshots


def git(cwd, *args):
    return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.DEVNULL)


class RetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'archive'
        self.archive.mkdir()
        git(self.archive, 'init', '-b', 'main')
        original = b'frozen source\n'
        path = self.archive / 'runtime/Frozen/source.c'
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
        manifest = {'files': [{'destination': 'runtime/Frozen/source.c',
                              'original_path': 'Frozen/source.c', 'bytes': len(original), 'git_mode': '100644',
                              'sha256': hashlib.sha256(original).hexdigest()}]}
        data = (json.dumps(manifest) + '\n').encode()
        (self.archive / 'manifest.json').write_bytes(data)
        git(self.archive, 'add', '.')
        git(self.archive, '-c', 'user.name=Archive test', '-c', 'user.email=archive@example.invalid',
            'commit', '-m', 'Test archive')
        commit = git(self.archive, 'rev-parse', 'HEAD').decode().strip()
        git(self.root, 'clone', '--bare', str(self.archive), str(self.root / 'remote.git'))
        self.checkout = self.root / 'active'
        (self.checkout / 'Frozen').mkdir(parents=True)
        (self.checkout / 'Frozen/source.c').write_bytes(original)
        (self.root / '.tools/github-publish').mkdir(parents=True)
        self.pin = {'repository': str(self.root / 'remote'), 'commit': commit,
                    'manifest_sha256': hashlib.sha256(data).hexdigest(),
                    'runtime_snapshots': ['Frozen']}

    def retire(self):
        return retire_runtime_snapshots(self.root, self.checkout, self.pin)

    def test_verified_retirement_and_repeat(self):
        self.assertEqual(self.retire(), ['Frozen'])
        self.assertFalse((self.checkout / 'Frozen').exists())
        self.assertEqual(self.retire(), [])
        self.assertTrue((self.root / '.tools/github-publish/history-verified/runtime/Frozen/source.c').is_file())

    def test_changed_original_preserved(self):
        (self.checkout / 'Frozen/source.c').write_bytes(b'uncommitted work')
        with self.assertRaises(RuntimeError):
            self.retire()
        self.assertEqual((self.checkout / 'Frozen/source.c').read_bytes(), b'uncommitted work')

    def test_changed_original_mode_preserved(self):
        path = self.checkout / 'Frozen/source.c'
        path.chmod(0o755)
        with self.assertRaises(RuntimeError):
            self.retire()
        self.assertTrue(path.stat().st_mode & 0o111)

    def test_extra_private_file_preserved(self):
        (self.checkout / 'Frozen/private.txt').write_text('local')
        with self.assertRaises(RuntimeError):
            self.retire()
        self.assertTrue((self.checkout / 'Frozen/source.c').exists())
        self.assertTrue((self.checkout / 'Frozen/private.txt').exists())

    def test_missing_original_refuses_all_removal(self):
        (self.checkout / 'Frozen/source.c').unlink()
        with self.assertRaises(RuntimeError):
            self.retire()
        self.assertTrue((self.checkout / 'Frozen').is_dir())

    def test_bad_manifest_pin_preserves_original(self):
        self.pin['manifest_sha256'] = '0' * 64
        with self.assertRaises(RuntimeError):
            self.retire()
        self.assertTrue((self.checkout / 'Frozen/source.c').exists())

    def test_unsafe_name_preserves_original(self):
        self.pin['runtime_snapshots'] = ['../active']
        with self.assertRaises(ValueError):
            self.retire()
        self.assertTrue((self.checkout / 'Frozen/source.c').exists())


if __name__ == '__main__':
    unittest.main()
