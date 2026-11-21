from app.domain.tags import HIGHLIGHT_TAGS, NOTE_TAGS, Tag, deal_tags
from tests.factories import all_real_highlights_and_notes, make_deal


def test_every_highlight_and_note_in_the_data_is_mapped() -> None:
    highlights, notes = all_real_highlights_and_notes()
    assert highlights <= HIGHLIGHT_TAGS.keys()
    assert notes <= NOTE_TAGS.keys()


def test_deal_tags_combine_highlights_and_notes() -> None:
    deal = make_deal(
        highlights=("Lakefront with private dock", "Wooded lot with good privacy"),
        analyst_notes="Seller open to offers.",
    )
    assert deal_tags(deal) == {Tag.WATERFRONT, Tag.LAKE_ACCESS, Tag.PRIVACY, Tag.NEGOTIABLE}
