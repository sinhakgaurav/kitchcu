import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import PortalApp from "./App";
import "../index.css";
import "../animations.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PortalApp />
  </StrictMode>,
);
