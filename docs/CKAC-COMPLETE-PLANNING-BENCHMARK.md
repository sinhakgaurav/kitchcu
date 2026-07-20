# Kitchcu — Complete Planning & Feature Benchmark (v2.0)

**Kitchcu cloud kitchen platform**

| Field | Value |
|-------|-------|
| Version | 2.0 — Complete Planning Edition |
| Status | Feature spec complete — **S1–S4 backend + S5 PWAs/portal/analytics/support partial** (see `CKAC-IMPLEMENTATION-GUIDE.md`) |
| Audience | CEO, CPO, CTO, Engineering, DBA, Investors |
| Companion docs | `CKAC-IMPLEMENTATION-GUIDE.md`, `CKAC-SYSTEM-BENCHMARK.md`, `CKAC-PITCH-DECK.pdf` |
| Last updated | July 2026 |

---

## Document Purpose

This document is the **master planning benchmark**. Every feature from the product vision is mapped to:

- Business rationale (CEO/CPO)
- User stories & acceptance criteria (CPO)
- Technical design (CTO / Senior Full-Stack)
- Data model & queries (DBA)
- Cache & event design
- Phase, priority, dependencies, and complexity

**Nothing is skipped.** Use this for sprint planning, investor diligence, and architecture reviews.

---

## Table of Contents

