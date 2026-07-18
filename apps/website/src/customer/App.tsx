import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CustomerAuthProvider } from "../shared/customerAuth";
import { CustomerNavbar } from "../components/CustomerNavbar";
import { CustomerFooter } from "../components/CustomerFooter";
import { Hero } from "../components/Hero";
import { ParallaxDivider } from "../components/ParallaxDivider";
import { FloatingGallery } from "../components/FloatingGallery";
import { CustomerShowcase } from "../components/CustomerShowcase";
import { NearbyKitchensList } from "../components/NearbyKitchensList";
import { CustomerHomePage, CustomerLoginPage } from "./pages/CustomerPages";
import { CustomerOAuthCallbackPage } from "./pages/CustomerOAuthCallbackPage";
import { KitchenMenuPage } from "../pages/customer/KitchenMenuPage";
import { CheckoutPage } from "../pages/customer/CheckoutPage";
import { OrderConfirmPage } from "../pages/customer/OrderConfirmPage";
import { OrdersPage } from "../pages/customer/OrdersPage";
import { MasterOrderConfirmPage } from "../pages/customer/MasterOrderConfirmPage";
import { RateOrderPage } from "../pages/customer/RateOrderPage";
import { TrackOrderPage } from "../pages/customer/TrackOrderPage";
import { CustomerAccountPage } from "../pages/customer/CustomerAccountPage";
import { CustomerDashboardPage } from "../pages/customer/CustomerDashboardPage";
import { BrandedMenuRedirect, BrandedStorefrontLayout } from "./BrandedStorefront";

function CustomerShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="customer-app">
      <CustomerNavbar />
      <main>{children}</main>
      <CustomerFooter />
    </div>
  );
}

export default function CustomerApp() {
  return (
    <BrowserRouter>
      <CustomerAuthProvider>
        <Routes>
          <Route
            path="/"
            element={
              <CustomerShell>
                <Hero variant="customer" />
                <ParallaxDivider />
                <CustomerHomePage />
                <NearbyKitchensList />
                <FloatingGallery />
                <ParallaxDivider reverse />
                <CustomerShowcase />
              </CustomerShell>            }
          />
          <Route path="/login" element={<CustomerLoginPage />} />
          <Route path="/oauth/callback" element={<CustomerOAuthCallbackPage />} />
          <Route
            path="/kitchen/:kitchenId/menu"
            element={
              <CustomerShell>
                <KitchenMenuPage />
              </CustomerShell>
            }
          />
          {/* Kitchen-first branded storefront — open in new tab from owner dashboard */}
          <Route path="/k/:code" element={<BrandedStorefrontLayout />}>
            <Route index element={<BrandedMenuRedirect />} />
            <Route path="menu" element={<KitchenMenuPage />} />
            <Route path="checkout" element={<CheckoutPage />} />
            <Route path="orders/:orderId/confirm" element={<OrderConfirmPage />} />
            <Route path="master-orders/:masterOrderId/confirm" element={<MasterOrderConfirmPage />} />
          </Route>
          <Route
            path="/checkout"
            element={
              <CustomerShell>
                <CheckoutPage />
              </CustomerShell>
            }
          />
          <Route
            path="/kitchen/:kitchenId/checkout"
            element={
              <CustomerShell>
                <CheckoutPage />
              </CustomerShell>
            }
          />
          <Route
            path="/orders"
            element={
              <CustomerShell>
                <OrdersPage />
              </CustomerShell>
            }
          />
          <Route
            path="/dashboard"
            element={
              <CustomerShell>
                <CustomerDashboardPage />
              </CustomerShell>
            }
          />
          <Route
            path="/account"
            element={
              <CustomerShell>
                <CustomerAccountPage />
              </CustomerShell>
            }
          />
          <Route
            path="/master-orders/:masterOrderId/confirm"
            element={
              <CustomerShell>
                <MasterOrderConfirmPage />
              </CustomerShell>
            }
          />
          <Route
            path="/orders/:orderId/rate"
            element={
              <CustomerShell>
                <RateOrderPage />
              </CustomerShell>
            }
          />
          <Route
            path="/orders/:orderId/confirm"
            element={
              <CustomerShell>
                <OrderConfirmPage />
              </CustomerShell>
            }
          />
          <Route
            path="/t/:token"
            element={
              <CustomerShell>
                <TrackOrderPage />
              </CustomerShell>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </CustomerAuthProvider>
    </BrowserRouter>
  );
}
