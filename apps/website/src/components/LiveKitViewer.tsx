import { useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track } from "livekit-client";

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
    const room = new Room({ adaptiveStream: true, dynacast: true });

    const attachRemote = (track: Track) => {
      if (track.kind !== Track.Kind.Video || !videoRef.current) return;
      track.attach(videoRef.current);
      if (!cancelled) setStatus("live");
    };

    room.on(RoomEvent.TrackSubscribed, (track) => attachRemote(track));
    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      if (videoRef.current) track.detach(videoRef.current);
      if (!cancelled) setStatus("waiting");
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
          await room.localParticipant.setCameraEnabled(true);
          await room.localParticipant.setMicrophoneEnabled(true);
          const cam = room.localParticipant.getTrackPublication(Track.Source.Camera);
          if (cam?.track && videoRef.current) {
            cam.track.attach(videoRef.current);
          }
          if (!cancelled) setStatus("live");
        } else {
          let found = false;
          for (const participant of room.remoteParticipants.values()) {
            for (const pub of participant.trackPublications.values()) {
              if (pub.track) {
                attachRemote(pub.track);
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
      room.disconnect();
    };
    // status intentionally omitted — only reconnect on url/token/publish change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, token, publish]);

  return (
    <div className="livekit-viewer">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={publish}
        style={{
          width: "100%",
          maxHeight: 420,
          background: "#0b1f1c",
          borderRadius: 8,
          display: "block",
        }}
      />
      {status === "connecting" && <p className="report-hint">Connecting to live room…</p>}
      {status === "waiting" && (
        <p className="report-hint">Connected — waiting for the kitchen to publish video.</p>
      )}
      {status === "error" && <p className="auth-card__error">{error}</p>}
    </div>
  );
}
