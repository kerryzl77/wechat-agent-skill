#!/usr/bin/env python3
"""Read-only WeChat 4.x CLI. No sending, key extraction, or remote service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from sqlcipher_db import DB, load_key, Zstd, zstd_library


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def literal(text):
    return "CAST(x'" + text.encode().hex() + "' AS TEXT)"


def root_for(value=None):
    if value:
        return Path(value).resolve(strict=True)
    roots = list((Path.home()/'Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files').glob('*/db_storage'))
    if len(roots) != 1:
        raise RuntimeError('select_account_with_--db-root')
    return roots[0].resolve()


class Reader:
    def __init__(self, root, key_file):
        self.root, self.keys = Path(root), Path(key_file)

    def open(self, path):
        return DB(path, load_key(self.keys, path))

    def resolve(self, name):
        with self.open(self.root/'contact/contact.db') as db:
            rows = db.query('SELECT username,nick_name,remark FROM contact WHERE '
                            f'username={literal(name)} OR nick_name={literal(name)} OR remark={literal(name)}')
        # Never select the first of multiple same-name contacts.
        return rows

    def paths(self, chat):
        table = 'Msg_' + hashlib.md5(chat.encode()).hexdigest()
        found = []
        paths = sorted((self.root/'message').glob('message_*.db'))
        if not paths:
            raise RuntimeError('message_databases_missing')
        for path in paths:
            with self.open(path) as db:
                if db.query(f"SELECT 1 FROM sqlite_master WHERE name='{table}' AND type='table'"):
                    found.append((path, table))
        if not found:
            raise RuntimeError('conversation_has_no_local_message_table')
        return found

    def read(self, chat, limit=100):
        result = []
        for path, table in self.paths(chat):
            with self.open(path) as db:
                rows = db.query('SELECT local_id,server_id,local_type,create_time,real_sender_id,'
                                'hex(message_content) AS body FROM "'+table+'" '+
                                f' ORDER BY create_time DESC, local_id DESC LIMIT {int(limit)}')
                for row in rows:
                    sender = db.query('SELECT user_name FROM Name2Id WHERE rowid='+str(int(row['real_sender_id'])))
                    sender_id = sender[0]['user_name'] if len(sender) == 1 else None
                    raw = bytes.fromhex(row.pop('body'))
                    row.update(database=path.name, sender_id=sender_id)
                    row['text'] = None
                    if int(row['local_type']) == 1:
                        if raw.startswith(b'\x28\xb5\x2f\xfd'):
                            raw = Zstd(zstd_library()).decompress(raw)
                        body = raw.decode('utf8', 'strict')
                        # Group received text includes sender prefix; preserve text following it.
                        if chat.endswith('@chatroom') and sender_id and body.startswith(sender_id+':\n'):
                            body = body[len(sender_id)+2:]
                        row['text'] = body
                    else:
                        row['omitted'] = 'non_text_message; XML/media credentials are not exported'
                    result.append(row)
        result.sort(key=lambda r:(int(r['create_time']), r['database'], int(r['local_id'])))
        return result[-limit:]


def main():
    ap = argparse.ArgumentParser(description="Read local WeChat chats; never sends or changes WeChat.")
    ap.add_argument('--db-root', type=Path, help='Account db_storage directory; auto-detected if exactly one exists')
    ap.add_argument('--key-file', type=Path, default=os.environ.get('WECHAT_KEY_FILE'),
                    required=not bool(os.environ.get('WECHAT_KEY_FILE')),
                    help='Private key manifest, or set WECHAT_KEY_FILE')
    sub = ap.add_subparsers(dest='command', required=True)
    find = sub.add_parser('find', help='Find a contact or group by name')
    find.add_argument('name')
    read = sub.add_parser('read', help='Read the latest locally stored messages')
    read.add_argument('--chat-id', required=True)
    read.add_argument('--limit', type=int, default=100)
    args = ap.parse_args()
    reader = Reader(root_for(args.db_root), args.key_file)
    if args.command == 'find':
        matches = reader.resolve(args.name)
        if not matches:
            q = literal(args.name)
            with reader.open(reader.root/'contact/contact.db') as db:
                matches = db.query('SELECT username,nick_name,remark FROM contact WHERE '
                    f'instr(lower(nick_name),lower({q}))>0 OR instr(lower(remark),lower({q}))>0 LIMIT 51')
        emit({'matches':matches[:50], 'truncated':len(matches)>50})
    else:
        if not 1 <= args.limit <= 1000:
            ap.error('--limit must be 1..1000')
        rows = reader.read(args.chat_id,args.limit)
        ids = {r['sender_id'] for r in rows if r['sender_id']}
        names = {}
        if ids:
            with reader.open(reader.root/'contact/contact.db') as db:
                contacts = db.query('SELECT username,nick_name,remark FROM contact WHERE username IN (' +
                                    ','.join(literal(x) for x in ids)+')')
            names = {c['username']:c['remark'] or c['nick_name'] for c in contacts}
        for row in rows:
            row['sender_name'] = names.get(row['sender_id'], row['sender_id'])
            row['create_time'] = int(row['create_time'])
        emit({'chat_id':args.chat_id, 'coverage':'latest locally stored messages only', 'messages':rows})
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except Exception as error:
        emit({'error':str(error)})
        sys.exit(2)
