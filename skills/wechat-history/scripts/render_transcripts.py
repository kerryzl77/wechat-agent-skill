#!/usr/bin/env python3
"""Render a private, complete, readable copy of a WeChat JSONL snapshot."""
import argparse
import json
import os
from pathlib import Path


def write_private(path, records):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        for row in records:
            chat = row['chat_name'] or row['chat_id'] or 'Unknown chat'
            sender = row['sender_name'] or row['sender_id'] or 'Unknown sender'
            out.write(f"[{row['timestamp_utc']}] {chat} | {sender} | type {row['local_type']} | local_id {row['local_id']}\n")
            out.write((row['content'] if row['content'] is not None else '[content could not be decoded]') + '\n\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('snapshot_dir', type=Path)
    p.add_argument('--group-id', required=True)
    a = p.parse_args()
    records = [json.loads(line) for line in (a.snapshot_dir / 'messages.jsonl').open(encoding='utf-8')]
    records.sort(key=lambda row: (row['create_time'], row['database'], row['table'], row['local_id']))
    write_private(a.snapshot_dir / 'all-conversations.txt', records)
    group = [row for row in records if row['chat_id'] == a.group_id]
    write_private(a.snapshot_dir / 'requested-group.txt', group)
    print(json.dumps({'all_records': len(records), 'group_records': len(group)}))


if __name__ == '__main__':
    main()
