"""Domain exceptions for the articles service."""


class ArticleError(Exception):
    """Base class for articles-service-specific errors."""


class ArticleNotFoundError(ArticleError):
    """No Article exists with the given id."""


class ArticleNotPublishableError(ArticleError):
    """Publish was requested but required fields (title/body/hero) are missing."""


class ChannelNotFoundError(ArticleError):
    """No Channel exists with the given id."""


class ChannelOnWrongProjectError(ArticleError):
    """The referenced Channel does not belong to the targeted Project."""


class HeroImageOnWrongProjectError(ArticleError):
    """The referenced ProjectImage does not belong to the Article's project."""


class PublishedArticleNeedsHeroImageError(ArticleError):
    """Clearing the hero image was requested on an already-published article."""


class InvalidCropError(ArticleError):
    """A crop rectangle is out of bounds, or its ratio does not match its rect."""


class DuplicateChannelNameError(ArticleError):
    """A Channel with this name already exists on the project."""


class ChannelHasArticlesError(ArticleError):
    """The channel cannot be deleted because it still has articles."""

    def __init__(self, article_count: int) -> None:
        super().__init__(f"channel has {article_count} article(s)")
        self.article_count = article_count


class LastChannelError(ArticleError):
    """The channel cannot be deleted because it is the only channel on the project."""
