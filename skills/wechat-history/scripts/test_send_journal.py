import sys,tempfile,unittest,copy,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from send_journal import Journal
class FakeReader:
 def __init__(self):
  self.root=Path('/fixture/account');self.rows=[];self.salts={'message_0.db':'salt'};self.cursor=5
 def resolve(self,value):return [{'username':value}]
 def snapshot(self,chat):return {'cursor':{'message_0.db':self.cursor},'salts':dict(self.salts)}
 def read(self,chat,limit=20,after=None,self_id=None):return [copy.deepcopy(x) for x in self.rows if after is None or int(x['local_id'])>after['message_0.db']]
 def add(self,text='Hi',sender=True,server='9',local='6'):
  self.cursor=max(self.cursor,int(local));self.rows.append({'database':'message_0.db','local_id':local,'server_id':server,'create_time':'1000','local_type':'1','from_self':sender,'text':text})
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=FakeReader();self.j=Journal(self.r,Path(self.tmp.name)/'private');self.j.prepare('op','chat','self','Hi')
 def tearDown(self):self.tmp.cleanup()
 def test_unarmed_phone_message_cannot_succeed(self):
  self.r.add()
  with self.assertRaises(RuntimeError):self.j.verify('op')
 def test_rearm_and_reprepare_are_refused(self):
  self.j.arm('op')
  with self.assertRaises(RuntimeError):self.j.arm('op')
  with self.assertRaises(RuntimeError):self.j.prepare('op','chat','self','Hi')
 def test_new_exact_outgoing_and_idempotent_verification(self):
  self.r.add(local='6');self.j.arm('op') # pre-arm message does not count
  self.r.add(local='7')
  result=self.j.verify('op');self.assertEqual(result['status'],'sent_db_verified');self.assertEqual(result['receipt']['local_id'],'7');self.assertEqual(self.j.verify('op'),result)
 def test_whitespace_incoming_and_unacknowledged_do_not_count(self):
  self.j.arm('op');self.r.add(text='Hi ');self.r.add(sender=False,local='7');self.assertEqual(self.j.verify('op')['status'],'not_verified')
  self.r.add(server='0',local='8');self.assertEqual(self.j.verify('op')['status'],'not_verified')
 def test_two_matches_are_ambiguous(self):
  self.j.arm('op');self.r.add();self.r.add(local='7');self.assertEqual(self.j.verify('op')['exact_matches'],2);self.assertFalse(self.j.verify('op')['retry_allowed'])
 def test_database_change_before_arm_refused(self):
  self.r.salts={"message_0.db":"new"}
  with self.assertRaises(RuntimeError):self.j.arm("op")
 def test_account_or_database_change_refused(self):
  self.j.arm('op');self.r.salts={'message_0.db':'new'}
  with self.assertRaises(RuntimeError):self.j.verify('op')
  self.r.root=Path('/different/account')
  with self.assertRaises(RuntimeError):self.j.status('op')
 def test_private_journal_and_non_disclosing_status(self):
  self.assertEqual((self.j.root/'op.json').stat().st_mode&0o777,0o600);self.assertEqual(self.j.root.stat().st_mode&0o777,0o700);self.assertNotIn('text',self.j.status('op'))
 def test_unsupported_text_and_unsafe_operation_ids_refused(self):
  for text in ['','Hi\n','Hi\r','😀'*251]:
   with self.assertRaises(ValueError):self.j.prepare('other','chat','self',text)
  with self.assertRaises(ValueError):self.j.prepare('../escape','chat','self','Hi')
if __name__=='__main__':unittest.main()
