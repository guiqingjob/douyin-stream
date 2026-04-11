from __future__ import annotations


class QwenTranscribeError(Exception):
    exit_code = 1


class UserFacingError(QwenTranscribeError):
    exit_code = 2


class ConfigurationError(UserFacingError):
    """Raised when local configuration or environment values are invalid."""


class InputValidationError(UserFacingError):
    """Raised when the user provides invalid command input."""


class AuthenticationRequiredError(UserFacingError):
    """Raised when a command needs a saved auth state that does not exist."""
