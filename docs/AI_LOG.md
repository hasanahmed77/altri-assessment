# AI usage log

Two kinds of AI are involved in this project, and each can be wrong in its own way:
1. **AI coding assistants** that helped analyze the data, plan and write code.
2. **The LLM inside the product** (OpenAI), which reads client comments and call summaries.

This log records real mistakes as they happen and the defenses in place against each kind.

## Where AI helped
- **Data analysis:** scripts to run the brief's formulas over all 675 client × deal pairs, find data traps and boundary cases.
- **Planning:** architecture options, test strategy, scope cuts for the deadline.
- **Code:** first drafts of code and tests, always read, run and rewritten where needed before commit.
- **In the product:** OpenAI turns client comments and call notes into quoted, validated signals (cost per client measured in the README).

## 1. Mistakes caught (coding assistant)

New entries go at the bottom, using the template at the end of this file.

### AI-01 A script shadowed Python's standard library
- **What happened:** During data analysis the assistant named a script `math.py`. A second script imported Python's `statistics` module, which imports the standard `math` module, and got the local file instead. It crashed with `ImportError: cannot import name 'log' from 'math'`.
- **How it was caught:** The traceback named the local file.
- **Fix:** Renamed to `dealmath.py`; analysis scripts now run with `python -I` (isolated mode, which doesn't import from the script's folder).
- **Lesson:** Never name modules after standard-library modules.

### AI-02 Two scripts disagreed about a deal with no bedroom count
- **What happened:** D-135 has `bedrooms: null`. The first analysis script counted it as excluded. A second script, written later to check the feedback, skipped the bedroom check when the value was missing and reported D-135 as "eligible" for C-03.
- **How it was caught:** Comparing the two outputs; D-135 appeared as excluded in one and eligible in the other.
- **Fix:** A decision (DESIGN D-07: unknown bedrooms are not recommended), implemented once in `rules.py`, with a unit test for the NULL case.
- **Lesson:** Business rules get one implementation and tests; ad-hoc copies drift.

### AI-03 Token cost overestimated
- **What happened:** The assistant first estimated the LLM cost at about 2–4K input tokens per client (later "3K").
- **How it was caught:** Challenged on it, then itemized the real inputs: notes, one or two call summaries and a few one-line comments come to a few hundred tokens; with instructions, about 1–1.5K.
- **Fix:** Cost is now measured from the API's `usage` field and stored per extraction (DESIGN D-11), not estimated.
- **Lesson:** Count or measure; don't accept round-number guesses.

### AI-04 Market matching missed town names
- **What happened:** The assistant's first market-alias migration registered market names ("Clearwater Area") and nicknames ("Smokies"), but not town names. C-07 and C-14 list "Clearwater" as a preferred market, so their preference silently resolved to nothing.
- **How it was caught:** Applying the migrations to a real database and listing every client market term that resolved to no market. "Clearwater" showed up next to the expected unknowns ("Charlotte", "Texas Hill Country").
- **Fix:** Every town is also registered as an alias for its market. The only unresolved terms left are the three that really have no market.
- **Lesson:** Run data migrations against real data and inspect what didn't match, not just that the migration succeeded.

### AI-05 A type check that only passed on the assistant's machine
- **What happened:** The assistant reported the frontend type check as passing. It ran `tsc` after a production build, which had already generated Next.js's route types (`LayoutProps`). On a clean checkout those types don't exist yet, so CI failed.
- **How it was caught:** The first CI run of the frontend job, which starts from a clean checkout.
- **Fix:** A `typecheck` script that runs `next typegen` before `tsc`, used by both CI and local runs. Reproduced locally from a clean `.next` first, then confirmed green on CI.
- **Lesson:** Verify from a clean state; a check that depends on leftover build output proves nothing.

### AI-06 The same number shown two ways on one card
- **What happened:** The assistant made the API round ratios to 4 places. The browser then rounded again for display, so D-108's card showed "CoC low 15.3%" (0.152482 → 0.1525 → 15.3%) while its explanation, written from the unrounded value, said "15.2%".
- **How it was caught:** Reading the rendered page in a browser during manual testing, not from any automated check.
- **Fix:** The API sends ratios with 6 places, so the only visible rounding happens once, in the browser.
- **Lesson:** Round once, as late as possible. Look at the real screen; tests asserted each number separately and both were "correct".

### AI-07 Formatting churn from an unconfigured formatter
- **What happened:** The assistant ran Prettier with its defaults over the frontend. The project has no Prettier config, so seven files the change never touched were rewrapped to 80 columns.
- **How it was caught:** Reading `git diff --stat` before going on: files outside the change showed up.
- **Fix:** Re-ran Prettier at width 100 (the style the code was written in) on the changed files only and put the remaining hunks back by hand, so the diff holds only real changes.
- **Lesson:** Don't run a tool the project doesn't use; check the diff's file list after any bulk edit.

### AI-08 A near-miss price past its own limit
- **What happened:** The price solver rounded its answer down to the nearest $1,000 after checking the discount limit, so one deal (C-10 / D-115) came out 10.1% under asking with a 10% limit.
- **How it was caught:** Reading the solver's output for all 15 clients before wiring it into the API.
- **Fix:** The limit is checked after rounding; a unit test asserts `0 < discount <= MAX_DISCOUNT`.
- **Lesson:** Check a constraint on the value you return, not on an intermediate one.

