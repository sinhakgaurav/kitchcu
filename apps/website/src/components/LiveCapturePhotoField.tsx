import { useCallback, useEffect, useRef, useState } from "react";
import { uploadKitchenMedia, type MediaUploadContext } from "../lib/api";

type Props = {
  kitchenId: string;
  context: MediaUploadContext;
  value?: string;
  onChange: (url: string) => void;
  label?: string;
  /** When true, only camera capture is allowed (dish hero). */
  requireLiveCapture?: boolean;
};

type Phase = "idle" | "camera" | "preview" | "uploading";

export function LiveCapturePhotoField({
  kitchenId,
  context,
  value,
  onChange,
  label = "Photo",
  requireLiveCapture = false,
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

  const startCamera = async () => {
    setError("");
    stopCamera();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setPhase("camera");
    } catch {
      setError("Camera access denied or unavailable. Use upload instead.");
    }
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
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
      const result = await uploadKitchenMedia(kitchenId, blob, {
        context,
        is_live_capture: isLive,
        captured_at: isLive ? new Date().toISOString() : undefined,
        filename: isLive ? "live-capture.jpg" : "upload.jpg",
      });
      onChange(result.url);
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
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => onChange("")}>
            Remove
          </button>
        </div>
      )}

      {error && <p className="live-capture-field__error">{error}</p>}

      {phase === "camera" && (
        <div className="live-capture-field__camera">
          <video ref={videoRef} playsInline muted className="live-capture-field__video" />
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

      {requireLiveCapture && (
        <p className="auth-card__hint">Truth in media — dish hero must be a live camera capture.</p>
      )}
    </div>
  );
}
