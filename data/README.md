# STR Search take-home: seed data

All data here is synthetic. Load it however you like:

- **JSON:** `markets.json`, `deals.json`, `clients.json`, `feedback.json`, `call_summaries.json`
- **Postgres:** `psql -d <your_db> -f seed.sql` creates the five tables and inserts every row. Nested fields (setup items, revenue, comps and so on) are stored as JSONB.

| File | Rows |
| --- | --- |
| markets.json | 14 |
| deals.json | 45 |
| clients.json | 15 |
| feedback.json | 69 |
| call_summaries.json | 20 |

A few notes on the fields:

- Money values are US dollars. Rates and percentages are decimals (0.07 means 7%).
- `deals.revenue` holds yearly estimates; `annual_opex` is yearly operating expenses.
- `deals.city` is the town the property is in. `markets.json` lists which towns belong to which market.
- `clients.setting_rank` ranks the client's preferred kind of trip, 1 being most preferred.
- `clients.market_preferences` is what the client told us, in their own words.

The data is a little messy on purpose, as real data is.
