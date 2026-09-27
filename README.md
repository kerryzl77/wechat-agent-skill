# WeChat — Read & Send

A macOS agent skill for reading local WeChat conversations and sending explicitly requested text messages with visual and database verification. The workflow was tested with Codex; the standard skill format is also intended for Claude Code, whose end-to-end behavior remains untested.

**First public draft.** The reading and sending approach was demonstrated on one Mac; setup on another machine has not been validated. This is an independent project, not an official Tencent integration.

## What it does

- Read, search, and summarize locally available personal and group chats.
- Draft replies without sending them.
- Send authorized single-line texts in existing conversations using AVFoundation display capture and native CGEvent input.
- Journal each send attempt and verify a new outgoing database record plus the visible result; uncertain attempts are not automatically repeated.
- Stop recording after the task and restore permissions introduced for unsuccessful experiments.

## The working loop

Read the local database for history. For a send, inspect a fresh AVFoundation display frame, operate the verified conversation with native CGEvent mouse/keyboard events, then reconcile the visible result with a new outgoing database record. Avoid repeating an accessibility lookup path when WeChat has already rejected it.

AVFoundation is also an Apple framework: the distinction is the capture backend and permission route, not Apple versus non-Apple recording. Native CGEvent input is macOS input, not browser automation. Permission to post events may still appear under Accessibility in System Settings.

## Requirements

- macOS, a logged-in WeChat desktop account, Python 3.9 or later, and Xcode Command Line Tools to compile the Swift helpers.
- SQLCipher 4 and zstd installed separately. With an existing Homebrew installation: `brew install sqlcipher zstd`.
- **Your own valid, authorized database-key manifest.** WeChat databases are encrypted. This project does not include keys, extract keys, decrypt arbitrary accounts, or make a fresh installation ready to read by itself. Both database reading and the tested send-verification workflow require this prerequisite.
- Screen Recording access for the recorder and native input access for the input helper, granted through macOS. Authentication or protected dialogs may require the human user.

## Install the skill

Copy `skills/wechat-history` into `~/.codex/skills/` for your local Codex user. Inspect and back up an existing skill of the same name before replacing it. It can be selected automatically for WeChat tasks or invoked as `$wechat-history`.

For Claude Code, copy that same folder into `~/.claude/skills/` and invoke `/wechat-history`, or let Claude select it for a relevant request. See [Claude Code's skill documentation](https://code.claude.com/docs/en/skills). The scripts do not require a Codex SDK; the agent needs local shell access and a way to inspect image files. On either agent, respect its tool permissions and do not use the native helper to evade an explicit safety block.

Provide your private manifest outside the repository at `~/Library/Application Support/CodexWeChatReader/keys.json`, with permissions 0600 and its parent directory 0700. Alternatively pass `--key-file /absolute/private/path/keys.json` to the database reader and send journal. Never paste key values into chat or commit the manifest.

The manifest is a JSON mapping from a database-relative path (such as `contact/contact.db`) or database salt to its 64-hex-character SQLCipher key. A top-level `keys` mapping is also accepted. Each database must resolve to exactly one key. No sample secret is distributed.

SQLCipher is discovered from standard Homebrew paths or `SQLCIPHER_LIBRARY`; zstd from Homebrew paths or `ZSTD_LIBRARY`. For history export, pass the zstd library path using `--zstd-lib`.

For capture and input, build the helpers locally:

```sh
python3 /absolute/path/to/installed/wechat-history/scripts/build_helpers.py --build
```

This only builds and signs the apps. It does not grant permissions, launch capture, or send messages. Follow `references/control.md` for permission probes and operation. Finish building before granting access: rebuilding can invalidate an existing grant. If an existing helper differs, inspect it before explicitly using `--replace`.

## Examples

- “Summarize today's messages in my dinner group.”
- “Find the address Alex sent me yesterday.”
- “Draft a reply to Alex, but don't send it.”
- “Send ‘I'm on my way’ to Alex.”

## Boundaries

The tested send path supports existing conversations and text up to 500 UTF-16 code units without newlines. Sending images, files, or voice, recalls, contact management, and first-message creation need separate implementation and validation. Local history may omit messages or media available on the phone.

The recorder captures the entire selected display, including unrelated visible content. Frames and movies are stored locally in private application-support directories and are not automatically deleted. It records no audio and has a bounded runtime. The input helper has no network or database code. The agent environment that inspects a frame determines any subsequent data handling; this project does not guarantee on-device model inference.

AVFoundation capture with explicit permission worked on WeChat 4.1.13 / macOS 27.0 in the original test. Earlier ScreenCaptureKit and accessibility interaction paths failed in that setup. This is evidence for an alternate route, not a guarantee across WeChat/macOS versions or proof of the precise omission mechanism.

## Validation

```sh
python3 skills/wechat-history/scripts/test_send_journal.py
```

These tests use synthetic data and never send messages. No private messages, account identifiers, key files, captures, receipt data, compiled helper apps, or third-party libraries are included in this draft. A distribution license has not yet been selected.

## Related work

Related WeChat agent skills and local integrations:

- [huangdijia/wechat-skills](https://github.com/huangdijia/wechat-skills): a macOS WeChat skill documented for Claude Code and Codex.
- [tonyshield/send-wechat-message](https://github.com/tonyshield/send-wechat-message): a Codex skill using Accessibility automation.
- [francismiko/wechat-automation](https://github.com/francismiko/wechat-automation): a Claude Code macOS automation skill.
- [wechat-mcp-macos](https://pypi.org/project/wechat-mcp-macos/0.1.0/): local database reading and AppleScript-based sending via MCP.

Our demonstrated design combines AVFoundation live display frames, native CGEvent input, and database-backed send verification. A controlled comparison with these other projects has not been performed.
