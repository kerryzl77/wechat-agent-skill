# Send text once, then verify

Read `control.md` for helper launches, fresh frames, native request schema and permission handling. An existing UI session is not proof of the recipient or delivery.

## Prepare

1. Confirm the current task authorizes sending, and resolve the exact intended recipient and text. For a draft-only task, stop at the draft. Resolve ambiguous personal/group names against local contacts; never guess from the first search result.
2. Identify account DB root and self sender ID. Use `wechat_db.py resolve/read` to inspect only relevant recent context. For a brand-new chat without a local message table, this verifier cannot establish its baseline; don't claim the existing-conversation workflow covers it.
3. Obtain a fresh AVFoundation image that shows the actual chat. Use native clicks to select the resolved contact; verify the visible selected conversation identity, matching context and composer. A blocked/obscured header alone isn't enough to assume a recipient. If necessary, obtain another unobscured identity cue or user clarification.
4. Record one stable operation ID for this user request. Reuse that operation ID after interruptions. Do not mint another ID simply because send success is uncertain. Store the authorized text in a 0600 private UTF-8 file, with exact whitespace and no accidental trailing newline.

## Send journal

`scripts/send_journal.py` is read-only with respect to WeChat databases; it only writes private operation journals. It never posts input or sends by itself. Supply the same account on every invocation:

```sh
python3 "$SKILL/scripts/send_journal.py" --db-root "$DB_ROOT" prepare \
  --op "$OP_ID" --chat-id "$CHAT_ID" --self-id "$SELF_ID" --text-file "$PRIVATE_TEXT_FILE"
```

Prepare refuses an existing operation. `status --op ID` shows the saved state without exposing message text. Use an operation ID tied to the user task and write it in the task progress so a resumed agent can find it. Concurrent workflows targeting the same conversation require coordination; don't operate WeChat's single foreground composer concurrently.

## Compose and submit

- Click the visible empty composer. If it already has a draft, preserve it and resolve the conflict rather than clearing/replacing it silently.
- Insert the approved text using the native `type` action. Inspect a fresh image for the exact text, intended conversation and enabled Send button. Do not include Return/newline in text injection.
- Immediately before the one submit action, run `arm --op ID`. This takes a fresh DB baseline and persists `attempted` before any Send event. If it refuses, do not send.
- Click the visible Send button or post Return once to the verified focused composer. Check the native result nonce. Inspect a fresh post-send image; restart an expired capture first. Never click Send again solely because an image or DB update is delayed.

## Verify and report

Run `verify --op ID`. It requires an armed operation, checks DB identity/cursors, and seeks exactly one new outgoing type-1 message with exact text (including whitespace) and a nonzero server ID. It stores a minimal receipt. Re-running verification is safe and does not send.

If no matching row is visible yet, allow a bounded synchronization wait and re-read (for example, every two seconds up to 30 seconds). If there are multiple matches, a DB identity change, an unknown sender, or no conclusive result, preserve the attempted journal and report uncertainty. Do not auto-resend. User authorization for a new attempt must account for the risk that the original was delivered.

A new row can theoretically be synced from another device. Attribute success using the coordinated native action receipt, observed composer/bubble transition, timestamp and DB baseline together. Do not credit an incoming/phone-synced message when no agent attempt occurred. A server ID supports outgoing-send verification, not proof that a recipient read it or that the user's phone has displayed it.

Report the recipient, exact sent text and verification result concisely. Stop the capture and clean up failed-test grants. This skill update itself never authorizes a demonstration send.

The journal state machine has offline regression tests: `python3 scripts/test_send_journal.py`. They use simulated records and never send or open live databases.
