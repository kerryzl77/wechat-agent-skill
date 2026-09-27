# WeChat for local agents

A skill for local agents to **read chats, see and operate WeChat, and send messages on macOS**. It gives Codex, Claude Code, or another capable harness the working approach and setup requirements in plain language.

Ask things like:

- “What is group chat xxx talking about?”
- “Send a private DM to yyy: hi.”

## Install

Copy [`skills/wechat-history`](skills/wechat-history) into your agent's skills directory:

| Agent | Directory | Invoke explicitly |
| --- | --- | --- |
| Codex | `~/.codex/skills/` | `$wechat-history` |
| Claude Code | `~/.claude/skills/` | `/wechat-history` |

The agent can also select it automatically when you ask about WeChat. For another harness, load `SKILL.md` and make its scripts available. Back up any existing skill of the same name before replacing it.

## Local setup

Start with WeChat installed and signed in on macOS, and a harness that can run local tools and inspect images. Seeing and controlling the app requires Screen Recording and Accessibility / Device Control permissions for the tools doing those jobs. Your agent should explain the needed settings and guide you through granting access; installing the skill alone does not configure your Mac.

For local history and database verification, the reader needs WeChat 4.x, Python 3.9+, SQLCipher 4, and zstd. With Homebrew:

```sh
brew install sqlcipher zstd
```

WeChat encrypts its database. **You must already have your own valid database-key manifest**; installing this skill alone does not grant access. The skill does not extract keys. Give your agent its private file path using `--key-file`, or set `WECHAT_KEY_FILE`. Keep the file outside this repository with permissions `0600`. Never paste keys into a chat or public issue.

The manifest maps database-relative paths, such as `contact/contact.db`, or database salts, to their 64-character hexadecimal keys. A top-level `keys` mapping is also accepted. Library paths can be overridden with `SQLCIPHER_LIBRARY` and `ZSTD_LIBRARY`. Account paths are detected; use `--db-root` if multiple accounts exist.

## The approach

Read history with the two bundled Python scripts. See the chat through AVFoundation display capture, then click and type with native macOS events rather than WeChat accessibility elements. Verify a send with a fresh image and a matching new outgoing database record.

The concise [skill instructions](skills/wechat-history/SKILL.md) explain the permissions, capture/input methods, and send verification. Capture and input tools are supplied or prepared by the harness; this is not a bundled desktop-control application.

The combined approach worked with Codex on one configured Mac. The earlier public reader also passed a fresh GPT-6 Sol agent test. The revised public instructions still need a full independent send test; fresh-machine setup and Claude Code have not been verified. Phone-only history and media may be missing, and media sending is untested. A distribution license has not yet been selected.
