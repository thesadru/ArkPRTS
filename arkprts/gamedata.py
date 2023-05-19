"""Gamedata client. Fetches from github and such."""
from __future__ import annotations

import json
import logging
import os.path
import pathlib
import re
import tarfile
import tempfile
import typing

import aiohttp

from arkprts.models import base as models

__all__ = ("GameData",)

PathLike = typing.Union[pathlib.Path, str]

GITHUB_REPOSITORY = "Kengxxiao/ArknightsGameData"
RELEVANT_FILES = r"excel"

logger: logging.Logger = logging.getLogger("arkprts.gamedata")


class GameData:
    """Game data client."""

    directory: pathlib.Path
    """Directory path."""
    server: str
    """Default server."""

    _cache: dict[str, dict[str, models.DDict]] = {}

    def __init__(self, directory: PathLike | None = None, *, server: str = "en_US") -> None:
        if directory:
            self.directory = pathlib.Path(directory)
        else:
            self.directory = pathlib.Path(tempfile.gettempdir()) / "ArknightsGameData"

        self.directory.mkdir(parents=True, exist_ok=True)
        self.server = server

    @property
    def tarball_file(self) -> pathlib.Path:
        """Tarball path."""
        return self.directory / "ArknightsGameData.tar.gz"

    @property
    def commit_file(self) -> pathlib.Path:
        """Commit path."""
        return self.directory / "commit.txt"

    async def _get_commit(self) -> str:
        """Get the commit hash."""
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/commits/master"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data["sha"]

    async def _download_tarball(self) -> None:
        """Download a tarball from github."""
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/tarball"
        async with aiohttp.ClientSession(auto_decompress=False) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                with self.tarball_file.open("wb") as file:
                    async for chunk in response.content.iter_any():
                        file.write(chunk)

    def _decompress_tarball(self, allow: str | None = None) -> str:
        """Decompress a tarball. Returns commit name."""
        allow = allow or RELEVANT_FILES

        with tarfile.open(self.tarball_file) as tar:
            top_directory = os.path.commonprefix(tar.getnames())

            members: list[tarfile.TarInfo] = []
            for member in tar.getmembers():
                if not re.search(allow, member.name):
                    continue

                member.name = member.name[len(top_directory + "/") :]
                members.append(member)

            tar.extractall(self.directory, members=members)

        return top_directory.split("-")[-1]

    async def download_gamedata(self, allow: str | None = None, *, force: bool = False) -> None:
        """Download game data."""
        commit = await self._get_commit()
        if not force and self.commit_file.exists() and self.commit_file.read_text() == commit:
            logger.debug("Game data is up to date [%s]", commit)
            return

        logger.info("Downloading game data to %s [%s]", self.directory, commit)
        await self._download_tarball()

        logger.debug("Decompressing game data")
        tarball_commit = self._decompress_tarball(allow)
        logger.debug("Decompressed data %s", tarball_commit)
        if tarball_commit not in commit:
            raise RuntimeError(f"Tarball commit {tarball_commit} does not match github commit {commit}")

        self.commit_file.write_text(commit)
        logger.info("Downloaded game data")

    def _get_data(self, name: str, *, server: str | None = None) -> models.DDict:
        """Get a file."""
        server = server or self.server

        if self._cache.get(server, {}).get(name):
            return models.DDict(self._cache[server][name])

        path = self.directory / server / "gamedata" / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError("Static gamedata has not been loaded.")

        with path.open(encoding="utf-8") as file:
            data = json.load(file)

        self._cache.setdefault(server, {})[name] = data

        return models.DDict(data)

    def _get_excel(self, name: str, *, server: str | None = None) -> models.DDict:
        """Get an excel file."""
        return self._get_data(f"excel/{name}", server=server)

    def get_operator(self, id: str, *, server: str | None = None) -> models.DDict:
        """Get an operator."""
        data = self._get_excel("character_table", server=server)
        return data[id]

    def get_item(self, id: str, *, server: str | None = None) -> models.DDict:
        """Get an item."""
        data = self._get_excel("item_table", server=server)
        return data["items"][id]

    def get_medal(self, id: str, *, server: str | None = None) -> models.DDict:
        """Get a medal."""
        data = self._get_excel("medal_table", server=server)
        return data["medalList"][id]

    def get_medal_group(self, id: str, *, server: str | None = None) -> models.DDict:
        """Get a medal group. Way too specific probably."""
        data = self._get_excel("medal_table", server=server)
        return next(i for i in data["medalTypeData"]["activityMedal"]["groupData"] if i["groupId"] == id)

    def get_skill(self, id: str, *, server: str | None = None) -> models.DDict:
        """Get a skill."""
        data = self._get_excel("skill_table", server=server)
        return data[id]

    def get_module(self, id: str, *, server: str | None = None) -> models.DDict:
        """Get a module."""
        data = self._get_excel("uniequip_table", server=server)
        return data["equipDict"][id]
