# Design

A tool for STR Search acquisitions reps: show each client fewer, better-fit deals, explain why, and help clients who are unsure where to buy.

## Architecture

```
Next.js rep screen (App Router, Server Components, Server Actions, shadcn/ui)
        │ typed HTTP (types generated from the API's OpenAPI schema)
        ▼
FastAPI ─ api/ ─ services/ ─ domain/  (pure business logic)
             │        └─ llm/ SignalExtractor ─► OpenAI (small model)
             ▼
        repository.py ─► Postgres
                          ├─ hosted Supabase project (development, demo)
                          └─ local Postgres container (reviewers: docker compose up)
```

**Functional core, imperative shell.** Deal math, hard rules, ranking, feedback effects, market fit and alerts are pure functions over immutable data. The shell (routers, services, repository) loads data, calls the core and serializes the result. The logic that matters is tested in milliseconds and can be explained without any framework.

## Decisions

Each entry: what was decided, what else was considered, and why. New decisions are appended; superseded ones are marked, not deleted.

### D-01 Hard rules and math in code; the LLM only reads text
- **Decision:** Eligibility, money math and ranking are deterministic code. An LLM only turns free text (comments, call summaries, notes) into structured signals.
- **Alternatives:** an LLM ranks deals directly; rules only, no LLM.
- **Why:** Reps must defend every suggestion to clients investing $200K+. Deterministic rules are testable and reproducible. Rules alone can't read sarcasm ("I'd love to fix a 1970s kitchen… Pass"), a "down" that means "bad timing", or a preference change mentioned on a call.

### D-02 Hosted Supabase as the main database; plain Postgres container for reviewers
- **Decision:** Development and the demo use a hosted Supabase project. `docker compose up` starts a plain Postgres container (same major version) and runs the **same** migration files from `supabase/migrations/`.
- **Alternatives:**
  - reviewers connect to the hosted project
  - self-hosted Supabase (`supabase start`, about ten containers)
  - plain Postgres only
- **Why not point reviewers at the hosted project:**
  - it needs credentials, which must never be in a public repo
  - reviewers' feedback would write into the shared demo database and interfere with each other
  - free-tier projects can be paused when idle
  - the reviewer's run would depend on the network and on my account
  - deployment is out of scope
- **Why not self-hosted Supabase:** the backend talks plain SQL to Postgres and uses no Supabase-only service (no Auth, Realtime, Storage or Edge Functions). A ten-container stack would slow the one-command start for no benefit.
- **Why Supabase at all:** managed Postgres with a dashboard, migration tooling (`supabase db push`) and row-level security, and the brief lists it as a plus.

### D-03 Row-level security on, no policies
- **Decision:** RLS is enabled on every table with no policies, and views are created `WITH (security_invoker = true)`.
- **Why:** The backend connects as the database owner and is unaffected. Supabase's public REST API, reachable with the anon key, can read and write nothing. A plain view runs with its owner's rights and would bypass RLS, so views must run with the caller's rights.

### D-04 Provided seed kept byte-for-byte; schema changes are additive
- **Decision:** Migration `0001` is the provided `seed.sql`, unchanged (SHA-256 recorded). Later migrations only add.
- **Why:** Results are checked by record id, so ids and raw values must provably match the source. Messy values (NULL bedrooms, conflicting budget range) are handled in code and flagged, never "fixed" in the data.

