# Kitchcu Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| **[KITCHCU-ENGINEERING-STANDARDS.md](./KITCHCU-ENGINEERING-STANDARDS.md)** | **Engineering constitution — DDD, EDD, TDD, security, observability** | Engineering, AI agents |
| **[templates/MODULE-DESIGN-PACK.md](./templates/MODULE-DESIGN-PACK.md)** | Pre-code design template (mandatory for new modules) | Engineering |
| **[ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md)** | **Living release board** — S1–S18 + post-S18 increments, credentials, seed checklist, kitchcu.com gate | CEO, CPO, CTO, Engineering, AI agents |
| **[PLATFORM-STRATEGIC-ANALYSIS.md](./PLATFORM-STRATEGIC-ANALYSIS.md)** | **CEO/CPO/CTO strategic brief** — competitive honesty, gaps, Waves A–D | CEO, CPO, CTO, Investors, AI agents |
| **[PLATFORM-PERSONA-DEEP-DIVE.md](./PLATFORM-PERSONA-DEEP-DIVE.md)** | **Persona/flow/architecture/implementation deep dive** — customer, owner, superadmin, ops, support, finance, kitchen staff; RBAC matrix; scorecards | CEO, CPO, CTO, Ops, Support, Finance, AI agents |
| **[CKAC-COMPLETE-GUIDE.md](./CKAC-COMPLETE-GUIDE.md)** | **Master guide v3.2.2 — modules through P28 (packages, templates, employees RBAC, kitchen workspace), flows §17.9–17.10, UI Catalog, OpenAPI** | CEO, CPO, CTO, DBA, QA, Investors, AI agents |
| **[CKAC-COMPLETE-GUIDE.pdf](./CKAC-COMPLETE-GUIDE.pdf)** | Complete Executive Guide PDF v3.2.2 (portrait; UI Catalog figures) | CEO, CPO, CTO, Investors |
| **[CKAC-USERFLOWS.md](./CKAC-USERFLOWS.md)** | **Full user journey pack** — every persona, every screen, every API call, step-by-step | Product, Design, Engineering, QA |
| **[CKAC-USERFLOWS.pdf](./CKAC-USERFLOWS.pdf)** | User journey pack PDF | Product, Design, Investors |
| **[assets/ui/](./assets/ui/)** | **Reference UI screenshots** (8 surfaces: portal, customer home/login, kitchen login, owner dashboard, admin login/overview/Control) — Complete Guide §18 | Product, Design, Engineering |
| **[API.md](./API.md)** | **Public API reference** — auth, body/response examples, error codes; live aggregated spec via gateway `/openapi.json`/`/docs`/`/redoc` and portal `/openapi` | Engineering, Partners |
| **[CKAC-IMPLEMENTATION-GUIDE.md](./CKAC-IMPLEMENTATION-GUIDE.md)** | **What's built** — architecture, DB, flows, APIs, feature matrix mapped to benchmarks | Product, Engineering, CPO |
| **[AGENTS.md](../AGENTS.md)** | **Agent implementation spec — read before every code change** | AI agents, developers |
| **[DEVELOPMENT-PHASES.md](./DEVELOPMENT-PHASES.md)** | **Phased roadmap — TDD, EDD, DB schemas, sprints** | Engineering |
| [.cursor/rules/](../.cursor/rules/) | Cursor auto-applied rules (constitution, TDD/EDD, backend, frontend, security) | Cursor IDE |
| [CKAC-COMPLETE-PLANNING-BENCHMARK.md](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) | **Master plan** — all 48 features with user stories, acceptance criteria, DB schema, cache, events | Product, Engineering, DBA |
| [CKAC-SYSTEM-BENCHMARK.md](./CKAC-SYSTEM-BENCHMARK.md) | Architecture deep dive — services, scaling, SLOs, phases | CTO, Senior Engineers |
| [CKAC-CPO-PRODUCT-BLUEPRINT.md](./CKAC-CPO-PRODUCT-BLUEPRINT.md) | **CPO blueprint v4.2** — modules, challenges, journeys, UI surfaces | CPO, Product |
| [CKAC-PRODUCT-DEPTH-GUIDE.md](./CKAC-PRODUCT-DEPTH-GUIDE.md) | Product depth guide (superseded by Complete Guide) | CPO, Product |
| [CKAC-PRODUCT-DEPTH-GUIDE.pdf](./CKAC-PRODUCT-DEPTH-GUIDE.pdf) | Product depth PDF (superseded by Complete Guide PDF) | CPO, Investors |
| [CKAC-PITCH-DECK.md](./CKAC-PITCH-DECK.md) | Investor pitch source (markdown, legacy) | CEO, Investors |
| [CKAC-PITCH-DECK.pdf](./CKAC-PITCH-DECK.pdf) | **CPO Product Blueprint PDF** (landscape slides, **v4.2** — includes UI Catalog + OpenAPI slide) | CPO, Investors, Partners |
| **[E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md)** | **Design pack (pre-code)** — purchase inventory (E1) + chef standard lock from ratings/volume (E2) | CPO, CTO, Engineering |
| [F19-INGREDIENTS-DESIGN.md](./F19-INGREDIENTS-DESIGN.md) | Ingredient mapper (shipped) | Engineering |
| [F07-F11-F39-GROWTH-DESIGN.md](./F07-F11-F39-GROWTH-DESIGN.md) | Growth intelligence (shipped) | Engineering |
| [F16-F18-RATINGS-DESIGN.md](./F16-F18-RATINGS-DESIGN.md) | Home-taste ratings (shipped) | Engineering |

## Regenerate PDFs

```bash
# Complete executive guide — CEO + CPO + CTO (portrait)
python scripts/generate_complete_guide_pdf.py

# Full user journey pack (every persona, every screen, every API call)
python scripts/generate_userflows_pdf.py

# Product depth guide (legacy; use complete guide instead)
python scripts/generate_product_depth_pdf.py

# CPO pitch deck (landscape slides + UI Catalog embeds)
python scripts/generate_pitch_pdf.py
```

## Quick Stats

- **S1–S18 + P19–P28 shipped** — track progress in [ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md); encyclopedia [Complete Guide v3.2.2](./CKAC-COMPLETE-GUIDE.md)
- **Prod:** `https://kitchcu.com` · `customer` / `kitchen` / `admin` / `api` / `media`.kitchcu.com
- **Local apps:** Portal :13000 · customer.kitchcu.in :13001 · kitchen.kitchcu.in :13002 · admin.kitchcu.in :13003
- **Stack:** React PWAs + Python FastAPI + PostgreSQL/PostGIS + Redis + Docker
- **Model:** Subscription SaaS, zero food commission
- **Positioning:** India's first — and the world's third — platform with this feature stack
- **Brand:** **Kitchcu** (internal repo/schemas retain `ckac_*` identifiers)
- **API:** Aggregated OpenAPI at gateway `/openapi.json` / `/docs` / `/redoc`, portal `/openapi` (`/api-docs`) — see [`API.md`](./API.md)
- **Next design:** [E1–E2 Kitchen Quality Loop](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md)
- **UI screenshots:** [`docs/assets/ui/`](./assets/ui/) — Complete Guide §18 (8 surfaces) + Pitch / Userflows PDF figures
- **PDF layout (v3.2):** `scripts/pdf_guide.py` — top margin clears running header; captions above figures; part-band body starts at y=46 (no header overlap)
- **User journeys:** [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) — full step-by-step pack for every persona
