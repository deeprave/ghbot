from collections.abc import Mapping
from datetime import datetime


class FatalError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class AuthError(FatalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


class GitHubApiError(FatalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)


class GitHubGraphQLPartialDataError(GitHubApiError):
    """A GraphQL response retained usable data alongside field errors."""

    def __init__(
        self,
        message: str,
        *,
        data: Mapping[str, object],
        errors: tuple[Mapping[str, object], ...],
    ) -> None:
        super().__init__(message)
        self.data = dict(data)
        self.errors = errors


class GitHubNotFoundError(GitHubApiError):
    pass


class GitHubForbiddenError(GitHubApiError):
    pass


class GitHubRateLimitError(GitHubApiError):
    """A GitHub limit with normalized retry timing, if GitHub supplied it."""

    def __init__(
        self,
        message: str,
        *,
        delay_seconds: float | None = None,
        reset_at: datetime | None = None,
    ) -> None:
        super().__init__(message)
        self.delay_seconds = delay_seconds
        self.reset_at = reset_at


class GitHubPrimaryRateLimitError(GitHubRateLimitError):
    """gidgethub RateLimitExceeded (403) — quota exhausted."""


class GitHubSecondaryRateLimitError(GitHubRateLimitError):
    """429 Too Many Requests — slow down, retry after delay."""


class RateLimitAbortError(FatalError):
    """A report was written but GitHub limits prevented completion."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=4)
