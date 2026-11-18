"""Neutralises text that a spreadsheet program would run as a formula."""

from __future__ import annotations

_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def neutralise(text: str) -> str:
    """Prefix an apostrophe when ``text`` starts like a formula.

    A name such as ``=HYPERLINK(...)`` can arrive through the API or a CSV. Opened
    in a spreadsheet it would execute, so every text cell written to a CSV or a
    workbook goes through here. Numbers are written as numbers and are not affected.
    """
    return "'" + text if text.startswith(_FORMULA_STARTS) else text
