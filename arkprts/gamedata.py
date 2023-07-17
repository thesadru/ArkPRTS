"""Gamedata client. Fetches from github and such."""
from __future__ import annotations

import asyncio
import bisect
import fnmatch
import json
import logging
import os
import os.path
import pathlib
import subprocess
import tarfile
import tempfile
import time
import typing

import aiohttp

from arkprts.auth import ArknightsLanguage
from arkprts.models import base as models

__all__ = ("GameData",)

PathLike = typing.Union[pathlib.Path, str]

GITHUB_REPOSITORY = "Kengxxiao/ArknightsGameData"
TW_GITHUB_REPOSITORY = "aelurum/ArknightsGameData"  # zh-tw fork
RELEVANT_FILES = r"excel"

logger: logging.Logger = logging.getLogger("arkprts.gamedata")


class GameData:
    """Game data client."""

    directory: pathlib.Path
    """Directory path."""
    language: ArknightsLanguage
    """Default language."""
    loaded: bool
    """Whether the data was loaded at any point during the code execution."""

    _cache: dict[str, dict[str, models.DDict]]
    """Loaded files."""
    _lock: asyncio.Lock
    """Gamedata update lock."""

    def __init__(self, directory: PathLike | None = None, *, language: ArknightsLanguage = "en_US") -> None:
        if directory:
            self.directory = pathlib.Path(directory).expanduser()
        else:
            self.directory = pathlib.Path(tempfile.gettempdir()) / "ArknightsGameData"

        self.directory.mkdir(parents=True, exist_ok=True)
        self.language = language
        self.loaded = False
        self._cache = {}
        self._lock = asyncio.Lock()

    @property
    def commit_file(self) -> pathlib.Path:
        """Commit path."""
        return self.directory / "commit.txt"

    async def _get_commit(self) -> str:
        """Get the commit hash."""
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/commits/master"
        async with aiohttp.ClientSession() as session, session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data["sha"]

    async def _download_tarball(self) -> None:
        """Download a tarball from github."""
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/tarball"
        async with aiohttp.ClientSession(auto_decompress=False) as session, session.get(url) as response:
            response.raise_for_status()
            with (self.directory / "ArknightsGameData.tar.gz").open("wb") as file:
                async for chunk in response.content.iter_any():
                    file.write(chunk)

    def _decompress_tarball(self, allow: str | None = None) -> str:
        """Decompress a tarball. Returns commit name."""
        allow = allow or RELEVANT_FILES

        with tarfile.open(self.directory / "ArknightsGameData.tar.gz") as tar:
            top_directory = os.path.commonprefix(tar.getnames())

            members: list[tarfile.TarInfo] = []
            for member in tar.getmembers():
                if not fnmatch.fnmatch(allow, member.name):
                    continue

                member.name = member.name[len(top_directory + "/") :]
                members.append(member)

            tar.extractall(self.directory, members=members)

        return top_directory.split("-")[-1]

    async def download_tarball_gamedata(self, allow: str | None = None, *, force: bool = False) -> None:
        """Download game data."""
        if not force and self.commit_file.exists() and time.time() - self.commit_file.stat().st_mtime < 60 * 60 * 6:
            logger.debug("Game data was updated recently, skipping download")
            return

        try:
            commit = await self._get_commit()
        except aiohttp.ClientResponseError:
            logger.warning("Failed to get game data commit, skipping download", exc_info=True)
            return

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

        # sometimes the contents are identical, we still want to update the mtime
        self.commit_file.write_text(commit)
        os.utime(self.commit_file, (time.time(), time.time()))

        logger.info("Downloaded game data")

    async def update_git_gamedata(self) -> None:
        """Update game data."""
        if not (self.directory / ".git").exists():
            logger.info("Initializing repository in %s", self.directory)
            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth=1",
                f"https://github.com/{GITHUB_REPOSITORY}.git",
                cwd=self.directory.parent,
            )
            await proc.wait()
        else:
            logger.info("Updating game data in %s", self.directory)
            proc = await asyncio.create_subprocess_exec("git", "pull", cwd=self.directory)
            await proc.wait()

    async def update_gamedata(self, allow: str | None = None, *, force: bool = False) -> None:
        """Update game data."""
        async with self._lock:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "--version",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if (await proc.wait()) == 0:
                await self.update_git_gamedata()
            else:
                await self.download_tarball_gamedata(allow=allow, force=force)

            self.loaded = True

    def _get_data(self, filename: str, *, language: str | None = None) -> typing.Any:
        """Get a file."""
        language = language or self.language

        if self._cache.get(language, {}).get(filename):
            return self._cache[language][filename]

        path = self.directory / language / "gamedata" / filename
        if not path.exists():
            raise FileNotFoundError("Static gamedata has not been loaded.")

        with path.open(encoding="utf-8") as file:
            data = json.load(file)

        self._cache.setdefault(language, {})[filename] = data

        return data

    def get_excel(self, name: str, *, language: str | None = None) -> models.DDict:
        """Get an excel table file."""
        return models.DDict(self._get_data(f"excel/{name}.json", language=language))

    def __getitem__(self, name: str) -> models.DDict:
        """Get an excel table file."""
        return self.get_excel(name)

    def __getattr__(self, name: str) -> models.DDict:
        """Get an excel table file."""
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    # helper stuff
    def get_operator(self, id: str, *, language: str | None = None) -> models.DDict:
        """Get an operator."""
        data = self.get_excel("character_table", language=language)
        return data[id]

    def get_item(self, id: str, *, language: str | None = None) -> models.DDict:
        """Get an item."""
        data = self.get_excel("item_table", language=language)
        return data["items"][id]

    def get_medal(self, id: str, *, language: str | None = None) -> models.DDict:
        """Get a medal."""
        data = self.get_excel("medal_table", language=language)
        return data["medalList"][id]

    def get_medal_group(self, id: str, *, language: str | None = None) -> models.DDict:
        """Get a medal group. Way too specific probably."""
        data = self.get_excel("medal_table", language=language)
        return next(i for i in data["medalTypeData"]["activityMedal"]["groupData"] if i["groupId"] == id)

    def get_skill(self, id: str, *, language: str | None = None) -> models.DDict:
        """Get a skill."""
        data = self.get_excel("skill_table", language=language)
        return data[id]

    def get_module(self, id: str, *, language: str | None = None) -> models.DDict:
        """Get a module."""
        data = self.get_excel("uniequip_table", language=language)
        return data["equipDict"][id]

    def calculate_trust_level(self, trust: int) -> int:
        """Calculate trust level from trust points."""
        frames = self.get_excel("favor_table")["favor_frames"]
        key_frames = [frame["data"]["favor_point"] for frame in frames]
        return bisect.bisect_left(key_frames, trust)
