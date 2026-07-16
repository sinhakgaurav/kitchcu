# Module Design Pack — Owner Integrations (WhatsApp + Wallet visibility)

**Feature ID:** F01 (connect) + M10 (wallet visibility) · **Service:** identity + billing · **Sprint:** gap-closure · **Date:** 2026-07-16

## 1. Business understanding
- **Problem:** Owners cannot connect Meta WhatsApp Business phone to their kitchen; inbound F01 orders never route. Paid ₹500 messaging wallet is invisible. Payment gateway page is present but broken (wrong auth hook).
- **Vision:** One Integrations area — payments + WhatsApp — so Day-1 “connect WhatsApp → first draft order” works.
- **Product gate:** Yes — WhatsApp-native ops is KitchCu’s growth channel; zero commission preserved.

## 2. Challenge & improvement
- **Not** giving owners Meta App Secret (platform-owned in Super Admin). Owners only set **Phone Number ID** (+ display E.164).
- Enforce **unique** `whatsapp_phone_id` so two kitchens cannot steal the same Meta number.
- Respect per-kitchen `whatsapp` module kill-switch.

## 3. Personas
| Persona | Goal |
|---------|------|
| Owner | Connect WA Business number; see wallet balance before blasts |
| Platform | Hold Meta app secret; kill WhatsApp per kitchen |

## 4. Functional requirements
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | GET/PUT kitchen WhatsApp integration (phone_number_id, display phone) | Must |
| FR-2 | Unique phone_number_id across kitchens | Must |
| FR-3 | Event `kitchen.whatsapp.updated` + outbox | Must |
| FR-4 | GET messaging wallet balance for owner | Must |
| FR-5 | Owner UI: WhatsApp page + fix Payment gateway kitchen context | Must |
| FR-6 | Nav: Integrations grouping | Should |

## 5. Permissions
| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | Own kitchen WA config + wallet read | Platform Meta secrets |
| Admin | Platform WA secrets + module kill | Silent menu/finance mutation |

## 6. API
- `GET/PUT /api/v1/kitchens/{id}/whatsapp-integration`
- `GET /api/v1/billing/kitchens/{id}/messaging-wallet`
- Events: `ckac:identity:kitchen` → `kitchen.whatsapp.updated`

## 7. Out of scope
- Per-kitchen Meta access token vault (Phase 2; platform token sufficient for Cloud API MVP)
- Twilio SMS keys on owner UI
