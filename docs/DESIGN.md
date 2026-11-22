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

### D-10 Reference data loaded once; two queries per recommendation request
- **Decision:** Markets, deals, clients (with their resolved market preferences) and call summaries are loaded at startup. A recommendations request makes two indexed queries: that client's feedback and their stored signals. `POST /feedback` validates ids in memory, then makes one insert. A test asserts the query count.
- **Why:** Editing deals, clients and markets is out of scope, so this data never changes at runtime. If it became editable, an ETag or TTL cache would replace this.

### D-11 LLM calls only when a client's text changes
- **Decision:** Signals are cached per client (`client_signals`) with a hash of the prompt version, the model and all of that client's text (notes, calls, feedback comments). Extraction runs only when the hash changes: never for an unchanged page load, never for a thumbs click without a comment. It runs as a FastAPI background task after the feedback is saved, so the write never waits on or fails because of the LLM. A page load that finds a changed hash schedules the same task, so a missed extraction heals itself; an in-process set keeps it to one extraction per client at a time. Status is derived, not stored: `fresh`, `updating`, `stale` (no key) or `unavailable`. While `updating`, the page refreshes itself every 2 s, at most 5 times.
- **Why:** Cost and reliability. Real token usage is stored per extraction, so the cost per client in the README is measured, not estimated.

### D-12 Grounded, closed-vocabulary signals
- **Decision:** The OpenAI response uses a strict JSON schema (Structured Outputs). Traits come from a closed list of 17 (`domain/signals.py`), each decided on deals by code from deal tags or market data; markets come from an enum of the 14 market ids. Every signal must quote the client's words verbatim (case, spacing and curly quotes normalized), or it is dropped and logged. Code, not the model, settles the citation: a copied header like `[call:2026-09-10] Call on…` resolves to its id, and a real quote cited to the wrong source is re-cited when exactly one source contains it.
- **Direction is in the schema:** the wish list offers 15 traits and the avoid list 9; nobody avoids privacy or views and nobody wants a party crowd, so the model can't return those (LLM-07). A thumbs-down comment can only avoid a feature the house actually has (LLM-08).
- **Why:** This prevents invented preferences or markets, lets the rep verify each signal, and makes signals directly comparable with deals. The model only reads; code decides what a signal means for a deal.

### D-13 Deal tags from a lookup table, not an LLM
- **Decision:** Deal highlights, notes and setup items map to tags through a fixed table in code.
- **Why:** Deal text is a closed vocabulary (21 highlights, 12 notes, 15 setup items across 45 deals). A lookup table is exact, free and testable; an LLM would add cost and variance for nothing.

### D-14 Works without an API key
- **Decision:** Signals extracted by the real model are committed as a migration snapshot (`…0004_signals_snapshot.sql`, written by `python -m evals.run --snapshot`). Without `OPENAI_API_KEY` they are served as `fresh`; a new comment marks them `stale`, and the deterministic feedback effects still apply.
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

### D-19 Each integration test gets its own database
- **Decision:** The migrations are applied once to a template database; each test clones it (`CREATE DATABASE … TEMPLATE`, milliseconds) and drops it afterwards. The fixture refuses any host other than localhost or the compose `db`.
- **Alternatives:** one shared database with cleanup; transactions rolled back after each test.
- **Why:** Tests run against real Postgres and real migrations, can't affect each other, and can never touch Supabase. Rollback-based isolation breaks as soon as the code under test commits, which `POST /feedback` does.

### D-20 Frontend scaffold and dependencies
- **Decision:** Next.js 16 (`create-next-app`), shadcn/ui with Radix primitives, API types generated from FastAPI's OpenAPI schema (`npm run gen:api`) and committed. The lockfile is generated with the same npm as the Docker build image.
- **Why:** Generated types make the frontend fail to compile when the API changes shape. A lockfile made by a different npm version (10.9.2 locally vs 10.9.9 in `node:22`) resolved one nested package differently and broke the strict `npm ci` build.
- **Known advisory:** a moderate `minimatch` advisory sits in the shadcn CLI's code-generation tooling (`ts-morph`), not in code the app runs; npm's only automatic fix downgrades shadcn to 1.0.0, so it is left as is. shadcn's `cn` package was checked: published from `shadcn-ui/cn` by GitHub Actions with build provenance.

