"""Errors written for an LLM (or a person): what, where, and how to fix it."""
from __future__ import annotations

import difflib


class NotationError(ValueError):
    """Raised with a message written for an LLM: what, where, and how to fix it."""


class SongError(ValueError):
    """A problem in a song map, located as `file:line section: message (suggestion)`."""

    def __init__(self, message: str, *, file: str | None = None, line: int | None = None,
                 section: str | None = None, suggestion: str | None = None):
        self.message, self.file, self.line, self.section, self.suggestion = message, file, line, section, suggestion
        super().__init__(str(self))

    def __str__(self) -> str:
        where = ""
        if self.file:
            where = self.file + (f":{self.line}" if self.line else "") + " "
        if self.section:
            where += f"{self.section}: "
        return where + self.message + (f" ({self.suggestion})" if self.suggestion else "")


def did_you_mean(word: str, valid) -> str:
    """'did you mean X? valid: a b c' hint for unknown names."""
    valid = sorted(valid)
    close = difflib.get_close_matches(str(word), valid, n=1)
    return (f"did you mean '{close[0]}'? " if close else "") + "valid: " + " ".join(valid)
