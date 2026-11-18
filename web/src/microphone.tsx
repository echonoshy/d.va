import { useEffect, useRef, useState } from "react";

export function Microphone({
  disabled,
  onFile,
}: {
  disabled: boolean;
  onFile: (file: File) => void;
}) {
  const recorder = useRef<MediaRecorder | null>(null);
  const mounted = useRef(true);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (recorder.current?.state === "recording") recorder.current.stop();
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);
  async function toggle() {
    if (recorder.current?.state === "recording") {
      recorder.current.stop();
      return;
    }
    setWaiting(true);
    setError("");
    let stream: MediaStream | undefined;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const capture = new MediaRecorder(stream);
      recorder.current = capture;
      const chunks: Blob[] = [];
      capture.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      capture.onstop = () => {
        capture.stream.getTracks().forEach((track) => track.stop());
        if (!mounted.current) return;
        setRecording(false);
        const type = capture.mimeType;
        const extension = type.includes("mp4")
          ? "m4a"
          : type.includes("ogg")
            ? "ogg"
            : "webm";
        if (chunks.length)
          onFile(new File(chunks, "录音." + extension, { type }));
      };
      capture.start();
      setRecording(true);
    } catch {
      stream?.getTracks().forEach((track) => track.stop());
      if (mounted.current) setError("无法启动麦克风，请检查浏览器的录音权限。");
    } finally {
      if (mounted.current) setWaiting(false);
    }
  }
  if (
    typeof MediaRecorder === "undefined" ||
    !navigator.mediaDevices?.getUserMedia
  )
    return null;
  return (
    <>
      <button
        type="button"
        disabled={waiting || (disabled && !recording)}
        onClick={() => void toggle()}
      >
        {recording ? "停止并使用录音" : "麦克风录音"}
      </button>
      {error && <span role="alert">{error}</span>}
    </>
  );
}
