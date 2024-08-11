"""Arkprts errors."""

from __future__ import annotations

import json
import typing


class BaseArkprtsError(Exception):
    """Base class for all Arkprts errors."""

    message: str = "Arkprts error."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class NotLoggedInError(BaseArkprtsError):
    """Raised when a user is not logged in."""

    message = "Not logged in."


class ArkPrtsError(BaseArkprtsError):
    """Raised when result code is not 0."""

    data: typing.Mapping[str, typing.Any]

    def __init__(self, data: typing.Mapping[str, typing.Any]) -> None:
        self.data = data
        super().__init__(f"[{data.get('result')}] {self.message} {json.dumps(data)}")


class GameServerError(ArkPrtsError):
    """Game server error."""

    data: typing.Mapping[str, typing.Any]
    status_code: int
    error: str
    code: int
    msg: str
    info: typing.Mapping[str, typing.Any]

    def __init__(self, data: typing.Mapping[str, typing.Any]) -> None:
        self.data = data
        self.status_code = data.get("statusCode", 400)
        self.error = data["error"]
        self.code = data.get("code", 0)
        self.msg = data.get("msg", "")
        self.info = json.loads(data.get("info", "{}"))

        BaseArkprtsError.__init__(self, json.dumps(data))


class GeetestError(ArkPrtsError):
    """Raised when login is flagged by geetest."""

    message: str = "Geetest verification is required."
    challenge: str
    gt: str

    def __init__(self, data: typing.Mapping[str, typing.Any]) -> None:
        self.challenge = data["captcha"]["challenge"]
        self.gt = data["captcha"]["gt"]
        super().__init__(data)


class InvalidStatusError(ArkPrtsError):
    """Raised when a response has an invalid status code."""

    status: int
    data: typing.Mapping[str, typing.Any]

    def __init__(self, status: int, data: typing.Mapping[str, typing.Any]) -> None:
        self.status = status
        self.data = data

        BaseArkprtsError.__init__(self, f"[{status}] {json.dumps(data)}")


class InvalidContentTypeError(BaseArkprtsError):
    """Raised when a response has an invalid content type."""

    message = "Invalid content type."
    content: str

    def __init__(self, content: str) -> None:
        self.content = content
        super().__init__()
