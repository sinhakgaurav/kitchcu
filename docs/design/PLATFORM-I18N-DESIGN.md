# Platform i18n — location language gate

**Feature:** Platform multilingual (start) · **Owner:** `apps/website/` · **Date:** 2026-07-19

## 1. Business

- **Problem:** UI is English-only; charter promises Hindi + regional at launch.
- **Vision:** Detect likely local language from location; ask once: English vs local (by name); persist choice.
- **Gate:** Helps owners/customers use kitchCU in their language → higher activation. Y.

## 2. Scope (this slice)

| In | Out |
|----|-----|
| Location → language suggestion | Server-side locale / Accept-Language APIs |
| One-time chooser (EN vs suggested) | Live translation / LLM |
| Portal + customer + kitchen shells + dashboard chrome | Admin (ops stays English for now) |
| Catalogs: en + hi + mr + ta + te + kn + ml + bn + gu + pa (184 keys; parity checked) | 100% of every long-form page body |

**Wired to `t()`:** LanguageGate/Switcher · PortalNavbar · PortalHero · OwnerLayout nav · Owner login/home/subscription · CustomerNavbar · customer login/discovery/checkout/orders/dashboard tabs.

**Parity:** `python scripts/check-i18n-locale-parity.py`

## 3. Detection order

1. Saved locale (`localStorage`) — skip prompt  
2. Geolocation → coarse India lat/lng regions → language code  
3. `navigator.languages` / `navigator.language`  
4. Default `en`

No third-party geocoding (Maps) — bounding boxes only.

## 4. UX

- Modal before app chrome (first visit only).  
- Copy: “We think your local language is **{Name}**. Continue in English or {Name}?”  
- Choices set `document.documentElement.lang` + i18n.

## 5. Super-admin

| Gate | Answer |
|------|--------|
| Kill-switch | Later: `platform_i18n` feature flag (optional). Not blocking this shell. |
| Credentials | N |

## 6. Events / DB

N/A — client preference only.