## 2. Mistakes caught (the product's LLM)
Found by the evals (`python -m evals.run`) and by reading the extracted signals. Each one changed the design, not just the prompt.

### LLM-01 Valid quotes cited with the wrong source format
- **What happened:** The model cited sources as `[call:2026-09-10] Call on 2026-09-10` instead of `call:2026-09-10`, so grounding dropped real quotes. C-08's ski wish and C-09's party avoidance disappeared: 11/14 cases passed on the first run.
- **Fix:** Sources are sent as `<source id="…" about="…">` tags, and code resolves a copied header to its id. The quote is still checked word for word.

### LLM-02 A pass for timing scored as negative
- **What happened:** For C-02's "Great house, honestly. Just bad timing for us this month." the model returned reason `timing` but sentiment `negative`, despite the prompt saying a timing pass is neutral. That would have pushed down every Smokies deal for a client who said they're "still very interested in the area".
- **Fix:** Code decides the effect: a `timing` or `undecided` reason counts zero (D-23). The eval now checks the reason, the part the model is responsible for.

### LLM-03 A real quote cited to the wrong source
- **What happened:** C-13's 1031 deadline was quoted correctly from the Oct 20 call but cited as the onboarding notes, so grounding dropped it and the rep lost the most urgent alert.
- **Fix:** Code re-cites a quote to the one source that contains it; a quote found in none, or in several, is dropped.

### LLM-04 "Not interested in mountain cabins" read as an interior style
- **What happened:** The model turned it into "avoid cabin feel" (log-cabin interiors), so C-03 still got a Poconos deal first. The eval passed, because the assistant had written it to accept either trait.
- **How it was caught:** Comparing each client's top three before and after signals, not from the pass rate.
- **Fix:** The trait descriptions now separate the kind of place from the interior style, and the eval requires the lake/mountain setting. C-03 now gets Bradenton first.
- **Lesson:** A lenient eval hides the error it exists to catch. Check outcomes, not just labels.

### LLM-05 Preferences inferred from metadata, blocked by grounding
- **What happened:** On every run the model tries to add "avoids Saint Augustine" or "prefers the Poconos" by quoting the header of a thumbs-down ("Thumbs down on D-106 in St. Augustine…"), not anything the client wrote.
- **Fix:** None needed: those quotes aren't in the client's text, so grounding drops them and the run log lists each one. This is the defense working as designed.

### LLM-06 A budget read as a cash limit
- **What happened:** "Budget around $275K, a little flexible" (C-05) and "Budget about $350K" (C-12) came back as spoken cash limits, so deals the profile allows were marked down and the rep got a false alert. Telling the model in the prompt that a budget is not a limit did not change its answer.
- **How it was caught:** Reading C-12's alerts on the rep screen.
- **Fix:** Code decides when a spoken limit counts: below the profile cap and not the profile budget said again. C-01's "keep total cash under about $320K" still counts. A new eval case checks the effect.
- **Lesson:** When a prompt fix doesn't stick, move the decision into code, where it is tested.

## 3. How coding-assistant mistakes are prevented
| Risk | Defense |
|---|---|
| Plausible but wrong math | Golden values are computed by hand from the brief's formulas (e.g. C-01 × D-126 cash needed = $235,295; $100K at 6% for 30 years = $599.55/month), not by the code under test. |
| Tests that just mirror the code | Tests are written from the brief's wording, including boundaries (exactly 10% over budget, exactly 3% CoC, cash flow exactly 0). |
| Silent behavior changes | The golden snapshot of all 675 client × deal decisions fails on any change until it is reviewed. |
| Outdated or invented library APIs | Supabase, OpenAI and Next.js usage is checked against current documentation; types (mypy, tsc strict) catch wrong signatures. |
| Code nobody can explain | Every line is read and must be explainable before it is committed. No padding comments; comments only say *why*. |
| Large unreviewable changes | Small commits, one Kanban card each. |

## 4. Failure modes of the LLM in the product, and defenses
| Failure mode | Defense |
|---|---|
| Invented quote or preference | Every signal must quote the client's own words verbatim; otherwise it is dropped and logged (LLM-05). Code settles which source a quote came from (LLM-01, LLM-03). |
| Invented market or trait | Strict JSON schema: market ids from an enum of the 14 real ids; traits from the same closed vocabulary as deal tags. |
| Malformed output | OpenAI Structured Outputs with a strict schema, then Pydantic validation; on failure the previous signals are kept. |
| Misread tone (sarcasm, "bad timing", "Hmm. Maybe?") | 16 eval cases from the real data (16/16 on two runs). The model only classifies; code decides the effect (LLM-02, LLM-06). |
| A wrong reading changes what the client sees | Signals only re-rank; hard rules come from the profile. Every adjustment shows its quote on the card, so the rep can overrule it. |
| Instructions hidden in a client comment | Comments are passed as data; the output can only be the schema; the LLM has no tools and can't change eligibility, which is decided in code. |
| Run-to-run variation | Temperature 0, and results are cached by content hash, so the same input is not re-asked. |
| API outage or timeout | Timeout plus one retry, then keep the last good signals; feedback is saved before extraction and never depends on it. |
| Runaway cost | Calls only when a client's text changes, never on page loads or comment-less thumbs; output token cap; small model. |
| Behavior change after a model or prompt update | Model and prompt version are stored with each result; changing either invalidates the cache, and the evals are rerun. |

## Template
```
### AI-NN Short title
- **What happened:**
- **How it was caught:**
- **Fix:**
- **Lesson:**
```
