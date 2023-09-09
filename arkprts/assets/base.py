"""Assets client.

Getting assets either requires a unity bundle extractor or a 3rd party git repository.
Image assets are often universal. Game data akways needs to be downloaded for each language.
"""
from __future__ import annotations

import abc
import bisect
import importlib.util
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

    def __init__(self, *, default_server: netn.ArknightsServer = "en") -> None:
        self.default_server = default_server
        self.loaded = False

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
            importlib.util.find_spec("UnityPy")
        except ImportError:
            from . import git

            LOGGER.debug("Creating GitAssets due to UnityPy being unavailable")
            return git.GitAssets(path, default_server=default_server or "en")
        else:
            from . import bundle

            return bundle.BundleAssets(path, default_server=default_server, network=network)

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
        data = self.get_file(f"gamedata/excel/{name}.json", server=server)
        return models.DDict(json.loads(data))

    async def aget_excel(self, name: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a gamedata table file without requiring load."""
        data = await self.aget_file(f"gamedata/excel/{name}.json", server=server)
        return models.DDict(json.loads(data))

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
        return data["medalList"][id]

    def get_medal_group(self, id: str, *, server: netn.ArknightsServer | None = None) -> models.DDict:
        """Get a medal group. Way too specific probably."""
        data = self.get_excel("medal_table", server=server)
        return next(i for i in data["medalTypeData"]["activityMedal"]["groupData"] if i["groupId"] == id)

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