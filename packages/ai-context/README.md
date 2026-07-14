# kitchCU AI Context Pack — WhatsApp + Support Assistant

**Branch intent:** `feature/whatsapp-ai-model-training`  
**Purpose:** Canonical context for training / grounding an **options-focused** assistant that:

1. Reads WhatsApp messages → extracts **orders** and related fields  
2. Reads business WhatsApp catalog/service posts → proposes **menu / dish** drafts  
3. Answers support questions with **stable answers** (same question → same facts)  
4. Escalates to **tickets** with correct category + required fields  
5. Assists owners across **all kitchen.kitchcu.in sections**

This pack is the single source of truth for prompts, FAQs, option trees, and few-shot examples. Runtime code in `services/notification` / `services/order` should **load** from here (or stay keyword-KB until wired) — do not invent pricing, commissions, or POS features.

---

## Layout

```text
packages/ai-context/
  README.md                          ← you are here
  design/
    WHATSAPP-AI-ASSISTANT-DESIGN.md  ← MODULE design pack
  prompts/
    system/
      core_guardrails.md             ← product laws + thinking loop
      owner_support.md
      customer_support.md
      whatsapp_order_intake.md
      whatsapp_menu_ingest.md
      ticket_escalation.md
    thinking/
      reason_then_options.md         ← how to think before answering
  knowledge/
    product_facts.yaml               ← canonical facts (pricing, domains…)
    faq/owner.yaml
    faq/customer.yaml
    sections/owner_dashboard.yaml    ← assist every owner section
  intents/
    registry.yaml                    ← intent → options → tools
  menus/                             ← WhatsApp-style option trees
    kitchen_main.json
    customer_main.json
    order_flow.json
    menu_ingest_flow.json
    ticket_flow.json
  fewshot/
    order_parse_examples.jsonl
    menu_ingest_examples.jsonl
    support_dialogues.jsonl
  evals/
    support_golden.json
    order_parse_golden.json
    options_tree_golden.json
  scripts/
    validate_pack.py
```

---

## Interaction style (options-first)

Default reply shape for chat + WhatsApp:

1. **One short answer** grounded in `product_facts.yaml` / FAQ answer_id  
2. **Numbered options** (3–6) for next step  
3. Optional **quick tip** / safety  
4. If escalated → ask only missing ticket fields, then confirm before create

Never dump long essays on WhatsApp. Portal chat may use short markdown + options.

---

## Consistency rule (same question → same answer)

Every FAQ entry has an `answer_id`. The model must:

- Detect paraphrase → map to `answer_id`  
- Copy **canonical_answer** (or paraphrase lightly without changing facts)  
- Attach the same `option_set_id` so follow-ups stay stable  

See `prompts/thinking/reason_then_options.md`.

---

## Pipelines

| Pipeline | Input | Output | Downstream |
|----------|-------|--------|------------|
| Order intake | Customer WA text | Structured draft items + notes | `order` parser / draft confirm |
| Menu ingest | Owner business WA catalog posts | Dish propose drafts | Owner review → `catalog` dishes |
| Support | Audience + message + history | Reply + options + ticket suggest | `/support/chat`, `/support/tickets` |
| Section assist | Owner asks about a dashboard area | Guided options for that section | Link to kitchen.kitchcu.in paths |

---

## Validation

```powershell
python packages/ai-context/scripts/validate_pack.py
```

---

## Privacy

- Training examples must use **fictional** phones (`+9198XXXXXXXX`) and kitchen codes (`CKPNQ001`).  
- Logs must mask OTP, tokens, and full phone numbers (engineering standards §10).

---

## Related code

| Area | Path |
|------|------|
| Support KB + optional LLM | `services/notification/app/support.py` |
| Tickets | `services/notification/app/tickets.py` |
| WA webhook | `services/notification/app/whatsapp.py`, `handlers.py` |
| Order parse | `services/order/app/parser.py` |
| Catalog dishes | `services/catalog/app/schemas.py` |
| UI chat | `apps/website/src/components/SupportChat.tsx` |
