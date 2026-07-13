/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CUSTOMER_APP_URL?: string;
  readonly VITE_KITCHEN_APP_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
