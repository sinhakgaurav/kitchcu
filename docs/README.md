# Kitchcu Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| **[KITCHCU-ENGINEERING-STANDARDS.md](./KITCHCU-ENGINEERING-STANDARDS.md)** | **Engineering constitution — DDD, EDD, TDD, security, observability** | Engineering, AI agents |
| **[templates/MODULE-DESIGN-PACK.md](./templates/MODULE-DESIGN-PACK.md)** | Pre-code design template (mandatory for new modules) | Engineering |
| **[CKAC-COMPLETE-GUIDE.md](./CKAC-COMPLETE-GUIDE.md)** | **Master guide — CEO + CPO + CTO** (strategy, product, architecture, build status) | CEO, CPO, CTO, Investors |
| **[CKAC-COMPLETE-GUIDE.pdf](./CKAC-COMPLETE-GUIDE.pdf)** | **Complete Executive Guide PDF** (portrait, v1.1) | CEO, CPO, CTO, Investors |
| **[CKAC-IMPLEMENTATION-GUIDE.md](./CKAC-IMPLEMENTATION-GUIDE.md)** | **What's built** — architecture, DB, flows, APIs, feature matrix mapped to benchmarks | Product, Engineering, CPO |
| **[AGENTS.md](../AGENTS.md)** | **Agent implementation spec — read before every code change** | AI agents, developers |
| **[DEVELOPMENT-PHASES.md](./DEVELOPMENT-PHASES.md)** | **Phased roadmap — TDD, EDD, DB schemas, sprints** | Engineering |
| [.cursor/rules/](../.cursor/rules/) | Cursor auto-applied rules (constitution, TDD/EDD, backend, frontend, security) | Cursor IDE |
| [CKAC-COMPLETE-PLANNING-BENCHMARK.md](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) | **Master plan** — all 48 features with user stories, acceptance criteria, DB schema, cache, events | Product, Engineering, DBA |
| [CKAC-SYSTEM-BENCHMARK.md](./CKAC-SYSTEM-BENCHMARK.md) | Architecture deep dive — services, scaling, SLOs, phases | CTO, Senior Engineers |
| [CKAC-CPO-PRODUCT-BLUEPRINT.md](./CKAC-CPO-PRODUCT-BLUEPRINT.md) | **CPO product blueprint** — modules, flows, pain points, solutions | CPO, Product |
| [CKAC-PRODUCT-DEPTH-GUIDE.md](./CKAC-PRODUCT-DEPTH-GUIDE.md) | Product depth guide (superseded by Complete Guide) | CPO, Product |
| [CKAC-PRODUCT-DEPTH-GUIDE.pdf](./CKAC-PRODUCT-DEPTH-GUIDE.pdf) | Product depth PDF (superseded by Complete Guide PDF) | CPO, Investors |
| [CKAC-PITCH-DECK.md](./CKAC-PITCH-DECK.md) | Investor pitch source (markdown, legacy) | CEO, Investors |
| [CKAC-PITCH-DECK.pdf](./CKAC-PITCH-DECK.pdf) | **CPO Product Blueprint PDF** (33 slides, v3.0) | CPO, Investors, Partners |

## Regenerate PDFs

```bash
# Complete executive guide — CEO + CPO + CTO (portrait)
python scripts/generate_complete_guide_pdf.py

# Product depth guide (legacy; use complete guide instead)
python scripts/generate_product_depth_pdf.py

# CPO pitch deck (33 landscape slides)
python scripts/generate_pitch_pdf.py
```

## Quick Stats

- **90+ tests** passing (Sprints 1–4 backend + notification support/tickets) — see [Complete Guide](./CKAC-COMPLETE-GUIDE.md)
- **Apps:** Portal :13000 · customer.kitchcu.in :13001 · kitchen.kitchcu.in :13002 · admin.kitchcu.in :13003
- **Stack:** React PWAs + Python FastAPI + PostgreSQL/PostGIS + Redis + Docker
- **Model:** Subscription SaaS, zero food commission
- **Brand:** **Kitchcu** (internal repo/schemas retain `ckac_*` identifiers)
