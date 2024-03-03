"""Arknights network client.

# Loading network configuration

As you likely know from the game itself, you need to get through two screens before entering the game.
The first checks the game version and network configuration.
The client and asset version must be sent along with a channel uid and access token to the game server.

| slug   | Example (en)                                                                    | Meaning                             |
| ------ | ------------------------------------------------------------------------------- | ----------------------------------- |
| gs     | https://gs.arknights.global:8443                                                | Game server                         |
| as     | https://as.arknights.global                                                     | Authentication server               |
| u8     | https://as.arknights.global/u8                                                  | u8* token authentication server     |
| hu     | https://ark-us-static-online.yo-star.com/assetbundle/official                   | Game assets                         |
| hv     | https://ark-us-static-online.yo-star.com/assetbundle/official/{0}/version       | Game assets & app versions          |
| rc     | https://ak-conf.arknights.global/config/prod/official/remote_config             | Unique server config                |
| an     | https://ark-us-static-online.yo-star.com/announce/{0}/announcement.meta.json    | Announcements                       |
| prean  | https://ark-us-static-online.yo-star.com/announce/{0}/preannouncement.meta.json | Pre-announcements on the login page |
| sl     | https://www.arknights.global/terms_of_service                                   | Terms of service                    |
| of     | https://www.arknights.global                                                    | Official webpage                    |
| pkgAd  | https://play.google.com/store/apps/details?id=com.YoStarEN.Arknights            | Google play store apk               |
| pkgIOS | https://apps.apple.com/us/app/id1464872022?mt=8                                 | IOS store apk                       |
"""

from __future__ import annotations

import asyncio
import json
import logging
import typing

import aiohttp

from . import errors

__all__ = [
    "ArknightsDistributor",
    "ArknightsDomain",
    "ArknightsServer",
    "NetworkSession",
]

LOGGER: logging.Logger = logging.getLogger("arkprts.network")

# these are in no way official slugs, just my own naming

ArknightsDistributor = typing.Literal["yostar", "hypergryph", "bilibili", "longcheng"]
ArknightsServer = typing.Literal["en", "jp", "kr", "cn", "bili", "tw"]

ArknightsDomain = typing.Literal["gs", "as", "u8", "hu", "hv", "rc", "an", "prean", "sl", "of", "pkgAd", "pkgIOS"]
NETWORK_ROUTES: dict[ArknightsServer, str] = {
    "en": "https://ak-conf.arknights.global/config/prod/official/network_config",
    "jp": "https://ak-conf.arknights.jp/config/prod/official/network_config",
    "kr": "https://ak-conf.arknights.kr/config/prod/official/network_config",
    "cn": "https://ak-conf.hypergryph.com/config/prod/official/network_config",
    "bili": "https://ak-conf.hypergryph.com/config/prod/b/network_config",
    "tw": "https://ak-conf.txwy.tw/config/prod/official/network_config",
}

# the unity version is outdated, but it doesn't seem to matter
DEFAULT_HEADERS: typing.Mapping[str, str] = {
    "Content-Type": "application/json",
    "X-Unity-Version": "2017.4.39f1",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; KB2000 Build/RP1A.201005.001)",
    "Connection": "Keep-Alive",
}

# aiohttp uses a very noisy library
_charset_normalizer_logger = logging.getLogger("charset_normalizer")
_charset_normalizer_logger.setLevel(logging.INFO)


class NetworkSession:
    """Config-aware network session."""

    default_server: ArknightsServer | None = None
    """Default arknights server."""

    _session: aiohttp.ClientSession | None = None
    """Aiohttp client session."""
    domains: dict[ArknightsServer, dict[ArknightsDomain, str]]
    """Arknights server domain routes."""
    versions: dict[ArknightsServer, dict[typing.Literal["resVersion", "clientVersion"], str]]
    """Arknights client versions."""

    def __init__(
        self,
        default_server: ArknightsServer | None = None,
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.default_server = default_server
        self._session = session

        self.domains = {server: {} for server in NETWORK_ROUTES}
        self.versions = {server: {} for server in NETWORK_ROUTES}

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the aiohttp client session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

        return self._session

    async def close(self) -> None:
        """Close underlying aiohttp client session."""
        if self._session is None:
            return

        await self._session.close()

    async def raw_request(
        self,
        method: str,
        url: str,
        *,
        headers: typing.Mapping[str, str] | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send a request to an arbitrary endpoint."""
        headers = {**DEFAULT_HEADERS, **(headers or {})}

        async with self.session.request(method, url, headers=headers, **kwargs) as resp:
            try:
                data = await resp.json(content_type=None)
            except TypeError as e:
                resp.raise_for_status()
                raise errors.InvalidContentTypeError(await resp.text()) from e

            if data.get("error"):
                raise errors.GameServerError(data)

            if resp.status != 200:
                raise errors.InvalidStatusError(resp.status, data)

            return data

    async def request(
        self,
        domain: ArknightsDomain,
        endpoint: str | None = None,
        *,
        server: ArknightsServer | None = None,
        method: str | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send a request to an arknights server."""
        server = server or self.default_server

        if "http" in domain:
            url = domain
        else:
            if server is None:
                raise ValueError("No default server set.")
            if server not in self.domains:
                raise ValueError(f"Invalid server {server!r}")
            if not self.domains[server]:
                await self.load_network_config(server)
            if domain not in self.domains[server]:
                raise ValueError(f"Invalid domain {domain!r}")

            url = self.domains[server][domain]

        if "{0}" in url:
            url = url.format("Android")  # iOS probably makes no difference
        if endpoint:
            url = url + "/" + endpoint

        if method is None:
            method = "POST" if kwargs.get("json") else "GET"

        data = await self.raw_request(method, url, **kwargs)

        if "result" in data and isinstance(data["result"], int) and data["result"] != 0:
            if "captcha" in data:
                raise errors.GeetestError(data)

            raise errors.ArkPrtsError(data)

        return data

    async def load_network_config(self, server: ArknightsServer | typing.Literal["all"] | None = None) -> None:
        """Load the network configuration."""
        server = server or self.default_server or "all"
        if server == "all":
            await asyncio.wait([asyncio.create_task(self.load_network_config(server)) for server in NETWORK_ROUTES])
            return

        LOGGER.debug("Loading network configuration for %s.", server)
        data = await self.request(NETWORK_ROUTES[server])  # type: ignore # custom domain
        content = json.loads(data["content"])
        self.domains[server].update(content["configs"][content["funcVer"]]["network"])

    async def load_version_config(self, server: ArknightsServer | typing.Literal["all"] | None = None) -> None:
        """Load the version configuration."""
        server = server or self.default_server or "all"
        if server == "all":
            await asyncio.wait([asyncio.create_task(self.load_version_config(server)) for server in NETWORK_ROUTES])
            return

        LOGGER.debug("Loading version configuration for %s.", server)
        data = await self.request("hv", server=server)
        self.versions[server].update(data)
