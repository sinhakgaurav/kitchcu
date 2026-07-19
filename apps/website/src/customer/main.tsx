import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CustomerApp from "./App";
import { LanguageGate } from "../i18n/LanguageGate";
import { applyAppTheme } from "../shared/theme";
import "../index.css";
import "../brand-ux.css";
import "../animations.css";
import "../owner-forms.css";
import "../owner-app.css";

applyAppTheme("brand-light");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LanguageGate>
      <CustomerApp />
    </LanguageGate>
  </StrictMode>,
);
