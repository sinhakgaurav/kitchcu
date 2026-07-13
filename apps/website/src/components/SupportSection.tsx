import type { RefObject } from "react";
import { useState } from "react";
import { useInView } from "../hooks/useParallax";
import { supportChannels, supportFaqs } from "../data/content";
import { ParallaxScene } from "./ParallaxScene";

type Tab = "owner" | "customer";

export function SupportSection() {
  const { ref, visible } = useInView();
  const [tab, setTab] = useState<Tab>("owner");
  const [openIdx, setOpenIdx] = useState<number | null>(0);
  const faqs = tab === "owner" ? supportFaqs.owner : supportFaqs.customer;

  return (
    <section className="section support-section support-section--parallax" id="support" ref={ref as RefObject<HTMLElement>}>
      <ParallaxScene variant="section" />
      <div className="container support-section__inner">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">Support</span>
          <h2>Help for owners &amp; customers</h2>
          <p>
            Browse FAQs below or chat with our AI assistant — choose owner or customer mode
            using the chat button in the corner.
          </p>
        </div>

        <div className={`support-section__grid reveal ${visible ? "reveal--visible" : ""}`}>
          <div className="glass support-section__channels">
            <h3>Contact &amp; hours</h3>
            <ul>
              {supportChannels.map((c) => (
                <li key={c.label}>
                  <strong>{c.label}</strong>
                  {c.href ? (
                    <a href={c.href}>{c.value}</a>
                  ) : (
                    <span>{c.value}</span>
                  )}
                </li>
              ))}
            </ul>
            <div className="support-section__ai-hint">
              <span className="support-section__ai-dot" />
              AI chat available 24/7 for instant answers
            </div>
          </div>

          <div className="support-section__faqs glass">
            <div className="support-section__tabs">
              <button
                type="button"
                className={tab === "owner" ? "active" : ""}
                onClick={() => { setTab("owner"); setOpenIdx(0); }}
              >
                Owner FAQ
              </button>
              <button
                type="button"
                className={tab === "customer" ? "active" : ""}
                onClick={() => { setTab("customer"); setOpenIdx(0); }}
              >
                Customer FAQ
              </button>
            </div>

            <div className="support-section__accordion">
              {faqs.map((item, i) => (
                <details
                  key={item.q}
                  open={openIdx === i}
                  onToggle={(e) => {
                    if ((e.target as HTMLDetailsElement).open) setOpenIdx(i);
                  }}
                >
                  <summary>{item.q}</summary>
                  <p>{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
