"""Arknights client."""
import dataclasses
import json
import typing
import uuid

import aiohttp

__all__ = ("Client",)

HEADERS = {
    "Content-Type": "application/json",
    "X-Unity-Version": "2017.4.39f1",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; KB2000 Build/RP1A.201005.001)",
    "Connection": "Keep-Alive",
}

ASSET_SERVER = "https://ark-us-static-online.yo-star.com"
CONF_SERVER = "https://ak-conf.arknights.global"
PASSPORT_SERVER = "https://passport.arknights.global"
GAME_SERVER = "https://gs.arknights.global:8443"
AUTH_SERVER = "https://as.arknights.global"


class ArkPrtsError(Exception):
    """Base exception class for this library."""


@dataclasses.dataclass
class Config:
    """Static configuration."""

    platform: int = 1
    device_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()).replace("-", ""))

    assets_version: str = ""
    client_version: str = ""

    sign: str = ""
    network_version: str = "1"
    network: typing.Mapping[str, str] = dataclasses.field(default_factory=dict)


class Client:
    """Arknights client."""

    config: Config
    proxy: typing.Optional[str] = None

    uid: typing.Optional[str]
    secret: typing.Optional[str]

    _seqnum: int

    def __init__(self, **config: object) -> None:
        self.config = Config(**config)

        self.uid = None
        self.secret = None
        self._seqnum = 1

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Make an arbitrary request."""
        headers = {**HEADERS, **(headers or {})}

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, **kwargs) as resp:
                try:
                    data = await resp.json(content_type=None)
                except TypeError as e:
                    resp.raise_for_status()
                    raise ArkPrtsError(await resp.read()) from e

                if resp.status != 200:
                    raise ArkPrtsError(data)
                if "result" in data and isinstance(data["result"], int) and data["result"] != 0:
                    raise ArkPrtsError(data)

                return data

    async def request(self, endpoint: str, *, method: str = "POST", **kwargs: typing.Any) -> typing.Any:
        """Make a request towards the game server."""
        if self.uid is None or self.secret is None:
            raise ArkPrtsError("Not logged-in")

        headers = {
            "secret": self.secret,
            "seqnum": str(self._seqnum),
            "uid": self.uid,
        }
        self._seqnum += 1  # tfw no x++

        return await self._request(method, f"{GAME_SERVER}/{endpoint}", headers=headers, **kwargs)

    async def _load_network_config(self) -> None:
        """Get network config."""
        data = await self._request("GET", f"{CONF_SERVER}/config/prod/official/network_config")
        content = json.loads(data["content"])
        self.config.sign = data["sign"]
        self.config.network = content["configs"][content["funcVer"]]["network"]
        self.config.network_version = content["configVer"]

    async def _load_version_config(self) -> None:
        """Get version config."""
        # for CN it's "/config/prod/official/Android/version"
        data = await self._request("GET", f"{ASSET_SERVER}/assetbundle/official/Android/version")
        self.config.assets_version = data["resVersion"]
        self.config.client_version = data["clientVersion"]

    async def _initialize_config(self) -> None:
        """Initialize config."""
        if not self.config.network_version:
            await self._load_network_config()
        if not self.config.assets_version:
            await self._load_version_config()

    async def _get_access_token(self, channel_uid: str, yostar_token: str) -> str:
        """Get an access token from a channel uid and yostar token."""
        body = {
            "platform": "android",
            "uid": channel_uid,
            "token": yostar_token,
            "deviceId": self.config.device_id,
        }
        data = await self._request("POST", f"{PASSPORT_SERVER}/user/login", json=body)
        # print(data["yostar_username"])
        return data["accessToken"]

    async def _get_u8_token(self, channel_uid: str, access_token: str) -> str:
        """Get an arknights uid and u8 token from a channel uid and access token."""
        body = {
            "appId": "1",
            "channelId": "3",
            "extension": json.dumps({"uid": channel_uid, "token": access_token}),
            "worldId": "3",
            "platform": 1,
            "subChannel": "3",
            "deviceId": self.config.device_id,
            "deviceId2": "",
            "deviceId3": "",
            "sign": "",
        }
        data = await self._request("POST", f"{AUTH_SERVER}/u8/user/v1/getToken", json=body)
        self.uid = data["uid"]
        return data["token"]

    async def _get_secret(self, u8_token: str) -> str:
        """Get a secret from a u8 uid and token."""
        await self._initialize_config()
        body = {
            "assetsVersion": self.config.assets_version,
            "clientVersion": self.config.client_version,
            "deviceId": self.config.device_id,
            "deviceId2": "",
            "deviceId3": "",
            "networkVersion": self.config.network_version,
            "platform": self.config.platform,
            "token": u8_token,
            "uid": self.uid,
        }
        self.secret = ""
        data = await self.request("account/login", json=body)
        self.secret = data["secret"]
        return self.secret

    async def _request_yostar_auth(self, email: str) -> None:
        """Request to log in with a yostar account."""
        body = {
            "platform": "android",
            "account": email,
            "authlang": "en",
        }
        await self._request("POST", f"{PASSPORT_SERVER}/account/yostar_auth_request", json=body)

    async def _submit_yostar_auth(self, email: str, code: str) -> typing.Tuple[str, str]:
        """Submit a yostar auth code and receieve a yostar uid and temporary token."""
        body = {
            "account": email,
            "code": code,
        }
        data = await self._request("POST", f"{PASSPORT_SERVER}/account/yostar_auth_submit", json=body)
        return data["yostar_uid"], data["yostar_token"]

    async def _get_yostar_token(self, email: str, yostar_uid: str, token: str) -> typing.Tuple[str, str]:
        """Get a channel uid and yostar token from a yostar uid and temporary token."""
        body = {
            "yostar_token": token,
            "deviceId": self.config.device_id,
            "channelId": "googleplay",
            "yostar_uid": yostar_uid,
            "createNew": "0",
            "yostar_username": email,
        }
        data = await self._request("POST", f"{PASSPORT_SERVER}/user/yostar_createlogin", json=body)
        return data["uid"], data["token"]

    async def login_with_token(self, channel_uid: str, yostar_token: str) -> None:
        """Login with a yostar token."""
        access_token = await self._get_access_token(channel_uid, yostar_token)
        u8_token = await self._get_u8_token(channel_uid, access_token)
        await self._get_secret(u8_token)

    async def login_with_email(self, email: typing.Optional[str] = None) -> None:
        """Login with a yostar account. Uses stdin."""
        if not email:
            email = input("Enter email: ")

        await self._request_yostar_auth(email)
        print(f"Code has been sent to {email}")  # noqa: T201

        code = input("Enter code: ")
        yostar_uid, yostar_token = await self._submit_yostar_auth(email, code)
        channel_uid, token = await self._get_yostar_token(email, yostar_uid, yostar_token)
        await self.login_with_token(channel_uid, token)

        print(f"Channel UID: {channel_uid} Token: {token}")  # noqa: T201
        print(f'Usage: client.login_with_token("{channel_uid}", "{token}")')  # noqa: T201

    async def get_data(self) -> typing.Any:
        """Get user data."""
        return await self.request("account/syncData", json={"platform": 1})

    async def _get_social_sort_list(
        self,
        type: int,
        sort_key: typing.Sequence[str] = ["level"],
        param: typing.Mapping[str, str] = {},
    ) -> typing.Any:
        """Request sortedusers."""
        return await self.request(
            "social/getSortListInfo",
            json={"type": type, "sortKeyList": sort_key, "param": param},
        )

    async def get_friend_info(self, ids: typing.Sequence[str]) -> typing.Any:
        """Get detailed player info. You don't need to be friends actually."""
        return await self.request("social/getFriendList", json={"idList": ids})

    async def get_player_info(self, ids: typing.Sequence[str]) -> typing.Any:
        """Get player info."""
        return await self.request("social/searchPlayer", json={"idList": ids})

    async def get_friends(self) -> typing.Any:
        """Get friends."""
        return await self._get_social_sort_list(1, ["level", "infoShare"])

    async def search_nickname(self, nickname: str, nicknumber: str = "") -> typing.Any:
        """Search for a nickname."""
        return await self._get_social_sort_list(0, ["level"], {"nickName": nickname, "nickNumber": nicknumber})

    async def bind_nickname(self, nickname: str) -> typing.Any:
        """Bind a nickname. Required for new accounts."""
        return await self.request("user/bindNickName", json={"nickName": nickname})
