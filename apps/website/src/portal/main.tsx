import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import PortalApp from "./App";
import { applyAppTheme } from "../shared/theme";
import "../index.css";
import "../brand-ux.css";
import "../animations.css";

applyAppTheme("brand-light");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PortalApp />
  </StrictMode>,
);
