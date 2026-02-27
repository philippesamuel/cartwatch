# cartwatch Roadmap

## V1 — Personal Finance Engine (MVP, ~4-6 weeks)

Goal: Works for me

Gmail ingestion → PydanticAI extraction → normalized Supabase
Canonical product matching (LLM-assisted)

- [x] Project scaffold
- [x] Supabase schema
- [ ] Gmail ingestion (on-demand, user-triggered)
- [ ] Receipt extraction (PydanticAI + Claude)
- [ ] Price per unit normalization (€/kg, €/L)
- [ ] Product reconciliation (async, confidence-scored)
- [ ] FastAPI backend (auth, receipts, products)
- [ ] Basic dashboard (Nuxt UI): spending over time, price history per product, store comparison for a given cart

Deliverable: "Here's what milk costs at REWE vs Lidl over 6 months, based on my real receipts."

## V2 — Community Price Index (network effect, ~4-6 weeks)

Goal: Convince others to join. Data is anonymized and shared.

- [ ] Multi-user auth (Supabase Auth + Google OAuth)
- [ ] Gmail Pub/Sub real-time ingestion
- [ ] Anonymized community prices layer
- [ ] Personal vs community inflation index
- [ ] Cross-store price optimizer

Anonymized shared community_prices layer — your receipt stays private, prices become public
Personal vs community inflation index
"Would you have saved?" cross-store optimizer

Deliverable: "Join and see how your grocery inflation compares to others in Berlin."

## V3 — Household Ops + Tandoor (daily utility, ongoing)

- [ ] Tandoor recipe sync -> ingredient mapping to canonical products
- [ ] Shopping list optimizer (recipe + inventory → cheapest store)
- [ ] Inventory tracking (purchased - consumed)
- [ ] Meal planning cost estimation

## Technical Debt / Future

- [ ] Gmail Pub/Sub (replace on-demand polling)
- [ ] Federated community price pool (self-hosted instances contribute)
- [ ] Grocy sync (optional integration)
- [ ] Mobile app
