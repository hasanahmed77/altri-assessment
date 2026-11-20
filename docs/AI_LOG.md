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

## 2. How coding-assistant mistakes are prevented
| Risk | Defense |
|---|---|
| Plausible but wrong math | Golden values are computed by hand from the brief's formulas (e.g. C-01 × D-126 cash needed = $235,295; $100K at 6% for 30 years = $599.55/month), not by the code under test. |
| Tests that just mirror the code | Tests are written from the brief's wording, including boundaries (exactly 10% over budget, exactly 3% CoC, cash flow exactly 0). |
| Silent behavior changes | The golden snapshot of all 675 client × deal decisions fails on any change until it is reviewed. |
| Outdated or invented library APIs | Supabase, OpenAI and Next.js usage is checked against current documentation; types (mypy, tsc strict) catch wrong signatures. |
| Code nobody can explain | Every line is read and must be explainable before it is committed. No padding comments; comments only say *why*. |
| Large unreviewable changes | Small commits, one Kanban card each. |

## 3. Failure modes of the LLM in the product, and defenses
| Failure mode | Defense |
|---|---|
| Invented quote or preference | Every signal must include a quote that appears verbatim in its cited source; otherwise it is dropped and logged. |
| Invented market or trait | Strict JSON schema: market ids from an enum of the 14 real ids; traits from the same closed vocabulary as deal tags. |
| Malformed output | OpenAI Structured Outputs with a strict schema, then Pydantic validation; on failure the previous signals are kept. |
| Misread tone (sarcasm, "bad timing", "Hmm. Maybe?") | Eval cases taken from the real data; the pass rate is reported in the README. |
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
