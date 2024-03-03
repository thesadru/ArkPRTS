"""Git managed asset interface.

Has to use two separate repositories,
a game data repository with all languages and an image resource repository with only one language.
"""

from __future__ import annotations

import asyncio
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

from arkprts import network as netn

from . import base

__all__ = ("GitAssets",)

LOGGER: logging.Logger = logging.getLogger("arkprts.assets.git")

CN_GAMEDATA_REPOSITORY = "Kengxxiao/ArknightsGameData"  # master
GLOBAL_GAMEDATA_REPOSITORY = "Kengxxiao/ArknightsGameData_YoStar"  # main
TW_GAMEDATA_REPOSITORY = "aelurum/ArknightsGameData"  # zh-tw fork  # master_v2
RESOURCES_REPOSITORY = "Aceship/Arknight-Images"  # main
ALT_RESOURCES_REPOSITORY = "yuanyan3060/ArknightsGameResource"  # contains zh-cn files  # main

GAMEDATA_LANGUAGE: typing.Mapping[netn.ArknightsServer, str] = {
    "en": "en_US",
    "jp": "ja_JP",
    "kr": "ko_KR",
    "cn": "zh_CN",
    "bili": "zh_CN",
    "tw": "zh_TW",
}

PathLike = typing.Union[pathlib.Path, str]


async def download_github_file(repository: str, path: str, *, branch: str = "HEAD") -> bytes:
    """Download a file from github."""
    url = f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"
    async with aiohttp.request("GET", url) as response:
        response.raise_for_status()
        return await response.read()


async def get_github_repository_commit(repository: str, *, branch: str = "HEAD") -> str:
    """Get the commit hash of a github repository."""
    url = f"https://api.github.com/repos/{repository}/commits/{branch}"
    async with aiohttp.request("GET", url) as response:
        response.raise_for_status()
        data = await response.json()
        return data["sha"]


async def download_github_tarball(
    repository: str,
    destination: PathLike | None,
    *,
    branch: str = "HEAD",
) -> pathlib.Path:
    """Download a tarball from github."""
    destination = pathlib.Path(destination or tempfile.mktemp(f"{repository.split('/')[-1]}.tar.gz"))
    if branch == "HEAD":
        url = f"https://api.github.com/repos/{repository}/tarball"
    else:
        url = f"https://github.com/{repository}/archive/refs/heads/{branch}.tar.gz"

    async with aiohttp.ClientSession(auto_decompress=False) as session, session.get(url) as response:
        response.raise_for_status()
        with destination.open("wb") as file:  # noqa: ASYNC101  # would need another dependency
            async for chunk in response.content.iter_any():
                file.write(chunk)

    return destination


def decompress_tarball(path: PathLike, destination: PathLike, *, allow: str = "*") -> str:
    """Decompress a tarball without the top directory and return the top directory name."""
    with tarfile.open(path) as tar:
        top_directory = os.path.commonprefix(tar.getnames())

        members: list[tarfile.TarInfo] = []
        for member in tar.getmembers():
            if not fnmatch.fnmatch(allow, member.name):
                continue

            member.name = member.name[len(top_directory + "/") :]
            members.append(member)

        tar.extractall(destination, members=members)  # noqa: S202 # type: ignore

    return top_directory


async def download_repository(
    repository: str,
    destination: PathLike,
    allow: str = "*",
    *,
    branch: str = "HEAD",
    force: bool = False,
) -> None:
    """Download a repository from github."""
    destination = pathlib.Path(destination)
    commit_file = destination / "commit.txt"

    if not force and commit_file.exists() and time.time() - commit_file.stat().st_mtime < 60 * 60 * 6:
        LOGGER.debug("%s was updated recently, skipping download", repository)
        return

    try:
        commit = await get_github_repository_commit(repository, branch=branch)
    except aiohttp.ClientResponseError:
        LOGGER.warning("Failed to get %s commit, skipping download", repository, exc_info=True)
        return

    if not force and commit_file.exists() and commit_file.read_text() == commit:
        LOGGER.debug("%s is up to date [%s]", repository, commit)
        return

    LOGGER.info("Downloading %s to %s [%s]", repository, str(destination), commit)
    tarball_path = await download_github_tarball(
        repository,
        destination / f"{repository.split('/')[-1]}.tar.gz",
        branch=branch,
    )

    LOGGER.debug("Decompressing %s", repository)
    tarball_commit = decompress_tarball(tarball_path, destination, allow=allow)
    LOGGER.debug("Decompressed %s %s", repository, tarball_commit)
    if tarball_commit not in commit:
        raise RuntimeError(f"Tarball commit {tarball_commit} does not match github commit {commit}")

    # sometimes the contents are identical, we still want to update the mtime
    commit_file.write_text(commit)
    os.utime(commit_file, (time.time(), time.time()))

    LOGGER.info("Downloaded %s", repository)


