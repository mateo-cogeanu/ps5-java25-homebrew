#!/usr/bin/env python3
"""Publish active source to Development; preserve frozen bytes in the verified archive."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from history_archive import retire_runtime_snapshots

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--message', required=True, help='Describe this completed set of changes')
args = parser.parse_args()
config = json.loads((ROOT / 'java25/github-publication.json').read_text())
checkout = ROOT / config['checkout']
if not (checkout / '.git').is_dir():
    checkout.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'clone', config['repository'] + '.git', str(checkout)], check=True)

retired = retire_runtime_snapshots(ROOT, checkout, config['history_archive'])

# Only this explicit source allowlist is published. Dependency caches, build
# outputs, local credentials, downloaded photos and generated logs stay local.
items = ['assets', 'docs', 'native', 'src', 'sce_sys', 'sounds', 'tools', 'java25',
         'Makefile', 'THIRD_PARTY_NOTICES.md', '.gitignore']
development = checkout / 'Development'
development.mkdir(exist_ok=True)
for name in items:
    source = ROOT / name
    target = development / name
    if not source.exists():
        continue
    if source.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    else:
        shutil.copy2(source, target)
if (ROOT / 'README.md').exists():
    shutil.copy2(ROOT / 'README.md', checkout / 'README.md')
    (development / 'README.md').write_text('# Active runtime development\n\nSee the [project README](../README.md), [build guide](docs/source-organization.md) and [port notes](java25/README.md). Frozen source is preserved in [the history archive](https://github.com/mateo-cogeanu/ps5-homebrew-history); original releases remain in this repository.\n')
    (development / 'WORKSPACE_README.md').unlink(missing_ok=True)
(checkout / 'docs').mkdir(exist_ok=True)
shutil.copy2(ROOT / 'docs/readme-banner.svg', checkout / 'docs/readme-banner.svg')
# Keep publication instructions visible to future agents in the public repo.
shutil.copy2(ROOT / 'AGENTS.md', checkout / 'AGENTS.md')
paths = ['Development', 'AGENTS.md', 'README.md', 'docs', *retired]
subprocess.run(['git', 'add', '--all', '--', *paths], cwd=checkout, check=True)
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=checkout, check=True)
changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', *paths], cwd=checkout)
if changed.returncode == 1:
    subprocess.run(['git', 'commit', '-m', args.message], cwd=checkout, check=True)
elif changed.returncode != 0:
    raise SystemExit(changed.returncode)
subprocess.run(['git', 'push', 'origin', 'main'], cwd=checkout, check=True)
print(config['repository'])
