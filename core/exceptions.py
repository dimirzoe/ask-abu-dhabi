"""Custom exception hierarchy for Ask Abu Dhabi.

All application errors derive from :class:`AskAbuDhabiError` so callers can catch
the whole domain with a single ``except`` while still being able to discriminate
specific failure modes.
"""

from __future__ import annotations


class AskAbuDhabiError(Exception):
    """Base class for every error raised by the application."""


class ConfigError(AskAbuDhabiError):
    """Raised when configuration is missing, malformed, or inconsistent."""


class LLMError(AskAbuDhabiError):
    """Raised when an LLM provider fails to return a usable completion."""


class KnowledgeBaseError(AskAbuDhabiError):
    """Raised when the knowledge base cannot be loaded or is unusable."""


class ETLError(AskAbuDhabiError):
    """Raised when an ETL run fails or does not meet validation thresholds."""
