import type { RefObject } from "react";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useInView } from "../hooks/useParallax";
import { images } from "../data/content";
import { ContactParallaxBg } from "./ContactParallaxBg";
import { PhoneField } from "./PhoneField";
import { createSupportTicket } from "../lib/supportApi";
import {
  firstError,
  toE164,
  validateNationalPhone,
  validatePersonName,
  validateText,
} from "../shared/validation";

type FormState = "idle" | "sending" | "sent" | "error";

type ContactErrors = {
  name?: string;
  kitchen?: string;
  phone?: string;
  city?: string;
  message?: string;
};

export function Contact() {
  const { t } = useTranslation();
  const { ref, visible } = useInView();
  const [state, setState] = useState<FormState>("idle");
  const [error, setError] = useState("");
  const [phone, setPhone] = useState("");
  const [fieldErrors, setFieldErrors] = useState<ContactErrors>({});

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const kitchen = String(form.get("kitchen") || "").trim();
    const city = String(form.get("city") || "").trim();
    const message = String(form.get("message") || "").trim();
    const nextErrors: ContactErrors = {
      name: validatePersonName(name) ?? undefined,
      kitchen: validateText(kitchen, "your kitchen name", { max: 120 }) ?? undefined,
      phone: validateNationalPhone(phone) ?? undefined,
      city: validateText(city, "your city", { max: 80 }) ?? undefined,
      message: validateText(message, "a message", { required: false, max: 1000 }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      setState("error");
      return;
    }
    setState("sending");
    setError("");
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
        customer_phone: toE164(phone),
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
                <input
                  name="name"
                  required
                  autoComplete="name"
                  className={fieldErrors.name ? "input-invalid" : undefined}
                  aria-invalid={Boolean(fieldErrors.name)}
                />
                {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
              </label>
              <label>
                {t("portal.contactKitchen")}
                <input
                  name="kitchen"
                  required
                  className={fieldErrors.kitchen ? "input-invalid" : undefined}
                  aria-invalid={Boolean(fieldErrors.kitchen)}
                />
                {fieldErrors.kitchen ? (
                  <span className="field-error">{fieldErrors.kitchen}</span>
                ) : null}
              </label>
              <PhoneField
                label={t("portal.contactPhone")}
                value={phone}
                onChange={(national) => {
                  setPhone(national);
                  setFieldErrors((f) => ({ ...f, phone: undefined }));
                }}
                error={fieldErrors.phone}
                required
              />
              <label>
                {t("portal.contactCity")}
                <input
                  name="city"
                  required
                  className={fieldErrors.city ? "input-invalid" : undefined}
                  aria-invalid={Boolean(fieldErrors.city)}
                />
                {fieldErrors.city ? <span className="field-error">{fieldErrors.city}</span> : null}
              </label>
              <label>
                {t("portal.contactMessage")}
                <textarea
                  name="message"
                  rows={3}
                  maxLength={1000}
                  className={fieldErrors.message ? "input-invalid" : undefined}
                  aria-invalid={Boolean(fieldErrors.message)}
                />
                {fieldErrors.message ? (
                  <span className="field-error">{fieldErrors.message}</span>
                ) : null}
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
