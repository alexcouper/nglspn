"""Crop rectangles for article listing images.

A crop is normalised against the source image, so it survives the image being
re-encoded or served at a different variant width. Cropping happens in CSS at
render time — nothing here cuts pixels.

There is exactly one crop per article and it is always 16:9, because the lead
card and the grid card render from the same rectangle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import InvalidCropError

# Listing cards are always 16:9 so a grid of them stays uniform.
CARD_RATIO = 16 / 9

# Enough to catch a client computing `ratio` wrongly, loose enough to survive
# float round-tripping through JSON.
_RATIO_TOLERANCE = 0.01

# A crop may extend past the edge of its source — the author can zoom out until
# the box is bigger than the image, and the surround renders as the shared
# background colour. So the only real bounds are that the crop still overlaps
# the image somewhere, and that it is not absurdly larger than it.
MAX_EXTENT = 6.0

# Stored coordinates are rounded so that re-deriving the same crop twice gives a
# byte-identical value and does not show up as a spurious change.
_PRECISION = 6

# Rejection reasons, named so the raise sites stay one line each.
ZERO_SIZE = "crop width and height must be greater than zero"
TOO_LARGE = "crop is more than six times the size of the image"
NO_OVERLAP = "crop does not overlap the image at all"
MALFORMED = "crop must carry x, y, w, h and ratio"
NO_LISTING_IMAGE = "cannot set a crop on an article with no listing image"


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
) -> None:
    """Raise ``InvalidCropError`` if ``crop`` could not have come from the cropper.

    A crop is allowed to run past the edges of its source — that is how a
    fixed-shape crop shows a whole image with background at the sides — so this
    checks that it overlaps the image at all rather than that it sits inside it.

    ``width``/``height`` are the source's pixel dimensions. They are nullable on
    ``ProjectImage``, and when absent the rect-versus-ratio consistency check is
    skipped rather than guessed at.
    """
    if crop.w <= 0 or crop.h <= 0:
        raise InvalidCropError(ZERO_SIZE)
    if crop.w > MAX_EXTENT or crop.h > MAX_EXTENT:
        raise InvalidCropError(TOO_LARGE)
    if crop.x >= 1 or crop.y >= 1 or crop.x + crop.w <= 0 or crop.y + crop.h <= 0:
        raise InvalidCropError(NO_OVERLAP)

    if not _close(crop.ratio, CARD_RATIO):
        msg = f"crop ratio {crop.ratio:.4f} must be {CARD_RATIO:.4f}"
        raise InvalidCropError(msg)

    if width and height:
        implied = (crop.w * width) / (crop.h * height)
        if not _close(crop.ratio, implied):
            msg = (
                f"crop ratio {crop.ratio:.4f} does not match its rectangle "
                f"({implied:.4f})"
            )
            raise InvalidCropError(msg)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _RATIO_TOLERANCE * max(abs(b), 1.0)
