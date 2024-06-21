"""Assets client.

Getting assets either requires a unity bundle extractor or a 3rd party git repository.
Image assets are often universal. Game data akways needs to be downloaded for each language.
"""

from __future__ import annotations

import abc
import bisect
import json
import logging
import pathlib
import typing

from arkprts import network as netn
from arkprts.models import base as models

__all__ = ("Assets",)

PathLike = typing.Union[pathlib.Path, str]

LOGGER = logging.getLogger("arkprts.assets")


class Assets(abc.ABC):
    """Game assets client."""

    default_server: netn.ArknightsServer
    """Default server."""
    loaded: bool
    """Whether the data was loaded at any point during the code execution."""
    excel_cache: dict[netn.ArknightsServer, dict[str, typing.Any]]
    """Cache of loaded excel files."""
    json_loads: typing.Callable[[bytes], typing.Any]
    """Alternative self.json_load"""

    def __init__(
        self,
        *,
        default_server: netn.ArknightsServer = "en",
        json_loads: typing.Callable[[bytes], typing.Any] = json.loads,
    ) -> None:
        self.default_server = default_server
        self.loaded = False
        self.excel_cache = {}
        self.json_loads = json_loads

    @classmethod
    def create(
        cls,
        path: PathLike | None = None,
        *,
        network: netn.NetworkSession | None = None,
        default_server: netn.ArknightsServer | None = None,
    ) -> Assets:
        """Create a new assets file based on what libraries are available."""
        try:
            from . import bundle

            return bundle.BundleAssets(path, default_server=default_server, network=network)
        except ImportError:
            from . import git

            return git.GitAssets(path, default_server=default_server or "en")

    @abc.abstractmethod
    async def update_assets(self) -> None:
        """Update game assets.

        Only gamedata for the default server is downloaded by default.
        """

    @abc.abstractmethod
    def get_file(self, path: str, *, server: netn.ArknightsServer | None = None) -> bytes:
        """Get an extracted asset file. If server is None any server is allowed with preference for default server."""

    @abc.abstractmethod
    async def aget_file(self, path: str, *, server: netn.ArknightsServer | None = None) -> bytes:
        """Get an extracted asset file without requiring load."""

    def get_excel(self, name: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a gamedata table file."""
        path = f"gamedata/excel/{name}.json"
        if data := self.excel_cache.setdefault(server or self.default_server, {}).get(path):
            return models.DDict(data)

        data = self.json_loads(self.get_file(path, server=server))
        self.excel_cache[server or self.default_server][path] = data

        return models.DDict(data)

    async def aget_excel(self, name: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a gamedata table file without requiring load."""
        path = f"gamedata/excel/{name}.json"
        if data := self.excel_cache.setdefault(server or self.default_server, {}).get(path):
            return models.DDict(data)

        data = self.json_loads(await self.aget_file(path, server=server))
        self.excel_cache[server or self.default_server][path] = data

        return models.DDict(data)

    def __getitem__(self, name: str) -> models.DDict:
        """Get a gamedata table file."""
        return self.get_excel(name)

    def __getattr__(self, name: str) -> models.DDict:
        """Get a gamedata table file."""
        if name.endswith("_table"):
            return self.get_excel(name)

        return getattr(super(), name)

    # helper stuff
    def get_operator(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get an operator."""
        data = self.get_excel("character_table", server=server)
        return data[id]

    def get_item(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get an item."""
        data = self.get_excel("item_table", server=server)
        return data["items"][id]

    def get_medal(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a medal."""
        data = self.get_excel("medal_table", server=server)
        return next(m for m in data["medalList"] if m["medalId"] == id)

    def get_medal_group(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a medal group. Way too specific probably."""
        data = self.get_excel("medal_table", server=server)
        return next(
            medal_group
            for groups in data["medalTypeData"].values()
            for medal_group in groups["groupData"]
            if medal_group["groupId"] == id
        )

    def get_skill(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a skill."""
        data = self.get_excel("skill_table", server=server)
        return data[id]

    def get_module(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a module."""
        data = self.get_excel("uniequip_table", server=server)
        return data["equipDict"][id]

    def calculate_trust_level(self, trust: int) -> int:
        """Calculate trust level from trust points."""
        frames = self.get_excel("favor_table")["favor_frames"]
        key_frames = [frame["data"]["favor_point"] for frame in frames]
        return bisect.bisect_left(key_frames, trust)
