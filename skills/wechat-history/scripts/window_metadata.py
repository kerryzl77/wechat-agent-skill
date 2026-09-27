#!/usr/bin/env python3
"""Read current display and WeChat window coordinates; no capture or input."""
import hashlib, subprocess
from pathlib import Path
source=Path(__file__).resolve().parent/'native/WindowMetadata.swift'
root=Path.home()/'Library/Application Support/CodexWeChatReader/metadata-helper'
root.mkdir(parents=True,exist_ok=True,mode=0o700)
binary=root/('window-metadata-'+hashlib.sha256(source.read_bytes()).hexdigest()[:16])
if not binary.exists():subprocess.run(['xcrun','swiftc',str(source),'-framework','Cocoa','-o',str(binary)],check=True)
subprocess.run([str(binary)],check=True)
