import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type OwnerPageShellProps = {
  eyebrow: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  backTo?: string;
  backLabel?: string;
  children: ReactNode;
  className?: string;
};

export function OwnerPageShell({
  eyebrow,
  title,
  description,
  meta,
  actions,
  backTo,
  backLabel = "← Back",
  children,
  className = "",
}: OwnerPageShellProps) {
  return (
    <div className={`owner-screen od-board ${className}`.trim()}>
      {backTo && (
        <Link to={backTo} className="owner-back">
          {backLabel}
        </Link>
      )}
      <section className="od-board__hero dash-card">
        <div className="od-board__hero-text">
          <p className="od-board__eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          {description && <p className="od-board__meta">{description}</p>}
          {meta}
        </div>
        {actions && (
          <div className="od-board__hero-actions od-board__hero-actions--row">{actions}</div>
        )}
      </section>
      <div className="owner-screen__body">{children}</div>
    </div>
  );
}

export function OwnerPanel({
  title,
  description,
  action,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`dash-card od-panel owner-panel ${className}`.trim()}>
      <header className="od-panel__head">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

export function OwnerEmpty({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="dash-card owner-empty-state">
      <p>{message}</p>
      {action}
    </div>
  );
}
