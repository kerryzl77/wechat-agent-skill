#!/usr/bin/env python3
"""Local AVFoundation recorder orchestration; no network or input injection."""
import argparse, json, subprocess, time
from pathlib import Path
root = Path.home() / 'Library/Application Support/CodexWeChatReader/alternate-screen'
app = root.parent / 'alternate-screen-helper/Alternate Screen Recorder.app'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('action', choices=['probe', 'start', 'frame', 'stop'])
p.add_argument('--display', type=int, default=1)
a = p.parse_args()
if a.action in ('probe', 'start'):
    cmd = ['/usr/bin/open', '-n', str(app)]
    if a.action == 'start': cmd += ['--args', '--capture', '--display', str(a.display)]
    subprocess.run(cmd, check=True)
    print('Started permission probe.' if a.action == 'probe' else 'Capture requested. Use frame to inspect a fresh image; capture stops after 120 seconds.')
else:
    run = Path((root / 'current-run.txt').read_text().strip())
    if run.parent.resolve() != root.resolve(): raise SystemExit('Invalid run directory')
    if a.action == 'stop':
        (run / 'STOP').touch(mode=0o600)
        for local in run.iterdir():
            if local.is_file(): local.chmod(0o600)
        print('Stop requested for this local recorder run.')
    else:
        frame = run / 'latest.png'
        frame.chmod(0o600)
        age = time.time() - frame.stat().st_mtime
        print(json.dumps({'path': str(frame), 'age_seconds': round(age, 2), 'fresh': age <= 3, 'run': run.name}))
        if age > 3: raise SystemExit('Frame is stale; do not use it to target input.')
