import hashlib


def source_hash(text: str) -> str:
    """Stable short hash of an English source string. Used to detect source drift."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
