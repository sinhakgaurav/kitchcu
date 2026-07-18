# Module Design Pack — Required Before Implementation

Copy this template for **every new module or feature** (fill all sections; skip only if explicitly N/A with reason).

**Feature ID:** F__ · **Service owner:** `services/<name>/` · **Sprint:** S__ · **Author:** · **Date:**

---

## 1. Business understanding

- **Problem:**
- **Vision:**
- **Business objective:**
- **Why now:**
- **KitchCu product gate:** Does this help cloud kitchens grow without aggregator dependency? (Y/N + why)

---

## 2. Challenge & improvement

- **Assumptions challenged:**
- **Improvements over raw requirement:**
- **Out of scope (explicit):**

---

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|---------------|
| | | |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | | Must |

---

## 5. Non-functional requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Latency p95 | |
| NFR-2 | Availability | |
| NFR-3 | Tenant isolation | |

---

## 6. Business rules & validation

| Rule | Enforcement layer |
|------|-------------------|
| | Pydantic / domain / DB |

---

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | | |
| Customer | | |
| Admin | | |

### 7.1 Super-admin integration gate (mandatory)

Copy answers into the PR / tracker. Fail any row → wire admin in the **same** change (see `.cursor/rules/kitchcu-superadmin-integration.mdc`).

| # | Question | Y/N | Delivery if yes |
|---|----------|-----|-----------------|
| 1 | Kitchen-scoped (ops, credentials, modules, marketing, streaming, billing UX)? | | Admin → Kitchens → workspace tab + admin API |
| 2 | Entitlement / monetized (plan, package, module)? | | Packages mapper + kitchen Package tab; server enforce |
| 3 | Ops/support need view or override? | | Admin API/UI + RBAC `resource:action` |
| 4 | Kill-switch needed? | | Feature flag and/or kitchen module flag |
| 5 | Credentials? | | Kitchen secrets on kitchen form; platform secrets under API Keys only |

Deferral only with tracker note + reserved permission code.

---

## 8. Domain model & bounded context

```
Aggregates:
  -
Entities / value objects:
  -
Invariants:
  -
```

---

## 9. Events

| Event | Producer | Stream | Subscribers | Idempotency key |
|-------|----------|--------|-------------|-----------------|
| | | `ckac:...` | | |

---

## 10. Database

| Table | Schema | Indexes | Migration |
|-------|--------|---------|-----------|
| | `ckac_<domain>` | | Alembic `00x_` |

---

## 11. API contracts

| Method | Path | Auth | Request | Response | Errors |
|--------|------|------|---------|----------|--------|
| POST | `/api/v1/...` | JWT | | | 400, 403, 404 |

OpenAPI updated: Y/N

---

## 12. Workflow & notifications

```
[Sequence diagram or numbered steps]
```

| Trigger | Channel | Template |
|---------|---------|----------|
| | WhatsApp / push / email | |

---

## 13. Analytics & reports

| Question answered | Metric | Storage |
|-------------------|--------|---------|
| | | |

---

## 14. Edge cases · failures · recovery

| Case | Behavior | Recovery |
|------|----------|----------|
| Duplicate request | Idempotent 200 | |
| Downstream unavailable | | Retry / DLQ |

---

## 15. Security & privacy

- PII fields:
- OWASP considerations:
- Audit log needed: Y/N

---

## 16. Test plan

| Test | Type | File |
|------|------|------|
| | unit / API / event / security | `tests/test_*.py` |

### BDD scenarios (Given / When / Then)

```
Scenario:
  Given
  When
  Then
```

### Contract tests (when service boundary changes)

- Consumer: gateway or calling service
- Provider: OpenAPI schema snapshot or pact file

**Acceptance criteria (from benchmark):**

- [ ]
- [ ]

---

## 17. Implementation plan

| Step | Task | Estimate |
|------|------|----------|
| 1 | Migration | |
| 2 | Domain + schemas | |
| 3 | Routes + gateway | |
| 4 | Events | |
| 5 | Tests + run-tests.ps1 | |

---

## 18. Future AI & expansion

- AI enhancement (Phase 2+):
- Service split trigger:

---

## Approval

- [ ] CPO acceptance criteria matched
- [ ] CTO architecture / events reviewed
- [ ] DBA schema reviewed
- [ ] QA test plan reviewed

**Only after approval → implement production code.**
