import { useEffect, useRef, useState } from "react";

type Props = {
  /** Prefer rear camera for kitchen cooking shots. */
  facingMode?: "user" | "environment";
  className?: string;
};

/**
 * Local getUserMedia preview (no LiveKit). Used when streaming is in showcase-only
 * / dev mode, or as a stable viewfinder while LiveKit connects.
 */
export function LocalCameraPreview({ facingMode = "environment", className = "" }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState<"starting" | "live" | "error">("starting");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;

    (async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("Camera API not available in this browser");
        }
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1280 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => {
            /* autoplay can race; muted + playsInline usually wins */
          });
        }
        if (!cancelled) setStatus("live");
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Camera permission denied");
          setStatus("error");
        }
      }
    })();

    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [facingMode]);

  return (
    <div className={`local-camera-preview ${className}`.trim()}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="local-camera-preview__video"
      />
      {status === "starting" && <p className="report-hint">Starting camera…</p>}
      {status === "error" && (
        <p className="auth-card__error">
          Camera: {error || "allow camera access and retry"}
        </p>
      )}
    </div>
  );
}