### D-05 Normalize only what the rules depend on
- **Decision:** Add `deals.market_id` (NOT NULL), a town-to-market table with explicit aliases, a market-alias table and a view that resolves each client's preferred and avoided markets to market ids. Keep setup items, comps, revenue and highlights as JSONB.
- **Why:** Deals link to markets only by a city string ("St. Augustine", "Mc Gaheysville" and "Lake Harmony" don't match the market town lists), and client preferences are free text ("Florida", "Smokies", "Upstate NY"). The avoided-market rule needs exact matches. JSONB details are always read together with their deal and never queried alone, so splitting them would add joins with no benefit. NOT NULL makes setup fail loudly if a city is unmapped.

### D-06 Same property, multiple underwriting plans
- **Decision:** `deals.property_key` (generated from the normalized address). Each house appears once at the top: its best-scoring plan leads and the other plans follow as `alternative_plan`. Once a client reacts to any plan, all plans of that house are `already_shared`.
- **Why:** D-116 and D-126 are one house with two renovation plans. A client was shown both and asked, "Same house as before?"

### D-07 Unknown bedroom count is not recommended
- **Decision:** A deal with NULL bedrooms is excluded with the code `BEDROOMS_UNKNOWN`; the flag mentions the projected count from its highlights.
- **Why:** "Never recommend a deal that breaks a hard rule" can't be guaranteed when the value is missing. The conservative choice is visible to the rep and is listed as a question for STR Search.

### D-08 Latest reaction wins, ordered by id
- **Decision:** For each client and deal, the reaction with the highest feedback id is the current one. History is kept.
- **Why:** Clients change their minds (C-15 on D-101). `created_at` is a date, so two reactions on one day would tie; the serial id is strictly increasing.

### D-09 Ranking: focus metric + preferences + feedback, explained by the same numbers
- **Decision:** `score = w_focus × focus + w_pref × preferences + feedback affinity`, with weights 0.7/0.3 for cash flow, tax savings and appreciation and 0.3/0.7 for lifestyle. The focus metric is one pure function per `main_focus` (Strategy). Preferences are a weighted average of only the preferences the client stated: market 0.35, setting 0.30, wow factors 0.15, renovation fit 0.10, turnkey 0.10 (where the house is matters more than how it's finished). Every term emits a reason; the explanation leads with the focus reason.
- **How it was tuned:** with equal preference weights, a lifestyle client's preferred-market deal lost to a higher-earning deal elsewhere (a unit test written from intent caught it).
- **Why:** The explanation is generated from the numbers that produced the rank, so it can't contradict it, and templated text costs nothing and can't invent figures.

### D-10 Reference data loaded once; three queries per recommendation request
- **Decision:** Markets, deals and mappings are loaded at startup. A recommendations request makes three indexed queries for one client: profile, feedback, signals.
- **Why:** Editing deals, clients and markets is out of scope, so this data never changes at runtime. If it became editable, an ETag or TTL cache would replace this.

### D-11 LLM calls only when a client's text changes
- **Decision:** Signals are cached per client with a hash of the prompt version plus all of that client's text. Extraction runs only when the hash changes: never on page loads, never for a thumbs click without a comment. It runs in the background after the feedback is saved, so the write never waits on or fails because of the LLM.
- **Why:** Cost and reliability. Real token usage is stored per extraction, so the cost per client in the README is measured, not estimated.

### D-12 Grounded, closed-vocabulary signals
- **Decision:** The OpenAI response uses a strict JSON schema. Traits come from the same tag vocabulary as deals; markets come from an enum of the 14 market ids. Every signal must include a quote that appears verbatim in its cited source, or it is dropped.
- **Why:** This prevents invented preferences or markets, lets the rep verify each signal, and makes signals directly comparable with deal tags.

### D-13 Deal tags from a lookup table, not an LLM
- **Decision:** Deal highlights, notes and setup items map to tags through a fixed table in code.
- **Why:** Deal text is a closed vocabulary (21 highlights, 12 notes, 15 setup items across 45 deals). A lookup table is exact, free and testable; an LLM would add cost and variance for nothing.

### D-14 Works without an API key
- **Decision:** Signals extracted by the real model are committed as a migration snapshot. Without `OPENAI_API_KEY`, new comments leave a client's signals marked stale; the deterministic feedback effects still apply.
- **Alternatives:** a keyword-based fallback extractor.
- **Why:** Reviewers can run everything, including Part B, with one command and no secrets. A keyword fallback would re-extract the client's whole history and overwrite good signals with worse ones (it reads "I'd love to fix a 1970s kitchen" as positive), and it is code to maintain for little value.

### D-15 Floats for money math, rounded at the API boundary
- **Decision:** Calculations use floats; responses round dollars to cents and ratios to four decimals.
- **Why:** Inputs are estimates with ±10% bands; float error is around 1e-12. `Decimal` would make the amortization formula harder to read with no practical gain.

### D-17 Every eligible deal is returned in `ranked`
- **Decision:** Feedback never removes an eligible deal from `ranked`; it changes the deal's score and status (`new` / `already_shared`). `ranked` and `excluded` together always contain all 45 deals exactly once.
- **Alternatives:** a separate "already shared" list outside `ranked`.
- **Why:** Results are checked by id. Hiding an eligible deal would look like a wrong exclusion. The frontend still groups deals by status.

### D-18 Rules compare unrounded values
- **Decision:** Rounding happens only when serializing the response.
- **Why:** 21 client × deal pairs are within 0.2 points of the 3% threshold and 10 are within 1% of the budget cap (e.g. C-03 × D-132 at 2.993%, C-04 × D-136 $600 over a strict $200K). Rounding first would flip real decisions.

### D-16 Endpoint paths exactly as the brief
- **Decision:** No `/api/v1` prefix; required paths unchanged; additions are `/clients/{id}/markets` and `/health`.
- **Why:** The brief fixes the paths, and the reviewers may call them directly.

## Assumptions
- `clients.budget` is authoritative when it conflicts with `budget_range` (C-03, C-06, C-09); the conflict is shown to the rep.
- Debt service is the 30-year loan's monthly payment × 12 (standard US amortization). Reading "yearly payment" as one annual payment would flip 9 eligibility decisions, so this is the first question sent to STR Search.
- "Flexible" means up to and including 10% over; exactly 3% CoC on low revenue passes; lifestyle cash flow of exactly 0 passes.
- "Lake Harmony, PA" belongs to the Poconos market.
- "Upstate NY" means the Catskills and Finger Lakes markets; "Florida" means all four Florida markets.
- Unmatched market terms ("Charlotte", "Texas Hill Country") don't restrict anything; they are shown to the rep.
- A thumbs down without a comment is a plain negative.

## Out of scope (per the brief)
Authentication, deployment, the client-facing portal, and creating or editing deals, clients or markets.
