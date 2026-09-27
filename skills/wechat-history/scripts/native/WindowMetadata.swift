import Cocoa
let target=NSRunningApplication.runningApplications(withBundleIdentifier:"com.tencent.xinWeChat").filter{$0.bundleURL?.path == "/Applications/WeChat.app"}
let pids=Set(target.map{$0.processIdentifier})
let windows=(CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] ?? []).filter{pids.contains(($0[kCGWindowOwnerPID as String] as? Int32) ?? -1) && ($0[kCGWindowLayer as String] as? Int)==0}.map{w -> [String:Any] in
 ["pid":w[kCGWindowOwnerPID as String] ?? NSNull(),"windowID":w[kCGWindowNumber as String] ?? NSNull(),"bounds":w[kCGWindowBounds as String] ?? NSNull(),"title":w[kCGWindowName as String] ?? NSNull()]
}
let screens=NSScreen.screens.map{s -> [String:Any] in
 let id=(s.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value ?? 0
 let b=CGDisplayBounds(id)
 return ["displayID":id,"name":s.localizedName,"scale":s.backingScaleFactor,"logicalBounds":["x":b.origin.x,"y":b.origin.y,"width":b.width,"height":b.height],"pixelWidth":CGDisplayCopyDisplayMode(id)?.pixelWidth ?? 0,"pixelHeight":CGDisplayCopyDisplayMode(id)?.pixelHeight ?? 0]
}
let value:[String:Any]=["frontmostPID":NSWorkspace.shared.frontmostApplication?.processIdentifier ?? -1,"wechatPIDs":Array(pids),"displays":screens,"windows":windows]
let data=try JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]);print(String(data:data,encoding:.utf8)!)
