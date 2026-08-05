import pytest

from services.articles.crop import (
    CARD_RATIO,
    CropRect,
    derive_card_crop,
    parse_crop,
    resolve_card_crop,
    validate_crop,
)
from services.articles.exceptions import InvalidCropError

SQUARE = (4000, 4000)
WIDE = (4000, 2000)
TALL = (1000, 4000)


def crop(x: float, y: float, w: float, h: float, ratio: float) -> CropRect:
    return CropRect(x=x, y=y, w=w, h=h, ratio=ratio)


def rect_for(
    source: tuple[int, int], x: float, y: float, w: float, h: float
) -> CropRect:
    """A crop whose stored ratio is consistent with its rectangle."""
    width, height = source
    return CropRect(x=x, y=y, w=w, h=h, ratio=(w * width) / (h * height))


def centre_of(rect: CropRect) -> tuple[float, float]:
    return rect.x + rect.w / 2, rect.y + rect.h / 2


def assert_ratio(rect: CropRect, source: tuple[int, int], expected: float) -> None:
    width, height = source
    assert (rect.w * width) / (rect.h * height) == pytest.approx(expected)


class TestDeriveCardCrop:
    def test_preserves_the_hero_centre(self) -> None:
        hero = rect_for(SQUARE, x=0.1, y=0.4, w=0.6, h=0.2)

        derived = derive_card_crop(hero, *SQUARE)

        assert derived is not None
        assert centre_of(derived) == pytest.approx(centre_of(hero))

    def test_lands_on_sixteen_by_nine(self) -> None:
        hero = rect_for(SQUARE, x=0.1, y=0.4, w=0.6, h=0.2)

        derived = derive_card_crop(hero, *SQUARE)

        assert derived is not None
        assert_ratio(derived, SQUARE, CARD_RATIO)
        assert derived.ratio == pytest.approx(CARD_RATIO)

    def test_keeps_the_centre_at_the_top_edge_rather_than_sliding(self) -> None:
        hero = rect_for(SQUARE, x=0.2, y=0.0, w=0.6, h=0.1)

        derived = derive_card_crop(hero, *SQUARE)

        assert derived is not None
        assert centre_of(derived) == pytest.approx(centre_of(hero))
        assert derived.y < 0

    def test_always_keeps_the_hero_width(self) -> None:
        hero = rect_for(WIDE, x=0.0, y=0.3, w=1.0, h=0.25)

        derived = derive_card_crop(hero, *WIDE)

        assert derived is not None
        assert derived.w == pytest.approx(hero.w)
        assert_ratio(derived, WIDE, CARD_RATIO)

    def test_overhangs_rather_than_shrinking_on_a_short_source(self) -> None:
        # A 4000x2000 source is wider than 16:9, so a full-width selection needs
        # more height for 16:9 than the image has. It overhangs, and the surround
        # renders as the shared background colour.
        hero = rect_for(WIDE, x=0.0, y=0.3, w=1.0, h=0.25)

        derived = derive_card_crop(hero, *WIDE)

        assert derived is not None
        assert derived.h > 1
        assert derived.y < 0

    @pytest.mark.parametrize(
        ("width", "height"),
        [(None, 4000), (4000, None), (None, None), (0, 4000)],
    )
    def test_returns_none_without_source_dimensions(
        self, width: int | None, height: int | None
    ) -> None:
        hero = crop(0.1, 0.4, 0.6, 0.2, ratio=3.0)

        assert derive_card_crop(hero, width, height) is None


class TestResolveCardCrop:
    def test_prefers_a_stored_override(self) -> None:
        override = rect_for(SQUARE, x=0.0, y=0.0, w=0.8, h=0.45).to_dict()
        hero = rect_for(SQUARE, x=0.4, y=0.4, w=0.5, h=0.2).to_dict()

        assert resolve_card_crop(override, hero, *SQUARE) == override

    def test_derives_when_no_override(self) -> None:
        hero = rect_for(SQUARE, x=0.1, y=0.4, w=0.6, h=0.2)

        resolved = resolve_card_crop(None, hero.to_dict(), *SQUARE)

        assert resolved is not None
        assert resolved["ratio"] == pytest.approx(CARD_RATIO)

    def test_returns_none_without_a_hero_crop(self) -> None:
        assert resolve_card_crop(None, None, *SQUARE) is None

    def test_returns_none_for_a_malformed_hero_crop(self) -> None:
        assert resolve_card_crop(None, {"x": 0.1}, *SQUARE) is None


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
        validate_crop(rect_for(SQUARE, 0.1, 0.2, 0.6, 0.3), width=4000, height=4000)

    def test_accepts_without_source_dimensions(self) -> None:
        validate_crop(crop(0.1, 0.2, 0.6, 0.3, ratio=2.0))

    def test_rejects_zero_width(self) -> None:
        with pytest.raises(InvalidCropError, match="greater than zero"):
            validate_crop(crop(0.1, 0.2, 0.0, 0.3, ratio=2.0))

    def test_accepts_a_crop_that_overhangs_the_image(self) -> None:
        # Zoomed out until the box is wider than the image: legal, and the
        # surround renders as the shared background colour.
        validate_crop(rect_for(SQUARE, -0.25, -0.1, 1.5, 0.84375))

    def test_rejects_a_crop_entirely_off_the_left(self) -> None:
        with pytest.raises(InvalidCropError, match="does not overlap"):
            validate_crop(crop(-0.8, 0.2, 0.6, 0.3, ratio=2.0))

    def test_rejects_a_crop_entirely_below_the_image(self) -> None:
        with pytest.raises(InvalidCropError, match="does not overlap"):
            validate_crop(crop(0.1, 1.2, 0.6, 0.3, ratio=2.0))

    def test_rejects_an_absurdly_large_crop(self) -> None:
        with pytest.raises(InvalidCropError, match="six times"):
            validate_crop(crop(-3.0, -1.5, 7.0, 3.5, ratio=2.0))

    def test_rejects_a_ratio_wider_than_four_to_one(self) -> None:
        with pytest.raises(InvalidCropError, match="between 1:1 and 4:1"):
            validate_crop(crop(0.0, 0.4, 1.0, 0.05, ratio=5.0))

    def test_rejects_a_ratio_taller_than_one_to_one(self) -> None:
        with pytest.raises(InvalidCropError, match="between 1:1 and 4:1"):
            validate_crop(crop(0.1, 0.1, 0.3, 0.8, ratio=0.5))

    def test_rejects_a_ratio_that_contradicts_its_rectangle(self) -> None:
        inconsistent = crop(0.1, 0.2, 0.6, 0.3, ratio=2.0)

        with pytest.raises(InvalidCropError, match="does not match its rectangle"):
            validate_crop(inconsistent, width=1000, height=4000)

    def test_rejects_a_card_crop_at_the_wrong_ratio(self) -> None:
        with pytest.raises(InvalidCropError, match="must be"):
            validate_crop(
                rect_for(SQUARE, 0.1, 0.2, 0.6, 0.45),
                width=4000,
                height=4000,
                expected_ratio=CARD_RATIO,
            )

    def test_accepts_a_card_crop_at_sixteen_by_nine(self) -> None:
        hero = rect_for(SQUARE, x=0.1, y=0.4, w=0.6, h=0.2)
        derived = derive_card_crop(hero, *SQUARE)

        assert derived is not None
        validate_crop(derived, width=4000, height=4000, expected_ratio=CARD_RATIO)
