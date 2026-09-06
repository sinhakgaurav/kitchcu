/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CUSTOMER_APP_URL?: string;
  readonly VITE_KITCHEN_APP_URL?: string;
  readonly VITE_ADMIN_APP_URL?: string;
  readonly VITE_PORTAL_APP_URL?: string;
  readonly VITE_GOOGLE_MAPS_API_KEY?: string;
  readonly VITE_APP_DOMAIN?: string;
  /** Force-show/hide seeded demo logins; defaults to hidden on *.kitchcu.com. */
  readonly VITE_SHOW_DEMO_CREDENTIALS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
