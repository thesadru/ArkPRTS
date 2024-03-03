"""Modified pydantic base model."""

from __future__ import annotations

import collections
import datetime
import typing

import pydantic
import pydantic_core

from arkprts.client import CoreClient

__all__ = ("BaseModel", "DDict")

# pydantic hack
_fake_client = type("", (object,), {})()
_fake_client.__class__ = CoreClient


def _set_recursively(obj: typing.Any, name: str, value: typing.Any) -> None:
    """Set an attribute recursively."""
    if isinstance(obj, BaseModel):
        object.__setattr__(obj, name, value)
        for field in type(obj).model_fields:
            _set_recursively(getattr(obj, field), name, value)

    elif isinstance(obj, typing.Mapping):
        for key, item in obj.items():  # pyright: ignore[reportUnknownVariableType]
            _set_recursively(key, name, value)
            _set_recursively(item, name, value)
    elif isinstance(obj, typing.Sequence) and not isinstance(obj, str):
        for item in obj:  # pyright: ignore[reportUnknownVariableType]
            _set_recursively(item, name, value)


def _to_camel_case(string: str) -> str:
    """Convert snake_case to camelCase."""
    return "".join(x.title() if i else x for i, x in enumerate(string.split("_")))


def parse_timestamp(timestamp: int) -> datetime.datetime | None:
    """Parse an arknights timestamp and use the local timezone.

    Arknights provides timestamps not with UTC but with the client's timezone.
    """
    if timestamp in (0, -1):
        return None

    return datetime.datetime.fromtimestamp(int(timestamp)).astimezone()


class BaseModel(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Client-aware pydantic base model."""

    client: CoreClient = pydantic.Field(repr=False)
    """Client instance."""

    def __init__(self, client: CoreClient | None = None, **kwargs: typing.Any) -> None:
        """Init."""
        super().__init__(client=_fake_client, **kwargs)
        if client:
            _set_recursively(self, "client", client)

    @pydantic.model_validator(mode="before")  # pyright: ignore
    def _fix_amiya(cls, value: typing.Any, info: pydantic.ValidationInfo) -> typing.Any:
        """Flatten Amiya to only keep her selected form if applicable."""
        if value and value.get("tmpl"):
            # tmplId present in battle replays
            current_tmpl = value["currentTmpl"] if "currentTmpl" in value else value["tmplId"]
            current = value["tmpl"].get(current_tmpl, next(iter(value["tmpl"].values())))
            value.update(current)

        return value


class DList(collections.UserList[typing.Any]):
    """Dot-accessed list."""

    def __getitem__(self, key: typing.Any) -> typing.Any:
        item = super().__getitem__(key)

        if isinstance(item, dict):
            item = DDict(item)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(item, list):
            item = DList(item)  # pyright: ignore[reportUnknownArgumentType]

        return item

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: typing.Any,
        handler: typing.Callable[[typing.Any], pydantic_core.CoreSchema],
    ) -> pydantic_core.CoreSchema:
        """Generate a pydantic core schema."""
        return pydantic_core.core_schema.no_info_plain_validator_function(cls)


class DDict(collections.UserDict[str, typing.Any]):
    """Dot-accessed dictionary."""

    def __getitem__(self, key: typing.Any) -> typing.Any:
        try:
            item = super().__getitem__(key)
        except KeyError:
            item = super().__getitem__(_to_camel_case(key))

        if isinstance(item, dict):
            item = DDict(item)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(item, list):
            item = DList(item)  # pyright: ignore[reportUnknownArgumentType]

        return item

    def __getattr__(self, key: str) -> typing.Any:
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(*e.args) from e

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: typing.Any,
        handler: typing.Callable[[typing.Any], pydantic_core.CoreSchema],
    ) -> pydantic_core.CoreSchema:
        """Generate a pydantic core schema."""
        return pydantic_core.core_schema.no_info_plain_validator_function(cls)


ArknightsTimestamp = typing.Annotated[datetime.datetime, pydantic.PlainValidator(parse_timestamp)]
