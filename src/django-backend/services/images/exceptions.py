"""Domain exceptions for the images service.

Each carries its own message, because the routers report these straight to the
client as the 400 body — `str(exc)` is the user-facing text.
"""


class ImageError(Exception):
    """Base class for images-service-specific errors."""


class UnsupportedContentTypeError(ImageError):
    """The declared content type is not one this service stores."""

    def __init__(self, allowed: frozenset[str]) -> None:
        super().__init__(f"Content type must be one of: {', '.join(sorted(allowed))}")


class FileTooLargeError(ImageError):
    """The declared file size is over the per-upload ceiling."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"File size must be less than {max_bytes // (1024 * 1024)}MB")


class ImageCapReachedError(ImageError):
    """The owner already holds as many images as it is allowed."""

    def __init__(self, limit: int, owner: str) -> None:
        super().__init__(f"Maximum {limit} images per {owner}")


class UploadNotCompletedError(ImageError):
    """The presigned PUT never landed an object in storage."""

    def __init__(self) -> None:
        super().__init__("Image not found in storage. Upload may have failed.")
