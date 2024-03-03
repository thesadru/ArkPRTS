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
>>> await client.account_sync_data()
"""

from __future__ import annotations

import base64
import io
import json
import typing
import warnings
import zipfile

from . import assets as assetsn
from . import auth as authn
from . import models
from . import network as netn

if typing.TYPE_CHECKING:
    from typing_extensions import Self

__all__ = ["Client"]


class CoreClient:
    """Base arknights client."""

    auth: authn.CoreAuth
    """Authentication client."""
    assets: assetsn.Assets
    """Game data client."""

    def __init__(
        self,
        auth: authn.CoreAuth | None = None,
        *,
        assets: assetsn.Assets | str | typing.Literal[False] | None = None,
        network: netn.NetworkSession | None = None,
        server: netn.ArknightsServer | None = None,
    ) -> None:
        """Initialize a client.

        auth: Authentication client. May be both public and private. GuestAuth by default.
        assets: Assets client or path to its location.
        network: Network session.
        server: Default server. Not recommended for large-scale usage.
        """
        self.auth = auth or authn.GuestAuth(network=network)
        if network:
            self.auth.network = network
        if server:
            self.auth.network.default_server = server

        if assets is False:
            self.assets = assetsn.Assets.create(
                default_server=self.auth.network.default_server,
                network=self.auth.network,
            )
            self.assets.loaded = True
        elif isinstance(assets, assetsn.Assets):
            self.assets = assets
        else:
            self.assets = assetsn.Assets.create(
                assets,
                default_server=self.auth.network.default_server,
                network=self.auth.network,
            )

    @property
    def network(self) -> netn.NetworkSession:
        """Return the network session of the client."""
        return self.auth.network

    @property
    def server(self) -> netn.ArknightsServer | None:
        """Return the default server of the network session."""
        return self.network.default_server

    async def request(self, endpoint: str, **kwargs: typing.Any) -> typing.Any:
        """Send an authenticated request to the arknights game server."""
        if self.assets and not self.assets.loaded:
            await self.update_assets()

        return await self.auth.auth_request(endpoint, **kwargs)

    async def update_assets(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Download excel assets."""
        await self.assets.update_assets(*args, **kwargs)

    @classmethod
    async def from_token(
        cls,
        channel_uid: str,
        token: str,
        server: netn.ArknightsServer = "en",
        *,
        network: netn.NetworkSession | None = None,
        assets: assetsn.Assets | str | typing.Literal[False] | None = None,
    ) -> Self:
        """Create a client from a token."""
        auth = await authn.Auth.from_token(server, channel_uid, token, network=network)
        return cls(auth, assets=assets)

    async def login_with_token(self, channel_uid: str, token: str) -> None:
        """Login with username and password."""
        warnings.warn(
            "client.login_with_token is deprecated, please use Client.from_token(...) or Client(auth=...)",
            category=DeprecationWarning,
        )
        self.auth = await authn.Auth.from_token(self.server or "en", channel_uid, token, network=self.network)


class Client(CoreClient):
    """Arknights client for accessing private data."""

    def _assert_private(self) -> None:
        """Assert that the client is not public."""
        if not isinstance(self.auth, authn.Auth):
            raise RuntimeError("This client can only access public data.")  # noqa: TRY004  # isn't a type check

        if not self.auth.server:
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
        server: netn.ArknightsServer | None = None,
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
        server: netn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Get detailed player info. You don't need to be friends actually."""
        return await self.request("social/getFriendList", json={"idList": ids}, server=server)

    async def get_raw_player_info(
        self,
        ids: typing.Sequence[str],
        *,
        server: netn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Get player info."""
        return await self.request("social/searchPlayer", json={"idList": ids}, server=server)

    async def get_raw_friend_ids(
        self,
        *,
        server: netn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Get friends."""
        self._assert_private()

        return await self._get_social_sort_list(1, ["level", "infoShare"], {}, server=server)

    async def search_raw_player_ids(
        self,
        nickname: str,
        nicknumber: str = "",
        *,
        server: netn.ArknightsServer | None = None,
    ) -> typing.Any:
        """Search for a nickname."""
        return await self._get_social_sort_list(
            0,
            ["level"],
            {"nickName": nickname, "nickNumber": nicknumber},
            server=server,
        )

    async def get_raw_battle_replay(self, battle_type: str, stage_id: str) -> typing.Any:
        """Get a battle replay."""
        self._assert_private()

        data = await self.request(f"{battle_type}/getBattleReplay", json={"stageId": stage_id})

        replay_data = base64.b64decode(data["battleReplay"])
        with zipfile.ZipFile(io.BytesIO(replay_data), "r") as z, z.open("default_entry") as f:
            return json.load(f)

    async def search_players(
        self,
        nickname: str,
        nicknumber: str = "",
        *,
        server: netn.ArknightsServer | None = None,
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
        server: netn.ArknightsServer | None = None,
    ) -> typing.Sequence[models.Player]:
        """Get players and return a model."""
        data = await self.get_raw_player_info(ids, server=server)
        return [models.Player(client=self, **i) for i in data["friends"]]

    async def get_partial_players(
        self,
        ids: typing.MutableSequence[str],
        *,
        server: netn.ArknightsServer | None = None,
    ) -> typing.Sequence[models.PartialPlayer]:
        """Get players and return a model."""
        data = await self.get_raw_player_info(ids, server=server)
        return [models.PartialPlayer(client=self, **i) for i in data["players"]]

    async def get_friends(
        self,
        *,
        server: netn.ArknightsServer | None = None,
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

    async def get_battle_replay(self, battle_type: str, stage_id: str) -> models.BattleReplay:
        """Get a battle replay and return a model."""
        data = await self.get_raw_battle_replay(battle_type, stage_id)
        return models.BattleReplay(client=self, **data)
