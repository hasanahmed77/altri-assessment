from collections.abc import Sequence

from app.domain.signals import EMPTY_SIGNALS, Signals
from app.llm.extractor import Extraction, Source


class FakeExtractor:
    """Returns canned signals and records every call, so tests can prove the cache works."""

    model = "fake-model"

    def __init__(self, signals: Signals = EMPTY_SIGNALS) -> None:
        self.signals = signals
        self.calls: list[list[Source]] = []
        self.fail = False

    def extract(self, sources: Sequence[Source]) -> Extraction:
        self.calls.append(list(sources))
        if self.fail:
            raise TimeoutError("model unavailable")
        return Extraction(self.signals, self.model, input_tokens=100, output_tokens=20)
