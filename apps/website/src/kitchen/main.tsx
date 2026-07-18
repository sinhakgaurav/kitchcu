import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import KitchenApp from "./App";
import { applyAppTheme } from "../shared/theme";
import "../index.css";
import "../brand-ux.css";
import "../animations.css";
import "../owner-forms.css";
import "../owner-app.css";
import "../dashboard-shell.css";

applyAppTheme("brand-light");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <KitchenApp />
  </StrictMode>,
);
