import { customerInitials } from "../shared/customerUi";

export function CustomerAvatar({
  name,
  src,
  size = "md",
}: {
  name?: string | null;
  src?: string | null;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <span className={`customer-avatar customer-avatar--${size}`}>
      {src ? <img src={src} alt="" /> : customerInitials(name)}
    </span>
  );
}
