# Kitchcu — System Benchmark & Architecture Blueprint

**Kitchcu cloud kitchen platform**

| Field | Value |
|-------|-------|
| Version | 2.0 |
| Status | Architecture benchmark — **Phase 1 partial implementation** (see `CKAC-IMPLEMENTATION-GUIDE.md`) |
| Audience | Founders, Product, Engineering, Investors |
| Last updated | July 2026 |
| Companion | `CKAC-COMPLETE-GUIDE.md`, `CKAC-IMPLEMENTATION-GUIDE.md`, `CKAC-COMPLETE-PLANNING-BENCHMARK.md`, `CKAC-PITCH-DECK.pdf` |

---

## Table of Contents

1. [Executive Summary (CEO Lens)](#1-executive-summary-ceo-lens)
2. [Product Vision & Strategy (CPO Lens)](#2-product-vision--strategy-cpo-lens)
3. [Technical Architecture (CTO Lens)](#3-technical-architecture-cto-lens)
4. [Database Architecture (DBA Lens)](#4-database-architecture-dba-lens)
5. [Caching Strategy](#5-caching-strategy)
6. [Docker & Infrastructure](#6-docker--infrastructure)
7. [Feature Catalog & Priority Matrix](#7-feature-catalog--priority-matrix)
8. [Core Domain Flows](#8-core-domain-flows)
9. [API & Integration Design](#9-api--integration-design)
10. [Security, Compliance & Trust](#10-security-compliance--trust)
11. [Scalability & Performance Benchmarks](#11-scalability--performance-benchmarks)
12. [Monetization & Unit Economics](#12-monetization--unit-economics)
13. [Development Phases & Milestones](#13-development-phases--milestones)
14. [Success Metrics (KPIs)](#14-success-metrics-kpis)
15. [Risks & Mitigations](#15-risks--mitigations)
16. [Appendix: Naming, Codes & Conventions](#16-appendix-naming-codes--conventions)
17. [Notification System (App + WhatsApp)](#17-notification-system-app--whatsapp)
18. [Aggregated Payment & Owner Settlement](#18-aggregated-payment--owner-settlement)
19. [Owner Growth Intelligence Engine](#19-owner-growth-intelligence-engine)

---

## 1. Executive Summary (CEO Lens)

### 1.1 What Kitchcu Is

Kitchcu is a **B2B2C cloud kitchen operating system** — not another food aggregator. It gives kitchen owners full control over orders, quality, ingredients, marketing, and customer relationships while giving customers **real-time transparency** into what they eat, how far it travels, and how it was prepared.

### 1.2 The Problem We Solve

| Stakeholder | Pain Today | Kitchcu Answer |
|-------------|-----------|-------------|
| Cloud kitchen owner | Orders scattered across WhatsApp, no revenue insight, inconsistent taste, aggregator commissions | Unified order hub, analytics, ingredient standards, subscription model (no per-order commission) |
| Customer | No trust in photos, unknown quality, opaque delivery | Live-capture dish photos, home-taste ratings, distance-aware delivery, optional live kitchen stream |
| Market | Fragmented local kitchens, no quality benchmark | City/state/national chef rankings, recipe rewards, social sharing |

### 1.3 Strategic Positioning

```
┌─────────────────────────────────────────────────────────────────┐
│  Aggregators (Swiggy/Zomato)     │  Kitchcu                        │
│  ─────────────────────────────   │  ─────────────────────────   │
│  Per-order commission            │  Monthly/yearly subscription │
│  Platform owns customer          │  Owner owns customer CRM       │
│  Stock photos                    │  Live-capture dish media       │
│  Speed-first delivery race       │  Quality-first delivery SLA    │
│  Single kitchen per cart         │  Multi-kitchen cart (unique)   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 Business Model (Simple)

- **Owners:** Monthly / yearly subscription tiers (Basic → Pro → Enterprise with live streaming)
- **Customers:** Free to browse; optional tiffin/monthly meal subscriptions per kitchen
- **No per-order commission** — growth is tied to owner retention, not order tax

### 1.5 North-Star Metrics

1. **Owner GMV managed on platform** (not Kitchcu revenue alone)
2. **Repeat order rate** (customer loyalty proxy)
3. **Dish rating consistency** (quality standardization)
4. **Owner NPS** (would they cancel aggregator dependency?)

### 1.6 CEO Guiding Principle

> **Keep the product simple for the owner on day one.** A kitchen owner should accept a WhatsApp order and see revenue in under 5 minutes of onboarding. Everything else (learning portal, chef rankings, live stream) is growth layers — not blockers.

---

## 2. Product Vision & Strategy (CPO Lens)

### 2.1 Vision Statement

*Empower every cloud kitchen to scale like a brand — with data, quality standards, and direct customer relationships — while giving diners honest, real-time visibility into their food.*

### 2.2 Personas

| Persona | Goals | Primary Surfaces |
|---------|-------|------------------|
| **Owner / Chef** | Track orders, control quality, market dishes, manage subscriptions | Owner PWA (tablet + phone) |
| **Customer** | Discover nearby kitchens, order, track, rate, repeat | Customer PWA |
| **Ops / Staff** | Update order lifecycle, manage inventory alerts | Staff PWA (subset of owner) |
| **Platform Admin** | Moderate content, manage subscriptions, city rankings | Admin console |

### 2.3 PWA-First UI Strategy (CPO + CEO)

**Why PWA, not native apps first:**

| Factor | Rationale |
|--------|-----------|
| Cost | One codebase for Android, iOS, desktop |
| Distribution | WhatsApp links open directly — critical for order capture |
| Offline | Service workers cache menu, last orders, draft orders |
| Updates | No app store delay for menu/price changes |
| Camera | Live dish photo capture works via `getUserMedia` in modern browsers |

**PWA Requirements (Benchmark):**

| Capability | Target |
|------------|--------|
| Lighthouse PWA score | ≥ 90 |
| Install prompt | After 2nd visit or first order |
| Offline | View menu, order history, draft order queue |
| Push notifications | Web Push (owners: new orders; customers: order status) |
| Add to home screen | Branded icons, splash, theme color per kitchen (white-label later) |

**UI Architecture:**

```
┌──────────────────┐     ┌──────────────────┐
│  Customer PWA    │     │  Owner PWA       │
│  (React/Vue)     │     │  (React/Vue)     │
├──────────────────┤     ├──────────────────┤
│ • Discovery map  │     │ • Order inbox    │
│ • Multi-kitchen  │     │ • Revenue dash   │
│   cart           │     │ • Dish manager   │
│ • Live ratings   │     │ • CRM / coupons  │
│ • Subscriptions  │     │ • WhatsApp push  │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         └──────────┬─────────────┘
                    ▼
            API Gateway (FastAPI)
```

### 2.4 Product Principles

1. **WhatsApp-native order intake** — meet owners where they already work
2. **Quality over speed** — owner-set prep/delivery windows, not fake "10 min" promises
3. **Trust through media** — live capture > uploaded stock photos
4. **Owner-owned CRM** — customer list, spend, patterns belong to the kitchen
5. **Progressive complexity** — MVP = orders + menu + reports; v2+ = learning portal, rankings, live stream

### 2.5 Feature Tiering (MoSCoW)

See [Section 7](#7-feature-catalog--priority-matrix) for full matrix. Summary:

| Tier | Scope |
|------|-------|
| **MVP (Phase 1)** | Order capture (WhatsApp + manual), menu CRUD, live photo dishes, basic reports, order lifecycle, COD/UPI, owner subscription billing |
| **Growth (Phase 2)** | Customer PWA discovery, multi-kitchen cart, delivery radius/fees, CRM, coupons, tiffin plans, social share cards |
| **Scale (Phase 3)** | Ingredient mapper, learning portal, recipe rewards, chef rankings, live kitchen stream, suggestion workflow |
| **Enterprise (Phase 4)** | White-label, API for POS integrations, multi-branch owners, advanced analytics ML |

---

## 3. Technical Architecture (CTO Lens)

### 3.1 Architecture Style

**Event-driven microservices** on Python + FastAPI, with clear bounded contexts. Start with a **modular monolith** that can split into services without rewrite.

```
                    ┌─────────────────┐
                    │   CDN / Nginx   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │ Customer │  │  Owner   │  │ Admin Portal │
        │   PWA    │  │   PWA    │  │   (Web)      │
        └────┬─────┘  └────┬─────┘  └──────┬───────┘
             │             │               │
             └─────────────┼───────────────┘
                           ▼
                 ┌─────────────────┐
                 │  API Gateway    │
                 │  (FastAPI)      │
                 │  • Auth (JWT)   │
                 │  • Rate limit   │
                 │  • Routing      │
                 └────────┬────────┘
                          │
     ┌────────────────────┼────────────────────┐
     ▼                    ▼                    ▼
┌─────────┐        ┌─────────────┐      ┌─────────────┐
│ Identity│        │   Catalog   │      │   Order     │
│ Service │        │   Service   │      │   Service   │
└────┬────┘        └──────┬──────┘      └──────┬──────┘
     │                    │                    │
     ▼                    ▼                    ▼
┌─────────┐        ┌─────────────┐      ┌─────────────┐
│ Billing │        │  Analytics  │      │ Notification│
│ Service │        │   Service   │      │   Service   │
└────┬────┘        └──────┬──────┘      └──────┬──────┘
     │                    │                    │
     └────────────────────┼────────────────────┘
                          ▼
                 ┌─────────────────┐
                 │  Message Bus    │
                 │  (Redis Streams │
                 │   → Kafka later)│
                 └────────┬────────┘
                          │
     ┌────────────────────┼────────────────────┐
     ▼                    ▼                    ▼
 PostgreSQL          Redis              Object Storage
 (+ PostGIS)         (cache/queue)      (S3/MinIO)
```

### 3.2 Service Boundaries

| Service | Responsibility | Key Events Published |
|---------|---------------|---------------------|
| **identity** | Users, roles, kitchen registration, auth | `UserRegistered`, `KitchenVerified` |
| **catalog** | Dishes, categories, ingredients, photos, pricing | `DishCreated`, `DishUpdated`, `MenuPublished` |
| **order** | Cart, checkout, lifecycle, multi-kitchen split | `OrderPlaced`, `OrderStatusChanged`, `OrderDelivered` |
| **delivery** | Radius calc, fee rules, tracking links | `DeliveryFeeQuoted`, `TrackingUpdated` |
| **billing** | Owner subscriptions, customer tiffin, payments | `PaymentCaptured`, `SubscriptionRenewed` |
| **analytics** | Reports, patterns, best dishes, CRM aggregates | `ReportGenerated` (internal) |
| **notification** | WhatsApp, SMS, push, email | Consumes order/status events |
| **media** | Live capture upload, transcoding, CDN URLs | `MediaUploaded` |
| **rating** | Dish ratings, home-taste scores, A/V reviews | `RatingSubmitted` |
| **marketing** | Coupons, campaigns, social share assets | `CouponRedeemed`, `CampaignSent` |
| **learning** | Recipe portal, scraping, trials (Phase 3) | `RecipeLearned`, `TrialPromoted` |
| **streaming** | Live prep sessions (Phase 3) | `StreamStarted`, `StreamEnded` |

### 3.3 Event-Driven Patterns

| Pattern | Use Case |
|---------|----------|
| **Event notification** | Order placed → notify owner via WhatsApp |
| **Event-carried state transfer** | Order service publishes full snapshot for analytics |
| **Saga (choreography)** | Multi-kitchen order: reserve inventory → charge → split bills |
| **CQRS (read models)** | Analytics/CRM reads from materialized views, not hot OLTP paths |
| **Outbox pattern** | Guarantee event publish with DB commit |

**Event envelope (standard):**

```json
{
  "event_id": "uuid",
  "event_type": "order.placed",
  "aggregate_id": "ORD-CK001-BILL-20260712-0042",
  "occurred_at": "2026-07-12T06:46:00Z",
  "payload": { },
  "metadata": { "kitchen_id": "CK001", "correlation_id": "..." }
}
```

### 3.4 Tech Stack (Recommended)

| Layer | Choice | Why |
|-------|--------|-----|
| API | **FastAPI** + Pydantic v2 | Async, OpenAPI, Python ecosystem |
| Task workers | **Celery** or **ARQ** + Redis | Background reports, WhatsApp, media |
| Frontend PWA | **React + Vite + TypeScript** | Ecosystem, PWA tooling |
| State | TanStack Query + Zustand | Server cache + local cart |
| Maps | Mapbox or Google Maps API | Distance, discovery |
| Real-time | **WebSockets** (FastAPI) + Redis Pub/Sub | Order status, live stream signaling |
| Live stream | **LiveKit** or **Agora** (managed) | Don't build WebRTC from scratch |
| WhatsApp | **WhatsApp Business Cloud API** | Official, template messages |
| Payments | **Razorpay** (India-first) | UPI, subscriptions, owner payouts |
| Search | **PostgreSQL FTS** → OpenSearch at scale | Dish/kitchen discovery |
| Observability | OpenTelemetry + Prometheus + Grafana | SLO tracking |
| CI/CD | GitHub Actions → Docker → cloud |

### 3.5 Repository Structure (Monorepo Start)

```
ckac/
├── apps/
│   ├── customer-pwa/
│   ├── owner-pwa/
│   └── admin-web/
├── services/
│   ├── gateway/
│   ├── identity/
│   ├── catalog/
│   ├── order/
│   ├── delivery/
│   ├── billing/
│   ├── analytics/
│   ├── notification/
│   ├── media/
│   └── rating/
├── packages/
│   ├── shared-events/      # Event schemas
│   ├── shared-models/      # Pydantic models
│   └── ui-kit/             # Shared components
├── infra/
│   ├── docker/
│   ├── k8s/                # Phase 2+
│   └── terraform/
├── docs/
└── docker-compose.yml
```

### 3.6 Senior Full-Stack Development Standards

| Standard | Benchmark |
|----------|-----------|
| API versioning | `/api/v1/` prefix, breaking changes → v2 |
| Idempotency | `Idempotency-Key` header on POST (orders, payments) |
| Pagination | Cursor-based for order history; offset for admin |
| Error format | RFC 7807 Problem Details |
| Testing | 80% coverage on order/billing paths; contract tests between services |
| Feature flags | LaunchDarkly or open-source Flagsmith for phased rollout |
| Migrations | Alembic (Python); backward-compatible migrations only |

---

## 4. Database Architecture (DBA Lens)

### 4.1 Database Strategy: PostgreSQL as Primary

**Recommendation: PostgreSQL 16+ as the single source of truth**, with extensions and selective auxiliary stores.

| Need | Solution |
|------|----------|
| Relational core (orders, users, billing) | PostgreSQL |
| Geo queries (kitchen discovery, distance) | **PostGIS** extension |
| Full-text search (dishes, kitchens) | `tsvector` + GIN indexes |
| JSON flexibility (order metadata, WhatsApp parse) | `JSONB` columns |
| Time-series analytics (daily revenue) | **TimescaleDB** extension OR materialized views |
| High-volume events / audit log | Separate `events` table partitioned by month |
| Media metadata | PostgreSQL; blobs in object storage |
| Cache | Redis (not a DB replacement) |

**Why not MongoDB-only or micro-DB-per-service at start:**

- Strong ACID needed for orders + payments + inventory
- PostGIS eliminates a separate geo DB
- One operational surface for a small team
- Split read replicas before splitting databases

### 4.2 Multi-Tenancy Model

**Shared database, shared schema, tenant isolation via `kitchen_id`.**

```sql
-- Every tenant-scoped table includes:
kitchen_id UUID NOT NULL REFERENCES kitchens(id),
-- Row Level Security (RLS) enforces isolation:
CREATE POLICY kitchen_isolation ON dishes
  USING (kitchen_id = current_setting('app.kitchen_id')::uuid);
```

| Approach | When |
|----------|------|
| Shared schema + RLS | MVP → 10K kitchens |
| Schema per enterprise tenant | Large franchise clients (Phase 4) |
| Read replicas | Analytics-heavy queries |

### 4.3 Core Entity Relationship (Simplified)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   owners    │──1:N──│  kitchens   │──1:N──│   dishes    │
└─────────────┘       └──────┬──────┘       └──────┬──────┘
                             │                     │
                             │                ┌──────┴──────┐
                             │                │ ingredients │
                             │                │  (recipe)   │
                             │                └─────────────┘
                      ┌──────┴──────┐
                      │  customers  │ (kitchen-scoped CRM)
                      └──────┬──────┘
                             │
┌─────────────┐       ┌──────┴──────┐       ┌─────────────┐
│  cart/order │──N:1──│ order_items │──N:1──│   dishes    │
│  (multi-K)  │       └─────────────┘       └─────────────┘
└──────┬──────┘
       │
┌──────┴──────┐       ┌─────────────┐       ┌─────────────┐
│order_status │       │  payments   │       │   ratings   │
│  history    │       └─────────────┘       └─────────────┘
└─────────────┘
```

### 4.4 Key Tables (Benchmark Schema)

#### Identity & Tenancy

```sql
owners (id, name, phone, email, subscription_plan, subscription_expires_at)
kitchens (id, owner_id, code, name, lat, lng, address, delivery_radius_km,
          free_delivery_radius_km, status, settings_jsonb)
kitchen_staff (kitchen_id, user_id, role)
```

#### Catalog

```sql
dish_categories (id, kitchen_id, name, slug) -- veg, nonveg, beverages...
dishes (id, kitchen_id, category_id, name, price, prep_time_min,
        description, quality_notes, is_active, avg_rating, rating_count)
dish_media (id, dish_id, type, url, captured_at, is_live_capture)
dish_ingredients (dish_id, ingredient_id, quantity, unit) -- recipe standard
ingredients (id, kitchen_id, name, unit, current_stock, low_stock_threshold)
```

#### Orders (Multi-Kitchen Support)

```sql
-- Master order (customer-facing single checkout)
master_orders (
  id, customer_id, total_amount, payment_status,
  created_at
)

-- Sub-order per kitchen (each gets own lifecycle)
orders (
  id, master_order_id, kitchen_id,
  bill_id,  -- e.g. BILL-20260712-0042
  order_code, -- CK001 prefix embedded
  status, delivery_type, delivery_fee, distance_km,
  owner_address_id, customer_address_id,
  lifecycle_jsonb, estimated_ready_at
)

order_items (order_id, dish_id, quantity, unit_price, special_instructions)
order_status_events (order_id, status, note, created_by, created_at)
```

**Order ID format (benchmark):**

```
Master:  MORD-20260712-A7F3
Kitchen: CK001-BILL-20260712-0042
         └code └──── bill id ────┘
```

#### CRM & Marketing

```sql
kitchen_customers (kitchen_id, customer_id, total_spend, order_count,
                   first_order_at, last_order_at, tags_jsonb)
coupons (id, kitchen_id, code, discount_type, value, valid_until, target_customer_ids[])
subscription_plans (id, kitchen_id, name, type, dishes_jsonb, price, billing_cycle)
customer_subscriptions (id, plan_id, customer_id, status, next_billing_date)
```

#### Ratings & Feedback

```sql
dish_ratings (id, dish_id, order_id, customer_id, home_taste_score,
              quality_score, media_url, media_type, is_anonymous, created_at)
dish_suggestions (id, dish_id, customer_id, suggestion_text, status) -- pending/accepted/rejected
```

#### Analytics (Materialized / Partitioned)

```sql
daily_kitchen_stats (kitchen_id, date, order_count, revenue, top_dish_id)
customer_order_patterns (kitchen_id, customer_id, day_of_week, dish_id, frequency)
-- Refreshed by analytics service via events
```

### 4.5 Indexing Strategy (DBA Benchmark)

| Query Pattern | Index |
|---------------|-------|
| Orders by kitchen + date | `(kitchen_id, created_at DESC)` |
| Customer order history | `(customer_id, created_at DESC)` |
| Nearby kitchens | PostGIS `GIST` on `kitchens.geom` |
| Dish search | GIN on `to_tsvector('english', name \|\| ' ' \|\| description)` |
| Active menu | `(kitchen_id, is_active)` partial index |
| Event replay | `(aggregate_id, occurred_at)` on events table |

### 4.6 Partitioning & Archival

| Table | Strategy |
|-------|----------|
| `order_status_events` | Partition by month; archive > 24 months to cold storage |
| `events` (outbox/audit) | Partition by month |
| `dish_ratings` | Keep forever (small rows); aggregate into `dishes.avg_rating` |

### 4.7 Backup & DR Benchmark

| Metric | Target |
|--------|--------|
| RPO (data loss) | ≤ 5 minutes (WAL streaming) |
| RTO (recovery) | ≤ 1 hour |
| Backup frequency | Continuous WAL + daily full snapshot |
| Cross-region replica | Phase 2 (when multi-city) |

### 4.8 Scaling Path

```
Phase 1: Single PostgreSQL instance (8 vCPU, 32GB RAM) — up to ~500 active kitchens
Phase 2: Primary + 1 read replica (analytics, reports)
Phase 3: Connection pooling (PgBouncer), partition hot tables
Phase 4: Citus or shard by region if national scale
```

---

## 5. Caching Strategy

### 5.1 Cache Layers

```
Client (PWA)  →  Service Worker cache (menu, static assets)
                     ↓
CDN           →  Dish images, share card videos
                     ↓
API Gateway   →  Rate limit counters (Redis)
                     ↓
Redis         →  Application cache (see below)
                     ↓
PostgreSQL    →  Source of truth
```

### 5.2 What to Cache (Redis)

| Key Pattern | Data | TTL | Invalidation |
|-------------|------|-----|--------------|
| `menu:{kitchen_id}` | Full active menu JSON | 5 min | On `DishUpdated` event |
| `dish:{dish_id}` | Dish detail + ratings summary | 10 min | On rating/dish update |
| `kitchen:{id}:profile` | Kitchen info, delivery rules | 15 min | On settings change |
| `customer:{id}:orders:recent` | Last 20 orders | 2 min | On new order |
| `analytics:{kitchen_id}:daily:{date}` | Pre-computed daily stats | 1 hour | Nightly refresh + event |
| `geo:nearby:{geohash}` | Kitchen list near point | 3 min | Low — kitchens rarely move |
| `order:{id}:status` | Current lifecycle state | Until terminal state | On status event |
| `session:{token}` | Auth session | 24 hours | Logout |

### 5.3 What NOT to Cache

- Payment transaction state (always read from DB)
- Inventory/stock for ingredient mapper (real-time or short 30s TTL max)
- Coupon redemption counts (atomic Redis INCR or DB row lock)

### 5.4 Cache-Aside Pattern (Standard)

```python
async def get_menu(kitchen_id: UUID) -> Menu:
    cached = await redis.get(f"menu:{kitchen_id}")
    if cached:
        return Menu.parse_raw(cached)
    menu = await db.fetch_menu(kitchen_id)
    await redis.setex(f"menu:{kitchen_id}", 300, menu.json())
    return menu
```

### 5.5 Order History Caching

| Scenario | Strategy |
|----------|----------|
| Owner dashboard "today's orders" | Redis list, append on event, TTL 24h |
| Customer "my orders" | Cache recent page; paginate from DB for older |
| Revenue report (monthly) | Pre-aggregate into `daily_kitchen_stats`; cache result |
| Best performing dishes | Nightly batch + cache 6 hours |

---

## 6. Docker & Infrastructure

### 6.1 Local Development (docker-compose)

```yaml
# Benchmark stack
services:
  postgres:      # PostgreSQL 16 + PostGIS
  redis:         # Cache + Celery broker
  minio:         # S3-compatible media storage
  api-gateway:
  identity:
  catalog:
  order:
  notification-worker:
  analytics-worker:
  customer-pwa:  # Vite dev server or nginx static
  owner-pwa:
  mailhog:       # Dev email
  redis-commander: # Optional debug UI
```

### 6.2 Production Target (Phase 2+)

| Component | Recommendation |
|-----------|---------------|
| Compute | AWS ECS Fargate or DigitalOcean App Platform (start simple) |
| DB | AWS RDS PostgreSQL / Supabase / Neon (managed) |
| Redis | ElastiCache / Upstash |
| Media | S3 + CloudFront |
| Secrets | AWS Secrets Manager / Doppler |
| Orchestration | Docker → Kubernetes when > 15 services |

### 6.3 Environment Parity

| Env | Purpose |
|-----|---------|
| `local` | docker-compose, seed data |
| `staging` | Full stack, WhatsApp sandbox, Razorpay test |
| `production` | Multi-AZ, autoscaling |

### 6.4 Health Checks

Every service exposes:

```
GET /health/live   → process up
GET /health/ready  → DB + Redis connected
```

---

## 7. Feature Catalog & Priority Matrix

| # | Feature | Phase | Priority | Complexity |
|---|---------|-------|----------|------------|
| 1 | WhatsApp order capture (chat parse + manual) | 1 | Must | High |
| 2 | Manual/custom order input | 1 | Must | Low |
| 3 | Dish CRUD with live photo capture | 1 | Must | Medium |
| 4 | Categories (veg, nonveg, drinks...) | 1 | Must | Low |
| 5 | Order lifecycle + customer notifications | 1 | Must | Medium |
| 6 | Revenue report (daily/weekly/monthly) | 1 | Must | Medium |
| 7 | Order history tracker | 1 | Must | Low |
| 8 | COD + UPI / payment gateway | 1 | Must | High |
| 9 | Owner subscription billing | 1 | Must | Medium |
| 10 | Best performing dishes report | 2 | Should | Medium |
| 11 | Customer order pattern analytics | 2 | Should | Medium |
| 12 | Delivery radius + fee rules | 2 | Should | Medium |
| 13 | Address mapping (lat/lng distance) | 2 | Should | Medium |
| 14 | Customer discovery (distance-wise kitchens) | 2 | Should | High |
| 15 | Multi-kitchen single checkout | 2 | Should | High |
| 16 | Customer ratings (home taste + quality) | 2 | Should | Medium |
| 17 | A/V experience reviews (anonymous) | 2 | Could | High |
| 18 | Repeat order | 2 | Should | Low |
| 19 | Owner CRM (spend, patterns) | 2 | Should | Medium |
| 20 | Custom coupons | 2 | Should | Medium |
| 21 | Customer tiffin subscriptions | 2 | Should | High |
| 22 | Owner custom meal plans | 2 | Should | Medium |
| 23 | Daily menu WhatsApp push | 2 | Should | Medium |
| 24 | Special event menus | 2 | Could | Low |
| 25 | Custom cooking requests on orders | 2 | Should | Low |
| 26 | Social share (WhatsApp status, Insta story cards) | 2 | Could | Medium |
| 27 | Ingredient balance mapper | 3 | Should | High |
| 28 | Recipe suggestions to chef (accept/reject) | 3 | Could | Medium |
| 29 | Learning portal + dish scraping | 3 | Could | High |
| 30 | Trial/sample promotion workflow | 3 | Could | High |
| 31 | Share recipe + rewards | 3 | Could | High |
| 32 | Best cloud chef rankings | 3 | Could | High |
| 33 | Live food preparation streaming | 3 | Could | Very High |
| 34 | Live prep customer package filter | 3 | Could | Medium |
| 35 | Per-owner payment / payout split | 2 | Should | Medium |
| 36 | Delivery tracking link + interval updates | 2 | Should | Medium |
| 37 | Targeted marketing / special pricing | 2 | Should | Medium |
| 38 | Owner growth suggestions (seasonal, patterns) | 2 | Should | Medium |
| 39 | App push + WhatsApp dual notifications | 1 | Must | Medium |
| 40 | Aggregated payment + multi-owner split | 2 | Must | High |

---

## 8. Core Domain Flows

### 8.1 Order Intake (WhatsApp)

```
Customer WhatsApp message
        │
        ▼
WhatsApp Business API webhook
        │
        ▼
Notification Service → parse message (NLP rules + manual fallback)
        │
        ├── Matched dishes → draft order created
        └── Unmatched → owner inbox for manual mapping
        │
        ▼
Owner confirms / edits → OrderPlaced event
        │
        ▼
Customer receives confirmation link (PWA tracking page)
```

**Parse strategy (keep simple):**

1. Rule-based: dish names, quantities, keywords ("2 biryani", "no onion")
2. Owner-defined shortcuts ("A" = today's special thali)
3. Always allow manual override — never block on AI

### 8.2 Order Lifecycle (Quality-First)

```
┌──────────┐   ┌────────────┐   ┌─────────────┐   ┌───────────┐   ┌───────────┐
│ Received │ → │ Accepted   │ → │ Preparing   │ → │ Ready     │ → │ Out for   │
│          │   │ (+ prep ETA│   │ (optional   │   │           │   │ delivery  │
└──────────┘   │  set)      │   │  live stream│   └───────────┘   └─────┬─────┘
               └────────────┘   └─────────────┘                         │
                                                                         ▼
                                                                  ┌───────────┐
                                                                  │ Delivered │
                                                                  └───────────┘
```

- Each transition → WhatsApp/push update to customer
- Owner sets **prep time per dish** — system sums for ETA, not competitor-style fake timers
- Configurable notification intervals (e.g., every 5 min during "Preparing")

### 8.3 Multi-Kitchen Checkout

```
Customer cart:
  [Kitchen A: 2 dishes] + [Kitchen B: 1 dish]
              │
              ▼
       master_orders (1 payment)
              │
      ┌───────┴───────┐
      ▼               ▼
  order (CKA…)    order (CKB…)
  separate lifecycle, separate bills
              │
              ▼
  Customer sees unified receipt + per-kitchen tracking tabs
```

### 8.4 Delivery Fee Decision

```
1. Compute distance (PostGIS) owner ↔ customer
2. If ≤ free_delivery_radius → fee = 0
3. If > radius → calculate fee (owner rules: flat/per-km)
4. Present to customer at checkout
5. If customer denies:
   a. Owner can cancel
   b. Owner can waive (min order amount rule)
   c. Customer switches to self-pickup
```

### 8.5 Rating Flow (Home Taste Benchmark)

| Score | Meaning |
|-------|---------|
| Home taste (1–5) | "Tastes like authentic home cooking" |
| Quality (1–5) | Freshness, portion, packaging |
| Optional A/V | 15–30 sec clip, face optional, voice anonymized |

Aggregated on dish page without customer identity.

### 8.6 Ingredient Balance Mapper

```
Dish "Butter Chicken" standard:
  • Garam masala: 10g
  • Lal mirch: 1g
  • Haldi: 1g
  • ...

On order × quantity → deduct from ingredient stock
Low stock → alert owner before accepting order
```

### 8.7 Learning Portal & Trial Loop (Phase 3)

```
Scrape/curate recipes by category
        → Owner marks "learned new dish"
        → Creates trial batch (small qty)
        → Promote free/sample to selected regulars
        → Collect ratings
        → If benchmark met → add to official menu
```

### 8.8 Best Cloud Chef Ranking (Benchmark Formula)

```
Monthly score =
  (0.30 × normalized_avg_dish_rating) +
  (0.20 × recipe_shares_appreciations) +
  (0.25 × customer_review_volume × quality) +
  (0.15 × repeat_order_rate) +
  (0.10 × community_votes)

Levels: City → State → National
Anti-gaming: min order threshold, verified reviews only, anomaly detection
```

---

## 9. API & Integration Design

### 9.1 External Integrations

| Integration | Purpose | Phase |
|-------------|---------|-------|
| WhatsApp Business Cloud API | Order intake, status updates, menu push | 1 |
| Razorpay | UPI, cards, subscriptions, owner payouts | 1 |
| Mapbox/Google Maps | Geocoding, distance, discovery map | 2 |
| LiveKit/Agora | Live kitchen streaming | 3 |
| FFmpeg (self-hosted) | Social share video generation | 2 |
| Optional: Twilio | SMS fallback | 2 |

### 9.2 Key API Groups (REST + WebSocket)

```
POST   /api/v1/orders                    # Create order
PATCH  /api/v1/orders/{id}/status        # Lifecycle update
GET    /api/v1/kitchens/nearby           # Discovery (?lat=&lng=&radius=)
GET    /api/v1/kitchens/{id}/menu        # Cached menu
POST   /api/v1/cart/checkout             # Multi-kitchen checkout
GET    /api/v1/analytics/revenue         # Owner reports
POST   /api/v1/dishes/{id}/ratings       # Submit rating + media
POST   /api/v1/media/capture             # Live photo upload
WS     /ws/orders/{id}                   # Real-time status
WS     /ws/stream/{kitchen_id}           # Live prep (Phase 3)
POST   /api/v1/webhooks/whatsapp         # Inbound messages
POST   /api/v1/webhooks/razorpay         # Payment callbacks
```

### 9.3 Owner Scanner (Direct UPI)

- Generate dynamic QR per order (Razorpay UPI intent)
- Owner app listens for payment confirmation webhook
- Fallback: manual "mark paid" with audit log

---

## 10. Security, Compliance & Trust

| Area | Benchmark |
|------|-----------|
| Auth | JWT access (15 min) + refresh token; OTP for customers |
| Tenant isolation | PostgreSQL RLS on all kitchen-scoped tables |
| Media | Signed URLs, expire in 1h; virus scan on upload |
| PII | Encrypt phone/email at rest; mask in logs |
| Payments | PCI via Razorpay (no card data on Kitchcu servers) |
| Ratings A/V | Moderation queue for reported content |
| Live stream | Owner opt-in per session; customer package gate |
| GDPR-ish | Data export + delete for customers (India DPDP aligned) |
| Rate limiting | 100 req/min customer; 500 req/min owner API |

---

## 11. Scalability & Performance Benchmarks

### 11.1 SLO Targets (Production)

| Metric | Target |
|--------|--------|
| API p95 latency (read) | < 200 ms |
| API p95 latency (write/order) | < 500 ms |
| Menu page load (PWA) | < 2 s on 4G |
| Order placement E2E | < 3 s |
| WhatsApp status notification | < 10 s from event |
| Uptime | 99.9% (Phase 2+) |
| Concurrent orders (peak) | 1,000/min platform-wide (Phase 3 design) |

### 11.2 Horizontal Scaling Triggers

| Signal | Action |
|--------|--------|
| API CPU > 70% sustained | Add gateway/service replicas |
| Redis memory > 80% | Increase cluster; review TTLs |
| PG connections exhausted | PgBouncer; read replica for reports |
| Notification backlog > 1 min | Scale worker pods |
| Media upload queue > 5 min | Scale media workers |

### 11.3 Load Test Scenarios (Pre-Launch)

1. 500 concurrent customers browsing menus
2. 100 orders/min spike (lunch hour simulation)
3. Multi-kitchen checkout with 3 kitchens in one cart
4. WhatsApp webhook burst (100 messages/min)

---

## 12. Monetization & Unit Economics

### 12.1 Owner Subscription Tiers (Benchmark)

| Tier | Monthly | Yearly | Includes |
|------|---------|--------|----------|
| **Starter** | ₹499 | ₹4,999 | 1 kitchen, 50 dishes, basic reports, WhatsApp orders |
| **Pro** | ₹1,499 | ₹14,999 | CRM, coupons, tiffin plans, marketing, multi-staff |
| **Enterprise** | ₹3,999 | ₹39,999 | Live streaming, API access, priority support, branches |

### 12.2 Customer Revenue (Optional, per kitchen)

- Tiffin subscriptions (kitchen-defined pricing — Kitchcu takes 0% commission)
- Live prep premium package (platform-level add-on: e.g., ₹99/mo to filter live kitchens)

### 12.3 Unit Economics Target

| Metric | Year 1 Goal |
|--------|-------------|
| CAC (owner) | < ₹2,000 |
| Owner LTV | > ₹18,000 (12+ month retention) |
| LTV:CAC | > 3:1 |
| Gross margin | > 75% (SaaS) |

---

## 13. Development Phases & Milestones

### Phase 1 — Foundation (Months 1–3): "Owner Can Run Kitchen"

**Goal:** 10 pilot kitchens processing real orders daily.

| Milestone | Deliverable |
|-----------|-------------|
| M1.1 | Docker dev stack, CI, identity, kitchen onboarding |
| M1.2 | Catalog service + live photo upload |
| M1.3 | Order service + manual + WhatsApp intake |
| M1.4 | Order lifecycle + notifications |
| M1.5 | Owner PWA: inbox, menu, basic revenue report |
| M1.6 | Razorpay owner subscription + COD/UPI orders |
| M1.7 | Pilot launch |

### Phase 2 — Growth (Months 4–6): "Customer Discovery & CRM"

| Milestone | Deliverable |
|-----------|-------------|
| M2.1 | Customer PWA + geo discovery |
| M2.2 | Multi-kitchen cart + split billing |
| M2.3 | Delivery radius, fees, tracking links |
| M2.4 | Ratings + repeat order |
| M2.5 | CRM, coupons, tiffin plans |
| M2.6 | Analytics: best dishes, customer patterns |
| M2.7 | Social share cards, daily menu push |

### Phase 3 — Differentiation (Months 7–10): "Quality & Community"

| Milestone | Deliverable |
|-----------|-------------|
| M3.1 | Ingredient mapper + stock alerts |
| M3.2 | Recipe suggestions workflow |
| M3.3 | Learning portal MVP |
| M3.4 | Recipe share + rewards |
| M3.5 | Chef rankings (city) |
| M3.6 | Live kitchen streaming beta |

### Phase 4 — Scale (Months 11–12+): "National Platform"

- State/national rankings
- Multi-branch owners
- ML demand forecasting
- POS / aggregator export APIs
- White-label for franchises

---

## 14. Success Metrics (KPIs)

### 14.1 Platform KPIs

| KPI | MVP Target | 12-Month Target |
|-----|------------|-----------------|
| Active kitchens | 10 | 500 |
| Orders/day (platform) | 50 | 5,000 |
| Owner retention (monthly) | 80% | 90% |
| Customer repeat rate (30-day) | 25% | 40% |
| Avg dish rating | 3.8+ | 4.2+ |
| WhatsApp order parse success | 60% | 85% |
| Report generation time | < 5 s | < 2 s |

### 14.2 Owner KPIs (In-App Dashboard)

- Daily / weekly / monthly revenue
- AOV (average order value)
- Top 5 dishes and combinations
- Customer retention cohort
- Delivery vs pickup ratio
- Coupon redemption rate
- Subscription MRR (tiffin)

### 14.3 Customer KPIs

- Time to discover kitchen (< 30 s)
- Order completion rate
- Rating submission rate (target 15%+ of delivered orders)

---

## 15. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WhatsApp API policy changes | Order intake breaks | Manual input always available; SMS fallback |
| Live stream complexity | Delays Phase 3 | Use managed provider (LiveKit); owner opt-in only |
| Multi-kitchen checkout disputes | Payment/refund mess | Clear per-kitchen refund policy; separate sub-order IDs |
| Rating fraud | Trust erosion | Verified purchase only; anomaly detection |
| Scope creep | Never launch | Strict MoSCoW; Phase 1 is sacred |
| Owner onboarding friction | Low adoption | WhatsApp-first; 5-min setup; import menu via photo OCR later |
| Ingredient tracking burden | Owner ignores feature | Optional Phase 3; start with top 10 dishes only |

---

## 17. Notification System (App + WhatsApp)

### 17.1 Dual-Channel Architecture

Every customer-facing and owner-critical event routes through `notification-service` with channel selection based on user preferences and urgency.

| Event | WhatsApp | App Push | SMS Fallback |
|-------|----------|----------|--------------|
| Order confirmed | Yes | Yes | Phase 2 |
| Lifecycle status change | Yes | Yes | No |
| Interval progress (preparing/delivery) | Yes | Yes | No |
| Daily menu blast | Yes | Optional | No |
| Coupon / promo | Yes | Yes | No |
| Payment receipt | Yes | Yes | No |
| Rating request post-delivery | Yes | Yes | No |
| Owner growth suggestion | No | Yes | No |
| Trial sample invite | Yes | Yes | No |

### 17.2 Implementation

- **WhatsApp:** Meta Cloud API with pre-approved templates
- **App Push:** Web Push API (VAPID) via service worker in both PWAs
- **Interval notifications:** Every N minutes during preparing/delivery with tracking link
- **Tracking page:** PWA at `/t/{token}` with WebSocket for instant updates

---

## 18. Aggregated Payment & Owner Settlement

Multi-kitchen cart requires **one customer payment** split across owner accounts via **Razorpay Route**. Each kitchen onboarded with `linked_account_id`. Settlement saga creates per-kitchen transfer on `payment.captured`. Partial refunds at sub-order level.

---

## 19. Owner Growth Intelligence Engine

Actionable suggestions (seasonal menus, win-back coupons, combo mining, peak staffing, delivery zone optimization) generated nightly by `growth-service` from analytics aggregates. One-tap owner actions: create coupon, event menu, WhatsApp blast.

---

## 16. Appendix: Naming, Codes & Conventions

### 16.1 Kitchen Code

- Assigned at registration: `CK` + 3-digit city code + 3-digit sequence
- Example: `CKPNQ001` (Pune kitchen #1)

### 16.2 Bill ID Format

```
{BILL}-{YYYYMMDD}-{SEQ}
Example: BILL-20260712-0042
Full order ref: CKPNQ001-BILL-20260712-0042
```

### 16.3 Dish Categories (Default Seed)

`veg`, `non_veg`, `vegan`, `beverages`, `hot_drinks`, `cold_drinks`, `snacks`, `desserts`, `combos`, `seasonal_special`

### 16.4 Order Status Enum

`received` → `accepted` → `preparing` → `ready` → `out_for_delivery` → `delivered` → `cancelled`

### 16.5 Subscription Status Enum

`active`, `paused`, `cancelled`, `past_due`, `expired`

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-12 | Kitchcu Founding Team | Initial benchmark document |

---

> **Next recommended artifacts:**
> 1. `docs/ADR/` — Architecture Decision Records (PostgreSQL choice, PWA, event bus)
> 2. `docs/API/openapi.yaml` — Contract-first API spec
> 3. `infra/docker/docker-compose.yml` — Dev environment
> 4. `docs/MVP-SCOPE.md` — Phase 1 sprint backlog derived from this benchmark
