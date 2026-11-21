# Kanban

Deadline: **5 days**. Day 1 = S + M1 · Day 2 = M2 + start M3 · Day 3 = `v0.1` by midday + start M4 · Day 4 = `v0.2` · Day 5 = ship `v1.0`.
WIP limit: **1** card in progress. Move a card by moving its line. Commits reference the card id: `feat(A-07): ...`.

**Definition of Done:** acceptance criteria met · tests green · lint and types clean · no code I can't explain · committed with the card id.
**End of each milestone:** a short "Created / Edited" summary of every file and folder touched, one line each.

## In progress

## Ready

## Backlog

### M4 Part B → tag v0.2
- **B-01** Migration `0003_client_signals.sql`
- **B-02** Signals schema (Pydantic, closed vocabulary, market-id enum) + grounding validator · AC: a non-verbatim quote is dropped (unit test)
- **B-03** `OpenAIExtractor` (Structured Outputs, temperature 0, timeout + retry) + test fake; no key → signals marked stale
- **B-04** `services/signals.py`: content-hash cache, upsert, usage logging · AC: an unchanged hash makes 0 extractor calls (integration test)
- **B-05** Signals in scoring: must-haves, avoid traits, soft cap, feedback readings · AC: C-02/D-145 not penalized; C-05 waterfront deals rise; C-09 party markets drop
- **B-06** Alerts: deadline, conflicts, unresolved terms, no-match-in-preferred, deal data flags
- **B-07** `GET /clients/{id}/markets` + "Where to buy" tab · AC: C-12 sees ranked markets with rationale
- **B-08** Evals: `tests/evals/cases.yaml` (12 cases) + `make eval` · AC: pass rate reported
- **B-09** Generate `0004_signals_snapshot.sql` with the real model · AC: the stack works with no API key
- **B-10** Signals panel in UI with quotes + sources; while `signals_status` is `updating`, show a badge and refresh (max ~5 tries) · AC: after a commented 👎, re-ranked signals appear without a manual reload
- **B-11** Near misses: gap ("needs $X more", "2.9% vs 3%") + price solver by bisection · AC: C-13/D-138 shows the price that pencils; unit tests on the solver
- **B-12** Re-extraction after POST /feedback via `BackgroundTasks`, only when the comment is non-empty
- **B-13** Stretch, day 5 morning only if ahead: Playwright smoke test of the demo flow, local only (not in CI)
- Tag `v0.2`

### M5 Ship → tag v1.0
- **S-09** README ≤ 2 pages: run, how it works + why (incl. schema changes and why), research + sources + what changed my thinking, assumptions, questions for v2, next steps, AI usage + measured cost per client; links to DESIGN.md and AI_LOG.md for depth
- **S-15** Research notes kept as you go in `prep/RESEARCH.md` (topic, source link, what changed) · AC: feeds the README research section
- **S-10** `docs/AI_LOG.md` finalized (at least one "AI got it wrong" story)
- **S-11** Fresh clone on a clean machine: compose up + test command
- **S-12** Video script, recording (~10 min) · AC: repo is public and video unlisted; both links opened in a private window without signing in
- **S-13** Rehearse: trace any recommendation from the screen to `finance.py` in under a minute