### D-21 Rep screen: fresh data streamed into a static shell
- **Decision:** With Next.js Cache Components, pages are not async: the layout and page shell render immediately and the client's data loads inside `<Suspense>` on every request (nothing is cached). Feedback is a Server Action that posts to the API and calls `refresh()`. The browser never calls FastAPI.
- **Why:** Recommendations change with every piece of feedback, so caching them would show stale rankings. `refresh()` re-renders with fresh server data in the same round trip. Server-side calls mean no CORS and no public API address.
- **Trade-off:** Because the shell is already streaming, an unknown client id shows the not-found page with HTTP 200 instead of 404. The API itself returns a proper 404.
- **Display:** cards are numbered by position within their tab ("#1" is the first deal to send), and the top 5 are shown before "show more", so the rep sees a short list first.

### D-22 Signals nudge the ranking; they never exclude
- **Decision:** Fixed, documented weights in `domain/signal_fit.py`: must-have met +0.10, missing −0.15, avoided trait −0.40, market the client spoke against −0.40, over a spoken cash limit −0.30. A spoken limit counts only if it is below the profile cap and isn't the profile budget said again (LLM-06). A reading that contradicts the profile (avoiding a heavy renovation when the profile says heavy, avoiding the #1 setting) or another reading (a trait both wanted and avoided) doesn't move the ranking; the rep gets a "confirm with the client" alert with the quote (LLM-09). A market the client mentioned counts like a profile market. Each adjustment is a reason on the card with the client's quote and its source.
- **Why:** Hard rules come from the structured profile, which the client signed off; a model's reading of a comment is not strong enough to hide a deal. A −0.40 sinks a deal without removing it, and the rep sees why.

### D-23 The model classifies; code decides what it means
- **Decision:** Each feedback comment gets a sentiment and a reason from a closed list. A reason of `timing` or `undecided` makes that reaction count zero, whatever sentiment came with it: the house isn't held against similar deals and a passed deal isn't penalized.
- **Why:** In the first eval run the model labelled "Just bad timing for us this month" as reason `timing` but sentiment `negative`, against the prompt (LLM-02). The same pattern held for cash limits (LLM-06). Classification is what models are good at; the business rule belongs in code, where it is tested.

### D-24 Where to buy is arithmetic, not an LLM
- **Decision:** `GET /clients/{id}/markets` ranks all 14 markets: setting rank 0.35, profile or mentioned market 0.25, eligible deal count (capped at 5) 0.20, median CoC on low revenue 0.20, plus market-level signals (a party crowd, a short drive from NYC, a lake/mountain setting). Markets with nothing to buy and avoided markets go last. The tab opens first when the client hasn't picked a market or their markets have nothing eligible.
- **Why:** It must be reproducible and explainable, and it is counting.

### D-25 Near misses: a price, not a rule change
- **Decision:** A deal excluded only by money rules (over budget, doesn't pencil) gets the highest round price ($1,000 steps) at which it passes every rule, found by bisection, if that is within 5% of asking. Shown on the Ruled out tab, first, as "Close call", with the analyst's note when the seller is negotiable.
- **Why:** A lower price moves cash needed and debt service together, so there is no closed form; bisection is exact enough in 40 steps. 5% keeps it to real negotiation leads (29 across all clients; 82 at 10%). The rules are untouched.

### D-26 Alerts before deals
- **Decision:** Deterministic checks, most pressing first: deadline (urgent within 30 days), a spoken cash limit below the profile cap, profile budget outside the stated range, a co-host mentioned with a 0% fee, unmatched market terms, nothing eligible in the client's markets, a must-have no eligible deal offers, and no market chosen.
- **Why:** These are the things a rep must fix or ask about before sending anything, and each is a conflict between two pieces of data, which code can detect exactly.

### D-27 Model and evals
- **Decision:** `gpt-5.4-mini` by default (`OPENAI_MODEL`), temperature 0, 1,500 output tokens max, 30 s timeout and one retry. `python -m evals.run` checks 18 labelled cases from the real data against the real model; it is not in CI.
- **Alternatives:** `gpt-4.1-mini` passed the same evals at half the price ($0.0013 per client) but OpenAI lists it as deprecated; `gpt-5-mini` rejects temperature 0.
- **Why:** The task is short extraction into a fixed schema, so a small model is enough. Measured: about 2,000 input and 270 output tokens per client, $0.003 per client ($0.75 / $4.50 per million tokens), 18/18 cases on two consecutive runs. gpt-5.4-mini also stopped quoting source headers, which gpt-4.1-mini did on every run. The cases were also used to fix the prompt, so they are a regression suite, not a held-out score. A newer snapshot is a new upsert migration (`…0005`), never an edit to an applied one.

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
