# kitchCU Web Apps — customer.kitchcu.in & kitchen.kitchcu.in

Two separate frontends sharing API client code under `src/shared/`.

| App | Dev URL | Purpose |
|-----|---------|---------|
| **customer.kitchcu.in** | http://localhost:13001 | Customer browse, sign-in, menus |
| **kitchen.kitchcu.in** | http://localhost:13002 | Owner OTP login, dashboard, kitchen ops |
| **admin.kitchcu.in** | http://localhost:13003 | Platform admin — stats, kitchens, tickets |
| **kitchcu.in** (portal) | http://localhost:13000 | Marketing / app chooser |

## Run locally

```powershell
docker compose up -d
python scripts/seed-dev-data.py

cd apps/website
npm install

# Terminal 1 — customer app
npm run dev:customer

# Terminal 2 — kitchen app
npm run dev:kitchen
```

## Auth isolation

| App | Storage keys | Login |
|-----|--------------|-------|
| customer.kitchcu.in | `ckac_customer_session` | Name + phone (local session) |
| kitchen.kitchcu.in | `ckac_kitchen_token` | Owner OTP |

Owner JWT is **never** stored on customer.kitchcu.in and vice versa.

## Demo

| | customer.kitchcu.in | kitchen.kitchcu.in |
|---|---------------|--------------|
| Sign in | Customer sign in → demo name/phone | Demo owner → `9876543210` / OTP `123456` |
| Kitchen code | `CKPNQ001` | Same (owner dashboard) |

## Production subdomains

Set build args / env:

```
VITE_CUSTOMER_APP_URL=https://customer.kitchcu.in
VITE_KITCHEN_APP_URL=https://kitchen.kitchcu.in
VITE_ADMIN_APP_URL=https://admin.kitchcu.in
```

Docker:

```powershell
docker compose up -d customer-web kitchen-web
```

## Build

```powershell
npm run build          # both apps
npm run build:customer
npm run build:kitchen
```
