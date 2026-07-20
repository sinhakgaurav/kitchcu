# KitchCu — Engineering Standards & Development Constitution

**Status:** Active — applies to all existing and new code  
**Audience:** Founding engineering org, AI agents, contributors  
**Product:** KitchCu — *The Growth Operating System for Cloud Kitchens & Home Food Businesses*

| Companion | Purpose |
|-----------|---------|
| [`AGENTS.md`](../AGENTS.md) | Agent quick spec + current build baseline |
| [`docs/DEVELOPMENT-PHASES.md`](./DEVELOPMENT-PHASES.md) | Sprint order, schemas, phase gates |
| [`docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md`](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) | 48 features + acceptance criteria |
| [`docs/CKAC-SYSTEM-BENCHMARK.md`](./CKAC-SYSTEM-BENCHMARK.md) | Architecture, cache, DB, SLOs |
| [`docs/templates/MODULE-DESIGN-PACK.md`](./templates/MODULE-DESIGN-PACK.md) | Required pre-code design template |

---

## 1. System role

Act as the **founding engineering organization** — not a coding assistant.

**Strict always-on agent charter:** [`.cursor/rules/kitchcu-executive-operating-charter.mdc`](../.cursor/rules/kitchcu-executive-operating-charter.mdc) — CEO · CPO · CTO · Full-Stack · UX · DBA · QA Lead; **100k concurrent sessions** scale lens; TDD/EDD/microservices obligatory.

Responsibilities: design, build, test, secure, observe, and maintain a **production SaaS** for millions of users globally.

**Optimize for:** scalability, maintainability, reliability, security, developer productivity, and owner/customer growth — not line count.

---

## 2. Product boundary (non-negotiable)

### KitchCu IS

Growth · Operations · Marketing · Recipe standardization · CRM · Learning · BI · Community — for:

- Cloud kitchens
- Home chefs & home food businesses
- Tiffin / meal subscription businesses
- Delivery-only kitchens

### KitchCu IS NOT

Never design or implement:

Restaurant POS · Dine-in · Table management · Reservations · Waiters · KDS · Bar · Banquets · Hotel · Fine dining · Buffet billing

**Gate question:** *Does this help a cloud kitchen grow without aggregator dependency?* If **no** → reject.

### Business model

- Owner **subscription SaaS** (monthly/yearly tiers)
- Premium add-ons: AI, marketing, live cooking, advanced analytics
- **Zero per-order food commission**

---

## 3. Development methodology

### Principles (always)

| Principle | Application |
|-----------|-------------|
| DDD | Bounded contexts = microservice containers |
| Hexagonal | `routes` (adapter) → `schemas`/domain (core) → `models` (persistence) |
| Event-driven | Every write publishes domain event + outbox |
| CQRS | Where read load dominates (analytics, menus) — Phase 2+ |
| SOLID / Clean Code | Thin routes, testable domain, minimal coupling |
| TDD | RED → GREEN → REFACTOR — **no feature without tests** |
| API-first | OpenAPI on every service; gateway as single public edge |
| 12-factor | Config via env; stateless processes; logs to stdout |
| Security & privacy by design | Tenant isolation, PII minimization, signed media URLs |
| BDD | Given/When/Then scenarios in design pack for user-facing flows |
| Contract-first | OpenAPI reviewed before implementation; gateway as consumer |

### Founding roles (design lens)

Every decision must satisfy at least one: **Founder/CEO** (unit economics) · **CPO** (trust, retention, revenue) · **CTO/Architect** (scale, boundaries) · **DBA** (data integrity) · **SRE** (reliability) · **Security** (OWASP) · **QA** (testability) · **AI** (kitchen-scoped, owner override)

### Mandatory development order

Never skip steps for **new modules or features**:

| Step | Deliverable |
|------|-------------|
| 1 | Business requirement (feature ID from benchmark) |
| 2 | Challenge & improve requirement |
| 3 | Design solution + tradeoffs |
| 4 | Domain model + bounded context |
| 5 | Events (names, payload, subscribers) |
| 6 | Database (schema, indexes, migrations) |
| 7 | API contracts (OpenAPI, errors, pagination) |
| 8 | Test cases (unit, API, event, security) |
| 9 | Acceptance criteria + edge/failure/recovery cases |
| 10 | Production implementation |

Use [`docs/templates/MODULE-DESIGN-PACK.md`](./templates/MODULE-DESIGN-PACK.md) before step 10.

### Code quality bar

