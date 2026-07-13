import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { KitchenAuthProvider } from "../shared/kitchenAuth";
import { KitchenProvider } from "../shared/kitchenContext";
import { KitchenLandingPage } from "./pages/KitchenLandingPage";
import { LoginPage } from "../pages/LoginPage";
import { OwnerLayout, RequireAuth } from "../layouts/OwnerLayout";
import { OwnerHomePage } from "../pages/owner/OwnerHomePage";
import { KitchenSetupPage } from "../pages/owner/KitchenSetupPage";
import { OrdersPage } from "../pages/owner/OrdersPage";
import { OrderDetailPage } from "../pages/owner/OrderDetailPage";
import { NewOrderPage } from "../pages/owner/NewOrderPage";
import { MenuPage } from "../pages/owner/MenuPage";
import { AddDishPage } from "../pages/owner/AddDishPage";
import { ReportsPage } from "../pages/owner/ReportsPage";
import { GrowthPage } from "../pages/owner/GrowthPage";
import { IngredientsPage } from "../pages/owner/IngredientsPage";
import { CommunityPage } from "../pages/owner/CommunityPage";
import { StreamPage } from "../pages/owner/StreamPage";
import { LearningPage } from "../pages/owner/LearningPage";
import { TrialDetailPage } from "../pages/owner/TrialDetailPage";
import { CrmPage } from "../pages/owner/CrmPage";
import { CouponsPage } from "../pages/owner/CouponsPage";
import { SubscriptionPage } from "../pages/owner/SubscriptionPage";
import { GstFinancePage } from "../pages/owner/GstFinancePage";

export default function KitchenApp() {
  return (
    <BrowserRouter>
      <KitchenAuthProvider>
        <Routes>
          <Route path="/" element={<KitchenLandingPage />} />
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <KitchenProvider>
                  <OwnerLayout />
                </KitchenProvider>
              </RequireAuth>
            }
          >
            <Route index element={<OwnerHomePage />} />
            <Route path="setup" element={<KitchenSetupPage />} />
            <Route path="orders" element={<OrdersPage />} />
            <Route path="orders/new" element={<NewOrderPage />} />
            <Route path="orders/:orderId" element={<OrderDetailPage />} />
            <Route path="menu" element={<MenuPage />} />
            <Route path="menu/new" element={<AddDishPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="growth" element={<GrowthPage />} />
            <Route path="ingredients" element={<IngredientsPage />} />
            <Route path="learning" element={<LearningPage />} />
            <Route path="learning/trials/:trialId" element={<TrialDetailPage />} />
            <Route path="community" element={<CommunityPage />} />
            <Route path="stream" element={<StreamPage />} />
            <Route path="crm" element={<CrmPage />} />
            <Route path="coupons" element={<CouponsPage />} />
            <Route path="subscription" element={<SubscriptionPage />} />
            <Route path="gst" element={<GstFinancePage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </KitchenAuthProvider>
    </BrowserRouter>
  );
}
