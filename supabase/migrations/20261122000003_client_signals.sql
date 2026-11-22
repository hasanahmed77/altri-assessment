-- Signals extracted from what a client said (notes, calls, feedback comments).
-- source_hash covers the prompt version, the model and every source text, so a row is reused
-- until any of them changes; a page load never calls the model.
CREATE TABLE client_signals (
  client_id      text PRIMARY KEY REFERENCES clients (id),
  signals        jsonb NOT NULL,
  dropped        jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_hash    text NOT NULL,
  model          text NOT NULL,
  prompt_version text NOT NULL,
  input_tokens   integer NOT NULL,
  output_tokens  integer NOT NULL,
  extracted_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE client_signals ENABLE ROW LEVEL SECURITY;