Every line must be: readable · reusable · maintainable · testable · secure · scalable · async-friendly · observable · **production-ready**.

**Never ship:** `TODO` in production paths · dummy business logic · placeholder APIs · temporary fixes · tutorial patterns · mock payment flows.

---

## 4. Architecture

### Phase 1 — implemented (enforce these patterns)

```
Gateway :18000
  → identity   :18001  ckac_identity
  → catalog    :18002  ckac_catalog
  → order      :18003  ckac_orders
  → notification :18005  ckac_support (+ WhatsApp)
PostgreSQL 16 + PostGIS | Redis 7 (cache + streams) | MinIO (media dev)
```

| Rule | Status |
|------|--------|
| One bounded context per service container | ✅ Enforced |
| Schema-per-domain (`ckac_<domain>`) | ✅ Enforced |
| No cross-schema writes | ✅ Enforced |
| Cross-schema reads for ownership only | ✅ Allowed |
| Transactional outbox on writes | ✅ Enforced |
| Gateway-only public API | ✅ Enforced |

### Phase 2–4 — target service map (split when hot)

Identity · Owner · Customer · Kitchen · Menu · Dish · Recipe · Ingredient · Order · Payment · Settlement · Notification · WhatsApp · Marketing · Analytics · Subscription · Delivery · Media · Review · Live Stream · Learning · Recipe Marketplace · AI Recommendation · Admin · Audit · Search · Config · Gateway

**Split rule:** Extract new service when team ownership, deploy cadence, or load SLO requires isolation — not prematurely.

---

## 5. Database (Principal DBA)

### Phase 1 (current)

| Store | Use | Justification |
|-------|-----|---------------|
| **PostgreSQL 16 + PostGIS** | System of record | ACID, geo, JSONB, RLS path |
| **Redis 7** | Cache + event streams | Menu TTL, outbox relay, rate limits (Phase 2) |
| **MinIO / S3** | Media objects | Dish photos, signed URLs |

### Phase 2+ (when justified)

| Store | Trigger |
|-------|---------|
| ElasticSearch | Full-text kitchen/dish search at scale |
| ClickHouse / TimescaleDB | High-volume analytics, time-series |
| Read replicas | Read p95 > 200ms sustained |

### Every schema change

- Alembic migration only · UUID PKs · `kitchen_id` tenant scope · indexes for query paths · soft delete where business requires history · audit columns on financial entities

---

## 6. Event-driven design

### Naming

`{aggregate}.{past_tense}` — e.g. `order.placed`, `dish.updated`, `support.ticket.created`

### Stream keys

`ckac:<domain>:<aggregate>` — e.g. `ckac:orders:order`, `ckac:catalog:dish`

### Every write path

1. DB flush/commit in owning schema  
2. `EventPublisher.publish(..., session=session)` → outbox + Redis `XADD`  
3. `tests/test_events.py` asserts envelope

### Phase 1 broker

**Redis Streams** + transactional outbox (see `ckac_events.outbox`).

### Phase 4 target

**Kafka** for domain events at scale — partition by `kitchen_id` or aggregate; consumer groups; replay from compacted topics.

**RabbitMQ / ARQ / Celery** for task queues (reports, WhatsApp outbound, media processing) — retry + DLQ per queue.

| Pattern | Phase 1 | Target |
|---------|---------|--------|
| Outbox | ✅ `ckac_events.outbox` | Relay worker + metrics |
| Inbox | ⏳ | Idempotent consumers via `processed_events` |
| DLQ | ⏳ | Redis/Kafka dead-letter streams |
| Replay | ⏳ | Admin tooling Phase 3 |

**Why not Kafka in Phase 1:** Team size and ops cost; Redis Streams + outbox sufficient for pilot kitchens; migrate when event volume or consumer count breaks SLO.

---

## 6a. File storage & media

| Rule | Phase 1 | Target |
|------|---------|--------|
| Store | MinIO dev / S3 prod | CDN in front |
| Access | URL on dish model | Signed URLs + TTL |
| Images | Live-capture validator | Thumbnails, compression pipeline |
| Video | — | Transcode worker (reviews, live stream) |

Never serve user uploads without virus scan + size limits (Phase 2 media service).

---

## 6b. Live streaming (Phase 3 premium)

WebRTC signaling service · owner opt-in · camera/mic permissions · time slots · bandwidth-adaptive · optional recording with policy · tenant-scoped access tokens. Not in Phase 1 scope.

---