## Done
- **A-19** Part A audit against the brief: independent recompute of all 675 client×deal pairs (numbers + rule codes) from the raw JSON matches the API exactly; "All" shown as "open to any market"; mypy now covers `tests/`
- **A-14** Layout: client sidebar + `/clients/[id]` with parallel server fetches
- **A-15** Client summary card + feedback history
- **A-16** Deal card: cash needed, CoC L/M/H, explanation, flags; Recommended (top 5 + show all) / Already shared / Excluded tabs
- **A-17** Feedback form: Server Action → POST → revalidate; pending and error states; toast
- **A-18** Fresh-copy test: only git-published files, no `.env` → `docker compose up` healthy, rep screen 200, local DB used, 52 tests pass · tag `v0.1` on commit
- **A-07** Golden snapshot `tests/golden/eligibility.json` for all 15 clients · built from the database (covers migrations too) · AC: matches the analysis script; all 15 clients cross-checked on day 1 (11/22/14/8/25/18/9/14/15/14/19/23/32/7/22)
- **A-08** `db.py`, `repository.py`; reference data loaded once in lifespan · AC: 1 query per recommendations request (asserted in a test); clients are reference data too
- **A-09** `GET /clients`, `GET /clients/{id}` · AC: 404 for unknown id; feedback newest first
- **A-10** `GET /clients/{id}/recommendations` · AC: every eligible deal in `ranked` (with status), excluded with all rule codes, messages and numbers; `ranked ∪ excluded` = 45, disjoint
- **A-11** `POST /feedback` · AC: 201; 404 unknown ids; 422 bad reaction; comment trimmed, ≤ 1,000 chars
- **A-12** Integration test: the feedback loop, on a dedicated test DB · AC: POST 👎 then GET shows the deal as already_shared/down and a same-market deal's score dropped
- **A-13** Next.js + Tailwind + shadcn init; `gen:api` from OpenAPI; add `web` to compose · AC: `tsc` strict passes
- **S-14** Supabase push spike · result: the seed's own BEGIN/COMMIT works with `supabase db push` (CLI 2.122.1, `--db-url`); no fallback needed
- **S-06** Hosted Supabase (Postgres 17, session pooler over IPv4) · AC met: 45/15/14/69/20 rows, migration history recorded, RLS on all 7 tables, public REST API returns `[]` for every table and the view; Docker api connects through the pooler
- **S-07** `docker-compose.yml` with db (Postgres 17, migrations mounted, no host port) + api, healthchecks · AC met: fresh volume → migrations applied, `/health` ok, `docker compose run --rm api pytest` passes · web service joins with A-13
- **S-08** CI: backend lint, format, strict types, tests + a migrations job on Postgres 17 · AC: green on GitHub after push; day 2 adds integration tests and frontend checks
- **S-02** Repo skeleton (`backend/`, `frontend/`, `supabase/migrations/`, `docs/`) + `.gitignore`, `.env.example` · AC: no secrets tracked
- **S-03** `docs/DESIGN.md` v1: architecture, decisions (alternatives + why), assumptions · AC: one page
- **S-04** Migration `0001_provided_seed.sql` = provided seed byte-for-byte; SHA-256 recorded · AC: checksum matches original
- **S-05** Migration `0002_reference_mappings.sql`: `market_towns` (+ aliases), `deals.market_id NOT NULL`, `deals.property_key`, `market_aliases`, `client_market_refs` view, indexes, RLS on all tables · AC: applies cleanly on Supabase and on local Postgres; all 45 deals mapped; D-116 and D-126 share a property_key
- **A-01** `domain/models.py` frozen dataclasses · AC: no framework imports in `domain/`
- **A-02** `finance.py`: cash needed, annual debt service, cash flows, CoC · AC: golden C-01×D-126 = $235,295 and 11.3/16.9/22.5%; $100K at 6%/30y = $599.55/mo (pins monthly amortization); Hypothesis monotonicity tests
- **A-03** `rules.py`: OVER_BUDGET, AVOIDED_MARKET, TOO_FEW_BEDROOMS, BEDROOMS_UNKNOWN, DOES_NOT_PENCIL (lifestyle branch), all violations collected, messages with numbers, unrounded comparisons · AC: synthetic boundary tests (exactly 10% over, exactly 3%, cash flow exactly 0) + real pairs C-03×D-132 (2.993% → out), C-04×D-136 ($600 over strict → out), C-02×D-127 and C-07×D-140 (just inside → in)
- **A-04** `tags.py`: closed-vocabulary maps for 21 highlights, 12 notes, 15 setup items; market traits · AC: every value in the data maps (test fails on unknown text)
- **A-05** `feedback.py`: latest reaction per deal (by id), property siblings, affinity · AC: C-15/D-101 counts as up; reacting to D-126 marks D-116 already_shared
- **A-06** `scoring.py`: focus strategies, preference score, reasons → explanation · AC: deterministic order, tie-break by id; each focus tested
