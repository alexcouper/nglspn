from __future__ import annotations


def flatten_en(obj: dict) -> dict[str, str]:
    """Convert nested en.json (dict of dicts of strings) into flat dotted-key map."""
    out: dict[str, str] = {}
    _walk(obj, prefix="", out=out)
    return out


def _walk(node: dict, prefix: str, out: dict[str, str]) -> None:
    for key, value in node.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _walk(value, prefix=full, out=out)
        elif isinstance(value, str):
            out[full] = value
        else:
            msg = f"en.json leaf at {full!r} is not a string: {value!r}"
            raise TypeError(msg)
