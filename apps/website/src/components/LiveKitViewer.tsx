import { useEffect, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  Track,
  createLocalVideoTrack,
  type LocalVideoTrack,
} from "livekit-client";

type Props = {
  url: string;
  token: string;
  /** When true, publish local camera (owner go-live). */
  publish?: boolean;
};

export function LiveKitViewer({ url, token, publish = false }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState<"connecting" | "live" | "waiting" | "error">("connecting");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let localTrack: LocalVideoTrack | null = null;
    const room = new Room({ adaptiveStream: true, dynacast: true });

    const attachToVideo = async (track: Track) => {
      const el = videoRef.current;
      if (track.kind !== Track.Kind.Video || !el) return;
      track.attach(el);
      try {
        await el.play();
      } catch {
        /* muted autoplay should succeed */
      }
      if (!cancelled) setStatus("live");
    };

    room.on(RoomEvent.TrackSubscribed, (track) => {
      void attachToVideo(track);
    });
    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      if (videoRef.current) track.detach(videoRef.current);
      if (!cancelled) setStatus("waiting");
    });
    room.on(RoomEvent.LocalTrackPublished, (pub) => {
      if (pub.track) void attachToVideo(pub.track);
    });
    room.on(RoomEvent.Disconnected, () => {
      if (!cancelled) setStatus("waiting");
    });

    (async () => {
      try {
        await room.connect(url, token);
        if (cancelled) {
          room.disconnect();
          return;
        }
        if (publish) {
          try {
            localTrack = await createLocalVideoTrack({
              facingMode: "environment",
            });
            if (cancelled) {
              localTrack.stop();
              return;
            }
            await attachToVideo(localTrack);
            await room.localParticipant.publishTrack(localTrack);
            try {
              await room.localParticipant.setMicrophoneEnabled(true);
            } catch {
              /* mic optional — video preview still works */
            }
            if (!cancelled) setStatus("live");
          } catch (camErr) {
            if (!cancelled) {
              setError(
                camErr instanceof Error
                  ? `Camera: ${camErr.message}`
                  : "Camera permission denied — allow camera access and retry",
              );
              setStatus("error");
            }
          }
        } else {
          let found = false;
          for (const participant of room.remoteParticipants.values()) {
            for (const pub of participant.trackPublications.values()) {
              if (pub.track) {
                await attachToVideo(pub.track);
                found = true;
              }
            }
          }
          if (!cancelled && !found) setStatus("waiting");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not connect to live room");
          setStatus("error");
        }
      }
    })();

    return () => {
      cancelled = true;
      try {
        localTrack?.stop();
      } catch {
        /* ignore */
      }
      room.disconnect();
    };
  }, [url, token, publish]);

  return (
    <div className="livekit-viewer">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={publish}
        className="livekit-viewer__video"
      />
      {status === "connecting" && <p className="report-hint">Connecting to live room…</p>}
      {status === "waiting" && (
        <p className="report-hint">Connected — waiting for the kitchen to publish video.</p>
      )}
      {status === "error" && <p className="auth-card__error">{error}</p>}
    </div>
  );
}
