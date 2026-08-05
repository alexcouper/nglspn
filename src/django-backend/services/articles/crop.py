"""Crop rectangles for article hero images and their listing cards.

A crop is normalised against the source image, so it survives the image being
re-encoded or served at a different variant width. Cropping happens in CSS at
render time — nothing here cuts pixels.

The hero → card derivation lives only here, for the same reason
``derive_summary`` does: a second implementation in TypeScript would drift, and
the difference would show as a card that disagrees with itself between the
editor's preview and the live listing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import InvalidCropError

# Listing cards are always 16:9 so a grid of them stays uniform.
CARD_RATIO = 16 / 9

# A hero wider than 4:1 is a hairline; taller than 1:1 is a tower. Neither
# survives the article layout. Loosening these later does not invalidate stored
# data, so they are deliberately a guess rather than a negotiation.
MIN_RATIO = 1.0
MAX_RATIO = 4.0

# Enough to catch a client computing `ratio` wrongly, loose enough to survive
# float round-tripping through JSON.
_RATIO_TOLERANCE = 0.01

# Geometry gets a far tighter slop than the ratio does: a rect overhanging the
# image by 1% is a bug, not rounding.
_BOUNDS_EPSILON = 1e-6

# Stored coordinates are rounded so that re-deriving the same crop twice gives a
# byte-identical value and does not show up as a spurious change.
_PRECISION = 6

# Rejection reasons, named so the raise sites stay one line each.
ZERO_SIZE = "crop width and height must be greater than zero"
NEGATIVE_ORIGIN = "crop origin must not be negative"
RIGHT_OVERHANG = "crop extends past the right edge of the image"
BOTTOM_OVERHANG = "crop extends past the bottom edge of the image"
RATIO_OUT_OF_RANGE = "crop ratio must be between 1:1 and 4:1"
MALFORMED = "crop must carry x, y, w, h and ratio"
NO_HERO_IMAGE = "cannot set a crop on an article with no hero image"


@dataclass(frozen=True)
class CropRect:
    """A normalised crop. ``x``/``y``/``w``/``h`` are fractions of the source."""

    x: float
    y: float
    w: float
    h: float
    ratio: float

    def to_dict(self) -> dict[str, float]:
        return {
            "x": round(self.x, _PRECISION),
            "y": round(self.y, _PRECISION),
            "w": round(self.w, _PRECISION),
            "h": round(self.h, _PRECISION),
            "ratio": round(self.ratio, _PRECISION),
        }


def parse_crop(value: Any) -> CropRect | None:
    """Build a ``CropRect`` from stored JSON, tolerating a missing or junk value.

    Reads are lenient on purpose: a malformed row should render as an uncropped
    article rather than break the listing it appears in. Writes are strict —
    that is what ``validate_crop`` is for.
    """
    if not isinstance(value, dict):
        return None
    try:
        return CropRect(
            x=float(value["x"]),
            y=float(value["y"]),
            w=float(value["w"]),
            h=float(value["h"]),
            ratio=float(value["ratio"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def validate_crop(
    crop: CropRect,
    *,
    width: int | None = None,
    height: int | None = None,
    expected_ratio: float | None = None,
) -> None:
    """Raise ``InvalidCropError`` if ``crop`` could not have come from a real image.

    ``width``/``height`` are the source's pixel dimensions. They are nullable on
    ``ProjectImage``, and when absent the rect-versus-ratio consistency check is
    skipped rather than guessed at.
    """
    if crop.w <= 0 or crop.h <= 0:
        raise InvalidCropError(ZERO_SIZE)
    if crop.x < 0 or crop.y < 0:
        raise InvalidCropError(NEGATIVE_ORIGIN)
    if crop.x + crop.w > 1 + _BOUNDS_EPSILON:
        raise InvalidCropError(RIGHT_OVERHANG)
    if crop.y + crop.h > 1 + _BOUNDS_EPSILON:
        raise InvalidCropError(BOTTOM_OVERHANG)

    if expected_ratio is not None:
        if not _close(crop.ratio, expected_ratio):
            msg = f"crop ratio {crop.ratio:.4f} must be {expected_ratio:.4f}"
            raise InvalidCropError(msg)
    elif not MIN_RATIO - _RATIO_TOLERANCE <= crop.ratio <= MAX_RATIO + _RATIO_TOLERANCE:
        raise InvalidCropError(RATIO_OUT_OF_RANGE)

    if width and height:
        implied = (crop.w * width) / (crop.h * height)
        if not _close(crop.ratio, implied):
            msg = (
                f"crop ratio {crop.ratio:.4f} does not match its rectangle "
                f"({implied:.4f})"
            )
            raise InvalidCropError(msg)


def derive_card_crop(
    hero: CropRect,
    width: int | None,
    height: int | None,
) -> CropRect | None:
    """The 16:9 rect sharing ``hero``'s centre, clamped inside the image.

    Returns ``None`` when the source has no recorded dimensions — normalised
    coordinates cannot be converted to an aspect without them, and those images
    fall back to CSS centre-cropping, which is what they get today anyway.
    """
    if not width or not height:
        return None

    # Keep the hero's width and solve for the height that lands on 16:9. On a
    # source wider than 16:9 that height can exceed the image, so cap it at the
    # full height and let the width give instead.
    w = hero.w
    h = w * width / (CARD_RATIO * height)
    if h > 1:
        h = 1.0
        w = CARD_RATIO * h * height / width

    centre_x = hero.x + hero.w / 2
    centre_y = hero.y + hero.h / 2
    x = _clamp(centre_x - w / 2, 0.0, 1.0 - w)
    y = _clamp(centre_y - h / 2, 0.0, 1.0 - h)

    return CropRect(x=x, y=y, w=w, h=h, ratio=CARD_RATIO)


def resolve_card_crop(
    stored_card: Any,
    stored_hero: Any,
    width: int | None,
    height: int | None,
) -> dict[str, float] | None:
    """What a listing card should actually use: the override, else the derived rect."""
    card = parse_crop(stored_card)
    if card is not None:
        return card.to_dict()

    hero = parse_crop(stored_hero)
    if hero is None:
        return None

    derived = derive_card_crop(hero, width, height)
    return derived.to_dict() if derived else None


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _RATIO_TOLERANCE * max(abs(b), 1.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
