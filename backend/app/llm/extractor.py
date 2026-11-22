from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

from app.domain.models import Market
from app.domain.signals import TRAIT_DESCRIPTIONS, Signals

PROMPT_VERSION = "signals-v6"
MAX_OUTPUT_TOKENS = 1500
TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class Source:
    id: str
    context: str
    text: str


@dataclass(frozen=True)
class Extraction:
    signals: Signals
    model: str
    input_tokens: int
    output_tokens: int


class SignalExtractor(Protocol):
    model: str

    def extract(self, sources: Sequence[Source]) -> Extraction: ...


def instructions(markets: Mapping[str, Market]) -> str:
    traits = "\n".join(f"- {t.value}: {d}" for t, d in TRAIT_DESCRIPTIONS.items())
    market_lines = "\n".join(
        f"- {m.id}: {m.name}, {m.state} ({m.setting}; travelers: {m.typical_traveler})"
        for m in markets.values()
    )
    return f"""\
You read what a short-term-rental investing client said to their acquisitions rep and record
only what the client clearly expressed. The rep uses your output to choose which homes to show.

Rules:
- Each source is a <source id="..." about="..."> tag. "source" is that id exactly, such as
  "notes", "call:2026-09-10" or "feedback:35".
- "quote" is the client's words that express the item, copied character for character from
  inside that tag. Never quote the "about" text, and never paraphrase.
- Record only the client's own wishes. Leave a field empty or null when nothing supports it.
- must_haves are traits the client wants or requires; avoid_traits are traits they do not
  want the home to have. A complaint that a home lacks something is a must-have for it ("Too
  close to the neighbors" is a must-have of privacy). Something the client would merely
  tolerate ("fine with a big renovation") is neither. Use only these traits:
{traits}
- preferred_markets / avoided_markets: use only these markets. Map towns, regions and states
  to the markets they name ("Hunter" is M-05; "Florida" is every Florida market). Settings
  such as "mountains or a lake" are traits, not markets. avoided_markets only when the client
  rules a market out; a condition ("only if it's near a mountain") does not rule it out.
{market_lines}
- soft_budget_cap: only when the client says they want to keep their cash under an amount
  ("keep total cash under about $320K"), in whole dollars. A stated budget or the money they
  have available is not a cap, least of all when they call it flexible.
- deadline: a date the client must act by, as YYYY-MM-DD; when no year is given, use the
  first such date on or after the date of the source.
- uses_cohost: the client says they will use or are fine with a co-host or property manager.
- client_questions: questions or requests the client put to the rep that need a reply
  ("What would the hot tub add?", "can we get a walkthrough video?"), quoted exactly.
- feedback_readings: one per feedback comment, keyed by its number. sentiment is how the
  client feels about that home, read through sarcasm and hedging: a pass caused only by
  timing is neutral, an unsure comment is neutral. reason is the main cause.
"""


def render_sources(sources: Sequence[Source]) -> str:
    return "\n".join(f'<source id="{s.id}" about="{s.context}">{s.text}</source>' for s in sources)


class OpenAIExtractor:
    def __init__(self, api_key: str, model: str, markets: Mapping[str, Market]) -> None:
        self.model = model
        self._client = OpenAI(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=1)
        self._instructions = instructions(markets)

    def extract(self, sources: Sequence[Source]) -> Extraction:
        completion = self._client.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": self._instructions},
                {"role": "user", "content": render_sources(sources)},
            ],
            response_format=Signals,
            temperature=0,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
        )
        message = completion.choices[0].message
        if message.parsed is None:
            raise RuntimeError(f"No signals returned: {message.refusal or 'empty response'}")
        usage = completion.usage
        return Extraction(
            signals=message.parsed,
            model=completion.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
