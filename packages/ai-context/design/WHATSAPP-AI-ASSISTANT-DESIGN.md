# Module Design Pack — WhatsApp AI Assistant (orders + menu + support)

**Feature ID:** F01 / F02 / F45 + Support AI · **Service owner:** `services/notification/` (+ `order`, `catalog` consumers)  
**Sprint:** training-context · **Author:** agent · **Date:** 2026-07-15  
**Branch:** `feature/whatsapp-ai-model-training`

---

## 1. Business understanding

- **Problem:** Owners get unstructured WhatsApp messages for orders and often post menus as free-text / media catalogs. Support chat must answer consistently and escalate tickets. Rule-based parsers miss nuance; LLM without grounding hallucinates commission/pricing.
- **Vision:** An **options-first** AI that (a) turns WA order messages into draft orders, (b) proposes menu dishes from business WA catalog text, (c) helps owners/customers via stable facts + tickets.
- **Business objective:** Faster order confirmation, faster menu go-live, fewer support tickets with wrong answers, higher trust.
- **Why now:** Webhook + draft parse + support KB exist; outbound Meta send and options UI are next growth unlocks.
- **KitchCu product gate:** Yes — WhatsApp-first growth without aggregator dependency; zero food commission preserved.

---

## 2. Challenge & improvement

- **Assumptions challenged:** Free-text LLM chat alone works on WhatsApp (it doesn't — use options). Order parse can be 100% LLM (no — keep deterministic matcher as source of truth; LLM assists structure).
- **Improvements over raw requirement:** Canonical FAQ `answer_id`s; option trees; separate menu-ingest vs order-intake; section assist map for owner dashboard.
- **Out of scope (explicit):** Live Meta Graph send (still simulated); restaurant POS/dine-in; training on real PII; auto-publishing dishes without owner confirm + live-capture media.

---

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|---------------|
| Home chef (owner) | Confirm WA orders fast | Customer texts → AI/options draft → owner confirms → lifecycle |
| Owner (menu) | Publish menu from WA catalog | Paste/forward catalog → AI dish proposes → owner edits + live photo → publish |
| Customer | Place order / get help | Options: Order / Status / Menu / Help → ticket if needed |
| Platform support | Resolve escalations | AI suggests ticket → admin queue |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Parse WA order text → structured items + notes + confidence | Must |
| FR-2 | Propose menu dishes from business WA catalog text | Must |
| FR-3 | Options-first replies (3–6 choices) for WA + portal chat | Must |
| FR-4 | Same intent/paraphrase → same canonical answer_id | Must |
| FR-5 | Suggest/create tickets with category + required fields | Must |
| FR-6 | Assist all owner dashboard sections with deep-links | Must |
| FR-7 | Never invent commission or restaurant POS features | Must |
| FR-8 | Owner must confirm drafts / dish publishes | Must |

---

## 5. Non-functional requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Support reply p95 | &lt; 2s KB; &lt; 6s LLM |
| NFR-2 | Tenant isolation | kitchen_id on all order/menu proposes |
| NFR-3 | PII | Mask phones in logs; no OTP/tokens in prompts |
| NFR-4 | Determinism | FAQ answers versioned; golden evals pass |

---

## 6. Business rules & validation

| Rule | Enforcement |
|------|-------------|
| Zero food commission | product_facts + system guardrails |
| Live-capture required for dish hero | catalog service; menu ingest marks `needs_live_capture` |
| Owner confirms order draft | order service confirm endpoint |
| Ticket categories closed set | tickets.py enums |
| Kitchen scoped by whatsapp_phone_id | notification handlers |

---

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Customer | Order options, status ask, ticket | Publish menu, see other kitchens' CRM |
| Owner | Confirm drafts, accept menu proposes, section help | Admin ticket queue |
| Admin | Tickets CRUD | Place orders as kitchen |
| AI | Propose structures, answers, options | Auto-confirm paid orders / auto-publish menu |

---

## 8. Domain model & bounded context

```
Aggregates: ProposedOrderDraft, ProposedDishDraft, SupportConversation, SupportTicket
Events (existing/target): whatsapp.message.received, order.draft.created,
  support.ticket.created, (future) menu.propose.created
```

---

## 9. API / integration (target)

| Step | System |
|------|--------|
| Inbound WA | notification webhook → handlers |
| Order structure | LLM/options → validated against menu → order draft |
| Menu propose | LLM extract → owner UI review → catalog POST dishes |
| Support | Load pack → options reply → ticket API |
| Outbound | Existing F45 templates (Meta send later) |

---

## 10. Test plan

- Golden FAQ paraphrases → same answer_id  
- Order parse few-shots → golden JSON  
- Menu ingest few-shots → dish fields  
- Options trees validate (unique ids, ≤6 options)  
- Ticket escalation phrases → suggest_ticket + category  

---

## 11. Rollout

1. Ship context pack (this branch)  
2. Wire `support.py` to load `product_facts` + FAQ yaml  
3. Add WA options dialogue adapter  
4. Menu propose API + owner review UI  
5. Eval harness in CI (`validate_pack.py` + goldens)  
