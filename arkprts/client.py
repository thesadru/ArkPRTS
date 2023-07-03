"""Arknights client.

## Usage:
>>> # Client for read-only public data
>>> client = arkprts.Client()
>>> await client.search_players("...", limit=10)
[Player(...), ...]

>>> # Client for read-only private data
>>> auth = arkprts.YostarAuth("en")
>>> await auth.login_with_email_code("doctor@gmail.com")
>>> client = arkprts.Client(auth=auth)
>>> await client.get_data()
User(...)

>>> # Client for read & write (usage is potentially bannable)
>>> auth = arkprts.YostarAuth("en")
>>> await auth.login_with_email_code("doctor@gmail.com")
>>> client = arkprts.AutomationClient(auth=auth)
>>> await client.login_with_token("...", "...")
>>> await client.claim_daily_reward()
"""
from __future__ import annotations

import typing

from . import auth as authn
from . import gamedata as gd
from . import models

if typing.TYPE_CHECKING:
    from typing_extensions import Self

__all__ = ["Client"]


class CoreClient:
    """Base arknights client."""

    auth: authn.CoreAuth
    """Authentication client."""
    gamedata: gd.GameData  # may actually be None, but that's a pain to typehint
    """Game data client."""

    def __init__(
        self,
        auth: authn.CoreAuth | None = None,
        *,
        gamedata: gd.GameData | typing.Literal[False] | None = None,
        network: authn.NetworkSession | None = None,
        server: authn.ArknightsServer | None = None,
        language: authn.ArknightsLanguage | None = None,
    ) -> None:
        """Initialize a client.

        auth: Authentication client. May be both public and private. GuestAuth by default.
        gamedata: Game data client. May be disabled with False.
        network: Network session.
        server: Default server. Not recommended for large-scale usage.
        language: Default language. Fallbacks on the gamedata's default language.
        """
        self.auth = auth or authn.GuestAuth(network=network)
        if gamedata is False:
            self.gamedata = None  # type: ignore
        else:
            self.gamedata = gamedata or gd.GameData()

        if network:
            self.auth.network = network
        if server:
            self.auth.network.default_server = server
        if language:
            if self.gamedata is None:
                raise ValueError("No need to use language, gamedata is disabled.")

            self.gamedata.language = language

    @property
    def network(self) -> authn.NetworkSession:
        """Return the network of the client."""
        return self.auth.network

    async def request(self, endpoint: str, **kwargs: typing.Any) -> typing.Any:
        """Authenticate a request."""
        if self.gamedata and not self.gamedata.loaded:
            await self.gamedata.update_gamedata()

        return await self.auth.auth_request(endpoint, **kwargs)

    async def update_gamedata(self, allow: str | None = None, *, force: bool = False) -> bool:
        """Download game data."""
        if not self.gamedata:
            return False

        await self.gamedata.update_gamedata(allow=allow, force=force)
        return True

    @classmethod
    async def from_token(
        cls,
        channel_uid: str,
        token: str,
        server: authn.ArknightsServer = "en",
        *,
        network: authn.NetworkSession | None = None,
        gamedata: gd.GameData | None = None,
    ) -> Self:
        """Create a client from a token."""
        auth = await authn.Auth.from_token(server, channel_uid, token, network=network)
        return cls(auth, gamedata=gamedata)


class Client(CoreClient):
    """Arknights client for accessing private data."""

    def _assert_private(self) -> None:
        """Assert that the client is not public."""
        if not isinstance(self.auth, authn.Auth):
            raise RuntimeError("This client can only access public data.")  # noqa: TRY004  # isn't a type check

        if not self.network.default_server:
            raise RuntimeError("Missing a default server for a private client.")

    async def get_raw_data(self) -> typing.Any:
        """Get user data."""
        self._assert_private()

        return await self.request("account/syncData", json={"platform": 1})

    async def _get_social_sort_list(
        self,
        type: int,
        sort_key: typing.Sequence[str] = ["level"],
        param: typing.Mapping[str, str] = {},
        *,
        server: authn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Request sortedusers."""
        data = await self.request(
            "social/getSortListInfo",
            json={"type": type, "sortKeyList": sort_key, "param": param},
            server=server,
        )
        data["result"].sort(key=lambda x: tuple(x[key] for key in sort_key), reverse=True)  # pyright: ignore

        return data

    async def get_raw_friend_info(
        self,
        ids: typing.Sequence[str],
        *,
        server: authn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Get detailed player info. You don't need to be friends actually."""
        return await self.request("social/getFriendList", json={"idList": ids}, server=server)

    async def get_raw_player_info(
        self,
        ids: typing.Sequence[str],
        *,
        server: authn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Get player info."""
        return await self.request("social/searchPlayer", json={"idList": ids}, server=server)

    async def get_raw_friend_ids(
        self,
        *,
        server: authn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Get friends."""
        self._assert_private()

        return await self._get_social_sort_list(1, ["level", "infoShare"], {}, server=server)

    async def search_raw_player_ids(
        self,
        nickname: str,
        nicknumber: str = "",
        *,
        server: authn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Search for a nickname."""
        return await self._get_social_sort_list(
            0,
            ["level"],
            {"nickName": nickname, "nickNumber": nicknumber},
            server=server,
        )

    async def search_players(
        self,
        nickname: str,
        nicknumber: str = "",
        *,
        server: authn.ArknightsServer | None = None,
        limit: int | None = None,
    ) -> typing.Sequence[models.Player]:
        """Search for a player and return a model."""
        if "#" in nickname:
            nickname, nicknumber = nickname.split("#", 1)

        uid_data = await self.search_raw_player_ids(nickname, nicknumber, server=server)
        data = await self.get_raw_friend_info([uid["uid"] for uid in uid_data["result"][:limit]], server=server)
        return [models.Player(client=self, **i) for i in data["friends"]]

    async def get_players(
        self,
        ids: typing.MutableSequence[str],
        *,
        server: authn.ArknightsServer | None = None,
    ) -> typing.Sequence[models.Player]:
        """Get players and return a model."""
        data = await self.get_raw_player_info(ids, server=server)
        return [models.Player(client=self, **i) for i in data["result"]]

    async def get_friends(
        self,
        *,
        server: authn.ArknightsServer | None = None,
        limit: int | None = None,
    ) -> typing.Sequence[models.Player]:
        """Get friends and return a model."""
        uid_data = await self.get_raw_friend_ids(server=server)
        data = await self.get_raw_friend_info([uid["uid"] for uid in uid_data["result"][:limit]], server=server)
        return [models.Player(client=self, **i) for i in data["friends"]]

    async def get_data(self) -> models.User:
        """Get user sync data and return a model. Use raw data for more info."""
        data = await self.get_raw_data()
        return models.User(client=self, **data["user"])
