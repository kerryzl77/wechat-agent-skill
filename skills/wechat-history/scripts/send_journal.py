#!/usr/bin/env python3
"""Private idempotent journal for one authorized text send; no UI or DB writes."""
import argparse, fcntl, hashlib, json, os, re, time
from contextlib import contextmanager
from pathlib import Path
from wechat_db import Reader, private_write, root_for
DEFAULT_ROOT=Path.home()/'Library/Application Support/CodexWeChatReader/send-operations'
DEFAULT_KEYS=Path.home()/'Library/Application Support/CodexWeChatReader/keys.json'
class Journal:
 def __init__(self,reader,root=DEFAULT_ROOT):
  self.reader=reader;self.root=Path(root)
  self.root.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(self.root,0o700)
 def identity(self):return hashlib.sha256(str(self.reader.root.resolve()).encode()).hexdigest()
 @contextmanager
 def lock(self,op):
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',op):raise ValueError('Use a stable operation ID of 1-80 letters, digits, underscores or hyphens')
  path=self.root/(op+'.json')
  fd=os.open(self.root/(op+'.lock'),os.O_RDWR|os.O_CREAT,0o600)
  with os.fdopen(fd,'w') as f:
   fcntl.flock(f,fcntl.LOCK_EX);yield path
 def load(self,p):
  d=json.loads(p.read_text())
  if d['root_hash']!=self.identity():raise RuntimeError('Account does not match this operation')
  return d
 def prepare(self,op,chat,self_id,text):
  if not text or '\n' in text or '\r' in text or len(text.encode('utf-16-le'))//2>500:raise ValueError('Tested input supports nonempty single-line text up to 500 UTF-16 units')
  with self.lock(op) as p:
   if p.exists():raise RuntimeError('Operation exists; inspect status/verify; do not create a new attempt')
   contacts=self.reader.resolve(chat)
   if len(contacts)!=1 or contacts[0]['username']!=chat:raise RuntimeError('Exact chat ID must uniquely resolve')
   selves=self.reader.resolve(self_id)
   if len(selves)!=1 or selves[0]['username']!=self_id:raise RuntimeError('Exact self sender ID must uniquely resolve')
   # Also validate self identity in the message database before creating state.
   self.reader.read(chat,limit=1,self_id=self_id)
   d={'version':1,'op':op,'status':'prepared','root_hash':self.identity(),'chat_id':chat,'self_id':self_id,'text':text,'prepared_at':time.time(),'baseline':self.reader.snapshot(chat)}
   private_write(p,d);return {'op':op,'status':'prepared','chat_id':chat}
 def arm(self,op):
  with self.lock(op) as p:
   d=self.load(p)
   if d['status']!='prepared':raise RuntimeError('Already attempted or verified; do not send again')
   current=self.reader.snapshot(d['chat_id']);before=d['baseline']
   if current['salts']!=before['salts'] or any(current['cursor'].get(n,-1)<c for n,c in before['cursor'].items()):raise RuntimeError('Database changed since preparation; inspect without sending')
   d['baseline']=current;d['attempted_at']=time.time();d['status']='attempted'
   private_write(p,d);return {'op':op,'status':'attempted','submit_events_allowed':1}
 def verify(self,op):
  with self.lock(op) as p:
   d=self.load(p)
   if d['status']=='sent_db_verified':return {'op':op,'status':d['status'],'receipt':d['receipt']}
   if d['status']!='attempted':raise RuntimeError('No armed send attempt; an independently synced message must not count')
   before=d['baseline'];now=self.reader.snapshot(d['chat_id'])
   if before['salts']!=now['salts'] or any(now['cursor'].get(n,-1)<c for n,c in before['cursor'].items()):raise RuntimeError('Database identity or cursor changed; manual review required')
   if any(now['cursor'][n]-c>2000 for n,c in before['cursor'].items()):raise RuntimeError('Too many rows for bounded verification; inspect manually without resending')
   rows=self.reader.read(d['chat_id'],limit=2000,after=before['cursor'],self_id=d['self_id'])
   if any(x['from_self'] is None for x in rows):raise RuntimeError('Unknown sender identity; inspect manually')
   matches=[x for x in rows if x['from_self'] is True and int(x['local_type'])==1 and x['text']==d['text']]
   if len(matches)==1 and int(matches[0]['server_id'])!=0:
    x=matches[0];receipt={k:x[k] for k in ('database','local_id','server_id','create_time')}
    d.update(status='sent_db_verified',verified_at=time.time(),receipt=receipt);private_write(p,d)
    return {'op':op,'status':d['status'],'receipt':receipt}
   return {'op':op,'status':'not_verified','exact_matches':len(matches),'new_rows':len(rows),'retry_allowed':False}
 def status(self,op):
  with self.lock(op) as p:
   d=self.load(p)
   return {k:d[k] for k in ('op','status','chat_id','prepared_at','attempted_at','verified_at','receipt') if k in d}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db-root',type=Path);p.add_argument('--key-file',type=Path,default=DEFAULT_KEYS)
 sub=p.add_subparsers(dest='action',required=True)
 for action in ('prepare','arm','verify','status'):
  s=sub.add_parser(action);s.add_argument('--op',required=True)
  if action=='prepare':
   s.add_argument('--chat-id',required=True);s.add_argument('--self-id',required=True);s.add_argument('--text-file',type=Path,required=True)
 a=p.parse_args();j=Journal(Reader(root_for(a.db_root),a.key_file))
 if a.action=='prepare':
  if a.text_file.stat().st_mode&0o077:raise RuntimeError('Text file must have private permissions, e.g. 0600')
  result=j.prepare(a.op,a.chat_id,a.self_id,a.text_file.read_text())
 else:result=getattr(j,a.action)(a.op)
 print(json.dumps(result,ensure_ascii=False))
 return 0 if result['status']!='not_verified' else 2
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps({'status':'error','reason':str(e)}));raise SystemExit(2)
