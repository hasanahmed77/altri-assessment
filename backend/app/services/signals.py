import hashlib
import json
import logging
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Connection, Engine

from app import repository
from app.domain.signals import (
    EMPTY_SIGNALS,
    ReactedDeal,
    Signals,
    check_against_deals,
    check_mentions,
    ground,
)
from app.llm.extractor import PROMPT_VERSION, SignalExtractor, Source
from app.repository import FeedbackRecord, Reference, StoredSignals

log = logging.getLogger(__name__)

SignalsStatus = Literal["fresh", "updating", "stale", "unavailable"]
# After a failed extraction the same text isn't retried for a while, so an outage can't turn
# every page view into another paid call
RETRY_AFTER_SECONDS = 600.0


@dataclass(frozen=True)
class CurrentSignals:
    signals: Signals
    status: SignalsStatus
    needs_refresh: bool
    labels: Mapping[str, str]


def client_sources(
    reference: Reference, client_id: str, feedback: Sequence[FeedbackRecord]
) -> list[Source]:
    """Everything the client said, oldest first. Thumbs without a comment say nothing new,
    so they are left out and never trigger an extraction."""
    profile = reference.clients[client_id]
    sources: list[Source] = []
    if profile.notes.strip():
        sources.append(Source("notes", f"Onboarding notes, {profile.onboarded_at}", profile.notes))
    for call in sorted(reference.calls.get(client_id, ()), key=lambda c: c.call_date):
        sources.append(Source(f"call:{call.call_date}", f"Call on {call.call_date}", call.summary))
    for record in sorted(feedback, key=lambda r: r.feedback.id):
        item = record.feedback
        if not item.comment.strip():
            continue
        deal = reference.deals_by_id[item.deal_id]
        market = reference.markets[deal.market_id]
        thumb = "Thumbs up" if item.reaction == "up" else "Thumbs down"
        context = f"{thumb} on {deal.id} in {deal.city} ({market.name}), {record.created_at}"
        sources.append(Source(f"feedback:{item.id}", context, item.comment))
    return sources


def verify(
    signals: Signals,
    sources: Sequence[Source],
    reference: Reference,
    feedback: Sequence[FeedbackRecord],
) -> tuple[Signals, list[str]]:
    """Everything the model said, minus what the client never said or the data contradicts."""
    grounded, unquoted = ground(signals, {s.id: s.text for s in sources})
    reacted = {}
    for record in feedback:
        deal = reference.deals_by_id[record.feedback.deal_id]
        reacted[f"feedback:{record.feedback.id}"] = ReactedDeal(
            deal, reference.markets[deal.market_id], record.feedback.reaction == "up"
        )
    consistent, contradicted = check_against_deals(grounded, reacted)
    relevant, unrelated = check_mentions(consistent, reference.market_aliases, reacted)
    return relevant, unquoted + contradicted + unrelated


def source_hash(sources: Sequence[Source], model: str) -> str:
    payload = json.dumps(
        [PROMPT_VERSION, model, [[s.id, s.context, s.text] for s in sources]],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class SignalService:
    """Signals are cached per client by a hash of everything they were read from, so a page
    load never calls the model; a changed hash schedules one background extraction."""

    def __init__(
        self, engine: Engine, reference: Reference, extractor: SignalExtractor | None, model: str
    ) -> None:
        self._engine = engine
        self._reference = reference
        self._extractor = extractor
        self._model = model
        self._in_flight: set[str] = set()
        self._failed: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def current(
        self, conn: Connection, client_id: str, feedback: Sequence[FeedbackRecord]
    ) -> CurrentSignals:
        sources = client_sources(self._reference, client_id, feedback)
        labels = {s.id: s.context for s in sources}
        stored = repository.client_signals(conn, client_id)
        if not sources:
            return CurrentSignals(EMPTY_SIGNALS, "fresh", False, labels)
        digest = source_hash(sources, self._model)
        if stored is not None and stored.source_hash == digest:
            return CurrentSignals(stored.signals, "fresh", False, labels)
        signals = stored.signals if stored is not None else EMPTY_SIGNALS
        if self._extractor is not None and not self._failed_recently(client_id, digest):
            return CurrentSignals(signals, "updating", True, labels)
        return CurrentSignals(signals, "stale" if stored else "unavailable", False, labels)

    def refresh(self, client_id: str) -> None:
        """Safe to call repeatedly: one extraction per client at a time, and none at all when
        the stored hash already matches."""
        if self._extractor is None:
            return
        with self._lock:
            if client_id in self._in_flight:
                return
            self._in_flight.add(client_id)
        try:
            self._refresh(client_id, self._extractor)
        except Exception:
            log.exception("Signal extraction failed for %s; keeping previous signals", client_id)
            with self._lock:
                self._failed[client_id] = (self._current_hash(client_id), time.monotonic())
        finally:
            with self._lock:
                self._in_flight.discard(client_id)

    def _failed_recently(self, client_id: str, digest: str) -> bool:
        with self._lock:
            failure = self._failed.get(client_id)
        if failure is None:
            return False
        failed_hash, at = failure
        return failed_hash == digest and time.monotonic() - at < RETRY_AFTER_SECONDS

    def _current_hash(self, client_id: str) -> str:
        with self._engine.connect() as conn:
            feedback = repository.client_feedback(conn, client_id)
        return source_hash(client_sources(self._reference, client_id, feedback), self._model)

    def _refresh(self, client_id: str, extractor: SignalExtractor) -> None:
        with self._engine.connect() as conn:
            feedback = repository.client_feedback(conn, client_id)
            sources = client_sources(self._reference, client_id, feedback)
            digest = source_hash(sources, self._model)
            stored = repository.client_signals(conn, client_id)
            if not sources or (stored is not None and stored.source_hash == digest):
                return

        extraction = extractor.extract(sources)
        signals, dropped = verify(extraction.signals, sources, self._reference, feedback)
        for reason in dropped:
            log.warning("Dropped ungrounded signal for %s: %s", client_id, reason)

        with self._engine.begin() as conn:
            repository.save_signals(
                conn,
                client_id,
                StoredSignals(
                    signals=signals,
                    dropped=tuple(dropped),
                    source_hash=digest,
                    model=extraction.model,
                    input_tokens=extraction.input_tokens,
                    output_tokens=extraction.output_tokens,
                    extracted_at=datetime.now(UTC),
                ),
                PROMPT_VERSION,
            )
