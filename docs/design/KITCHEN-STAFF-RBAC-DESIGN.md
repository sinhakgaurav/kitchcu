# Module Design Pack — Kitchen Staff RBAC (manager / cook)

**Feature ID:** G-P1-5 · **Service owner:** `services/identity/` (+ order/catalog route deps) · **Sprint:** Wave B · **Author:** Platform · **Date:** 2026-07-19

---

## 1. Business understanding

- **Problem:** Real cloud kitchens have ≥2 humans. Today only the owner JWT works — cooks share the owner phone (security + audit disaster).
- **Vision:** Owner invites staff by phone; staff OTP login scoped to one kitchen with a role matrix (manager / cook / cashier).
- **Business objective:** Unlock multi-person kitchens (TAM) without diluting owner subscription SaaS.
- **Why now:** Wave A trust (admin RBAC) shipped; next honesty gap is kitchen ops sharing.
- **KitchCU product gate:** Yes — grows kitchens that are not solo home chefs; no POS/dine-in.

---

## 2. Challenge & improvement

- **Assumptions challenged:** “Second owner account” is not staff — wrong scope and billing.
- **Improvements:** Role-scoped JWT `{type:staff, kitchen_id, role}`; invite OTP reuses WhatsApp OTP path; no platform admin employee confusion.
- **Out of scope:** Multi-kitchen staff; waiter/table roles; payroll; KDS.

---

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|---------------|
| Owner | Add cook without sharing OTP | Team → Invite phone + role → staff verifies OTP |
| Cook | Advance prep statuses | Login → Orders inbox → status chips only |
| Manager | Accept + menu edit | Login → Orders + Menu (no GST/billing) |
| Cashier | COD confirm | Login → mark paid / COD note |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | `kitchen_members` + invites tables | Must |
| FR-2 | Owner invite / revoke / list | Must |
| FR-3 | Staff OTP login → JWT `type=staff` | Must |
| FR-4 | Order routes accept staff with role matrix | Must |
| FR-5 | Catalog write: manager only | Must |
| FR-6 | Billing/GST/Integrations: owner only | Must |
| FR-7 | Audit: who changed status | Should |

---

## 5. Non-functional requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Latency p95 invite/login | < 400ms |
| NFR-2 | Tenant isolation | Always filter `kitchen_id` |
| NFR-3 | Scale | Index `(kitchen_id, phone)` unique active |

---

## 6. Business rules & validation

| Rule | Enforcement |
|------|-------------|
| One active membership per (kitchen_id, phone) | DB unique |
| Staff cannot change kitchen delivery-settings / PG keys | Route guard |
| Cook cannot cancel after preparing without manager | Domain matrix |
| Owner always retains full access | Existing owner JWT |

---

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | Invite/revoke, full kitchen | — |
| Manager | Accept orders, menu CRUD, view analytics | Billing, WA secrets, packages |
| Cook | Status: accepted→…→ready (not cancel freely) | Menu price edit, refunds |
| Cashier | COD / payment_method note | Status beyond ready |
| Admin (platform) | View memberships on kitchen workspace (ops) | Impersonate staff JWT |

### 7.1 Super-admin integration gate

| # | Question | Y/N | Delivery |
|---|----------|-----|----------|
| 1 | Kitchen-scoped? | Y | Admin → Kitchens → Team tab (list/revoke) |
| 2 | Entitlement? | Y | Module `kitchen_staff` on packages |
| 3 | Ops need view? | Y | `kitchens:read` list members |
| 4 | Kill-switch? | Y | Feature `kitchen_staff_rbac` |
| 5 | Credentials? | N | Staff use OTP only |

---

## 8. Domain model

```
ckac_identity.kitchen_members
  id UUID PK
  kitchen_id UUID NOT NULL INDEX
  phone E.164 NOT NULL
  name TEXT NULL
  role TEXT NOT NULL  -- manager|cook|cashier
  status TEXT NOT NULL -- invited|active|revoked
  invited_by UUID NULL  -- owner_id
  created_at / updated_at

UNIQUE (kitchen_id, phone) WHERE status != 'revoked'
```

JWT claims: `{ sub: member_id, type: "staff", kitchen_id, role, phone }`

---

## 9. API (sketch)

| Method | Path | Auth |
|--------|------|------|
| POST | `/kitchens/{id}/staff/invites` | owner |
| GET | `/kitchens/{id}/staff` | owner |
| DELETE | `/kitchens/{id}/staff/{member_id}` | owner |
| POST | `/auth/staff/otp/request` | public |
| POST | `/auth/staff/otp/verify` | public → staff JWT |
| GET | `/staff/me` | staff |

Order deps: `get_current_kitchen_actor` → owner | staff with permission check.

---

## 10. Events

| Event | Stream | When |
|-------|--------|------|
| `kitchen.staff.invited` | `ckac:identity:kitchen` | invite |
| `kitchen.staff.activated` | `ckac:identity:kitchen` | first verify |
| `kitchen.staff.revoked` | `ckac:identity:kitchen` | revoke |

---

## 11. Tests (TDD)

1. Invite → OTP → staff JWT scoped kitchen  
2. Cook cannot PATCH delivery-settings  
3. Manager can accept order  
4. Revoke → 401 on next call  
5. Tenant: staff kitchen A cannot see kitchen B orders  

---

## 12. Implementation order

1. Migration + models  
2. Invite/list/revoke + OTP (reuse `otp_delivery`)  
3. Auth deps in order (then catalog)  
4. Owner Team UI + Admin Team tab  
5. Package module flag  

**Status:** Design pack complete — implementation next PR (P33+).
