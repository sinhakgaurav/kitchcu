import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LegalPage } from "./LegalPage";
import { OpenApiPage } from "./OpenApiPage";
import { PortalHomePage } from "./PortalHomePage";

export default function PortalApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PortalHomePage />} />
        <Route path="/terms" element={<LegalPage kind="terms" />} />
        <Route path="/privacy" element={<LegalPage kind="privacy" />} />
        <Route path="/refund-policy" element={<LegalPage kind="refund" />} />
        <Route path="/platform-refund-policy" element={<LegalPage kind="platform-refund" />} />
        <Route path="/openapi" element={<OpenApiPage />} />
        <Route path="/api-docs" element={<OpenApiPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
