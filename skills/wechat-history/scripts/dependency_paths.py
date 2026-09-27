"""Resolve separately installed runtime libraries; no automatic installation."""
import ctypes.util
import os
from pathlib import Path


def zstd_library():
    candidates = [os.environ.get('ZSTD_LIBRARY'),
                  '/opt/homebrew/opt/zstd/lib/libzstd.dylib',
                  '/usr/local/opt/zstd/lib/libzstd.dylib',
                  ctypes.util.find_library('zstd')]
    for candidate in candidates:
        if candidate and (not candidate.startswith('/') or Path(candidate).exists()):
            return candidate
    raise RuntimeError('zstd library missing; install zstd or set ZSTD_LIBRARY')
