import { useCallback, useEffect, useRef, useState } from "react";
import { uploadKitchenMedia, type MediaUploadContext } from "../lib/api";

type Props = {
  kitchenId?: string;
  context?: MediaUploadContext;
  /** When set, used instead of kitchen media upload (customer photos). */
  upload?: (blob: Blob, isLive: boolean) => Promise<string>;
  value?: string;
  onChange: (url: string) => void;
  label?: string;
  /** When true, only camera capture is allowed (dish hero / customer live photo). */
  requireLiveCapture?: boolean;
  facingMode?: "user" | "environment";
  hint?: string;
  allowClear?: boolean;
};

type Phase = "idle" | "camera" | "preview" | "uploading";

export function LiveCapturePhotoField({
  kitchenId,
  context,
  upload,
  value,
  onChange,
  label = "Photo",
  requireLiveCapture = false,
  facingMode = "environment",
  hint,
  allowClear = true,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [pendingBlob, setPendingBlob] = useState<Blob | null>(null);
  const [pendingLive, setPendingLive] = useState(false);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  useEffect(() => () => stopCamera(), [stopCamera]);

  // Attach stream only after the <video> mounts (phase === "camera").
  useEffect(() => {
    if (phase !== "camera") return;
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!video || !stream) return;
    video.srcObject = stream;
    void video.play().catch(() => {
      /* muted + playsInline — ignore transient autoplay rejection */
    });
  }, [phase]);

  const startCamera = async () => {
    setError("");
    stopCamera();
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera API not available");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode }, width: { ideal: 1280 } },
        audio: false,
      });
      streamRef.current = stream;
      // Mount video first; effect above attaches the stream.
      setPhase("camera");
    } catch {
      setError(
        requireLiveCapture
          ? "Camera access denied or unavailable. This photo requires a live camera capture."
          : "Camera access denied or unavailable. Use upload instead.",
      );
      setPhase("idle");
    }
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
    if (!w || !h) {
      setError("Camera still starting — wait a moment and capture again.");
      return;
    }
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);
    stopCamera();
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError("Capture failed");
          return;
        }
        const url = URL.createObjectURL(blob);
        setPreviewUrl(url);
        setPendingBlob(blob);
        setPendingLive(true);
        setPhase("preview");
      },
      "image/jpeg",
      0.9,
    );
  };

  const resetPending = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPendingBlob(null);
    setPendingLive(false);
    setPhase("idle");
  };

  const doUpload = async (blob: Blob, isLive: boolean) => {
    setError("");
    setPhase("uploading");
    try {
      if (upload) {
        const url = await upload(blob, isLive);
        onChange(url);
      } else if (kitchenId && context) {
        const result = await uploadKitchenMedia(kitchenId, blob, {
          context,
          is_live_capture: isLive,
          captured_at: isLive ? new Date().toISOString() : undefined,
          filename: isLive ? "live-capture.jpg" : "upload.jpg",
        });
        onChange(result.url);
      } else {
        throw new Error("Upload is not configured");
      }
      resetPending();
      setPhase("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setPhase(pendingBlob ? "preview" : "idle");
    }
  };

  const onFilePicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose an image file");
      return;
    }
    if (requireLiveCapture) {
      setError("Dish photos must be captured live with the camera.");
      return;
    }
    setError("");
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setPendingBlob(file);
    setPendingLive(false);
    setPhase("preview");
  };

  const confirmUpload = () => {
    if (pendingBlob) void doUpload(pendingBlob, pendingLive);
  };

  return (
    <div className="live-capture-field">
      <span className="live-capture-field__label">{label}</span>

      {value && phase === "idle" && (
        <div className="live-capture-field__current">
          <img src={value} alt="" className="owner-recipe-preview" />
          {allowClear ? (
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => onChange("")}>
              Remove
            </button>
          ) : null}
        </div>
      )}

      {error && <p className="live-capture-field__error">{error}</p>}

      {phase === "camera" && (
        <div className="live-capture-field__camera">
          <video ref={videoRef} playsInline muted autoPlay className="live-capture-field__video" />
          <canvas ref={canvasRef} className="live-capture-field__canvas" />
          <div className="live-capture-field__actions">
            <button type="button" className="btn btn--primary btn--sm" onClick={captureFrame}>
              Capture
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => {
                stopCamera();
                setPhase("idle");
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {phase === "preview" && previewUrl && (
        <div className="live-capture-field__preview">
          <img src={previewUrl} alt="Preview" className="owner-recipe-preview" />
          {pendingLive && <span className="live-badge">Live capture</span>}
          <div className="live-capture-field__actions">
            <button type="button" className="btn btn--primary btn--sm" onClick={confirmUpload}>
              Use this photo
            </button>
            <button type="button" className="btn btn--ghost btn--sm" onClick={resetPending}>
              Retake
            </button>
          </div>
        </div>
      )}

      {phase === "uploading" && <p className="owner-page__code">Uploading…</p>}

      {(phase === "idle" || (phase === "preview" && !pendingBlob)) && (
        <div className="live-capture-field__actions">
          <button type="button" className="btn btn--primary btn--sm" onClick={() => void startCamera()}>
            {value ? "Retake with camera" : "Open camera"}
          </button>
          {!requireLiveCapture && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="live-capture-field__file"
                onChange={onFilePicked}
              />
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => fileInputRef.current?.click()}
              >
                Upload image
              </button>
            </>
          )}
        </div>
      )}

      {hint ? <p className="auth-card__hint">{hint}</p> : requireLiveCapture ? (
        <p className="auth-card__hint">Truth in media — this photo must be a live camera capture.</p>
      ) : null}
    </div>
  );
}
