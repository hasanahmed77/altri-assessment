BEGIN;

CREATE TABLE market_towns (
  town_key  text PRIMARY KEY,
  market_id text NOT NULL REFERENCES markets(id),
  source    text NOT NULL CHECK (source IN ('market_data', 'alias'))
);

INSERT INTO market_towns (town_key, market_id, source)
SELECT lower(trim(town)), m.id, 'market_data'
FROM markets m, jsonb_array_elements_text(m.towns) AS town;

-- Deal cities that are spelled differently from the market data, or missing from it
INSERT INTO market_towns (town_key, market_id, source) VALUES
  ('st. augustine',  'M-11', 'alias'),
  ('mc gaheysville', 'M-04', 'alias'),
  ('lake harmony',   'M-01', 'alias');

ALTER TABLE deals ADD COLUMN market_id text REFERENCES markets(id);

UPDATE deals d
SET market_id = t.market_id
FROM market_towns t
WHERE t.town_key = lower(trim(d.city));

-- Fails the migration if any deal city is still unmapped
ALTER TABLE deals ALTER COLUMN market_id SET NOT NULL;

-- One house can be underwritten with several plans (D-116 and D-126)
ALTER TABLE deals ADD COLUMN property_key text
  GENERATED ALWAYS AS (lower(trim(address)) || '|' || lower(trim(state))) STORED;

CREATE INDEX deals_property_key_idx ON deals (property_key);

CREATE TABLE market_aliases (
  alias_key text NOT NULL,
  market_id text NOT NULL REFERENCES markets(id),
  PRIMARY KEY (alias_key, market_id)
);

INSERT INTO market_aliases (alias_key, market_id)
SELECT lower(name), id FROM markets;

-- Clients also name towns ("Clearwater" is a town in the "Clearwater Area" market)
INSERT INTO market_aliases (alias_key, market_id)
SELECT town_key, market_id FROM market_towns
ON CONFLICT DO NOTHING;

INSERT INTO market_aliases (alias_key, market_id)
SELECT 'florida', id FROM markets WHERE state = 'FL';

INSERT INTO market_aliases (alias_key, market_id) VALUES
  ('smokies',    'M-02'),
  ('shenandoah', 'M-04'),
  ('upstate ny', 'M-05'),
  ('upstate ny', 'M-06');

-- security_invoker: a plain view runs as its owner and would bypass row-level security
CREATE VIEW client_market_refs WITH (security_invoker = true) AS
SELECT c.id AS client_id, r.kind, r.raw_term, a.market_id
FROM clients c
CROSS JOIN LATERAL (
  SELECT 'prefer' AS kind, term AS raw_term
  FROM jsonb_array_elements_text(c.market_preferences) AS term
  UNION ALL
  SELECT 'avoid', term
  FROM jsonb_array_elements_text(c.avoid_markets) AS term
) r
LEFT JOIN market_aliases a ON a.alias_key = lower(trim(r.raw_term))
WHERE lower(trim(r.raw_term)) <> 'all';

CREATE INDEX feedback_client_idx ON feedback (client_id, id);
CREATE INDEX call_summaries_client_idx ON call_summaries (client_id);

ALTER TABLE feedback ALTER COLUMN created_at SET DEFAULT current_date;

ALTER TABLE markets        ENABLE ROW LEVEL SECURITY;
ALTER TABLE deals          ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients        ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback       ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_towns   ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_aliases ENABLE ROW LEVEL SECURITY;

COMMIT;
