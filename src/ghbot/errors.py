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


class GitHubNotFoundError(GitHubApiError):
    pass


class GitHubPrimaryRateLimitError(GitHubApiError):
    """gidgethub RateLimitExceeded (403) — quota exhausted, carries rate_limit object."""

    pass


class GitHubSecondaryRateLimitError(GitHubApiError):
    """429 Too Many Requests — slow down, retry after delay."""

    pass


class UnexpectedError(FatalError):
    pass
