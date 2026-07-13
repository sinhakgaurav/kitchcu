import type { RefObject } from "react";
import { FormEvent, useState } from "react";
import { useInView } from "../hooks/useParallax";
import { images } from "../data/content";
import { ContactParallaxBg } from "./ContactParallaxBg";

type FormState = "idle" | "sending" | "sent";

export function Contact() {
  const { ref, visible } = useInView();
  const [state, setState] = useState<FormState>("idle");

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setState("sending");
    setTimeout(() => setState("sent"), 900);
  };

  return (
    <section className="section contact contact--parallax" id="contact" ref={ref as RefObject<HTMLElement>}>
      <ContactParallaxBg />

      <div className="container contact__grid">
        <div className={`contact__info reveal ${visible ? "reveal--visible" : ""}`}>
          <div className="contact__image-wrap">
            <img src={images.contact.src} alt={images.contact.alt} loading="lazy" />
          </div>
          <span className="section__eyebrow">Contact</span>
          <h2>Join the kitchCU pilot program</h2>
          <p>
            Limited to 10 cloud kitchens in Phase 1. Tell us about your kitchen and
            we&apos;ll help you get onboarded.
          </p>

          <ul className="contact__details">
            <li>
              <strong>Email</strong>
              <a href="mailto:hello@kitchCU.in">hello@kitchCU.in</a>
            </li>
            <li>
              <strong>Location</strong>
              <span>Pune, Maharashtra, India</span>
            </li>
          </ul>
        </div>

        <form
          className={`contact__form glass reveal ${visible ? "reveal--visible" : ""}`}
          onSubmit={handleSubmit}
        >
          {state === "sent" ? (
            <div className="contact__success">
              <span className="contact__success-icon">✓</span>
              <h3>Request received!</h3>
              <p>We&apos;ll contact you within 24 hours about pilot access.</p>
              <button type="button" className="btn btn--ghost" onClick={() => setState("idle")}>
                Send another
              </button>
            </div>
          ) : (
            <>
              <h3>Request pilot access</h3>
              <label>
                Full name
                <input name="name" required placeholder="Raj Sharma" />
              </label>
              <label>
                Kitchen name
                <input name="kitchen" required placeholder="Raj Home Kitchen" />
              </label>
              <label>
                Phone
                <input name="phone" type="tel" required placeholder="+91 98765 43210" />
              </label>
              <label>
                City
                <input name="city" required placeholder="Pune" />
              </label>
              <label>
                Message (optional)
                <textarea name="message" rows={3} placeholder="Orders per day, current channels..." />
              </label>
              <button type="submit" className="btn btn--primary btn--lg" disabled={state === "sending"}>
                {state === "sending" ? "Sending..." : "Submit Request"}
              </button>
            </>
          )}
        </form>
      </div>
    </section>
  );
}
