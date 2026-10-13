#!/usr/bin/env python3
"""Publish completed source changes to Development; never mutate passing snapshots."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--message', required=True, help='Describe this completed set of changes')
args = parser.parse_args()
config = json.loads((ROOT / 'java25/github-publication.json').read_text())
checkout = ROOT / config['checkout']
if not (checkout / '.git').is_dir():
    checkout.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'clone', config['repository'] + '.git', str(checkout)], check=True)

# Only this explicit source allowlist is published. Dependency caches, build
# outputs, local credentials, downloaded photos and generated logs stay local.
items = ['assets', 'native', 'src', 'sce_sys', 'sounds', 'tools', 'java25',
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
    shutil.copy2(ROOT / 'README.md', development / 'WORKSPACE_README.md')
# Keep publication instructions visible to future agents in the public repo.
shutil.copy2(ROOT / 'AGENTS.md', checkout / 'AGENTS.md')
subprocess.run(['git', 'add', '--', 'Development', 'AGENTS.md'], cwd=checkout, check=True)
changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', 'Development', 'AGENTS.md'], cwd=checkout)
if changed.returncode == 1:
    subprocess.run(['git', 'commit', '-m', args.message], cwd=checkout, check=True)
elif changed.returncode != 0:
    raise SystemExit(changed.returncode)
subprocess.run(['git', 'push', 'origin', 'main'], cwd=checkout, check=True)
print(config['repository'])
