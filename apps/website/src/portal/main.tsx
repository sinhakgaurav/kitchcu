import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import PortalApp from "./App";
import { LanguageGate } from "../i18n/LanguageGate";
import { applyAppTheme } from "../shared/theme";
import "../index.css";
import "../owner-forms.css";
import "../brand-ux.css";
import "../animations.css";

applyAppTheme("brand-light");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LanguageGate>
      <PortalApp />
    </LanguageGate>
  </StrictMode>,
);
