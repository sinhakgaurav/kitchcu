import type { RefObject } from "react";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useInView } from "../hooks/useParallax";
import { images } from "../data/content";
import { ContactParallaxBg } from "./ContactParallaxBg";
import { createSupportTicket } from "../lib/supportApi";

type FormState = "idle" | "sending" | "sent" | "error";

export function Contact() {
  const { t } = useTranslation();
  const { ref, visible } = useInView();
  const [state, setState] = useState<FormState>("idle");
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setState("sending");
    setError("");
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const kitchen = String(form.get("kitchen") || "").trim();
    const phone = String(form.get("phone") || "").trim();
    const city = String(form.get("city") || "").trim();
    const message = String(form.get("message") || "").trim();
    try {
      await createSupportTicket({
        audience: "owner",
        category: "general",
        source: "web_form",
        subject: `Pilot access request — ${kitchen}`,
        description: [
          `Kitchen: ${kitchen}`,
          `City: ${city}`,
          message ? `Message: ${message}` : null,
        ]
          .filter(Boolean)
          .join("\n"),
        customer_name: name,
        customer_phone: phone,
      });
      setState("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("portal.contactError"));
      setState("error");
    }
  };

  return (
    <section className="section contact contact--parallax" id="contact" ref={ref as RefObject<HTMLElement>}>
      <ContactParallaxBg />

      <div className="container contact__grid">
        <div className={`contact__info reveal ${visible ? "reveal--visible" : ""}`}>
          <div className="contact__image-wrap">
            <img src={images.contact.src} alt={images.contact.alt} loading="lazy" />
          </div>
          <span className="section__eyebrow">{t("portal.contactEyebrow")}</span>
          <h2>{t("portal.contactTitle")}</h2>
          <p>{t("portal.contactBody")}</p>
        </div>

        <form
          className={`contact__form glass reveal ${visible ? "reveal--visible" : ""}`}
          onSubmit={handleSubmit}
        >
          {state === "sent" ? (
            <div className="contact__success">
              <span className="contact__success-icon">✓</span>
              <h3>{t("portal.contactSent")}</h3>
              <button type="button" className="btn btn--ghost" onClick={() => setState("idle")}>
                {t("common.retry")}
              </button>
            </div>
          ) : (
            <>
              <h3>{t("portal.contactTitle")}</h3>
              <label>
                {t("portal.contactName")}
                <input name="name" required autoComplete="name" />
              </label>
              <label>
                {t("portal.contactKitchen")}
                <input name="kitchen" required />
              </label>
              <label>
                {t("portal.contactPhone")}
                <input name="phone" type="tel" required autoComplete="tel" />
              </label>
              <label>
                {t("portal.contactCity")}
                <input name="city" required />
              </label>
              <label>
                {t("portal.contactMessage")}
                <textarea name="message" rows={3} />
              </label>
              {state === "error" && <div className="auth-card__error">{error}</div>}
              <button type="submit" className="btn btn--primary btn--lg" disabled={state === "sending"}>
                {state === "sending" ? t("portal.contactSending") : t("portal.contactSubmit")}
              </button>
            </>
          )}
        </form>
      </div>
    </section>
  );
}
