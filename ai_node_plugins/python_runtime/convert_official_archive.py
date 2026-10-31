"""Convert the pinned upstream CPython install_only tar.gz into a validated ZIP.

This is an offline developer/build utility, not a runtime download or installer.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import tarfile
import zipfile
from pathlib import Path

UPSTREAM_SHA256 = '5ac66ae49a2104efeba985c1dc1cb40987757ee81cc6c7f218d10b801f3276ed'
UPSTREAM_FILENAME = 'cpython-3.12.10+20250409-x86_64-pc-windows-msvc-install_only.tar.gz'
REQUIRED = {'python.exe', 'LICENSE.txt', 'Lib/venv/__init__.py', 'Lib/ensurepip/__init__.py', 'Lib/site.py'}
LIMIT_BYTES = 1024 * 1024 * 1024
LIMIT_ENTRIES = 20000
RESERVED = {'CON','PRN','AUX','NUL'} | {f'COM{i}' for i in range(1,10)} | {f'LPT{i}' for i in range(1,10)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_member(member: tarfile.TarInfo) -> str:
    raw = member.name
    if not (member.isfile() or member.isdir()):
        raise ValueError(f'Unsupported TAR entry (links are forbidden): {raw}')
    if '\\' in raw or '\x00' in raw or raw.startswith('/') or ':' in raw:
        raise ValueError(f'Unsafe TAR path: {raw}')
    pieces = raw.rstrip('/').split('/')
    if not pieces or pieces[0] != 'python' or len(pieces) < 2:
        raise ValueError(f'Unexpected TAR prefix: {raw}')
    rel = pieces[1:]
    if any(not part or part in ('.','..') or part.endswith((' ','.')) or part.split('.')[0].upper() in RESERVED for part in rel):
        raise ValueError(f'Unsafe Windows path: {raw}')
    return '/'.join(rel)


def convert(source: Path, destination: Path) -> dict:
    if source.name != UPSTREAM_FILENAME:
        raise ValueError(f'Expected upstream filename: {UPSTREAM_FILENAME}')
    if sha256(source).lower() != UPSTREAM_SHA256:
        raise ValueError('Upstream SHA256 mismatch; no ZIP produced')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Destination already exists: {destination}')
    if not destination.parent.is_dir():
        raise FileNotFoundError(destination.parent)
    seen: set[str] = set()
    files: set[str] = set()
    dirs: set[str] = set()
    total = 0
    with tarfile.open(source, 'r:gz') as archive:
        members = archive.getmembers()
        if len(members) > LIMIT_ENTRIES:
            raise ValueError('Too many archive entries')
        planned = []
        for member in members:
            rel = validate_member(member)
            key = rel.casefold()
            if key in seen:
                raise ValueError(f'Case-insensitive path collision: {rel}')
            seen.add(key)
            if member.isfile():
                total += member.size
                if total > LIMIT_BYTES:
                    raise ValueError('Uncompressed size limit exceeded')
                files.add(key)
            else:
                dirs.add(key)
            planned.append((member, rel))
        for _, rel in planned:
            parts = rel.split('/')
            for index in range(1, len(parts)):
                if '/'.join(parts[:index]).casefold() in files:
                    raise ValueError(f'File/directory collision: {rel}')
        if files & dirs:
            raise ValueError('File/directory collision')
        if not {n.casefold() for n in REQUIRED}.issubset(files):
            raise ValueError(f'Missing required files: {sorted(n for n in REQUIRED if n.casefold() not in files)}')
        temporary = destination.with_name(destination.name + '.part-' + os.urandom(8).hex())
        try:
            with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as output:
                for member, rel in planned:
                    if member.isdir():
                        output.writestr(rel + '/', b'')
                        continue
                    src = archive.extractfile(member)
                    if src is None:
                        raise ValueError(f'Cannot read TAR member: {rel}')
                    with src, output.open(rel, 'w', force_zip64=True) as dst:
                        remaining = member.size
                        while remaining:
                            chunk = src.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise ValueError(f'Truncated TAR member: {rel}')
                            dst.write(chunk)
                            remaining -= len(chunk)
            with zipfile.ZipFile(temporary) as check:
                if check.testzip() is not None:
                    raise ValueError('ZIP CRC validation failed')
            temporary.rename(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
    return {'zip': str(destination), 'sha256': sha256(destination), 'files': len(files), 'uncompressed_bytes': total}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(convert(args.source, args.destination))
