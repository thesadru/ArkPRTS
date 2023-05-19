"""Modified pydantic base model."""
import collections
import typing

import pydantic

from arkprts.client import Client

__all__ = ("BaseModel", "DDict")

# pydantic hack
_fake_client = type("", (object,), {})()
_fake_client.__class__ = Client


def _set_recursively(obj: typing.Any, name: str, value: typing.Any) -> None:
    """Set an attribute recursively."""
    if isinstance(obj, BaseModel):
        object.__setattr__(obj, name, value)
        for field in obj.__fields__:
            _set_recursively(getattr(obj, field), name, value)

    elif isinstance(obj, typing.Mapping):
        for key, item in obj.items():  # pyright: ignore[reportUnknownVariableType]
            _set_recursively(key, name, value)
            _set_recursively(item, name, value)
    elif isinstance(obj, typing.Sequence) and not isinstance(obj, str):
        for item in obj:  # pyright: ignore[reportUnknownVariableType]
            _set_recursively(item, name, value)


def _to_snake_case(string: str) -> str:
    """Convert camelCase to snake_case."""
    return "".join(
        ("_" if i and string[i].isupper() and not string[i : i + 2].isupper() else "") + x.lower()
        for i, x in enumerate(string)
    )


class BaseModel(pydantic.BaseModel):
    """Client-aware pydantic base model."""

    client: Client = pydantic.Field(repr=False)
    """Client instance."""

    def __init__(self, client: typing.Optional[Client] = None, **kwargs: typing.Any) -> None:
        """Init."""
        super().__init__(client=_fake_client, **kwargs)
        if client:
            _set_recursively(self, "client", client)

    class Config:
        """Config."""

        arbitrary_types_allowed = True


class DList(collections.UserList[typing.Any]):
    """Dot-accessed list."""

    def __getitem__(self, key: typing.Any) -> typing.Any:
        item = super().__getitem__(key)
        if isinstance(item, dict):
            item = DDict(item)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(item, list):
            item = DList(item)  # pyright: ignore[reportUnknownArgumentType]

        return item


class DDict(collections.UserDict[str, typing.Any]):
    """Dot-accessed dictionary."""

    def __getitem__(self, key: typing.Any) -> typing.Any:
        item = super().__getitem__(_to_snake_case(key))
        if isinstance(item, dict):
            item = DDict(item)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(item, list):
            item = DList(item)  # pyright: ignore[reportUnknownArgumentType]

        return item

    def __getattr__(self, key: str) -> typing.Any:
        return self[key]
