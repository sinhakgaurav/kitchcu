import { customerInitials } from "../shared/customerUi";

export function CustomerAvatar({
  name,
  src,
  size = "md",
  live = false,
}: {
  name?: string | null;
  src?: string | null;
  size?: "sm" | "md" | "lg";
  live?: boolean;
}) {
  return (
    <span className={`customer-avatar customer-avatar--${size}${live ? " customer-avatar--live" : ""}`}>
      {src ? <img src={src} alt="" /> : customerInitials(name)}
      {live ? <span className="customer-avatar__live">Live</span> : null}
    </span>
  );
}
