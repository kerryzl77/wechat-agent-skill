#!/usr/bin/env python3
"""Check or explicitly build local WeChat helpers; never launch or grant access."""
import argparse, hashlib, json, plistlib, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path.home()/'Library/Application Support/CodexWeChatReader'
MANIFEST=HERE/'native/verified-builds.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True);g.add_argument('--check',action='store_true');g.add_argument('--build',action='store_true')
 p.add_argument('--replace',action='store_true',help='Explicitly rebuild existing changed helpers; may invalidate macOS grants')
 a=p.parse_args();manifest=json.loads(MANIFEST.read_text());failed=False
 for name,m in manifest.items():
  source=HERE/'native'/name;app=ROOT/m['app_relative'];binary=app/'Contents/MacOS'/m['executable']
  source_ok=sha(source)==m['source_sha256'];binary_ok=binary.exists() and sha(binary)==m['installed_binary_sha256']
  signature_ok=binary.exists() and subprocess.run(['/usr/bin/codesign','--verify','--strict',str(app)],capture_output=True).returncode==0
  if source_ok and binary_ok and signature_ok:
   print(json.dumps({'helper':m['executable'],'status':'verified_existing'}));continue
  if a.check:
   failed=True;print(json.dumps({'helper':m['executable'],'status':'missing_or_changed','source_matches':source_ok,'binary_matches':binary_ok,'signature_valid':signature_ok}));continue
  if app.exists() and not a.replace: raise SystemExit('Existing helper differs; inspect before --build --replace. Rebuilding may invalidate its grant.')
  binary.parent.mkdir(parents=True,exist_ok=True)
  recorder=m['executable']=='AlternateScreenRecorder'
  info={'CFBundleIdentifier':'local.codex.alternate-screen-recorder' if recorder else 'local.codex.wechat-native-input','CFBundleName':app.stem,'CFBundleDisplayName':app.stem,'CFBundleExecutable':m['executable'],'CFBundlePackageType':'APPL','CFBundleVersion':'1','LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True}
  (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
  cmd=['xcrun','swiftc',str(source),'-o',str(binary),'-framework','Cocoa']
  if recorder:cmd+=['-framework','AVFoundation']
  subprocess.run(cmd,check=True);subprocess.run(['codesign','--force','--sign','-',str(app)],check=True);subprocess.run(['codesign','--verify','--strict',str(app)],check=True)
  m['source_sha256']=sha(source);m['installed_binary_sha256']=sha(binary)
  print(json.dumps({'helper':m['executable'],'status':'built','permission_recheck_required':True}))
 if a.build:MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
 return 2 if failed else 0
if __name__=='__main__':raise SystemExit(main())
