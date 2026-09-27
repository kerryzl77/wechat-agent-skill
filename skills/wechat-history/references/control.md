# Live view and native control on macOS

## Working route and installed helpers

- Capture app: `~/Library/Application Support/CodexWeChatReader/alternate-screen-helper/Alternate Screen Recorder.app`
- Input app: `~/Library/Application Support/CodexWeChatReader/native-input/WeChat Native Input.app`
- Sources: `scripts/native/AlternateScreenRecorder.swift`, `scripts/native/WeChatNativeInput.swift`.
- `python3 scripts/build_helpers.py --check` checks their binaries against the local build manifest. Do not rebuild a working signed helper routinely: changing its binary can invalidate its macOS permission even if the switch still appears on.
- `python3 scripts/build_helpers.py --build` builds missing apps from these sources. Existing changed apps require the explicit `--replace` flag; finish building and signing BEFORE granting permissions. No build command launches an app or changes OS settings.

The recorder uses AVFoundation `AVCaptureScreenInput`, not ScreenCaptureKit. It captures the selected entire display, writes an MP4 and updates a local `latest.png` about once per second, with no microphone, camera or network. Each run ends after 120 seconds, with a 140-second watchdog; a STOP file requests an earlier clean exit. Continue with a new bounded run if necessary rather than treating a stale PNG as live.

The input helper uses native CGEvent mouse and keyboard events, not WeChat AX element actions. It handles exactly one request per launch, checks the expected WeChat PID, foreground app and top visible WeChat window ID, and uses window-relative logical coordinates. It has no capture, network or database code.

## Tool and permission routing

For normal System Settings interaction use the available computer-use tool and its skill. For authorized WeChat capture and input, launch those helpers through `node_repl` with `child_process.execFile('/usr/bin/open', ...)` or the currently available authorized native execution route. Use structured argument arrays, never interpolate chat content into shell commands.

- Recorder default launch is a read-only permission probe; result: `alternate-screen/probe.json`.
- Recorder `--request-permission` explicitly requests Screen Recording. Permission page: `x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture`.
- Recorder `--capture --display ID` requires the actual grant. System Settings should show **Alternate Screen Recorder** ON in Screen & System Audio Recording. The app records no audio despite the OS permission category's name.
- Input default launch probes `CGPreflightPostEventAccess`; result: `native-input/result.json`.
- Input `--request-permission` requests native event-posting access. System Settings may label this **Device Control and Data Access** or **Accessibility**. Page: `x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility`.
- If the input app does not appear after requesting, add the exact prepared `.app` using System Settings's Add button. Re-probe afterward. Do not enable unrelated applications.

Authorization does not supply a password or Touch ID. A protected UserNotificationCenter alert was blocked by the Computer Use tool; the helper could still capture, and unobscured WeChat controls were operable. Do not click the blocked alert through a different API. Continue only independent authorized work that is actually observable and permitted; ask the user to handle protected UI if it is necessary.

At cleanup, stop the specific recorder run. Restore newly enabled permissions from failed experiments through System Settings and verify OFF. Preserve only useful grants that the user authorized retaining; don't reset other apps' permissions or kill unrelated recording processes.

## Live frames and coordinates

`python3 scripts/live_view.py start --display 1` launches the recorder; choose the actual display ID from current screen metadata, not from this old example. `frame` prints the latest PNG path and its age and refuses stale frames over three seconds. `stop` signals only the current run. Through node_repl, the equivalent launch is:

```js
await new Promise((resolve, reject) => cp.execFile('/usr/bin/open',
  ['-n', recorderApp, '--args', '--capture', '--display', String(displayID)],
  e => e ? reject(e) : resolve()));
```

Read the PNG with an image-view tool. Validate WeChat chat content, not just frame counts. Run `python3 scripts/window_metadata.py` for current display bounds, backing scale, WeChat PID and on-screen window bounds using read-only AppKit/CoreGraphics metadata. Full-screen image pixels, resized tool-preview pixels and native logical screen points are different coordinate systems. Use the actual captured image dimensions as the capture scale authority; a recorder may scale its output differently from the display mode. Convert to logical points and subtract the current WeChat window origin; never reuse old x/y, PID or window ID blindly.

The helper's foreground/window checks do not detect every overlay from another app. Visually verify the target is unobscured and correct before every consequential action. After clicking or typing, inspect a NEW frame before the next decision. If a stream expires, restart and verify again before sending.

## Native requests

Write a 0600 JSON request under the private `native-input/` directory. Every action needs a unique nonce, current WeChat PID and current expected top window ID:

```json
{"nonce":"task-step-unique","pid":12345,"windowID":456,"action":"click","x":150,"y":80}
```

Supported actions:

- `click`: relative `x`, `y` inside the window.
- `scroll`: relative `x`, `y`, signed pixel `delta` with absolute value <=600.
- `type`: exact `text`, up to 500 UTF-16 units, no newline or carriage return. It does NOT submit.
- `key`: `Return`, `Escape`, `Tab`, or `Backspace`. Return is consequential in a chat composer.

Launch the input app with `--request /absolute/private/request.json`, then read `native-input/result.json`. Match its nonce to the request; an old success file is not evidence the new action ran. `status:ok` means an event was posted, so still verify visually. For longer or multiline messages, do not improvise Return-key insertion; extend/test the helper separately or report the constraint.

## Avoid the failed default paths

On this setup, the SDK's WeChat x/y click path still performed AX lookup and failed with `AXError.notImplemented`. Its capture and the tested ScreenCaptureKit picker streams omitted the chat window. QuickTime's prior recording attempt was inconclusive. OBS's modern Mac source also uses ScreenCaptureKit, so simply naming another UI application does not establish a new backend.

AVFoundation with explicit Screen Recording access succeeded. This does not prove whether backend, authorization mode or their interaction explains the earlier omission. “Keep current window when clicking the screenshot button” was unrelated; do not confuse it with “Hide Weixin main window during demonstration,” whose active state was never verified. Do not change WeChat privacy preferences on that assumption.