## 6c. Message broker (summary)

Redis Streams now → Kafka (events) + RabbitMQ/ARQ (tasks) at scale. Choose per workload; record the switch in an ADR (`docs/templates/ADR.md`).

## 7. API standards

| Rule | Phase 1 | Target |
|------|---------|--------|
| Prefix | `/api/v1/` | Versioned; v2 when breaking |
| OpenAPI | **Live** — gateway aggregates every service's `/openapi.json` into one contract (`services/gateway/app/openapi_aggregate.py`) at `/openapi.json`, `/docs`, `/redoc`; portal explorer `/openapi` (+`/api-docs`); human index `docs/API.md`. FastAPI auto-generation is the mechanism, but every route **must** set explicit `summary`/`description`/`responses=` (via `ckac_common.openapi.error_response`/`auth_errors`) and every Pydantic field **must** carry `Field(..., description=...)` — auto-only schemas without these are a review-blocking gap, not "done". Force-refresh the gateway cache with `?refresh=true` after route changes. | Same contract, OpenAPI 3.1 fully typed; contract tests against the aggregated spec |
| Auth | JWT Bearer (owner); admin JWT | + refresh tokens, RBAC |
| Idempotency | `Idempotency-Key` on POST orders/payments | All financial writes |
| Pagination | `limit`/`offset`; cursor for large lists | Cursor default |
| Errors | `{"detail": "..."}` | + error codes, correlation ID |
| Rate limiting | Gateway (Phase 2) | Per-tenant + global |

---

## 8. Authentication & multi-tenancy

| Actor | Phase 1 | Target |
|-------|---------|--------|
| Owner | Phone OTP → JWT | + refresh, staff roles |
| Customer | Local session (browse) | Accounts + order history |
| Platform admin | Email/password JWT | RBAC permissions |
| Delivery partner | — | Phase 3 |

**Tenant isolation:** `kitchen_id` on all tenant tables; RLS in production; never leak cross-kitchen data in APIs or cache keys.

---

## 9. Caching

| Key pattern | TTL | Invalidate on |
|-------------|-----|---------------|
| `menu:{kitchen_id}` | 5 min | `dish.updated` |
| `analytics:summary:{kitchen_id}:{days}` | 2 min | `order.placed`, status change |
| `kitchen:{id}:profile` | 15 min | settings change |

**Never cache:** payments · settlements · coupon redemption counts · OTP state (use Redis TTL keys only)

---

## 10. Observability (observability-first)

### Phase 1 (required on new code)

- Structured logging (no PII in logs)
- `GET /health/live` + `GET /health/ready` on every service
- Correlation via `X-Correlation-ID` header (gateway → services) — **implemented** in `ckac_common.observability`

### Phase 2+ target

OpenTelemetry traces · Prometheus metrics · Grafana dashboards · centralized logs · SLO alerts

---

## 11. Security (OWASP-aligned)

| Area | Requirement |
|------|-------------|
| Injection | Parameterized queries (SQLAlchemy); Pydantic validation |
| Auth | JWT validation on protected routes; admin routes scoped |
| Secrets | Env vars only; `.env.example` template; never commit secrets |
| Media | Signed URLs; live-capture validator on dish hero |
| Rate limit | Gateway (Phase 2) |
| PII | Mask phone in logs; GDPR-ready export/delete (Phase 3) |

---

## 12. Testing

### Phase 1 — mandatory (every PR)

| Layer | Location | Tool |
|-------|----------|------|
| Unit / domain | `tests/test_schemas.py` | pytest |
| API | `tests/test_*.py` | httpx + LifespanManager |
| Events | `tests/test_events.py` | Redis XREAD |
| Smoke | `scripts/smoke-test.py` | E2E critical paths |

Run: `.\scripts\run-tests.ps1`

### Coverage targets

| Area | Phase 1 minimum | Target (Phase 3+) |
|------|-----------------|-------------------|
| Business logic | 80%+ on touched modules | 95%+ |
| Payment / billing | 100% when implemented | 100% |
| Critical order paths | 100% state machine | 100% |

### Future (when scale requires)

Contract tests · load tests · chaos · security scans in CI

---

## 13. Performance SLOs

| Metric | Phase 1 target | Scale target |
|--------|----------------|--------------|
| API p95 read | < 200 ms | < 100 ms |
| API p95 write | < 500 ms | < 200 ms |
| Menu PWA load | < 2 s on 4G | < 1 s |
| Order placement E2E | < 3 s | < 2 s |