**Part A — Strategy & Architecture**
1. [Executive Vision (CEO)](#1-executive-vision-ceo)
2. [Product Strategy (CPO)](#2-product-strategy-cpo)
3. [PWA UI Blueprint (CPO + CEO)](#3-pwa-ui-blueprint-cpo--ceo)
4. [Technical Architecture (CTO)](#4-technical-architecture-cto)
5. [Database Architecture (DBA)](#5-database-architecture-dba)
6. [Caching Strategy](#6-caching-strategy)
7. [Docker & Scalable Infrastructure](#7-docker--scalable-infrastructure)
8. [Notification System (App + WhatsApp)](#8-notification-system-app--whatsapp)
9. [Payment Gateway & Owner Settlement](#9-payment-gateway--owner-settlement)
10. [Owner Growth Intelligence Engine](#10-owner-growth-intelligence-engine)

**Part B — Complete Feature Specifications**
11. [Feature Index (All 45 Features)](#11-feature-index-all-45-features)
12. [Order Management Features (F01–F06)](#12-order-management-features-f01f06)
13. [Analytics & Reporting (F07–F12)](#13-analytics--reporting-f07f12)
14. [Catalog & Quality (F13–F20)](#14-catalog--quality-f13f20)
15. [Learning, Community & Rankings (F21–F26)](#15-learning-community--rankings-f21f26)
16. [Marketing & Social (F27–F33)](#16-marketing--social-f27f33)
17. [Delivery & Logistics (F34–F40)](#17-delivery--logistics-f34f40)
18. [Customer Experience (F41–F45)](#18-customer-experience-f41f45)
19. [Live Streaming (F46–F48)](#19-live-streaming-f46f48)

**Part C — Execution**
20. [Cross-Feature Dependency Map](#20-cross-feature-dependency-map)
21. [Development Phases & Sprint Backlog](#21-development-phases--sprint-backlog)
22. [KPIs, SLOs & Benchmarks](#22-kpis-slos--benchmarks)
23. [Risks & Governance](#23-risks--governance)

---

# Part A — Strategy & Architecture

## 1. Executive Vision (CEO)

### 1.1 Mission

Help cloud kitchen owners **scale, track, enhance, and manage** their operations while giving customers a **real-time view of ingredients, quality, and trust** — powered by a rating aggregator built on authentic home-taste benchmarks.

### 1.2 Market Opportunity (India-first)

| Metric | Estimate |
|--------|----------|
| Cloud / home kitchens (India) | 500K+ informal, 50K+ semi-formal |
| Food delivery GMV | ₹2.5L Cr+ annually |
| Aggregator commission pain | 18–30% per order |
| WhatsApp as order channel | 70%+ of small kitchens |

**Kitchcu wedge:** Own the kitchen's operating stack before they need an aggregator. Subscription SaaS, not commission tax.

### 1.3 Value Proposition Matrix

| Stakeholder | Core Promise | Proof Point |
|-------------|-------------|-------------|
| Owner | Run entire kitchen from one PWA | WhatsApp order → revenue report in same day |
| Owner | Own your customers | CRM with spend, patterns, targeted pricing |
| Owner | Consistent quality at scale | Ingredient mapper + home-taste ratings |
| Customer | Trust what you order | Live-capture photos, anonymous A/V reviews |
| Customer | Fair delivery | Distance-aware fees, quality-first ETA |
| Platform | Community moat | Chef rankings, recipe rewards, learning portal |

### 1.4 Business Model

| Revenue Stream | Model | Kitchcu Take |
|----------------|-------|-----------|
| Owner subscription | Monthly / Yearly tiers | 100% |
| Customer tiffin plans | Kitchen-defined pricing | 0% commission |
| Live prep premium (optional) | Customer add-on package | 100% |
| Payment gateway | Pass-through; optional platform fee on split checkout | Configurable (0% at launch) |

**Explicit:** No per-order commission on food GMV.

### 1.5 Competitive Moat (5 Layers)

1. **WhatsApp-native ops** — meets owners where they work
2. **Quality data graph** — home-taste ratings + ingredient standards
3. **Owner CRM lock-in** — customer history cannot be exported easily from aggregators
4. **Multi-kitchen cart** — unique customer convenience
5. **Community & rankings** — network effects at city/state/national level

### 1.6 CEO Simplicity Mandate

| Rule | Implementation |
|------|----------------|
| Day-1 value | Owner processes first order within 5 minutes of signup |
| Progressive disclosure | Advanced features hidden until kitchen has 50+ orders |
| No feature without metric | Every Phase 2+ feature tied to a KPI |
| One primary action per screen | Owner inbox, Customer discover |

---

## 2. Product Strategy (CPO)

### 2.1 Product Principles

1. **Truth in food media** — live capture required for menu photos; uploaded gallery secondary
2. **Quality over speed** — owner-defined prep/delivery windows
3. **Owner sovereignty** — customer relationships belong to the kitchen
4. **Transparent delivery economics** — lat/long distance visible to both parties
5. **Earned trust** — ratings only from verified orders

### 2.2 Personas (Detailed)

#### Persona A: Raj — Cloud Kitchen Owner (Primary)

| Attribute | Detail |
|-----------|--------|
| Age | 32–45 |
| Setup | 1–2 kitchen units, 2–5 staff |
| Current tools | WhatsApp, Excel, maybe PetPooja |
| Pain | Orders lost in chat, no analytics, inconsistent taste batch-to-batch |
| Goal | 2× revenue in 12 months without aggregator dependency |
| Success | "I know my best dish, my best customer, and my daily profit" |

#### Persona B: Priya — Regular Customer

| Attribute | Detail |
|-----------|--------|
| Age | 25–40 |
| Behavior | Orders lunch 3×/week, trusts home-style food |
| Pain | Stock photos lie, doesn't know real distance/kitchen hygiene |
| Goal | Reliable tasty food, fair price, optional tiffin |
| Success | "I re-order my usual in 2 taps and see real reviews" |

#### Persona C: Admin — Platform Operator

| Attribute | Detail |
|-----------|--------|
| Role | Moderation, subscription billing, ranking integrity |
| Goal | Keep platform quality high, prevent ranking fraud |

### 2.3 User Journey Maps

#### Owner — First Week

```
Day 0: Sign up → OTP → Kitchen profile → Set location
Day 0: Add 5 dishes with live photos → Publish menu
Day 1: Connect WhatsApp Business → First WhatsApp order parsed
Day 1: Mark lifecycle → Customer gets tracking link
Day 3: View first revenue report
Day 7: Identify top dish → Send daily menu push to 10 customers
```

#### Customer — First Order

```
Open PWA link / Discover nearby kitchens (map)
→ Filter by distance, rating, live-prep (if subscribed)
→ Add dishes (possibly from 2 kitchens)
→ See delivery fee breakdown → Pay UPI or COD
→ Track lifecycle via link + WhatsApp
→ Rate home taste + optional 15s video
→ Repeat order next week
```

### 2.4 Information Architecture (Both PWAs)

**Owner PWA — Primary Navigation**

```
Home (Inbox + Today's Stats)
├── Orders
│   ├── Active
│   ├── History
│   └── WhatsApp Drafts
├── Menu
│   ├── Dishes
│   ├── Categories
│   ├── Ingredients
│   └── Event Menus
├── Customers (CRM)
├── Analytics
│   ├── Revenue
│   ├── Best Dishes
│   ├── Patterns
│   └── Growth Suggestions ★
├── Marketing
│   ├── Coupons
│   ├── Daily Push
│   └── Special Pricing
├── Subscriptions (Tiffin Plans)
├── Payments & Scanner
├── Live Stream Control
└── Settings
```

**Customer PWA — Primary Navigation**

```
Discover (Map + List)
├── Kitchen Profile
├── Cart (Multi-Kitchen)
├── Orders & Tracking
├── Subscriptions
├── Ratings & History
├── Live Kitchens (Premium)
└── Profile & Addresses
```

---

## 3. PWA UI Blueprint (CPO + CEO)

### 3.1 Why PWA (Decision Record)

| Criterion | PWA | Native App | Winner |
|-----------|-----|------------|--------|
| Time to market | 1 codebase | 2–3 codebases | PWA |
| WhatsApp link → app | Instant URL | App store friction | PWA |
| Live camera capture | Supported | Supported | Tie |
| Push notifications | Web Push | FCM/APNs | Native slight edge; PWA sufficient |
| Offline menu/history | Service Worker | Local DB | Tie |
| Cost for startup | Low | High | PWA |

**Decision:** PWA for Phase 1–3. Wrap with TWA (Trusted Web Activity) for Play Store in Phase 4 if needed.

### 3.2 PWA Technical Requirements

| Requirement | Benchmark |
|-------------|-----------|
| Framework | React 18 + Vite + TypeScript |
| UI Library | Tailwind + shadcn/ui (owner) / custom warm palette (customer) |
| State | TanStack Query (server) + Zustand (cart, drafts) |
| Offline | Workbox — cache menu, order history, draft orders |
| Camera | MediaDevices API — enforce live capture flag in EXIF/metadata |
| Maps | Mapbox GL JS or Google Maps embed |
| Install | `beforeinstallprompt` after 2nd session |
| Lighthouse | Performance ≥ 85, PWA ≥ 90, Accessibility ≥ 90 |

### 3.3 Live Photo Capture (Anti-False-Commitment)

**CPO requirement:** Menu photos must be captured in-app, not uploaded from gallery (gallery allowed only for "kitchen ambiance" photos).

**Technical enforcement:**

```typescript
// Capture metadata sent with upload
{
  "source": "live_capture",      // required for dish hero image
  "captured_at": "ISO8601",
  "device_id_hash": "...",
  "gps_optional": { "lat", "lng" }
}
```

Backend rejects dish publish if hero image lacks `live_capture` flag (owner can override after warning for legacy import).

### 3.4 Responsive Layouts

| Device | Owner | Customer |
|--------|-------|----------|
| Phone | Single column inbox | Map-first discover |
| Tablet | Split: list + detail | Grid menu |
| Desktop | Full dashboard | Optional; not primary |

### 3.5 Accessibility & Localization

- Hindi + English + major IN regional languages at launch (i18n via react-i18next; 10 locales shipped — see `docs/design/PLATFORM-I18N-DESIGN.md`)
- Minimum touch target 44px
- High contrast mode for kitchen (greasy hands, bright light)

---

## 4. Technical Architecture (CTO)

### 4.1 Architecture Decision: Event-Driven Microservices

**Strict adherence:** Python 3.12+, FastAPI, async-first, domain-driven service boundaries.

**Phase 1 deployment:** Modular monolith with internal event bus (Redis Streams).  
**Phase 2+ deployment:** Extract hot services (order, notification, billing) to independent containers.

### 4.2 Service Catalog

| Service | Port | DB Schema | Publishes | Consumes |
|---------|------|-----------|-----------|----------|
| gateway | 8000 | — | — | all |
| identity | 8001 | identity | UserRegistered, KitchenCreated | — |
| catalog | 8002 | catalog | DishCreated, MenuPublished | — |
| order | 8003 | orders | OrderPlaced, StatusChanged | PaymentCaptured |
| delivery | 8004 | delivery | FeeQuoted, TrackingUpdated | OrderPlaced |
| billing | 8005 | billing | PaymentCaptured, SubscriptionRenewed | OrderPlaced |
| analytics | 8006 | analytics | ReportReady | all order/catalog events |
| notification | 8007 | notification | — | all customer-facing events |
| media | 8008 | media | MediaProcessed | DishCreated |
| rating | 8009 | ratings | RatingSubmitted | OrderDelivered |
| marketing | 8010 | marketing | CampaignSent, CouponRedeemed | — |
| learning | 8011 | learning | RecipeLearned, TrialStarted | — |
| streaming | 8012 | streaming | StreamStarted | — |
| growth | 8013 | growth | SuggestionGenerated | analytics events |

### 4.3 Event Bus Specification

**Transport:** Redis Streams (Phase 1) → Apache Kafka (Phase 3, > 5K orders/day)

**Stream naming:** `ckac.{domain}.{event}` e.g. `ckac.order.placed`

**Standard envelope:**

```json
{
  "event_id": "uuid-v4",
  "event_type": "order.placed",
  "schema_version": "1.0",
  "aggregate_type": "order",
  "aggregate_id": "CKPNQ001-BILL-20260712-0042",
  "occurred_at": "2026-07-12T07:00:00Z",
  "producer": "order-service",
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null",
  "payload": {}
}
```

**Reliability patterns:**

| Pattern | Use |
|---------|-----|
| Transactional Outbox | Every write + event in same PG transaction |
| Idempotent consumers | `event_id` dedup table |
| Dead letter queue | Failed events after 3 retries |
| Saga | Multi-kitchen checkout + split settlement |

### 4.4 FastAPI Service Template (Standard)

```
service/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Pydantic Settings
│   ├── api/v1/routes/       # Thin controllers
│   ├── domain/              # Business logic, pure Python
│   ├── repositories/        # DB access
│   ├── events/              # Publishers, consumers
│   └── schemas/             # Pydantic request/response
├── alembic/                 # Migrations per service (shared DB, separate schemas)
├── tests/
├── Dockerfile
└── pyproject.toml
```

**Middleware stack (gateway):**

- CORS (PWA origins)
- JWT validation
- Rate limiting (Redis sliding window)
- Request ID / correlation ID
- Prometheus metrics

### 4.5 Inter-Service Communication

| Type | When |
|------|------|
| Sync REST | Read paths needing immediate consistency (checkout validation) |
| Async events | Everything else (notifications, analytics, cache invalidation) |
| WebSocket | Order tracking, live stream signaling |
| gRPC | Phase 4 internal high-volume calls only |

### 4.6 Tech Stack (Locked)

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| API | FastAPI, Uvicorn, Pydantic v2 |
| ORM | SQLAlchemy 2.0 async + Alembic |
| Tasks | Celery or ARQ |
| Frontend | React + Vite + TypeScript |
| Message bus | Redis Streams → Kafka |
| Cache | Redis 7 |
| DB | PostgreSQL 16 + PostGIS |
| Object storage | MinIO (dev) / S3 (prod) |
| Search | PostgreSQL FTS → OpenSearch |
| Payments | Razorpay (Route for split payouts) |
| WhatsApp | Meta Cloud API |
| Live stream | LiveKit Cloud |
| Observability | OpenTelemetry, Prometheus, Grafana, Sentry |
| CI/CD | GitHub Actions |

---

## 5. Database Architecture (DBA)

### 5.1 Primary Database: PostgreSQL 16 + Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- fuzzy search
CREATE EXTENSION IF NOT EXISTS btree_gin;
-- Optional Phase 3:
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 5.2 Schema Separation (Logical Microservice Schemas)

```
ckac_identity.*
ckac_catalog.*
ckac_orders.*
ckac_billing.*
ckac_analytics.*
ckac_notifications.*
ckac_ratings.*
ckac_marketing.*
ckac_learning.*
ckac_growth.*
ckac_events.*          -- outbox + audit
```

Single PostgreSQL cluster; schemas enforce boundaries. Enables future physical split.

### 5.3 Complete Entity Model (DBA)

#### Identity Schema

```sql
CREATE TABLE ckac_identity.owners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(20) DEFAULT 'starter',
    subscription_status VARCHAR(20) DEFAULT 'trial',
    subscription_expires_at TIMESTAMPTZ,
    razorpay_customer_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_identity.kitchens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES ckac_identity.owners(id),
    code VARCHAR(10) UNIQUE NOT NULL,        -- CKPNQ001
    name VARCHAR(255) NOT NULL,
    description TEXT,
    address_line TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    free_delivery_radius_km DECIMAL(5,2) DEFAULT 3.0,
    max_delivery_radius_km DECIMAL(5,2) DEFAULT 10.0,
    delivery_fee_per_km DECIMAL(8,2) DEFAULT 0,
    delivery_fee_flat_beyond DECIMAL(8,2) DEFAULT 0,
    min_order_for_free_delivery DECIMAL(10,2),
    whatsapp_business_id VARCHAR(100),
    razorpay_linked_account_id VARCHAR(100),   -- for split settlement
    settings JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending_verification',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kitchens_location ON ckac_identity.kitchens USING GIST(location);
CREATE INDEX idx_kitchens_owner ON ckac_identity.kitchens(owner_id);
```

#### Catalog Schema

```sql
CREATE TABLE ckac_catalog.categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL,
    sort_order INT DEFAULT 0,
    UNIQUE(kitchen_id, slug)
);
-- Seed slugs: veg, non_veg, vegan, beverages, hot_drinks, cold_drinks,
--             snacks, desserts, combos, seasonal_special

CREATE TABLE ckac_catalog.dishes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    category_id UUID REFERENCES ckac_catalog.categories(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    prep_time_min INT NOT NULL DEFAULT 30,
    delivery_time_min INT,                   -- per-dish delivery allowance
    ingredients_description TEXT,
    quality_measures TEXT,
    avg_home_taste_rating DECIMAL(3,2) DEFAULT 0,
    avg_quality_rating DECIMAL(3,2) DEFAULT 0,
    overall_rating DECIMAL(3,2) DEFAULT 0,
    rating_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    is_seasonal BOOLEAN DEFAULT false,
    event_tag VARCHAR(100),                  -- diwali, holi, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_catalog.dish_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dish_id UUID NOT NULL REFERENCES ckac_catalog.dishes(id),
    media_type VARCHAR(20) NOT NULL,         -- image, video
    url TEXT NOT NULL,
    is_hero BOOLEAN DEFAULT false,
    is_live_capture BOOLEAN NOT NULL DEFAULT false,
    captured_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE ckac_catalog.ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(20) NOT NULL,               -- g, ml, pcs
    current_stock DECIMAL(12,3) DEFAULT 0,
    low_stock_threshold DECIMAL(12,3) DEFAULT 0,
    UNIQUE(kitchen_id, name)
);

CREATE TABLE ckac_catalog.dish_ingredients (
    dish_id UUID REFERENCES ckac_catalog.dishes(id),
    ingredient_id UUID REFERENCES ckac_catalog.ingredients(id),
    quantity DECIMAL(12,3) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    PRIMARY KEY (dish_id, ingredient_id)
);
```

#### Orders Schema

```sql
CREATE TABLE ckac_orders.master_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    master_order_code VARCHAR(30) UNIQUE NOT NULL,
    customer_id UUID NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    total_delivery_fee DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    payment_method VARCHAR(20),              -- upi, cod, card
    payment_status VARCHAR(20) DEFAULT 'pending',
    razorpay_order_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_orders.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    master_order_id UUID REFERENCES ckac_orders.master_orders(id),
    kitchen_id UUID NOT NULL,
    order_code VARCHAR(40) UNIQUE NOT NULL,
    bill_id VARCHAR(30) NOT NULL,
    customer_id UUID NOT NULL,
    status VARCHAR(30) DEFAULT 'received',
    source VARCHAR(20) NOT NULL,             -- whatsapp, manual, pwa, phone
    delivery_type VARCHAR(20),               -- delivery, pickup
    distance_km DECIMAL(6,2),
    delivery_fee DECIMAL(10,2) DEFAULT 0,
    delivery_fee_accepted BOOLEAN,
    subtotal DECIMAL(12,2) NOT NULL,
    special_instructions TEXT,
    cooking_request TEXT,
    estimated_ready_at TIMESTAMPTZ,
    tracking_token VARCHAR(64) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_orders.order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES ckac_orders.orders(id),
    dish_id UUID NOT NULL,
    dish_name VARCHAR(255) NOT NULL,           -- snapshot
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(10,2) NOT NULL
);

CREATE TABLE ckac_orders.order_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    status VARCHAR(30) NOT NULL,
    note TEXT,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);
```

#### Billing Schema (Split Payment)

```sql
CREATE TABLE ckac_billing.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    master_order_id UUID,
    order_id UUID,                           -- null if master-level
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    method VARCHAR(20),
    razorpay_payment_id VARCHAR(100),
    status VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_billing.settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    master_order_id UUID NOT NULL,
    kitchen_id UUID NOT NULL,
    order_id UUID NOT NULL,
    gross_amount DECIMAL(12,2) NOT NULL,
    delivery_fee_amount DECIMAL(10,2) DEFAULT 0,
    platform_fee DECIMAL(10,2) DEFAULT 0,
    net_to_owner DECIMAL(12,2) NOT NULL,
    razorpay_transfer_id VARCHAR(100),
    settlement_status VARCHAR(20) DEFAULT 'pending',
    settled_at TIMESTAMPTZ
);

CREATE TABLE ckac_billing.owner_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    plan_tier VARCHAR(20),
    billing_cycle VARCHAR(10),               -- monthly, yearly
    amount DECIMAL(10,2),
    razorpay_subscription_id VARCHAR(100),
    status VARCHAR(20),
    current_period_end TIMESTAMPTZ
);
```

#### CRM & Marketing Schema

```sql
CREATE TABLE ckac_marketing.kitchen_customers (
    kitchen_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    total_spend DECIMAL(12,2) DEFAULT 0,
    monthly_spend DECIMAL(12,2) DEFAULT 0,
    order_count INT DEFAULT 0,
    last_order_at TIMESTAMPTZ,
    favorite_dish_id UUID,
    tags JSONB DEFAULT '[]',
    PRIMARY KEY (kitchen_id, customer_id)
);

CREATE TABLE ckac_marketing.coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    code VARCHAR(30) NOT NULL,
    discount_type VARCHAR(10),               -- flat, percent
    discount_value DECIMAL(10,2),
    min_order_amount DECIMAL(10,2),
    target_customer_ids UUID[],
    max_uses INT,
    used_count INT DEFAULT 0,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ
);

CREATE TABLE ckac_marketing.subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    name VARCHAR(255),
    plan_type VARCHAR(20),                   -- tiffin, combo, single_dish
    dishes_config JSONB NOT NULL,
    price DECIMAL(10,2),
    billing_cycle VARCHAR(10),
    is_active BOOLEAN DEFAULT true
);
```

#### Ratings Schema

```sql
CREATE TABLE ckac_ratings.dish_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dish_id UUID NOT NULL,
    order_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    home_taste_score SMALLINT CHECK (home_taste_score BETWEEN 1 AND 5),
    quality_score SMALLINT CHECK (quality_score BETWEEN 1 AND 5),
    media_url TEXT,
    media_type VARCHAR(10),                  -- video, audio
    is_anonymous BOOLEAN DEFAULT true,
    is_verified_purchase BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_ratings.dish_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dish_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    order_id UUID,
    suggestion_text TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',    -- pending, accepted, rejected
    owner_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Growth Intelligence Schema

```sql
CREATE TABLE ckac_growth.suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kitchen_id UUID NOT NULL,
    suggestion_type VARCHAR(50),             -- seasonal, dish_promo, customer_winback, inventory
    title VARCHAR(255),
    description TEXT,
    action_payload JSONB,
    priority INT DEFAULT 0,
    dismissed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ckac_growth.seasonal_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region VARCHAR(100),
    season_event VARCHAR(100),
    dish_category VARCHAR(50),
    demand_multiplier DECIMAL(4,2),
    sample_dishes JSONB
);
```

#### Notifications Schema

```sql
CREATE TABLE ckac_notifications.notification_preferences (
    user_id UUID PRIMARY KEY,
    whatsapp_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,
    order_updates BOOLEAN DEFAULT true,
    marketing BOOLEAN DEFAULT false
);

CREATE TABLE ckac_notifications.notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    channel VARCHAR(20),                     -- whatsapp, push, sms
    template_id VARCHAR(100),
    payload JSONB,
    status VARCHAR(20),
    sent_at TIMESTAMPTZ
) PARTITION BY RANGE (sent_at);
```

### 5.4 Row-Level Security

```sql
ALTER TABLE ckac_catalog.dishes ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ckac_catalog.dishes
    USING (kitchen_id = current_setting('app.current_kitchen_id', true)::uuid);
```

Set `app.current_kitchen_id` per request in FastAPI middleware after JWT decode.

### 5.5 Scaling Roadmap

| Scale | Kitchens | Orders/day | Architecture |
|-------|----------|------------|--------------|
| Seed | 10 | 100 | Single PG, single Redis |
| Growth | 500 | 5,000 | PG + read replica, Redis cluster |
| Scale | 5,000 | 50,000 | PgBouncer, partition orders, Kafka |
| National | 50,000+ | 500,000 | Regional shards, Citus/evaluate |

---

## 6. Caching Strategy

### 6.1 Cache Decision Matrix

| Data | Cache? | Store | TTL | Notes |
|------|--------|-------|-----|-------|
| Active menu | Yes | Redis | 5 min | Invalidate on DishUpdated |
| Dish detail + ratings summary | Yes | Redis | 10 min | |
| Order history (recent 20) | Yes | Redis | 2 min | Customer + owner |
| Order history (paginated old) | No | PG | — | Direct query with index |
| Today's orders (owner) | Yes | Redis List | 24h | Append on event |
| Revenue report (daily) | Yes | Redis | 1h | Pre-aggregated |
| Revenue report (monthly) | Yes | Redis | 6h | Heavy query |
| Best dishes report | Yes | Redis | 6h | Nightly refresh |
| Customer patterns | Yes | Redis | 12h | Analytics worker |
| Growth suggestions | Yes | Redis | 24h | Regenerate daily |
| Nearby kitchens | Yes | Redis | 3 min | Key: geohash precision 6 |
| Order live status | Yes | Redis | until terminal | |
| Payment state | **No** | PG | — | Strong consistency |
| Settlement state | **No** | PG | — | |
| Coupon redemption count | Partial | Redis INCR + PG | — | Atomic |
| Ingredient stock | Short | Redis | 30 sec | Or no cache |
| WhatsApp parse draft | Yes | Redis | 1h | Draft orders |

### 6.2 Order History — Deep Design

**Owner "Order History Tracker":**

```
Key: owner:{kitchen_id}:orders:history:{YYYY-MM-DD}
Type: Sorted Set (score = timestamp, value = order_id)
TTL: 7 days rolling

On OrderPlaced → ZADD + trim to 500 entries
Full history pagination → PostgreSQL (source of truth)
Dashboard "today" → Redis only (sub-ms)
```

**Customer repeat order:**

```
Key: customer:{id}:recent_orders
Type: List of compact order JSON (dish ids, qty)
TTL: 2 min
"Repeat" button → POST /orders/repeat with order_id (validates dish still active)
```

---

## 7. Docker & Scalable Infrastructure

### 7.1 docker-compose.yml (Development)

```yaml
version: "3.9"
services:
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: ckac
      POSTGRES_USER: ckac
      POSTGRES_PASSWORD: ckac_dev
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]

  api-gateway:
    build: ./services/gateway
    ports: ["8000:8000"]
    depends_on: [postgres, redis]

  # ... identity, catalog, order, billing, notification-worker, analytics-worker

  owner-pwa:
    build: ./apps/owner-pwa
    ports: ["3001:3000"]

  customer-pwa:
    build: ./apps/customer-pwa
    ports: ["3002:3000"]

volumes:
  pgdata:
```

### 7.2 Production Kubernetes (Phase 3)

- HPA on order, notification, gateway services
- PG managed (RDS/Cloud SQL)
- CDN for PWA static assets + media
- Secrets via external secrets operator

---

## 8. Notification System (App + WhatsApp)

### 8.1 Dual-Channel Strategy (CPO)

| Event | WhatsApp | App Push | Priority |
|-------|----------|----------|----------|
| Order confirmed | ✅ | ✅ | Critical |
| Status change | ✅ | ✅ | Critical |
| Delivery tracking interval | ✅ | ✅ | High |
| Daily menu | ✅ | Optional | Medium |
| Coupon received | ✅ | ✅ | Medium |
| Rating request | ✅ | ✅ | Medium |
| Growth suggestion (owner) | ❌ | ✅ | Low |
| Payment receipt | ✅ | ✅ | Critical |
| Trial sample invite | ✅ | ✅ | Medium |

### 8.2 Architecture

```
Domain Event
     │
     ▼
notification-service
     ├── Template engine (Jinja2 / Handlebars)
     ├── Channel router (prefs + urgency)
     ├── WhatsApp adapter (Meta Cloud API)
     ├── Web Push adapter (VAPID keys)
     └── Retry + DLQ
```

### 8.3 WhatsApp Templates (Pre-approved)

| Template | Variables |
|----------|-----------|
| order_confirmed | order_code, amount, tracking_link |
| order_status_update | status, eta, tracking_link |
| delivery_progress | interval_msg, tracking_link |
| daily_menu | kitchen_name, menu_link |
| payment_received | amount, order_code |

### 8.4 Tracking Link Progress Notifications

Owner marks lifecycle → event → notification-service:

- Immediate push on status change
- **Interval mode** during `preparing` / `out_for_delivery`: cron every N minutes (owner config, default 5) sends progress reminder with tracking link
- Customer opens PWA tracking page with WebSocket for live updates

### 8.5 Web Push (PWA)

- Service worker registration on first order
- VAPID keys in notification-service
- Fallback to WhatsApp if push not subscribed

---

## 9. Payment Gateway & Owner Settlement

### 9.1 Payment Scenarios

| Scenario | Flow |
|----------|------|
| Single kitchen order | Customer pays → 100% to owner linked account |
| Multi-kitchen cart | Customer pays once → platform splits via Razorpay Route |
| COD | No gateway; owner marks collected |
| Owner scanner (UPI QR) | Dynamic QR per order → webhook confirms |
| Owner subscription | Razorpay subscription API |
| Customer tiffin | Razorpay recurring on kitchen's linked account |

### 9.2 Aggregated Multi-Kitchen Payment (Critical Feature)

```
Customer checkout total: ₹850
  Kitchen A sub-order: ₹500 (dishes) + ₹30 delivery
  Kitchen B sub-order: ₹300 (dishes) + ₹20 delivery

1. Create master_orders record
2. Create Razorpay order for ₹850
3. On payment.captured webhook:
   a. Insert payments record
   b. Calculate per-kitchen settlement:
      - Kitchen A net: ₹530 - platform_fee
      - Kitchen B net: ₹320 - platform_fee
   c. Create settlement records
   d. Trigger Razorpay Route transfers to each kitchen's linked_account_id
   e. Publish PaymentSplitCompleted event
4. Each owner sees their portion in dashboard (not other kitchen amounts)
```

### 9.3 Per-Owner Payment Support

- Each kitchen onboarding includes Razorpay Linked Account (KYC)
- Owner PWA: UPI scanner, payment history, settlement status
- Direct UPI QR for walk-in / phone orders without PWA checkout

### 9.4 Refund Policy (Multi-Kitchen)

- Partial refund at sub-order level
- Master order payment spawns reverse transfer per affected kitchen
- Saga coordinator tracks refund state

### 9.5 COD Flow

```
Order placed (COD) → payment_status = pending_cod
Delivered → owner marks collected → payment_status = captured
Analytics includes COD in revenue on collection, not placement
```

---

## 10. Owner Growth Intelligence Engine

### 10.1 Purpose (CPO)

Proactive, actionable suggestions based on orders, customers, seasons — not just dashboards.

### 10.2 Suggestion Types

| Type | Trigger Logic | Example Output |
|------|---------------|----------------|
| **Seasonal** | Match calendar + regional seasonal_patterns | "Diwali in 3 weeks — add seasonal_special menu; similar kitchens saw 40% uplift on mithai combos" |
| **Dish promo** | High rating + low order volume | "Your Paneer Tikka rates 4.8 but only 5% of orders — promote at ₹199 this week" |
| **Customer winback** | Regular customer inactive 21+ days | "12 customers haven't ordered in 3 weeks — send coupon MAAS20" |
| **Combo opportunity** | Association rule mining on order_items | "Customers who order Butter Naan also order Dal Makhani 68% of time — create combo" |
| **Inventory alert** | Ingredient stock vs forecast | "Garam masala low — 3 top dishes affected" |
| **Peak staffing** | Historical order volume by hour/day | "Friday 12–2 PM is 3× average — prep extra Biryani portions" |
| **Delivery zone** | Orders outside free radius converting poorly | "40% cart abandons at 4km — consider ₹399 min order for free delivery" |
| **Rating response** | New suggestions pending | "3 customers suggested less oil in Dal — review suggestions" |

### 10.3 Processing Pipeline

```
Nightly cron + on-demand after 50th order
        │
        ▼
analytics-service aggregates
        │
        ▼
growth-service rules engine + optional ML (Phase 4)
        │
        ▼
Insert ckac_growth.suggestions
        │
        ▼
Push notification to owner PWA
```

### 10.4 Owner UX

- "Growth" tab with card-based suggestions
- One-tap actions: "Create coupon", "Add event menu", "Send WhatsApp blast"
- Dismiss / snooze / mark done

---

# Part B — Complete Feature Specifications

## 11. Feature Index (All 45 Features)

| ID | Feature | Phase | Priority |
|----|---------|-------|----------|
| F01 | WhatsApp order capture | 1 | Must |
| F02 | Normal message order capture | 1 | Must |
| F03 | Custom manual order input | 1 | Must |
| F04 | Order lifecycle management | 1 | Must |
| F05 | Order history tracker | 1 | Must |
| F06 | Multi-kitchen single checkout | 2 | Must |
| F07 | Revenue report | 1 | Must |
| F08 | Best performing dishes report | 2 | Must |
| F09 | Best dish combinations report | 2 | Should |
| F10 | Customer order pattern (day/dish) | 2 | Must |
| F11 | Owner growth suggestions | 2 | Should |
| F12 | Performance report with recipe suggestions | 3 | Should |
| F13 | Add dish with live photo capture | 1 | Must |
| F14 | Price, ingredients, quality measures | 1 | Must |
| F15 | Dish categories | 1 | Must |
| F16 | Home taste + quality rating | 2 | Must |
| F17 | Overall dish rating aggregator | 2 | Must |
| F18 | A/V experience reviews (anonymous) | 2 | Should |
| F19 | Ingredient balance mapper | 3 | Should |
| F20 | Customer recipe suggestions (accept/reject) | 3 | Should |
| F21 | Learning portal (scrape/curate) | 3 | Could |
| F22 | New dish trial / sample promotion | 3 | Could |
| F23 | Share recipe + rewards | 3 | Could |
| F24 | Best cloud chef rankings | 3 | Could |
| F25 | Social share (WhatsApp/Insta cards) | 2 | Should |
| F26 | No commission — owner subscription | 1 | Must |
| F27 | Service range & delivery radius | 2 | Must |
| F28 | Delivery fee accept/deny flow | 2 | Must |
| F29 | Tracking link + interval notifications | 2 | Must |
| F30 | Per-dish prep/delivery time | 1 | Must |
| F31 | Address lat/long distance mapping | 2 | Must |
| F32 | Customer kitchen discovery (distance) | 2 | Must |
| F33 | Customer order history + repeat | 2 | Must |
| F34 | Customer monthly subscription (tiffin) | 2 | Must |
| F35 | Owner custom meal plans | 2 | Must |
| F36 | Owner custom coupons | 2 | Must |
| F37 | Owner CRM (spend, patterns) | 2 | Must |
| F38 | Targeted marketing / special pricing | 2 | Should |
| F39 | Daily menu WhatsApp push | 2 | Should |
| F40 | Special event menus | 2 | Should |
| F41 | Custom cooking requests | 2 | Must |
| F42 | Online pay + COD | 1 | Must |
| F43 | Owner UPI scanner / payment gateway | 1 | Must |
| F44 | Aggregated payment + owner split | 2 | Must |
| F45 | App + WhatsApp notifications | 1 | Must |
| F46 | Live food preparation streaming | 3 | Could |
| F47 | Owner opt-in live sharing | 3 | Could |
| F48 | Customer live-prep package filter | 3 | Could |

---

## 12. Order Management Features (F01–F06)

### F01 — WhatsApp Order Capture

**User story:** As an owner, I want orders from WhatsApp chat automatically parsed into draft orders so I don't lose sales in chat scroll.

**Acceptance criteria:**
- [ ] WhatsApp Business Cloud API webhook receives inbound messages
- [ ] Parser extracts dish names, quantities, special notes
- [ ] Unmatched items flagged for owner manual mapping
- [ ] Owner confirms/edits draft → creates official order
- [ ] Customer receives confirmation with tracking link
- [ ] Parse success rate tracked (target 60% MVP, 85% v2)

**Technical:** notification-service webhook → order-service `WhatsAppParser` (rule engine + kitchen menu fuzzy match via pg_trgm)

**Events:** `whatsapp.message.received`, `order.draft.created`, `order.placed`

**DB:** `orders.source = 'whatsapp'`, raw message in `orders.special_instructions` or JSONB metadata

---

### F02 — Normal Message Order Capture

**User story:** As an owner, I want SMS/plain text patterns (non-WhatsApp) logged similarly.

**Acceptance criteria:**
- [ ] Manual paste of message text into owner app creates same draft flow
- [ ] Phase 2: SMS gateway inbound (optional)

**Technical:** Same parser as F01; source = `manual_message`

---

### F03 — Custom Manual Order Input

**User story:** As an owner, I want to create orders from phone calls or walk-ins manually.

**Acceptance criteria:**
- [ ] Owner selects customer (or creates quick customer)
- [ ] Adds dishes from menu with qty
- [ ] Sets delivery/pickup, payment method
- [ ] Saves without WhatsApp

**Technical:** `POST /api/v1/orders/manual` — source = `manual`

---

### F04 — Order Lifecycle Management

**User story:** As an owner, I mark each order through stages; customer sees progress.

**Statuses:** `received → accepted → preparing → ready → out_for_delivery → delivered | cancelled`

**Acceptance criteria:**
- [ ] Owner one-tap status advance
- [ ] Each transition logged in order_status_events
- [ ] Customer notified (WhatsApp + push) on every change
- [ ] Optional note per transition ("Adding extra spice as requested")
- [ ] Cancel requires reason

**Events:** `order.status.changed` → notification-service

---

### F05 — Order History Tracker

**User story:** As an owner, I view/filter all past orders by date, status, customer, source.

**Acceptance criteria:**
- [ ] Filter: today, week, month, custom range
- [ ] Filter: source (whatsapp, pwa, manual)
- [ ] Export CSV (Phase 2)
- [ ] Sub-second load for today's orders (Redis)
- [ ] Paginated full history from PG

**DB index:** `(kitchen_id, created_at DESC)`

---

### F06 — Multi-Kitchen Single Checkout

**User story:** As a customer, I order from 2+ kitchens in one payment with separate tracking per kitchen.

**Acceptance criteria:**
- [ ] Cart groups items by kitchen
- [ ] Single payment at checkout
- [ ] Separate order_code per kitchen: `{kitchen_code}-{bill_id}`
- [ ] Master receipt shows all; each kitchen sees only their sub-order
- [ ] Independent lifecycle per sub-order
- [ ] Split settlement (F44)

**Technical:** Saga: `master_orders` → N × `orders` → payment → N × settlements

---

## 13. Analytics & Reporting (F07–F12)

### F07 — Revenue Report

**Metrics:** Daily, weekly, monthly revenue; COD vs online; delivery fees collected; subscription revenue

**Acceptance criteria:**
- [ ] Owner dashboard charts
- [ ] Compare to previous period
- [ ] Filter by payment method
- [ ] Generate < 5s (cached aggregates)

**DB:** `daily_kitchen_stats` materialized view refreshed nightly + on OrderDelivered

---

### F08 — Best Performing Dishes Report

**Metrics:** Top dishes by revenue, order count, rating, margin (if cost entered later)

**Acceptance criteria:**
- [ ] Top 10 dishes default
- [ ] Date range selector
- [ ] Show rating alongside volume

---

### F09 — Best Dish Combinations Report

**Metrics:** Frequent itemsets (A + B ordered together)

**Technical:** analytics-worker runs association rule mining nightly on `order_items`

**Acceptance criteria:**
- [ ] Top 5 combos with support % and suggested bundle price

---

### F10 — Customer Order Pattern Analytics

**Metrics:** Day-of-week heatmap, dish frequency per customer, peak hours

**Acceptance criteria:**
- [ ] Kitchen-level and per-customer views
- [ ] "Mostly orders on Tuesday lunch" insight text

**DB:** `customer_order_patterns (kitchen_id, customer_id, day_of_week, dish_id, frequency)`

---

### F11 — Owner Growth Suggestions

See [Section 10](#10-owner-growth-intelligence-engine). Phase 2.

---

### F12 — Performance Report with Recipe Suggestions

**User story:** As an owner, I see customer recipe suggestions per dish in my performance report and accept/reject them.

**Acceptance criteria:**
- [ ] Suggestions listed under dish in analytics
- [ ] Accept → optional menu update reminder
- [ ] Reject → optional thank-you to customer
- [ ] Accepted suggestions tracked for chef ranking credit

---

## 14. Catalog & Quality (F13–F20)

### F13 — Add Dish with Live Photo Capture

**Acceptance criteria:**
- [ ] In-app camera required for hero image
- [ ] Multiple angles allowed
- [ ] Timestamp and live_capture flag stored
- [ ] Compress + upload to MinIO/S3 via media-service

---

### F14 — Price, Ingredients Description, Quality Measures

**Fields:** price (INR), ingredients_description (text), quality_measures (text — e.g., "Made with farm-fresh paneer, low oil")

---

### F15 — Dish Categories

**Default:** veg, non_veg, vegan, beverages, hot_drinks, cold_drinks, snacks, desserts, combos, seasonal_special

**Acceptance criteria:** Owner can assign one primary category; filter on customer menu

---

### F16 — Home Taste Rating

**Scale:** 1–5 — "Compared to authentic home cooking"

**Rule:** Only verified purchase (delivered order) can rate

---

### F17 — Overall Dish Rating

**Formula:** `overall = (0.6 × home_taste + 0.4 × quality)` — weighted average displayed on dish card

**Updated:** On each new rating via trigger or event consumer

---

### F18 — A/V Experience Reviews

**Acceptance criteria:**
- [ ] 15–30 sec video or audio optional
- [ ] Displayed on dish page without customer name/phone
- [ ] Moderation queue for reported content
- [ ] Max file size 10MB; transcoded to HLS/mp3

---

### F19 — Ingredient Balance Mapper

**Example:** Dish 1 → 10g garam masala, 1g lal mirch, 1g haldi

**Acceptance criteria:**
- [ ] Owner defines recipe per dish
- [ ] On order confirm → deduct qty × order qty from stock
- [ ] Low stock warning before accept
- [ ] Stock adjustment manual override

**Phase 3** — optional for MVP kitchens

---

### F20 — Customer Recipe Suggestions

**Flow:** Customer submits → owner sees in dish performance → accept/reject (F12)

---

## 15. Learning, Community & Rankings (F21–F26)

### F21 — Learning Portal

**Content:** Curated/scraped recipes by category (respect robots.txt; prefer licensed/API sources)

**Flow:**
1. Owner browses category
2. "I learned this dish" → creates trial dish (inactive on public menu)
3. Links to F22 trial workflow

**Legal:** Scraping policy document; DMCA takedown process

---

### F22 — New Dish Trial / Sample Promotion

**Flow:**
1. Owner prepares small batch
2. Selects 5–20 regular customers
3. Offers free sample / small paid sample via WhatsApp
4. Collects ratings
5. If avg ≥ threshold → promote to official menu

---

### F23 — Share Recipe & Gain Rewards

**Mechanism:** Owner shares original recipe to community → earns points for ratings/appreciations → redeemable for subscription discount or featured listing

---

### F24 — Best Cloud Chef Rankings

**Levels:** City → State → National (monthly)

**Score formula:**
```
0.30 × norm(avg_dish_rating)
+ 0.20 × recipe_shares_score
+ 0.25 × review_volume × quality
+ 0.15 × repeat_order_rate
+ 0.10 × community_votes
```

**Anti-fraud:** Min 50 verified orders/month, anomaly detection on ratings

---

## 16. Marketing & Social (F27–F33)

### F27 — Service Range & Delivery Radius

**Rules:** Free delivery within X km (default 3); beyond = chargeable; max delivery radius configurable

---

### F28 — Delivery Fee Accept/Deny

**Flow:**
1. System calculates fee based on lat/long distance
2. Customer accepts or denies at checkout
3. If denied → owner notified → cancel OR deliver free if order ≥ min_amount

---

### F29 — Tracking Link + Interval Notifications

**Tracking URL:** `https://customer.kitchcu.in/t/{tracking_token}`

**Interval:** During preparing/delivery, notify every N minutes (default 5) with link

---

### F30 — Per-Dish Prep/Delivery Time

**Owner sets:** prep_time_min per dish; system sums for ETA (quality-first, not race)

---

### F31 — Address Lat/Long Distance Mapping

**PostGIS:** `ST_Distance(kitchen.location, customer.location) / 1000` → km

**UI:** Show distance on owner order card and customer checkout

---

### F32 — Customer Kitchen Discovery

**Page:** Map + list sorted by distance; filters: category, rating, live-prep, veg

---

### F33 — Customer Order History + Repeat Order

**Repeat:** One tap re-create order; validates dishes still active/priced

---

### F34 — Customer Monthly Subscription (Tiffin)

**Owner-created plans;** customer subscribes; recurring billing via Razorpay

---

### F35 — Owner Custom Meal Plans

**Types:** Combo of dishes, individual dish packs, weekday-only plans

---

### F36 — Owner Custom Coupons

**Generate code → share via WhatsApp to specific customers or public**

---

### F37 — Owner CRM

**Per customer:** total spend, monthly spend, order count, favorite dishes, order patterns, tags

---

### F38 — Targeted Marketing / Special Pricing

**Owner action:** Select segment (e.g., top 20 spenders) → special price on dish X for 7 days

---

### F39 — Daily Menu WhatsApp Push

**Owner selects dishes for today → one-tap blast to opted-in customers**

---

### F40 — Special Event Menus

**Tag dishes with event_tag (diwali);** auto-surface on customer app during event window

---

### F41 — Custom Cooking Requests

**Free text on order item or order level;** visible to owner in kitchen ticket

---

## 17. Delivery & Logistics (F34–F40)

*(Covered above in F27–F31, F41)*

### Delivery Self-Managed Model

- Kitchcu does **not** operate fleet
- Owner manages delivery staff
- Platform provides tracking link + customer notifications
- Owner can share third-party tracking URL (optional field)

---

## 18. Customer Experience (F42–F45)

### F42 — Online Pay + COD

**Methods:** UPI, cards, wallets via Razorpay; COD flag on order

---

### F43 — Owner UPI Scanner / Payment Gateway

**Owner PWA:** Scan customer UPI QR or show dynamic QR for order amount

---

### F44 — Aggregated Payment + Owner Split

See [Section 9](#9-payment-gateway--owner-settlement). Razorpay Route transfers.

---

### F45 — App + WhatsApp Notifications

See [Section 8](#8-notification-system-app--whatsapp).

---

## 19. Live Streaming (F46–F48)

### F46 — Live Food Preparation Streaming

**Tech:** LiveKit room per session; owner publishes video+audio

**Features:** Mic mute/unmute, customer listen-only or Q&A mode (Phase 4)

---

### F47 — Owner Opt-In Live Sharing

**Default off;** owner toggles "Go Live" per order or open kitchen hours

---

### F48 — Customer Live-Prep Package

**Customer subscription add-on:** Discovery filter shows only kitchens currently streaming or offering live prep

---

# Part C — Execution

## 20. Cross-Feature Dependency Map

```
F13 (Dishes) ──► F01,F03,F06 (Orders)
F04 (Lifecycle) ──► F29,F45 (Notifications)
F06 (Multi-cart) ──► F44 (Split payment)
F16 (Ratings) ──► F17,F18,F24 (Rankings)
F37 (CRM) ──► F36,F38,F39 (Marketing)
F19 (Ingredients) ──► F11 (Growth alerts)
F10 (Patterns) ──► F09,F11 (Combos, suggestions)
F43 (Scanner) ──► F42 (Payments)
```

---

## 21. Development Phases & Sprint Backlog

### Phase 1 (Months 1–3) — 12 Sprints

| Sprint | Deliverables |
|--------|-------------|
| S1 | Repo, Docker, CI, identity, kitchen onboarding |
| S2 | Catalog: categories, dishes, live photo upload |
| S3 | Order: manual input, lifecycle |
| S4 | WhatsApp webhook + parser MVP |
| S5 | Owner PWA: inbox, menu, orders |
| S6 | Notifications: WhatsApp templates |
| S7 | Billing: Razorpay, COD, owner subscription |
| S8 | Owner scanner UPI |
| S9 | Revenue report + order history |
| S10 | FCM/Web push |
| S11 | Per-dish prep time, polish |
| S12 | Pilot with 10 kitchens |

### Phase 2 (Months 4–6)

Customer PWA, discovery, multi-cart, split payment, CRM, coupons, tiffin, ratings, delivery fees, tracking, growth suggestions, social share

### Phase 3 (Months 7–10)

Ingredients, learning portal, trials, rankings, live stream, recipe rewards

---

## 22. KPIs, SLOs & Benchmarks

| Category | Metric | Target |
|----------|--------|--------|
| Business | Active kitchens @ 12mo | 500 |
| Business | Owner monthly retention | 90% |
| Product | WhatsApp parse rate | 85% |
| Product | Repeat order rate (30d) | 40% |
| Quality | Avg home taste rating | 4.2+ |
| Tech | API p95 read | < 200ms |
| Tech | Order placement E2E | < 3s |
| Tech | Uptime | 99.9% |

---

## 23. Risks & Governance

| Risk | Mitigation |
|------|------------|
| Scope creep | This doc + strict phase gates |
| Split payment complexity | Razorpay Route; extensive staging tests |
| WhatsApp policy | Manual fallback always |
| Live stream cost | Premium tier only; LiveKit pay-as-you-go |
| Ranking fraud | Verified orders, statistical anomaly detection |
| Scraping legal | Curated content first; licensed APIs |

---

## Document Control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-12 | Initial system benchmark |
| 2.0 | 2026-07-12 | Complete feature specs, notifications, split payment, growth engine |

**Related files:**
- `docs/CKAC-SYSTEM-BENCHMARK.md` — Architecture deep dive
- `docs/CKAC-PITCH-DECK.pdf` — Investor pitch
- `docs/CKAC-PITCH-DECK.md` — Pitch source markdown
