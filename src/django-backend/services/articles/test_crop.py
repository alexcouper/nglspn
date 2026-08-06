import pytest

from services.articles.crop import (
    CARD_RATIO,
    CropRect,
    parse_crop,
    validate_crop,
)
from services.articles.exceptions import InvalidCropError

SQUARE = (4000, 4000)
WIDE = (4000, 2000)
TALL = (1000, 4000)


def crop(x: float, y: float, w: float, h: float, ratio: float = CARD_RATIO) -> CropRect:
    return CropRect(x=x, y=y, w=w, h=h, ratio=ratio)


def card_rect(source: tuple[int, int], x: float, y: float, w: float) -> CropRect:
    """A 16:9 crop of `source` whose stored ratio matches its rectangle."""
    width, height = source
    h = (w * width) / (CARD_RATIO * height)
    return CropRect(x=x, y=y, w=w, h=h, ratio=CARD_RATIO)


class TestParseCrop:
    def test_reads_a_stored_dict(self) -> None:
        stored = {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.25, "ratio": 2.0}

        assert parse_crop(stored) == crop(0.1, 0.2, 0.5, 0.25, ratio=2.0)

    @pytest.mark.parametrize(
        "value",
        [None, "nope", 7, {}, {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.25}],
    )
    def test_returns_none_for_junk(self, value: object) -> None:
        assert parse_crop(value) is None


class TestValidateCrop:
    def test_accepts_a_consistent_rect(self) -> None:
        validate_crop(card_rect(SQUARE, 0.1, 0.2, 0.6), width=4000, height=4000)

    def test_accepts_without_source_dimensions(self) -> None:
        validate_crop(crop(0.1, 0.2, 0.6, 0.3))

    def test_rejects_zero_width(self) -> None:
        with pytest.raises(InvalidCropError, match="greater than zero"):
            validate_crop(crop(0.1, 0.2, 0.0, 0.3))

    def test_accepts_a_crop_that_overhangs_the_image(self) -> None:
        # Zoomed out until the box is wider than the image: legal, and the
        # surround renders as the shared background colour.
        validate_crop(card_rect(SQUARE, -0.25, -0.1, 1.5))

    def test_rejects_a_crop_entirely_off_the_left(self) -> None:
        with pytest.raises(InvalidCropError, match="does not overlap"):
            validate_crop(crop(-0.8, 0.2, 0.6, 0.3))

    def test_rejects_a_crop_entirely_below_the_image(self) -> None:
        with pytest.raises(InvalidCropError, match="does not overlap"):
            validate_crop(crop(0.1, 1.2, 0.6, 0.3))

    def test_rejects_an_absurdly_large_crop(self) -> None:
        with pytest.raises(InvalidCropError, match="six times"):
            validate_crop(crop(-3.0, -1.5, 7.0, 3.9375))

    def test_rejects_a_ratio_that_is_not_sixteen_by_nine(self) -> None:
        with pytest.raises(InvalidCropError, match="must be"):
            validate_crop(crop(0.1, 0.2, 0.6, 0.45, ratio=4 / 3))

    def test_rejects_a_ratio_that_contradicts_its_rectangle(self) -> None:
        inconsistent = crop(0.1, 0.2, 0.6, 0.3375)

        with pytest.raises(InvalidCropError, match="does not match its rectangle"):
            validate_crop(inconsistent, width=1000, height=4000)

    def test_accepts_a_card_crop_on_a_wide_source(self) -> None:
        validate_crop(card_rect(WIDE, 0.0, 0.3, 1.0), width=WIDE[0], height=WIDE[1])

    def test_accepts_a_card_crop_on_a_tall_source(self) -> None:
        validate_crop(card_rect(TALL, 0.0, 0.4, 1.0), width=TALL[0], height=TALL[1])
