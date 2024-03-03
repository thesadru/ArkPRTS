"""Direct asset download.

Downloads assets directly from arknights servers.
Unfortunately assets are stored as unity files, so they need to be extracted.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import fnmatch
import functools
import io
import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile
import typing
import warnings
import zipfile

from arkprts import network as netn

from . import base, git

__all__ = ("BundleAssets",)

LOGGER = logging.getLogger("arkprts.assets.bundle")

PathLike = typing.Union[pathlib.Path, str]
# unfortunately UnityPy lacks typing
UnityPyAsset = typing.Any
UnityPyObject = typing.Any

UPDATED_FBS = {"cn": False, "yostar": False}


def asset_path_to_server_filename(path: str) -> str:
    """Take a path to a zipped unity asset and return its filename on the server."""
    filename = path.replace("/", "_").replace("#", "__").replace(".ab", ".dat")
    return filename


def unzip_only_file(stream: io.BytesIO | bytes) -> bytes:
    """Unzip a single file from a zip archive."""
    if not isinstance(stream, io.BytesIO):
        stream = io.BytesIO(stream)

    with zipfile.ZipFile(stream) as archive:
        return archive.read(archive.namelist()[0])


def resolve_unity_asset_cache(filename: str, server: netn.ArknightsServer) -> pathlib.Path:
    """Resolve a path to a cached arknights ab file."""
    path = pathlib.Path(tempfile.gettempdir()) / "ArknightsUnity" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.with_suffix(".ab")


def load_unity_file(stream: io.BytesIO | bytes) -> bytes:
    """Load an unzipped arknights unity .ab file."""
    import UnityPy

    env: typing.Any = UnityPy.load(io.BytesIO(stream))  # pyright: ignore

    bundle_file, *_ = env.files.values()
    assert not _
    asset_file, *_ = bundle_file.files.values()
    assert not _

    return asset_file


def decrypt_aes_text(data: bytes, *, rsa: bool = True) -> bytes:
    """Decrypt aes text."""
    from Crypto.Cipher import AES

    mask = bytes.fromhex("554954704169383270484157776e7a7148524d4377506f6e4a4c49423357436c")

    if rsa:
        data = data[128:]

    aes_key = mask[:16]
    aes_iv = bytearray(b ^ m for b, m in zip(data[:16], mask[16:]))
    aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)  # pyright: ignore[reportUnknownMemberType]

    decrypted_padded = aes.decrypt(data[16:])
    decrypted = decrypted_padded[: -decrypted_padded[-1]]
    return decrypted


def run_flatbuffers(
    fbs_path: PathLike,
    fbs_schema_path: PathLike,
    output_directory: PathLike,
) -> pathlib.Path:
    """Run the flatbuffers cli. Returns the output filename."""
    code = subprocess.call(
        [  # noqa: S603  # check for execution of untrusted input
            "flatc",
            "-o",
            str(output_directory),
            str(fbs_schema_path),
            "--",
            str(fbs_path),
            "--json",
            "--strict-json",
            "--natural-utf8",
            "--defaults-json",
            "--unknown-json",
            "--raw-binary",
            # unfortunately not in older versions
            # "--no-warnings",
            "--force-empty",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if code != 0:
        raise ValueError(f"flatc failed with code {code}")

    return pathlib.Path(output_directory) / (pathlib.Path(fbs_path).stem + ".json")


def resolve_fbs_schema_directory(server: typing.Literal["cn", "yostar"]) -> pathlib.Path:
    """Resolve the flatbuffers schema directory."""
    path = os.environ.get(f"FLATBUFFERS_SCHEMA_DIR_{server.upper()}")
    if path:
        return pathlib.Path(path)

    core_path = pathlib.Path(tempfile.gettempdir()) / "ArknightsFBS"
    core_path.mkdir(parents=True, exist_ok=True)
    path = core_path / server / "OpenArknightsFBS" / "FBS"
    os.environ[f"FLATBUFFERS_SCHEMA_DIR_{server.upper()}"] = str(path)
    return path


async def update_fbs_schema(*, force: bool = False) -> None:
    """Download or otherwise update FBS files."""
    for server, branch in [("cn", "main"), ("yostar", "YoStar")]:
        if UPDATED_FBS[server] and not force:
            continue

        UPDATED_FBS[server] = True
        directory = resolve_fbs_schema_directory(server).parent
        await git.update_repository("MooncellWiki/OpenArknightsFBS", directory, branch=branch, force=force)


def recursively_collapse_keys(obj: typing.Any) -> typing.Any:
    """Recursively collapse arknights flatc dictionaries."""
    if isinstance(obj, list):
        obj = typing.cast("typing.Any", obj)
        if all(isinstance(item, dict) and item.keys() == {"key", "value"} for item in obj):
            return {item["key"]: recursively_collapse_keys(item["value"]) for item in obj}

        return [recursively_collapse_keys(item) for item in obj]

    if isinstance(obj, dict):
        obj = typing.cast("typing.Any", obj)
        return {k: recursively_collapse_keys(v) for k, v in obj.items()}

    return obj


def decrypt_fbs_file(
    data: bytes,
    table_name: str,
    server: netn.ArknightsServer,
    *,
    rsa: bool = True,
    normalize: bool = False,
) -> bytes:
    """Decrypt fbs json file."""
    if rsa:
        data = data[128:]

    tempdir = pathlib.Path(tempfile.gettempdir()) / "TempArknightsFBS"
    tempdir.mkdir(parents=True, exist_ok=True)

    fbs_path = tempdir / (table_name + ".bytes")
    fbs_path.write_bytes(data)
    fbs_schema_path = resolve_fbs_schema_directory(server="cn" if server in ("cn", "bili") else "yostar") / (
        table_name + ".fbs"
    )
    output_directory = tempdir / "output"

    output_path = run_flatbuffers(fbs_path, fbs_schema_path, output_directory)

    parsed_data = output_path.read_text(encoding="utf-8")
    parsed_data = recursively_collapse_keys(json.loads(parsed_data))
    if len(parsed_data) == 1:
        parsed_data, *_ = parsed_data.values()

    return json.dumps(parsed_data, indent=4 if normalize else None, ensure_ascii=False).encode("utf-8")


def decrypt_arknights_text(
    data: bytes,
    name: str,
    server: netn.ArknightsServer,
    *,
    rsa: bool = True,
    normalize: bool = False,
) -> bytes:
    """Decrypt arbitrary arknights data."""
    if match := re.search(r"(\w+_(?:table|data|const|database))[0-9a-fA-F]{6}", name):
        return decrypt_fbs_file(data, match[1], rsa=rsa, server=server, normalize=normalize)

    return decrypt_aes_text(data, rsa=rsa)


def load_json_or_bson(data: bytes) -> typing.Any:
    """Load json or possibly bson."""
    if b"\x00" in data[:256]:
        import bson

        return bson.loads(data)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]

    return json.loads(data)


def normalize_json(data: bytes, *, indent: int = 4, lenient: bool = True) -> bytes:
    """Normalize a json format."""
    if lenient and b"\x00" not in data[:256]:
        return data

    json_data = load_json_or_bson(data)
    return json.dumps(json_data, indent=indent, ensure_ascii=False).encode("utf-8")


DYNP = r"assets/torappu/dynamicassets/"


def unpack_assets(
    asset: UnityPyAsset,
    target_container: str | None = None,
    # target_path: str | None = None,
    *,
    server: netn.ArknightsServer | None = None,
    normalize: bool = False,
) -> typing.Iterable[tuple[str, bytes]]:
    """Yield relative paths and data for a unity asset."""
    for container, obj in asset.container.items():
        if target_container and container != target_container:
            continue

        if obj.type.name == "TextAsset":
            if server is None:
                raise TypeError("Server required for text decryption")

            if match := re.match(DYNP + r"(.+\.txt)", container):
                data = obj.read()
                yield (match[1], data.script)
                continue

            if match := re.match(DYNP + r"(gamedata/.+?\.json)", container):
                data = obj.read()
                yield (match[1], normalize_json(bytes(data.script), lenient=not normalize))
                continue

            if match := re.match(DYNP + r"(gamedata/.+?)\.lua\.bytes", container):
                data = obj.read()
                text = decrypt_aes_text(data.script)
                yield (match[1] + ".lua", text)
                continue

            if match := re.match(DYNP + r"(gamedata/levels/(?:obt|activities)/.+?)\.bytes", container):
                data = obj.read()
                try:
                    text = normalize_json(bytes(data.script)[128:], lenient=not normalize)
                except UnboundLocalError:  # effectively bson's "type not recognized" error
                    text = decrypt_fbs_file(data.script, "prts___levels", server=server)

                yield (match[1] + ".json", text)
                continue

            if match := re.match(DYNP + r"(gamedata/.+?)(?:[a-fA-F0-9]{6})?\.bytes", container):
                data = obj.read()
                # the only rsa-less file is ~~global~~ tw's enemy_database

                text = decrypt_arknights_text(
                    data.script,
                    name=data.name,
                    rsa=data.name != "enemy_database",
                    server=server,
                    normalize=normalize,
                )
                yield (match[1] + ".json", normalize_json(text, lenient=not normalize))
                continue


def guess_asset_path(path: str, hot_update_list: typing.Any) -> typing.Sequence[str]:
    """Return a sequence of all files thought to be needed to be downloaded for an asset to be available."""
    # images have to be added later
    match = re.match(r"(gamedata/\w+).json", path)
    if not match:
        return []

    filename = match[0]

    asset_paths: list[str] = []
    for info in hot_update_list["abInfos"]:
        # just supporting excel for now
        match = re.match(DYNP + filename + r"(?:[a-fA-F0-9]{6})?\.ab", info["name"])
        if match:
            asset_paths.append(info["name"])

    return asset_paths


def get_outdated_hashes(hot_update_now: typing.Any, hot_update_before: typing.Any) -> typing.Sequence[str]:
    """Compare hashes and return all files that need to be updated."""
    before_hashes = {info["name"]: info["hash"] for info in hot_update_before["abInfos"]}
    return [info["name"] for info in hot_update_now["abInfos"] if info["hash"] != before_hashes.get(info["name"])]


class BundleAssets(base.Assets):
    """Game assets client downloaded as unity files from arknights servers."""

    network: netn.NetworkSession
    """Network session."""
    directory: pathlib.Path
    """Directory where assets are stored."""

    def __init__(
        self,
        directory: PathLike | None = None,
        *,
        default_server: netn.ArknightsServer | None = None,
        network: netn.NetworkSession | None = None,
        json_loads: typing.Callable[[bytes], typing.Any] = json.loads,
    ) -> None:
        super().__init__(default_server=default_server or "en", json_loads=json_loads)

        temporary_directory = pathlib.Path(tempfile.gettempdir())
        self.directory = pathlib.Path(directory or temporary_directory / "ArknightsResources")
        self.network = network or netn.NetworkSession(default_server=default_server)

    async def _download_asset(self, path: str, *, server: netn.ArknightsServer | None = None) -> bytes:
        """Download a raw zipped unity asset."""
        server = server or self.default_server
        if not self.network.versions[server]:
            await self.network.load_version_config(server)

        url = (
            self.network.domains[server]["hu"]
            + f"/Android/assets/{self.network.versions[server]['resVersion']}/"
            + asset_path_to_server_filename(path)
        )

        async with self.network.session.get(url) as response:
            response.raise_for_status()
            return await response.read()

    async def _get_hot_update_list(self, server: netn.ArknightsServer) -> typing.Any:
        """Get a list of files to download."""
        data = await self._download_asset("hot_update_list.json", server=server)
        return json.loads(data)

    def _get_current_hot_update_list(self, server: netn.ArknightsServer) -> typing.Any | None:
        """Get the current stored hot_update_list.json for a server."""
        path = self.directory / server / "hot_update_list.json"
        if not path.exists():
            return None

        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("r") as file:
            return json.load(file)

    async def _download_unity_file(
        self,
        path: str,
        *,
        save: bool = True,
        server: netn.ArknightsServer | None = None,
    ) -> bytes:
        """Download an asset and return it unzipped."""
        LOGGER.debug("Downloading and unzipping asset %s for server %s", path, server)
        zipped_data = await self._download_asset(path, server=server)
        data = unzip_only_file(zipped_data)
        if save:
            p = resolve_unity_asset_cache(path, server=server or self.default_server)
            p.write_bytes(data)

        return data

    def _parse_and_save(
        self,
        data: bytes,
        *,
        target_container: str | None = None,
        server: netn.ArknightsServer | None = None,
        normalize: bool = False,
    ) -> typing.Iterable[tuple[str, bytes]]:
        """Download and extract an asset."""
        server = server or self.default_server

        asset = load_unity_file(data)

        fetched_any = False
        for fetched_any, (unpacked_rel_path, unpacked_data) in enumerate(
            unpack_assets(asset, target_container, server=server, normalize=normalize),
            1,
        ):
            savepath = self.directory / server / unpacked_rel_path
            savepath.parent.mkdir(exist_ok=True, parents=True)
            savepath.write_bytes(unpacked_data)

            yield (unpacked_rel_path, unpacked_data)

        if not fetched_any:
            warnings.warn(f"Unpacking yielded no results (container: {target_container}) ")

    async def update_assets(
        self,
        allow: str = "gamedata/excel/*",
        *,
        server: netn.ArknightsServer | typing.Literal["all"] | None = None,
        force: bool = False,
        normalize: bool = False,
    ) -> None:
        """Update game data.

        Only gamedata for the default server is downloaded by default.
        """
        server = server or self.default_server or "all"
        if server == "all":
            for server in netn.NETWORK_ROUTES:
                await self.update_assets(allow, server=server, force=force, normalize=normalize)

            return

        hot_update_list = await self._get_hot_update_list(server)
        requested_names = [info["name"] for info in hot_update_list["abInfos"] if fnmatch.fnmatch(info["name"], allow)]

        old_hot_update_list = self._get_current_hot_update_list(server)
        if old_hot_update_list and not force:
            outdated_names = set(get_outdated_hashes(hot_update_list, old_hot_update_list))
            requested_names = [name for name in requested_names if name in outdated_names]

        if any("gamedata" in name for name in requested_names):
            await update_fbs_schema()

        datas = await asyncio.gather(*(self._download_unity_file(name, server=server) for name in requested_names))
        loop = asyncio.get_event_loop()
        # this should be a ProcessPoolExecutor but pickling is a problem in classes
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    functools.partial(self._parse_and_save, d, server=server, normalize=normalize),
                )
                for d in datas
            ]
            for name, f in zip(requested_names, asyncio.as_completed(futures)):
                try:
                    for path, _ in await f:
                        LOGGER.debug("Extracted asset %s from %s for server %s", path, name, server)
                except Exception as e:
                    LOGGER.exception("Failed to extract asset %s for server %s", name, server, exc_info=e)

        hot_update_list_path = self.directory / server / "hot_update_list.json"
        hot_update_list_path.parent.mkdir(parents=True, exist_ok=True)
        with hot_update_list_path.open("w") as file:
            json.dump(hot_update_list, file, indent=4, ensure_ascii=False)

        self.loaded = True

    def get_file(self, path: str, *, server: netn.ArknightsServer | None = None) -> bytes:
        """Get an extracted asset file. If server is None any server is allowed with preference for default server."""
        return (self.directory / (server or self.default_server) / path).read_bytes()

    async def aget_file(self, path: str, *, server: netn.ArknightsServer | None = None, save: bool = True) -> bytes:
        """Get an extracted asset file without requiring load."""
        server = server or self.default_server
        hot_update_list = await self._get_hot_update_list(server)
        asset_paths = guess_asset_path(path, hot_update_list)
        if not asset_paths:
            raise ValueError("No viable asset path found, please load all assets and use get_file.")

        for potential_asset_path in asset_paths:
            asset = load_unity_file(await self._download_unity_file(potential_asset_path, server=server))
            for output_path, data in unpack_assets(asset, path, server=server):
                if save:
                    savepath = self.directory / server / output_path
                    savepath.parent.mkdir(exist_ok=True, parents=True)
                    savepath.write_bytes(data)

                return data

        raise ValueError("File not found, please load all assets and use get_file.")
