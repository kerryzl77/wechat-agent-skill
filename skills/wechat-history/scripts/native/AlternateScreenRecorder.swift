import Cocoa
import AVFoundation
import CoreImage
import ImageIO
import UniformTypeIdentifiers

// Local read-only AVFoundation display capture. No ScreenCaptureKit, AX, input,
// microphone, camera, network, login item, or hidden permission requests.
let root=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/CodexWeChatReader/alternate-screen")
try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
let args=CommandLine.arguments
func writeJSON(_ value:[String:Any],_ path:URL) {
 if let data=try? JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]) {try? data.write(to:path,options:.atomic)}
}
if args.contains("--self-check") {print("AVCaptureScreenInput; full display; 120 second limit; local PNG and MP4; no audio/network/input. Permission request requires --request-permission.");exit(0)}
let app=NSApplication.shared;app.setActivationPolicy(.accessory)
if args.contains("--request-permission") {
 let allowed=CGRequestScreenCaptureAccess()
 writeJSON(["at":ISO8601DateFormatter().string(from:Date()),"permission_result":allowed],root.appendingPathComponent("permission.json"));exit(0)
}
if !args.contains("--capture") {
 writeJSON(["at":ISO8601DateFormatter().string(from:Date()),"screen_permission":CGPreflightScreenCaptureAccess()],root.appendingPathComponent("probe.json"));exit(0)
}
guard CGPreflightScreenCaptureAccess() else {
 writeJSON(["error":"Screen Recording permission is required for this AVFoundation route; nothing captured."],root.appendingPathComponent("capture-error.json"));exit(2)
}
let output=root.appendingPathComponent(UUID().uuidString)
try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true,attributes:[.posixPermissions:0o700])
try output.path.write(to:root.appendingPathComponent("current-run.txt"),atomically:true,encoding:.utf8)
func log(_ value:[String:Any]) {
 var v=value;v["at"]=ISO8601DateFormatter().string(from:Date())
 guard let data=try? JSONSerialization.data(withJSONObject:v,options:[.sortedKeys]) else{return}
 let path=output.appendingPathComponent("events.jsonl")
 if !FileManager.default.fileExists(atPath:path.path) {FileManager.default.createFile(atPath:path.path,contents:nil,attributes:[.posixPermissions:0o600])}
 if let f=try? FileHandle(forWritingTo:path){defer{try? f.close()};_=try? f.seekToEnd();try? f.write(contentsOf:data+Data([10]))}
}
let queue=DispatchQueue(label:"alternate.frames")
final class Frames:NSObject,AVCaptureVideoDataOutputSampleBufferDelegate {
 let context=CIContext(options:[.useSoftwareRenderer:true]);var count=0;var saved=0;var last=Date.distantPast
 var writer:AVAssetWriter?;var video:AVAssetWriterInput?
 func captureOutput(_ captureOutput:AVCaptureOutput,didOutput sample:CMSampleBuffer,from connection:AVCaptureConnection) {
  autoreleasepool {
   guard sample.isValid,let pixel=sample.imageBuffer else{return};count += 1
   if writer == nil {
    do {
     let w=try AVAssetWriter(outputURL:output.appendingPathComponent("display.mp4"),fileType:.mp4)
     let input=AVAssetWriterInput(mediaType:.video,outputSettings:[AVVideoCodecKey:AVVideoCodecType.h264,AVVideoWidthKey:CVPixelBufferGetWidth(pixel),AVVideoHeightKey:CVPixelBufferGetHeight(pixel)])
     input.expectsMediaDataInRealTime=true
     guard w.canAdd(input) else{log(["event":"movie_input_rejected"]);return}
     w.add(input);writer=w;video=input
     guard w.startWriting() else{log(["event":"movie_start_error","detail":String(describing:w.error)]);return}
     w.startSession(atSourceTime:CMSampleBufferGetPresentationTimeStamp(sample))
     log(["event":"first_frame","width":CVPixelBufferGetWidth(pixel),"height":CVPixelBufferGetHeight(pixel)])
    } catch {log(["event":"movie_error","detail":String(describing:error)])}
   }
   if let writer,writer.status == .writing,let video,video.isReadyForMoreMediaData {if !video.append(sample){log(["event":"append_error","detail":String(describing:writer.error)])}}
   guard Date().timeIntervalSince(last)>=1 else{return};last=Date()
   let ci=CIImage(cvPixelBuffer:pixel)
   guard let image=context.createCGImage(ci,from:ci.extent) else{return}
   let data=NSMutableData()
   if let dst=CGImageDestinationCreateWithData(data,UTType.png.identifier as CFString,1,nil) {
    CGImageDestinationAddImage(dst,image,nil)
    if CGImageDestinationFinalize(dst) {try? (data as Data).write(to:output.appendingPathComponent("latest.png"),options:.atomic);saved += 1}
   }
   if saved % 5 == 0 {log(["event":"frames","received":count,"png_updates":saved])}
  }
 }
 func finish() {
  log(["event":"stopped","frames":count,"png_updates":saved])
  guard let writer,writer.status == .writing else{exit(0)}
  video?.markAsFinished();writer.finishWriting {log(["event":"movie_finished","status":writer.status.rawValue,"error":String(describing:writer.error)]);exit(0)}
 }
}
let display:CGDirectDisplayID = {
 if let i=args.firstIndex(of:"--display"),i+1<args.count,let id=UInt32(args[i+1]) {return id}
 return CGMainDisplayID()
}()
let session=AVCaptureSession();let receiver=Frames()
guard let screen=AVCaptureScreenInput(displayID:display) else{log(["event":"screen_input_nil"]);exit(3)}
screen.minFrameDuration=CMTime(value:1,timescale:5);screen.capturesCursor=true
let dataOutput=AVCaptureVideoDataOutput();dataOutput.alwaysDiscardsLateVideoFrames=true
dataOutput.videoSettings=[kCVPixelBufferPixelFormatTypeKey as String:kCVPixelFormatType_32BGRA]
dataOutput.setSampleBufferDelegate(receiver,queue:queue)
guard session.canAddInput(screen),session.canAddOutput(dataOutput) else{log(["event":"session_rejected_input_or_output"]);exit(4)}
session.beginConfiguration();session.addInput(screen);session.addOutput(dataOutput);session.commitConfiguration()
let observer=NotificationCenter.default.addObserver(forName:.AVCaptureSessionRuntimeError,object:session,queue:nil) {note in log(["event":"runtime_error","detail":String(describing:note.userInfo)])}
let start=Date();var stopping=false
let timer=Timer.scheduledTimer(withTimeInterval:1,repeats:true) {_ in
 guard !stopping else{return}
 if Date().timeIntervalSince(start)>120 || FileManager.default.fileExists(atPath:output.appendingPathComponent("STOP").path) {
  stopping=true;session.stopRunning();queue.async {receiver.finish()}
 }
}
DispatchQueue.global().asyncAfter(deadline:.now()+140) {log(["event":"watchdog"]);exit(5)}
log(["event":"starting","display":display,"backend":"AVCaptureScreenInput"])
DispatchQueue.global().async {session.startRunning();log(["event":"session_started","running":session.isRunning])}
app.run()
