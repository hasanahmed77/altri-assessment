# Kanban

Deadline: **5 days**. Day 1 = S + M1 · Day 2 = M2 + start M3 · Day 3 = `v0.1` by midday + start M4 · Day 4 = `v0.2` · Day 5 = ship `v1.0`.
WIP limit: **1** card in progress. Move a card by moving its line. Commits reference the card id: `feat(A-07): ...`.

**Definition of Done:** acceptance criteria met · tests green · lint and types clean · no code I can't explain · committed with the card id.
**End of each milestone:** a short "Created / Edited" summary of every file and folder touched, one line each.

## In progress

## Ready

## Backlog

### M5 Ship → tag v1.0
- **S-12** Record the video (~10 min, script ready) · AC: repo is public and video unlisted; both links opened in a private window without signing in; video link added to the README
- **S-13** Rehearse: trace any recommendation from the screen to `finance.py` in under a minute
- Tag `v1.0` once the video link is in

## Done
- **R-03** "See N deals to send" on each Where to buy card opens Recommended filtered to that market, in ranked order, with a clear button · frontend only; checked in the browser, including a reaction while filtered and switching clients
- **R-02** "Fine managing a heavier renovation" no longer counts as wanting one: it shows as "Open to", with no nudge, because the profile's renovation appetite already scores it (LLM-11) · only C-02 and C-06 re-rank; no eligibility or alert changes · 95 tests
- **R-01** Deep review against the brief and every client's text: Part A recomputed independently (0 mismatches over 675 pairs); named markets now rank first; the "nothing in your markets" alert counts deals still to send and says how close the nearest miss is; quotes must mention what they support; client questions become alerts; signals panel grouped; no retry storm after a failed extraction; live comment → model → refreshed page verified in the browser · 94 tests, 20/20 evals on two runs
- **S-11** Fresh copy (only files git publishes, no `.env`): `docker compose up` healthy, signals `fresh` without a key, web 200, 90 tests pass
- **S-10** `docs/AI_LOG.md`: AI-01..08 and LLM-01..09, each with how it was caught
- **S-09** README, 2 pages at 11 pt; research with sources folded in (replaces S-15's separate notes)
- **B-13** Dropped: a Playwright smoke test would repeat the API integration tests; the demo flow was checked by hand in the browser
- **B-12** Re-extraction in the background after a comment (and after a page load that finds a changed hash), one per client at a time · AC met: integration test, thumbs without a comment make no call
- **B-11** Near misses: bisection price solver, ≤ 5% under asking, $1,000 steps; "Close call" first on Ruled out · AC met: C-13/D-138 passes at $960,000 (0.7% under); 4 unit tests
- **B-10** Signals panel with quotes and sources, status line, page refreshes every 2 s (max 5) while `updating`
- **B-09** Snapshot `0004_signals_snapshot.sql` written by the eval run with the real model · AC met: no key → signals `fresh`, a new comment → `stale` (integration test)
- **B-08** Evals: 18 cases in `backend/evals/cases.py`, `python -m evals.run` · AC met: 18/18 on two runs, $0.003 per client measured on gpt-5.4-mini
- **B-14** Switched from gpt-4.1-mini (deprecated) to gpt-5.4-mini; snapshot `0005` as an upsert migration; polarity in the schema, deal and profile consistency checks
- **B-07** `GET /clients/{id}/markets` + "Where to buy" tab, opened first when the client is undecided or their markets have nothing eligible · AC met: C-12 sees ranked markets with reasons
- **B-06** Alerts: deadline, spoken cash limit, budget vs range, co-host with 0% fee, unmatched terms, nothing in preferred markets, unmet must-have, undecided
- **B-05** Signals in scoring (must-haves, avoided traits and markets, mentioned markets, soft cap, feedback readings) · AC met: C-02/D-145 not penalized; C-03 gets Bradenton first; C-09 party markets drop
- **B-04** `services/signals.py`: content-hash cache, upsert, usage stored · AC met: unchanged hash makes 0 extractor calls (integration test)
- **B-03** `OpenAIExtractor` (Structured Outputs, temperature 0, timeout + 1 retry) + fake for tests; tests force a blank key
- **B-02** Signals schema (closed traits, market-id enum) + grounding that re-cites a misattributed quote · AC met: a non-verbatim quote is dropped (unit + integration tests)
- **B-01** Migration `0003_client_signals.sql`
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
