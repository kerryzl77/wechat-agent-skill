import Cocoa
import CoreGraphics
// Local, one-action native input for the user's WeChat task. No network, capture,
// database access, background loop, or AX element APIs. No permission prompts
// unless launched with --request-permission. Every input requires a request file
// with an exact expected WeChat PID, visible window ID, and action.
let root=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/CodexWeChatReader/native-input")
try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
var nonce="probe"
func finish(_ status:String,_ detail:String)->Never {
 let record:[String:Any]=["time":ISO8601DateFormatter().string(from:Date()),"nonce":nonce,"status":status,"detail":detail]
 if let bytes=try? JSONSerialization.data(withJSONObject:record,options:[.sortedKeys]) {try? bytes.write(to:root.appendingPathComponent("result.json"),options:.atomic)}
 exit(status=="ok" ? 0:1)
}
let args=CommandLine.arguments
if args.contains("--request-permission"){finish("permission",String(CGRequestPostEventAccess()))}
guard args.count==3,args[1]=="--request" else{finish("probe","canPostEvents=\(CGPreflightPostEventAccess())")}
guard let data=try? Data(contentsOf:URL(fileURLWithPath:args[2])),let req=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else{finish("refused","Invalid request file")}
nonce=req["nonce"] as? String ?? "missing"
guard CGPreflightPostEventAccess() else{finish("refused","No existing native input permission")}
guard let pid=req["pid"] as? Int32,let windowID=req["windowID"] as? UInt32,let action=req["action"] as? String,let app=NSRunningApplication(processIdentifier:pid),app.bundleIdentifier=="com.tencent.xinWeChat" else{finish("refused","Expected WeChat identity missing")}
if NSWorkspace.shared.frontmostApplication?.processIdentifier != pid {app.activate(options:[]);usleep(500000)}
guard NSWorkspace.shared.frontmostApplication?.processIdentifier==pid else{finish("refused","WeChat is not foreground")}
func visibleWindows()->[[String:Any]] {(CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] ?? []).filter{($0[kCGWindowOwnerPID as String] as? Int32)==pid && ($0[kCGWindowLayer as String] as? Int)==0}}
func bounds(_ w:[String:Any])->CGRect? {guard let b=w[kCGWindowBounds as String] as? [String:Any] else{return nil};return CGRect(dictionaryRepresentation:b as CFDictionary)}
let wins=visibleWindows().filter{guard let r=bounds($0) else{return false};return r.width>100 && r.height>100}
guard let top=wins.first,(top[kCGWindowNumber as String] as? UInt32)==windowID,let r=bounds(top) else{finish("refused","Expected window is not the top visible WeChat window")}
let source=CGEventSource(stateID:.hidSystemState)
if action=="click" || action=="scroll" {
 guard let x=req["x"] as? Double,let y=req["y"] as? Double,x>=0,y>=0,x<r.width,y<r.height else{finish("refused","Coordinates outside verified window")}
 let point=CGPoint(x:r.minX+x,y:r.minY+y)
 let old=CGEvent(source:nil)?.location
 CGEvent(mouseEventSource:source,mouseType:.mouseMoved,mouseCursorPosition:point,mouseButton:.left)?.post(tap:.cghidEventTap)
 usleep(120000)
 if action=="click" {
  CGEvent(mouseEventSource:source,mouseType:.leftMouseDown,mouseCursorPosition:point,mouseButton:.left)?.post(tap:.cghidEventTap)
  usleep(80000)
  CGEvent(mouseEventSource:source,mouseType:.leftMouseUp,mouseCursorPosition:point,mouseButton:.left)?.post(tap:.cghidEventTap)
 } else {
  guard let delta=req["delta"] as? Int32,abs(Int(delta))<=600 else{finish("refused","Invalid scroll delta")}
  let event=CGEvent(scrollWheelEvent2Source:source,units:.pixel,wheelCount:1,wheel1:delta,wheel2:0,wheel3:0)
  event?.location=point;event?.post(tap:.cghidEventTap)
 }
 usleep(250000)
 if let old {CGEvent(mouseEventSource:source,mouseType:.mouseMoved,mouseCursorPosition:old,mouseButton:.left)?.post(tap:.cghidEventTap)}
 finish("ok","Posted one native \(action); visual verification required")
}
if action=="type" {
 guard let text=req["text"] as? String,text.utf16.count<=500,!text.contains("\n"),!text.contains("\r") else{finish("refused","Text must be short and contain no submit keys")}
 let chars=Array(text.utf16)
 for down in [true,false] {
  let event=CGEvent(keyboardEventSource:source,virtualKey:0,keyDown:down)
  chars.withUnsafeBufferPointer {event?.keyboardSetUnicodeString(stringLength:chars.count,unicodeString:$0.baseAddress)}
  event?.post(tap:.cghidEventTap)
 }
 finish("ok","Posted text only; no Return key; verify composer before submitting")
}
if action=="key" {
 let keys:[String:CGKeyCode]=["Return":36,"Escape":53,"Tab":48,"Backspace":51]
 guard let name=req["key"] as? String,let code=keys[name] else{finish("refused","Unsupported key")}
 CGEvent(keyboardEventSource:source,virtualKey:code,keyDown:true)?.post(tap:.cghidEventTap)
 CGEvent(keyboardEventSource:source,virtualKey:code,keyDown:false)?.post(tap:.cghidEventTap)
 finish("ok","Posted \(name); verify resulting UI")
}
finish("refused","Unsupported action")
