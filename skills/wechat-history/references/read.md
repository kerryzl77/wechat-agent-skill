# Read and search locally stored chats

Use the bundled scripts without starting a capture or opening WeChat. The libraries and original export/render tools remain installed.

## Resolve an account and conversation

List the database-root directory names, not credentials. Use one explicitly selected root. `scripts/wechat_db.py` reads live databases read-only, including committed WAL records, and supports exact contact nickname, remark or ID resolution:

```sh
python3 "$SKILL/scripts/wechat_db.py" --db-root "$DB_ROOT" resolve "$RECIPIENT"
python3 "$SKILL/scripts/wechat_db.py" --db-root "$DB_ROOT" read --chat-id "$CHAT_ID" --self-id "$SELF_ID" --limit 50
```

Here `SKILL` is this skill's absolute directory; set task-specific shell variables appropriately. Do not print keys. `wechat_db.py` discovers a separately installed SQLCipher library and uses the private manifest by default; use `--key-file` only when an appropriate existing alternative has been identified.

Exact name resolution may return several contacts. Use context and chat IDs to disambiguate; never silently choose the first. Resolve the intended account and recipient anew for each task.

## Comprehensive search, date ranges and summaries

For multi-chat searches, date ranges or account coverage, create a NEW private snapshot:

```sh
python3 "$SKILL/scripts/export_history.py" \
  --db-root "$DB_ROOT" --key-file "$KEY_FILE" --out-dir "$NEW_PRIVATE_DIR" \
  --zstd-lib "$ZSTD_LIBRARY"
```

The output directory must be new for the task. Inspect `coverage.json` for available time range, message counts, unmapped tables and decode errors before saying the search is complete. Use `messages.jsonl` to filter by exact chat ID, date and keywords; run `scripts/render_transcripts.py --help` for its supported rendering options. Keep plaintext output private and bound tool output to the requested conversation and relevant records.

Resolve the user's intended timezone for local date ranges. Distinguish sender, incoming/outgoing direction, timestamps, quoted content and actual text. Nontext/XML metadata may describe media without containing its cached payload. Report gaps; do not imply all phone or server history exists on this Mac.

For “new since last check,” `wechat_db.py init/check/ack` provides per-database cursors. `check` does not acknowledge automatically. Acknowledge only a reviewed batch; do not skip unprocessed messages. Use bounded `watch` only for an expressly requested monitor, and do not turn it into automatic replies.

If keys fail, sender identity is unknown, database salts change, or cursors regress, stop that interpretation and explain the condition. Do not silently reset cursors, obtain new keys, modify databases, or relaunch/login as part of a read request.
