# Read WeChat

A skill for Codex and Claude Code to read and summarize your local WeChat chats on macOS.

Ask things like:

- “What did the dinner group ask me to bring?”
- “Summarize my recent messages with Alex.”
- “Find the address someone shared in the group.”

## Install

Copy [`skills/wechat-history`](skills/wechat-history) into your agent's skills directory:

| Agent | Directory | Invoke explicitly |
| --- | --- | --- |
| Codex | `~/.codex/skills/` | `$wechat-history` |
| Claude Code | `~/.claude/skills/` | `/wechat-history` |

The agent can also select it automatically when you ask about WeChat. Back up any existing skill of the same name before replacing it.

## Local setup

You need WeChat 4.x on macOS, Python 3.9+, SQLCipher 4, and zstd. With Homebrew:

```sh
brew install sqlcipher zstd
```

WeChat encrypts its database. **You must already have your own valid database-key manifest**; installing this skill alone does not grant access. The skill does not extract keys. Give your agent its private file path using `--key-file`, or set `WECHAT_KEY_FILE`. Keep the file outside this repository with permissions `0600`. Never paste keys into a chat or public issue.

The manifest maps database-relative paths, such as `contact/contact.db`, or database salts, to their 64-character hexadecimal keys. A top-level `keys` mapping is also accepted. Library paths can be overridden with `SQLCIPHER_LIBRARY` and `ZSTD_LIBRARY`. Account paths are detected; use `--db-root` if multiple accounts exist.

## How it works

Two small Python scripts find conversations and read their local database directly. No screen recording, mouse control, message sending, or background service is involved.

This draft was tested with Codex on one Mac. Claude Code uses the same skill format but has not been tested end to end. Results cover locally available text; phone-only history, images, and voice content may be missing. A distribution license has not yet been selected.