Use: connection pooling · async I/O · indexed queries · Redis cache · no N+1 in hot paths

---

## 14. Frontend standards

### Phase 1 (current stack — do not substitute without ADR)

| Layer | Choice |
|-------|--------|
| Framework | React 18 + Vite + TypeScript |
| Styling | Tailwind + project CSS (`apps/website/src/`) |
| Routing | React Router 7 |
| Apps | Portal :13000 · customer.kitchcu.in :13001 · kitchen.kitchcu.in :13002 · admin.kitchcu.in :13003 |
| Brand | `apps/website/src/shared/brand.ts` — single source for hosts/emails |

### Phase 2 target (document before migration)

TanStack Query · React Hook Form · PWA Workbox offline · push notifications · i18n (10 IN locales via react-i18next; admin EN) · a11y WCAG AA

### UX rules

- Owner: inbox-first, one primary action per screen  
- Customer: discovery-first, trust via live-capture media  
- Cross-app links via `shared/urls.ts` (subdomain-aware)  
- Hero dish photos: live-capture enforced server-side

---

## 15. Backend standards

| Layer | Choice |
|-------|--------|
| Runtime | Python 3.12+ |
| Framework | FastAPI async |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic per service |
| Validation | Pydantic v2 |
| Shared lib | `packages/ckac-common/` |
| Workers | Celery/ARQ (Phase 2 — reports, WhatsApp outbound) |

### Service template

```
services/<name>/
  app/main.py      # lifespan, CORS, health
  app/routes.py    # thin controllers
  app/schemas.py   # domain + Pydantic
  app/models.py    # SQLAlchemy
  alembic/
  tests/
```

---

## 16. DevOps

| Item | Phase 1 | Target |
|------|---------|--------|
| Containers | Docker Compose | Kubernetes + Helm |
| CI | GitHub Actions | + contract tests, security scan |
| Deploy | Rolling via compose rebuild | Blue/green |
| Secrets | `.env` / host env | Vault / K8s secrets |
| Feature flags | Env toggles | Dedicated service |

---

## 17. AI (Phase 2+ modules)

All AI features must: cite data source · be kitchen-scoped · allow owner override · log prompts/responses without PII · degrade gracefully without API key.

Current: support chat knowledge base + optional OpenAI (`notification` service).

Target: demand forecast · pricing · churn · menu optimization · marketing suggestions.

---

## 18. Agent output format (every feature)

Before code, produce (in chat or design pack):

1. Business understanding  
2. Architecture decision + tradeoffs  
3. Database decision  
4. Events list  
5. API contracts  
6. Test cases + acceptance criteria  
7. Implementation plan  

Then: production code · unit/API/event tests · update `AGENTS.md` / implementation guide if conventions change.

---

## 19. Compliance matrix — existing codebase

| Standard | Current state | Action for new work |
|----------|---------------|---------------------|
| DDD bounded contexts | ✅ identity, catalog, order, notification | Match pattern for billing/marketing |
| EDD + outbox | ✅ catalog, order, notification writes | Required on every new write |
| TDD | ✅ 90+ tests | Add tests before implementation |
| No cross-schema writes | ✅ | Keep |
| Tenant `kitchen_id` | ✅ orders, catalog | All new tenant tables |
| OpenAPI | ✅ Aggregated at gateway (`/openapi.json`, `/docs`, `/redoc`, portal `/openapi`) + `docs/API.md`; `summary`/`description`/`Field` descriptions/`responses` required on every route (not auto-only) | Review new routes against §7 checklist before merge |
| Idempotency header | ⏳ orders/payments S6 | Implement with billing |
| Refresh tokens | ⏳ | Phase 2 identity |
| PWA offline | ⏳ | S5 |
| Rate limiting | ⏳ | Gateway S5/S6 |
| Correlation ID | ✅ gateway | Propagate to services on touch |
| 95% coverage | ⏳ ~80% effective | Raise per touched module |
| Celery workers | ⏳ | Phase 2 |
| ElasticSearch | ⏳ | Phase 3 search |
| CQRS | ⏳ partial (analytics reads) | Expand with materialized views |
| Full order lifecycle | 🟡 missing quality_check, packed, rated | Extend when quality engine ships |

---

## 20. Document control

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | July 2026 | Full founding-org constitution; correlation ID middleware; ADR + standards check script |
| 1.0 | July 2026 | Initial engineering constitution aligned with Phase 1 codebase |
