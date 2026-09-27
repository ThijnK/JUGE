#!/usr/bin/env python3
"""Fetch the official pinned Kex distribution into a JUGE tool template."""
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import sys
import urllib.request
import zipfile

VERSION = '0.0.11'
SHA256 = 'f83468d5bc09f1434a490a728ecfee1cfe80f10b2cbb45e134a53fc6129ebb27'
URL = f'https://github.com/vorpal-research/kex/releases/download/{VERSION}/kex-{VERSION}.zip'


def main():
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    archive = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else destination.parent / '.downloads' / f'kex-{VERSION}.zip'
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise SystemExit('Kex archive SHA256 mismatch')
    jar_names = {f'{module}/target/{module}-{VERSION}-jar-with-dependencies.jar'
                 for module in ('kex-runner', 'kex-executor')}
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            name = entry.filename
            if name not in jar_names | {'kex.ini', 'kex.policy', 'LICENSE'} and not name.startswith('runtime-deps/'):
                continue
            if '..' in PurePosixPath(name).parts or name.startswith('/'):
                raise SystemExit('Unsafe archive member')
            if entry.is_dir():
                continue
            target = destination / 'lib/kex' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(entry) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)
    shutil.copy2(Path(__file__).with_name('runtool'), destination / 'runtool')
    shutil.copy2(Path(__file__).resolve().parents[1] / 'generation.py', destination / 'generation.py')
    (destination / 'runtool').chmod(0o755)
    print(f'Kex {VERSION}: {destination}')


if __name__ == '__main__':
    main()
