# STR Search: client deal recommendations

Fewer, better-fit deals per client, with reasons, and help for clients unsure where to buy. Next.js + shadcn/ui, FastAPI, Postgres (Supabase or local), OpenAI. [Architecture diagram](docs/architecture.pdf). Video: _[link]_

## Run it
```bash
docker compose up                    # http://localhost:3000 (API docs: :8000/docs)
docker compose run --rm api pytest   # 95 tests, against a throwaway local database
```
No `.env` needed: compose runs its own Postgres, and the model's extracted signals ship as a migration. Optional (`.env.example`): `DATABASE_URL` for Supabase; `OPENAI_API_KEY` to read new comments live and run the evals (`python -m evals.run`).

## How recommendations work, and why
**Part A is arithmetic.** Deal numbers are computed per client (their down payment and co-host fee). Four hard rules exclude a deal and list every rule it breaks: over budget (+10% if flexible), avoided market, too few bedrooms, doesn't pencil. The rest are ranked, deals in markets the client named first, by a score whose parts are also the explanation lines:

- **Main focus, 70%** (30% for lifestyle): downside-weighted CoC; tax savings per dollar invested; equity growth plus CoC; low-case cash flow.
- **Preferences, 30%** (70% for lifestyle): market, setting rank, wow factors, renovation appetite, turnkey.
- **Feedback:** latest reaction wins; a reacted deal (and the other plan for the same house) moves to "Already shared"; similar deals rise or fall.

**Part B reads what clients say.** C-03 said "Leaning beach. Not interested in mountain cabins" and still got a Poconos house first. An LLM turns notes, calls and comments into **signals** from a closed list (wants, avoids, markets, a spoken cash limit, a deadline, co-host plans, why each comment was up or down). Code decides what they mean:

- **Every signal quotes the client word for word, and the quote must mention what it supports**, or it is dropped; the rep sees the quote on every card it touches.
- **Signals nudge, never exclude.** Readings that contradict the profile or each other become "confirm with the client" alerts. The model labels *why* a client passed; code decides that "bad timing" isn't held against the house.
- **Alerts** first: questions the client asked (C-15: "can we get a walkthrough video?"), C-13's 1031 deadline, budget vs stated range, a 0% co-host fee.
- **Where to buy:** 14 markets ranked by setting, preferences and buyable deals; shown first to undecided clients (C-12).
- **Close calls:** a deal excluded only for money shows the highest price that passes every rule, within 5% of asking (bisection). C-13's D-138 passes at $960,000.

Why: a rep must defend every deal to someone spending $200K+, so rules and arithmetic decide and the LLM only reads, with the client's words attached. C-03 now gets Bradenton first.

## What I researched, and what changed
- **"STR loophole"** ([CBIZ](https://www.cbiz.com/insights/article/short-term-rental-tax-strategy-unlocking-tax-savings), [JofA](https://www.journalofaccountancy.com/issues/2000/jan/shorttermrentalsclassifiedaspassiveactivitylosses.html)): stays of 7 days or less plus material participation let STR losses offset W-2 income (C-02). A co-host makes that harder. **Changed:** C-09's tax savings may not apply, so it's a question below, not an invented rule.
- **Bonus depreciation** ([RSM](https://www.rsmus.com/insights/services/business-tax/obba-tax-bonus-depreciation)): back to 100% after Jan 19, 2025. **Changed:** the large year-1 tax numbers looked like a data error; they're plausible, so tax-focused clients rank on them as given.
- **1031** ([CBIZ](https://www.cbiz.com/insights/article/1031-exchange-deadlines-45-day-and-180-day-rules-explained)): 45 days to identify, almost never extended. **Changed:** C-13's deadline is an urgent alert, not a ranking nudge.

## Assumptions
Debt service = monthly payment × 12 (an annual payment flips 9 decisions). `budget` beats `budget_range`; the conflict is flagged. Boundaries (10% over, 3% CoC, $0 cash flow) pass. No bedroom count, no recommendation. D-116/D-126 are one house. `seed.sql` is untouched; changes are additive migrations, ids kept. More in [`docs/DESIGN.md`](docs/DESIGN.md).

## What I'd ask STR Search before v2
1. Debt service: monthly × 12, or one annual payment?
2. When profile and call disagree (C-01 "under $320K"), which wins? Can reps override?
3. Does `est_year1_tax_savings` assume material participation, even for co-hosted clients (C-09)?
4. C-07 plans to use a co-host but entered 0%: check break-even with a co-host fee?
5. How many deals per batch? Can we get purchase outcomes to learn weights from?

## What I'd build next
Learned ranking weights; drive time from home (C-01, C-08); tax checks with `land_value_pct`; underwriting outliers (revenue vs comps); rep confirm/reject on each signal; an LLM-drafted note for the top three deals, approved by the rep.

## Where AI helped, and LLM cost
Claude Code helped with analysis, plans and first drafts of code and tests, each read, run and rewritten before commit; its mistakes and the product LLM's are in [`docs/AI_LOG.md`](docs/AI_LOG.md). In the product, `gpt-5.4-mini` ([gpt-4.1-mini is deprecated](https://developers.openai.com/api/docs/models/gpt-4.1-mini); temperature 0, strict JSON schema) costs **≈ $0.003 per client**, measured (2,000 tokens in, 270 out), and re-runs only when a client's text changes. 20 eval cases from the data (sarcasm, timing, polarity, deadlines) pass 20/20 on two runs; the first attempt passed 11 of 14.
