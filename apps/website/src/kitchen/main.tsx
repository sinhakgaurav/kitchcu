import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import KitchenApp from "./App";
import "../index.css";
import "../animations.css";
import "../owner-forms.css";
import "../owner-app.css";
import "../dashboard-shell.css";
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <KitchenApp />
  </StrictMode>,
);
