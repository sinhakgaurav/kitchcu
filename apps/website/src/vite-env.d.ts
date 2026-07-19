/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CUSTOMER_APP_URL?: string;
  readonly VITE_KITCHEN_APP_URL?: string;
  readonly VITE_ADMIN_APP_URL?: string;
  readonly VITE_PORTAL_APP_URL?: string;
  readonly VITE_GOOGLE_MAPS_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
