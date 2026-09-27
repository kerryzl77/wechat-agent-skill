#!/usr/bin/env python3
"""Read locally available WeChat 4.x message tables into a private JSONL snapshot."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sqlcipher_probe import DB, load_key


class Zstd:
    def __init__(self, path):
        self.lib = ctypes.CDLL(path)
        self.lib.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        self.lib.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
        self.lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
        self.lib.ZSTD_decompress.restype = ctypes.c_size_t
        self.lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
        self.lib.ZSTD_isError.restype = ctypes.c_uint

    def decompress(self, raw):
        source = ctypes.create_string_buffer(raw)
        size = self.lib.ZSTD_getFrameContentSize(source, len(raw))
        if size >= 2**64 - 2 or size > 16 * 1024 * 1024:
            raise ValueError('unknown or excessive zstd frame size')
        dest = ctypes.create_string_buffer(size)
        actual = self.lib.ZSTD_decompress(dest, size, source, len(raw))
        if self.lib.ZSTD_isError(actual):
            raise ValueError('zstd decompression failed')
        return dest.raw[:actual]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db-root', type=Path, required=True)
    p.add_argument('--key-file', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True)
    p.add_argument('--zstd-lib', required=True)
    args = p.parse_args()
    root = args.db_root.resolve(strict=True)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(out, 0o700)
    zstd = Zstd(args.zstd_lib)

    def open_db(relative):
        path = root / relative
        return DB(path, load_key(args.key_file, path))

    names = {}
    with open_db('contact/contact.db') as db:
        for row in db.query('SELECT username,nick_name,remark FROM contact'):
            names[row['username']] = row['remark'] or row['nick_name'] or row['username']

    output = out / 'messages.jsonl'
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    counts = {}
    unknown_tables = []
    min_time = max_time = None
    with os.fdopen(descriptor, 'w') as file:
        for database in ['message/message_0.db', 'message/biz_message_0.db']:
            with open_db(database) as db:
                id_rows = db.query('SELECT rowid,user_name,is_session FROM Name2Id')
                sender_ids = {int(x['rowid']): x['user_name'] for x in id_rows}
                table_names = {x['name'] for x in db.query("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")}
                chat_ids = {('Msg_' + hashlib.md5(x['user_name'].encode()).hexdigest()): x['user_name'] for x in id_rows}
                for table in sorted(table_names):
                    chat = chat_ids.get(table)
                    if not chat:
                        unknown_tables.append(database + ':' + table)
                    rows = db.query('SELECT local_id,server_id,local_type,create_time,real_sender_id,'
                                    'status,hex(message_content) AS body FROM "' + table + '" ORDER BY local_id')
                    counts[database + ':' + table] = len(rows)
                    for row in rows:
                        timestamp = int(row['create_time'])
                        min_time = timestamp if min_time is None else min(min_time, timestamp)
                        max_time = timestamp if max_time is None else max(max_time, timestamp)
                        sender = sender_ids.get(int(row['real_sender_id']))
                        raw = bytes.fromhex(row.pop('body') or '')
                        compressed = raw.startswith(b'\x28\xb5\x2f\xfd')
                        decode_error = None
                        try:
                            body = zstd.decompress(raw) if compressed else raw
                            text = body.decode('utf-8', 'strict')
                        except Exception as error:
                            text = None
                            decode_error = type(error).__name__
                        data = dict(row)
                        data.update(chat_id=chat, chat_name=names.get(chat), sender_id=sender,
                                    sender_name=names.get(sender), timestamp_utc=datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                                    content=text, content_compressed=compressed, content_bytes=len(raw), decode_error=decode_error,
                                    database=database, table=table)
                        file.write(json.dumps(data, ensure_ascii=False) + '\n')
    report = {'snapshot_utc': datetime.now(timezone.utc).isoformat(),
              'message_count': sum(counts.values()), 'chat_tables': len(counts),
              'unmapped_chat_tables': unknown_tables,
              'earliest_utc': datetime.fromtimestamp(min_time, timezone.utc).isoformat() if min_time else None,
              'latest_utc': datetime.fromtimestamp(max_time, timezone.utc).isoformat() if max_time else None,
              'content_decode_errors': sum(1 for line in output.open() if json.loads(line)['decode_error']),
              'output': str(output)}
    with (out / 'coverage.json').open('x') as file:
        json.dump(report, file, indent=2)
    os.chmod(out / 'coverage.json', 0o600)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
