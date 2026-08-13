"""Domain errors (CHASSIS, framework-free). Streamlit pages render ``.message`` to the user."""
from __future__ import annotations


class CoreError(Exception):
    """Base for user-facing domain errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(CoreError):
    pass


class NotFoundError(CoreError):
    pass


class ConflictError(CoreError):
    """A rule was violated (e.g. writing to a closed cohort, duplicate name)."""
