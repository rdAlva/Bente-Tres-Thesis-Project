"""Helpers for separating a document's display name from its file identity."""

from pathlib import Path
import uuid


_SEPARATOR = "__"


def make_internal_filename(filename: str) -> str:
    """Return a collision-safe filename while retaining the original suffix."""
    name = Path(filename).name
    return f"{uuid.uuid4().hex}{_SEPARATOR}{name}"


def display_filename(filename: str) -> str:
    """Return the user-facing portion of a filename created above.

    Legacy filenames do not contain the separator and are returned unchanged.
    """
    name = Path(filename).name
    prefix, separator, original = name.partition(_SEPARATOR)
    if separator and len(prefix) == 32 and original:
        return original
    return name


def companion_filename(filename: str, suffix: str) -> str:
    """Return the same internal name with a different file suffix."""
    return Path(filename).with_suffix(suffix).name
