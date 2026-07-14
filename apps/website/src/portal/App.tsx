import { BrowserRouter, Route, Routes } from "react-router-dom";
import { PortalHomePage } from "./PortalHomePage";
import { OpenApiPage } from "./OpenApiPage";

export default function PortalApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PortalHomePage />} />
        <Route path="/openapi" element={<OpenApiPage />} />
        <Route path="/api-docs" element={<OpenApiPage />} />
      </Routes>
    </BrowserRouter>
  );
}
