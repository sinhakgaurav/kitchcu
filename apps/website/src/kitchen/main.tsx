import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import KitchenApp from "./App";
import "../index.css";
import "../animations.css";
import "../owner-app.css";
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <KitchenApp />
  </StrictMode>,
);
