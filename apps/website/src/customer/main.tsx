import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CustomerApp from "./App";
import "../index.css";
import "../animations.css";
import "../owner-app.css";
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CustomerApp />
  </StrictMode>,
);
