"""Arkprts errors."""
import typing


class BaseArkprtsError(Exception):
    """Base class for all Arkprts errors."""

    message: str = "Arkprts error."

    def __init__(self, message: typing.Optional[str] = None) -> None:
        super().__init__(message or self.message)


class NotLoggedInError(BaseArkprtsError):
    """Raised when a user is not logged in."""

    message = "Not logged in."


class ArkPrtsError(BaseArkprtsError):
    """Raised when result code is not 0."""

    data: typing.Mapping[str, typing.Any]

    def __init__(self, data: typing.Mapping[str, typing.Any]) -> None:
        self.data = data
        super().__init__(f"[{data['result']}] {data}")


class InvalidStatusError(BaseArkprtsError):
    """Raised when a response has an invalid status code."""

    status: int
    data: typing.Mapping[str, typing.Any]

    def __init__(self, status: int, data: typing.Mapping[str, typing.Any]) -> None:
        self.status = status
        self.data = data

        super().__init__(f"[{status}] {data}")


class InvalidContentTypeError(BaseArkprtsError):
    """Raised when a response has an invalid content type."""

    message = "Invalid content type."
    content: str

    def __init__(self, content: str) -> None:
        self.content = content
        super().__init__()
