from enum import StrEnum

from app.domain.models import Deal


class Tag(StrEnum):
    WATERFRONT = "waterfront"
    LAKE_ACCESS = "lake_access"
    BEACH_ACCESS = "beach_access"
    SKI_ACCESS = "ski_access"
    VIEWS = "views"
    PRIVACY = "privacy"
    NEWER_BUILD = "newer_build"
    CABIN_FEEL = "cabin_feel"
    UPDATED_INTERIOR = "updated_interior"
    DATED_INTERIOR = "dated_interior"
    NEAR_ATTRACTIONS = "near_attractions"
    ROOM_TO_ADD = "room_to_add"
    EXTRA_BEDROOM_POTENTIAL = "extra_bedroom_potential"
    NEGOTIABLE = "negotiable"


# Deal text comes from a closed vocabulary: every highlight and note in the data is listed,
# and an unknown string is an error rather than a silently untagged deal.
HIGHLIGHT_TAGS: dict[str, frozenset[Tag]] = {
    "Short walk to lake access": frozenset({Tag.LAKE_ACCESS}),
    "Lakefront with private dock": frozenset({Tag.WATERFRONT, Tag.LAKE_ACCESS}),
    "Fifteen minutes to the beach": frozenset({Tag.BEACH_ACCESS}),
    "Ten minutes to ski lifts": frozenset({Tag.SKI_ACCESS}),
    "Long-range mountain views from the main deck": frozenset({Tag.VIEWS}),
    "Wooded lot with good privacy": frozenset({Tag.PRIVACY}),
    "Newer build with low maintenance": frozenset({Tag.NEWER_BUILD}),
    "Classic log-cabin interior": frozenset({Tag.CABIN_FEEL}),
    "Updated kitchen and baths": frozenset({Tag.UPDATED_INTERIOR}),
    "Recently updated interior": frozenset({Tag.UPDATED_INTERIOR}),
    "Close to downtown dining": frozenset({Tag.NEAR_ATTRACTIONS}),
    "Walkable to event venues": frozenset({Tag.NEAR_ATTRACTIONS}),
    "Flat backyard with room for a sauna": frozenset({Tag.ROOM_TO_ADD}),
    "Big backyard for pickleball and mini golf": frozenset({Tag.ROOM_TO_ADD}),
    "Large fenced backyard ready for a pool": frozenset({Tag.ROOM_TO_ADD}),
    "Oversized lot for the area": frozenset({Tag.ROOM_TO_ADD}),
    "Garage can convert to a bedroom": frozenset({Tag.EXTRA_BEDROOM_POTENTIAL}),
    "Bed / Bath (projected): 5 / 3, office converts to 5th bedroom": frozenset(
        {Tag.EXTRA_BEDROOM_POTENTIAL}
    ),
    "Screened lanai": frozenset(),
    "Quiet street with no rental restrictions": frozenset(),
    "Corner lot with extra parking": frozenset(),
}

NOTE_TAGS: dict[str, frozenset[Tag]] = {
    "": frozenset(),
    "Interior dated; budgeted paint and fixtures.": frozenset({Tag.DATED_INTERIOR}),
    "Price dropped last week.": frozenset({Tag.NEGOTIABLE}),
    "Seller open to offers.": frozenset({Tag.NEGOTIABLE}),
    "Septic location limits pool placement.": frozenset(),
    "Roof replaced in 2022.": frozenset(),
    "Backyard is sloped near the fence line; check photos.": frozenset(),
    "Comps are strong at the high end.": frozenset(),
    "Revenue hedged slightly since it isn't a true log cabin.": frozenset(),
    "Existing STR. Revenue set to seller's trailing 12 months.": frozenset(),
    "Full plan: adds game room and sauna. Same house as the light plan.": frozenset(),
    "Light plan: hot tub and fire pit only.": frozenset(),
}

# "unique" has no reliable signal in the deal data, so it matches nothing rather than a guess
WOW_FACTOR_TAGS: dict[str, frozenset[Tag]] = {
    "views": frozenset({Tag.VIEWS}),
    "seclusion": frozenset({Tag.PRIVACY}),
    "waterfront": frozenset({Tag.WATERFRONT}),
    "unique": frozenset(),
}


def deal_tags(deal: Deal) -> frozenset[Tag]:
    tags: set[Tag] = set()
    for highlight in deal.highlights:
        tags |= HIGHLIGHT_TAGS[highlight]
    tags |= NOTE_TAGS[deal.analyst_notes]
    return frozenset(tags)


LIGHT_SETUP_MAX = 125_000
MEDIUM_SETUP_MAX = 160_000


def renovation_level(deal: Deal) -> str:
    if deal.setup_cost <= LIGHT_SETUP_MAX:
        return "light"
    if deal.setup_cost <= MEDIUM_SETUP_MAX:
        return "medium"
    return "heavy"