async def update_git_repository(repository: str, directory: PathLike, *, branch: str = "HEAD") -> None:
    """Update game data."""
    directory = pathlib.Path(directory)

    if not (directory / ".git").exists():
        LOGGER.info("Initializing repository in %s", directory)
        directory.parent.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth=1",
            *([] if branch == "HEAD" else ["--branch", branch]),
            f"https://github.com/{repository}.git",
            cwd=directory.parent,
        )
        await proc.wait()
    else:
        LOGGER.info("Updating %s in %s", repository, directory)
        proc = await asyncio.create_subprocess_exec("git", "pull", cwd=directory)
        await proc.wait()


async def _check_git_installed_async() -> bool:
    """Check if git is installed."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        "--version",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return (await proc.wait()) == 0


async def update_repository(
    repository: str,
    directory: PathLike,
    *,
    allow: str = "*",
    branch: str = "HEAD",
    force: bool = False,
) -> None:
    """Update a repository even if git is not installed."""
    if await _check_git_installed_async():
        await update_git_repository(repository, directory, branch=branch)
    else:
        await download_repository(repository, directory, allow=allow, branch=branch, force=force)


class GitAssets(base.Assets):
    """Game assets client downloaded through 3rd party git repositories."""

    gamedata_directory: pathlib.Path
    resources_directory: pathlib.Path
    gamedata_repository: str
    resources_repository: str

    def __init__(
        self,
        gamedata_directory: PathLike | None = None,
        resources_directory: PathLike | None = None,
        gamedata_repository: str | None = None,
        resources_repository: str | None = None,
        *,
        default_server: netn.ArknightsServer = "en",
        json_loads: typing.Callable[[bytes], typing.Any] = json.loads,
    ) -> None:
        super().__init__(default_server=default_server, json_loads=json_loads)

        default_directory = pathlib.Path(tempfile.gettempdir())

        if gamedata_repository:
            self.gamedata_repository = gamedata_repository
        elif self.default_server == "cn":
            self.gamedata_repository = CN_GAMEDATA_REPOSITORY
        elif self.default_server == "tw":
            self.gamedata_repository = TW_GAMEDATA_REPOSITORY
        else:
            self.gamedata_repository = GLOBAL_GAMEDATA_REPOSITORY

        self.resources_repository = resources_repository or RESOURCES_REPOSITORY

        self.gamedata_directory = pathlib.Path(
            gamedata_directory or default_directory / self.gamedata_repository.split("/")[1],
        )
        self.resources_directory = pathlib.Path(
            resources_directory or default_directory / self.resources_repository.split("/")[1],
        )

    async def update_assets(
        self,
        resources: bool = False,
        *,
        force: bool = False,
    ) -> None:
        """Update game data.

        Only gamedata for the default server is downloaded by default.
        """
        await update_repository(
            self.gamedata_repository,
            self.gamedata_directory,
            allow="gamedata/excel/*",
            force=force,
        )

        if resources:
            await update_repository(self.resources_repository, self.resources_directory, force=force)

        self.loaded = True

    def get_file(self, path: str, *, server: netn.ArknightsServer | None = None) -> bytes:
        """Get an extracted asset file."""
        if "gamedata" in path:
            directory = self.gamedata_directory / GAMEDATA_LANGUAGE[server or self.default_server]
        else:
            directory = self.resources_directory

        return (directory / path).read_bytes()

    async def aget_file(self, path: str, *, server: netn.ArknightsServer | None = None) -> bytes:
        """Get an extracted asset file without requiring load."""
        if "gamedata" in path:
            repository = self.gamedata_repository
            path = f"{GAMEDATA_LANGUAGE[server or self.default_server]}/{path}"
        else:
            repository = self.resources_repository

        return await download_github_file(repository, path)
