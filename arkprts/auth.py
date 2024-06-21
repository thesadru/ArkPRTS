"""Arknights authentication client.

# Authentication

Authentication allows you to get a session secret. Currently only email login is documented.

## Global (YoStar)

Global allows you to create guest accounts with only a device id.
The account however needs to bind a nickname before making any requests (after authentication).

### Get a permanent token
- Request a verification code to be sent to your email.
- Use the verification code to receive a yostar uid and token.
- Use the yostar uid and token to receive a channel uid and token

### Authenticate
- Use the channel uid and token to get an access token.
- Use the access token and channel uid to get an arknights player uid and u8 token.
- Use the arknights player uid and u8 token to get a session secret.


## CN (HyperGryph)

### Get a permanent token
- Send unhashed username and password to receive an access token.
- Optionally, send the access token to receive a channel uid.

### Authenticate
- Use the access token and channel uid to get an arknights player uid and u8 token.
- Use the arknights player uid and u8 token to get a session secret.


## Bilibili

### Get a permanent token
- Get a cipher key and hash from the bilibili api.
- Send a hashed password to receive a channel uid and access key.

### Authenticate
- Use the access key and channel uid to get an arknights player uid and u8 token.
- Use the arknights player uid and u8 token to get a session secret.


## Taiwan (Longcheng)

### Get a permanent token
Taiwan clearly has guest login and facebook / google play.
Unfortunately I have not been able to figure out how it works.

### Authenticate
- Use the channel uid and access token to get an arknights player uid and u8 token.
- Use the arknights player uid and u8 token to get a session secret.


# Making requests

Starting with getting the session secret, every request towards the game server needs to have:
- `secret` - session secret (except for the first request)
- `seqnum` - request sequence number (increments for every request, prevents concurrent requests)
- `uid` - arknights player uid

# Wrapper representation of sessions

The wrapper can represent a single or multiple sessions per client.
Single sessions are for getting personal data, but disallow concurrent requests.
Multiple sessions are for getting public data and allow concurrent requests.
"""

from __future__ import annotations

import abc
import asyncio
import base64
import contextlib
import dataclasses
import hashlib
import hmac
import json
import logging
import pathlib
import random
import string
import tempfile
import time
import typing
import urllib.parse
import uuid
import warnings

import aiohttp

from . import errors
from . import network as netn

__all__ = [
    "Auth",
    "AuthSession",
    "BilibiliAuth",
    "CoreAuth",
    "GuestAuth",
    "HypergryphAuth",
    "LongchengAuth",
    "MultiAuth",
    "YostarAuth",
]

LOGGER: logging.Logger = logging.getLogger("arkprts.auth")

RawAuthMapping = typing.TypedDict("RawAuthMapping", {"server": netn.ArknightsServer, "channel_uid": str, "token": str})

YOSTAR_PASSPORT_DOMAINS: dict[typing.Literal["en", "jp", "kr"], str] = {
    "en": "https://passport.arknights.global",
    "jp": "https://passport.arknights.jp",
    "kr": "https://passport.arknights.kr",
}


def create_random_device_ids() -> tuple[str, str, str]:
    """Create a random device id."""
    deviceid2 = "86" + "".join(random.choices(string.digits, k=13))
    return uuid.uuid4().hex, deviceid2, uuid.uuid4().hex


def generate_u8_sign(data: typing.Mapping[str, object]) -> str:
    """u8 auth sign."""
    query = urllib.parse.urlencode(sorted(data.items()))

    code = hmac.new(b"91240f70c09a08a6bc72af1a5c8d4670", query.encode(), "sha1")
    return code.hexdigest().lower()


@dataclasses.dataclass()
class AuthSession:
    """An already authenticated session."""

    server: netn.ArknightsServer
    """Arknights server."""
    uid: str
    """Arknights user UID."""
    secret: str = ""
    """Arknights session token."""
    seqnum: int = 1
    """Request sequence number."""
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)
    """Lock to prevent concurrent requests."""

    @property
    def is_locked(self) -> bool:
        """Whether the session is currently making a request."""
        return self.lock.locked()

    async def __aenter__(self) -> typing.Mapping[str, str]:
        """Prepare for the next request and return headers."""
        await self.lock.acquire()
        self.seqnum += 1
        return {"secret": self.secret, "seqnum": str(self.seqnum), "uid": self.uid}

    async def __aexit__(self, *exc: object) -> None:
        """Release lock."""
        self.lock.release()


class CoreAuth(typing.Protocol):
    """Authentication client typing protocol.

    Look for subclasses for more specific authentication methods.
    """

    network: netn.NetworkSession
    """Network session."""

    async def auth_request(
        self,
        endpoint: str,
        *,
        server: netn.ArknightsServer | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send an authenticated request to the arkights game server."""


class Auth(abc.ABC, CoreAuth):
    """Authentication client for single sessions."""

    server: netn.ArknightsServer
    """Arknights server."""
    network: netn.NetworkSession
    """Network session."""
    device_ids: tuple[str, str, str]
    """Device ids."""
    session: AuthSession
    """Authentication session."""

    def __init__(
        self,
        server: netn.ArknightsServer | None = None,
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        if server is None and network is not None:
            server = network.default_server

        self.server = server or "en"
        self.network = network or netn.NetworkSession(default_server=self.server)
        self.session = AuthSession(self.server, "", "")
        self.device_ids = create_random_device_ids()

    @property
    def uid(self) -> str:
        """Arknights user UID."""
        return self.session.uid

    @property
    def secret(self) -> str:
        """Arknights session token."""
        return self.session.secret

    async def request(
        self,
        domain: netn.ArknightsDomain,
        endpoint: str | None = None,
        *,
        server: netn.ArknightsServer | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send a request to an arknights server."""
        if server and server != self.server:
            raise ValueError(f"Single-session client is bound to {self.server!r} server.")

        return await self.network.request(domain, endpoint, server=self.server, **kwargs)

    async def auth_request(
        self,
        endpoint: str,
        *,
        server: netn.ArknightsServer | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send an authenticated request to the arknights game server."""
        if server and server != self.server:
            raise ValueError(f"Single-session client is bound to {self.server!r} server.")

        if not self.session.uid:
            raise errors.NotLoggedInError("Not logged in.")

        async with self.session as headers:
            LOGGER.debug("[UID: %s] Sending request #%s to %s.", self.uid, headers["seqnum"], endpoint)
            return await self.request("gs", endpoint, headers=headers, server=self.server, **kwargs)

    async def _get_u8_token(
        self,
        channel_uid: str,
        access_token: str,
    ) -> tuple[str, str]:
        """Get an arknights uid and u8 token from a channel uid and access token."""
        LOGGER.debug("Getting u8 token for %s.", channel_uid)
        channel_id = {"cn": "1", "bili": "2", "en": "3", "jp": "3", "kr": "3"}[self.server]
        if channel_id == "3":
            extension = {"uid": channel_uid, "token": access_token}
        else:
            extension = {"uid": channel_uid, "access_token": access_token}

        body = {
            "appId": "1",
            "platform": 1,
            "channelId": channel_id,
            "subChannel": channel_id,
            "extension": json.dumps(extension),
            # optional fields:
            "worldId": channel_id,
            "deviceId": self.device_ids[0],
            "deviceId2": self.device_ids[1],
            "deviceId3": self.device_ids[2],
        }
        # optional:
        body["sign"] = generate_u8_sign(body)

        data = await self.request("u8", "user/v1/getToken", json=body)
        uid, token = data["uid"], data["token"]
        self.session.uid = uid
        return uid, token

    async def _get_secret(
        self,
        uid: str,
        u8_token: str,
    ) -> str:
        """Get a secret from an arknights uid and a u8 token."""
        LOGGER.debug("Getting session secret for %s.", uid)
        if not self.network.versions.get(self.server):
            await self.network.load_version_config(self.server)

        network_version = {"cn": "5", "bili": "5", "en": "1", "jp": "1", "kr": "1"}[self.server]

        body = {
            "platform": 1,
            "networkVersion": network_version,
            "assetsVersion": self.network.versions[self.server]["resVersion"],
            "clientVersion": self.network.versions[self.server]["clientVersion"],
            "token": u8_token,
            "uid": uid,
            "deviceId": self.device_ids[0],
            "deviceId2": self.device_ids[1],
            "deviceId3": self.device_ids[2],
        }
        headers = {
            "secret": "",
            "seqnum": "1",
            "uid": uid,
        }
        data = await self.request("gs", "account/login", json=body, headers=headers)
        secret = data["secret"]
        self.session.secret = secret
        LOGGER.info("Logged in with UID %s", uid)
        return secret

    @abc.abstractmethod
    async def login_with_token(self, channel_uid: str, token: str, /) -> None:
        """Login with a channel uid and token."""

    @classmethod
    async def from_token(
        cls,
        server: netn.ArknightsServer,
        channel_uid: str,
        token: str,
        *,
        network: netn.NetworkSession | None = None,
    ) -> Auth:
        """Create a client from a token."""
        if server in ("en", "jp", "kr"):
            auth = YostarAuth(server, network=network)
            await auth.login_with_token(channel_uid, token)
        elif server == "cn":
            auth = HypergryphAuth(server, network=network)
            await auth.login_with_token(channel_uid, token)
        elif server == "bili":
            auth = BilibiliAuth(server, network=network)
            await auth.login_with_token(channel_uid, token)
        elif server == "tw":
            auth = LongchengAuth(server, network=network)
            await auth.login_with_token(channel_uid, token)
        else:
            raise ValueError(f"Cannot create a generic auth client for server {server!r}")

        return auth


class YostarAuth(Auth):
    """Authentication client for global accounts."""

    distributor: typing.Literal["yostar"]

    def __init__(
        self,
        server: typing.Literal["en", "jp", "kr"] = "en",
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        super().__init__(server, network=network)

    async def request_passport(self, endpoint: str, **kwargs: typing.Any) -> typing.Any:
        """Send a request to a yostar passport endpoint."""
        return await self.request(YOSTAR_PASSPORT_DOMAINS[self.server], endpoint, **kwargs)  # type: ignore  # custom domain

    async def _get_access_token(self, channel_uid: str, yostar_token: str) -> str:
        """Get an access token from a channel uid and yostar token."""
        body = {
            "platform": "android",
            "uid": channel_uid,
            "token": yostar_token,
            "deviceId": self.device_ids[0],
        }
        data = await self.request_passport("user/login", json=body)
        return data["accessToken"]

    async def send_email_code(self, email: str) -> None:
        """Request to log in with a yostar account."""
        LOGGER.debug("Sending code to %s.", email)
        body = {"platform": "android", "account": email, "authlang": "en"}
        await self.request_passport("account/yostar_auth_request", json=body)

    async def _submit_yostar_auth(self, email: str, code: str) -> tuple[str, str]:
        """Submit a yostar auth code and receieve a yostar uid and yostar token."""
        body = {"account": email, "code": code}
        data = await self.request_passport("account/yostar_auth_submit", json=body)
        return data["yostar_uid"], data["yostar_token"]

    async def _get_yostar_token(self, email: str, yostar_uid: str, yostar_token: str) -> tuple[str, str]:
        """Get a channel uid and yostar token from a yostar uid and yostar token."""
        body = {
            "yostar_username": email,
            "yostar_uid": yostar_uid,
            "yostar_token": yostar_token,
            "deviceId": self.device_ids[0],
            "createNew": "0",
        }
        data = await self.request_passport("user/yostar_createlogin", json=body)
        return data["uid"], data["token"]

    async def create_guest_account(self) -> tuple[str, str]:
        """Create a new guest account."""
        body = {
            "deviceId": self.device_ids[0],
        }
        data = await self.request_passport("user/create", json=body)
        LOGGER.debug("Created guest account %s", data["uid"])
        return data["uid"], data["token"]

    async def _bind_nickname(self, nickname: str) -> None:
        """Bind a nickname. Required for new accounts."""
        LOGGER.debug("Binding nickname of %s to %r.", self.uid, nickname)
        await self.auth_request("user/bindNickName", json={"nickName": nickname})

    async def login_with_token(self, channel_uid: str, yostar_token: str) -> None:
        """Login with a yostar token."""
        access_token = await self._get_access_token(channel_uid, yostar_token)
        self.session.uid, u8_token = await self._get_u8_token(channel_uid, access_token)
        await self._get_secret(self.session.uid, u8_token)

    async def get_token_from_email_code(
        self,
        email: str | None = None,
        code: str | None = None,
        *,
        stdin: bool = False,
    ) -> tuple[str, str]:
        """Get a token from a yostar account."""
        if not email:
            if not stdin:
                raise TypeError("Email not provided but stdin is disabled.")

            email = input("Enter email:")

        if not code:
            await self.send_email_code(email)
            if not stdin:
                return "", ""

            print(f"Code sent to {email}.")  # noqa: T201
            code = input("Enter code: ")

        yostar_uid, yostar_token = await self._submit_yostar_auth(email, code)
        return await self._get_yostar_token(email, yostar_uid, yostar_token)

    async def login_with_email_code(
        self,
        email: str | None = None,
        code: str | None = None,
        *,
        stdin: bool = True,
    ) -> tuple[str, str]:
        """Login with a yostar account. Uses stdin by default."""
        channel_uid, token = await self.get_token_from_email_code(email, code, stdin=stdin)
        await self.login_with_token(channel_uid, token)

        if stdin:
            print(f"Channel UID: {channel_uid} Token: {token}")  # noqa: T201
            print(f'Usage: login_with_token("{channel_uid}", "{token}")')  # noqa: T201

        return channel_uid, token

    async def login_as_guest(self, nickname: str | None = None) -> tuple[str, str]:
        """Login as guest and return tokens."""
        channel_uid, yostar_token = await self.create_guest_account()
        await self.login_with_token(channel_uid, yostar_token)
        await self._bind_nickname(nickname or "Doctor")
        return channel_uid, yostar_token


class HypergryphAuth(Auth):
    """Authentication client for chinese accounts."""

    distributor: typing.Literal["hypergryph"]

    def __init__(
        self,
        server: typing.Literal["cn"] = "cn",
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        super().__init__(server, network=network)

    async def _get_hypergryph_access_token(self, username: str, password: str) -> str:
        """Get an access token from a username and password."""
        data = {
            "account": username,
            "password": password,
            "deviceId": self.device_ids[0],
            "platform": 1,
        }
        data["sign"] = generate_u8_sign(data)
        data = await self.network.request("as", "user/login", json=data)
        return data["token"]

    async def _get_hypergryph_uid(self, token: str) -> str:
        """Get a channel uid from a hypergryph access token."""
        data = {"token": token}
        data["sign"] = generate_u8_sign(data)
        data = await self.network.request("as", "user/auth", json=data)
        return data["uid"]

    async def login_with_token(self, channel_uid: str, access_token: str) -> None:
        """Login with an access token."""
        self.session.uid, u8_token = await self._get_u8_token(channel_uid, access_token)
        await self._get_secret(self.session.uid, u8_token)

    async def get_token_from_password(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        stdin: bool = False,
    ) -> tuple[str, str]:
        """Get a token from a hypergryph account."""
        if not username or not password:
            if not stdin:
                raise TypeError("Password not provided but stdin is disabled.")

            username = input("Enter username: ")
            password = input("Enter password: ")

        access_token = await self._get_hypergryph_access_token(username, password)
        channel_uid = await self._get_hypergryph_uid(access_token)
        return channel_uid, access_token

    async def login(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        stdin: bool = True,
    ) -> tuple[str, str]:
        """Login with a hypergryph account."""
        channel_uid, access_token = await self.get_token_from_password(username, password, stdin=stdin)
        await self.login_with_token(channel_uid, access_token)

        if stdin:
            print(f"Channel UID: {channel_uid} Access token: {access_token}")  # noqa: T201
            print(f'Usage: login_with_token("{channel_uid}", "{access_token}")')  # noqa: T201

        return channel_uid, access_token


class BilibiliAuth(Auth):
    """Authentication client for bilibili accounts."""

    distributor: typing.Literal["bilibili"]

    cipher_key: str
    """Bilibili pkcs1 openssl key for arknights."""
    password_hash: str
    """Extra text to go at the start of the password."""

    def __init__(
        self,
        server: typing.Literal["bili"] = "bili",
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        super().__init__(server, network=network)

    @staticmethod
    def _sign_body(body: typing.Mapping[str, str]) -> str:
        """Sign request body."""
        body = dict(sorted(body.items()))
        string = "".join(body.values()) + "8783abfb533544c59e598cddc933d1bf"
        return hashlib.md5(string.encode()).hexdigest()

    def _sign_password(self, password: str) -> str:
        """Sign password."""
        import rsa

        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(self.cipher_key.encode())
        signed = rsa.encrypt((self.password_hash + password).encode(), public_key)
        return base64.b64encode(signed).decode()

    async def _load_cipher(self) -> None:
        """Load the cipher key and hash."""
        body = dict(
            merchant_id="328",
            game_id="952",
            server_id="1178",
            version="3",
            timestamp=str(int(time.time())),
            cipher_type="bili_login_rsa",
        )
        body["sign"] = self._sign_body(body)
        async with aiohttp.request(
            "POST",
            "https://line1-sdk-center-login-sh.biligame.net/api/external/issue/cipher/v3",
            data=body,
        ) as r:
            data = await r.json()

        self.cipher_key, self.password_hash = data["cipher_key"], data["hash"]

    async def _get_access_key(self, username: str, password: str, *, bd_id: str | None = None) -> tuple[str, str]:
        """Get an access key from username and password."""
        await self._load_cipher()

        bd_id = bd_id or "-".join(random.randbytes(round(n / 2)).hex()[:n] for n in (8, 4, 4, 4, 12, 8, 4, 4, 4, 3))
        body = dict(
            merchant_id="328",
            game_id="952",
            server_id="1178",
            version="3",
            timestamp=str(int(time.time())),
            bd_id=bd_id,
            user_id=username,
            pwd=self._sign_password(password),
        )
        body["sign"] = self._sign_body(body)
        async with aiohttp.request(
            "POST",
            "https://line1-sdk-center-login-sh.biligame.net/api/external/login/v3",
            data=body,
        ) as r:
            data = await r.json()

        return data["uid"], data["access_key"]

    async def login_with_token(self, channel_uid: str, access_token: str) -> None:
        """Login with an access key."""
        self.session.uid, u8_token = await self._get_u8_token(channel_uid, access_token)
        await self._get_secret(self.session.uid, u8_token)

    async def get_token_from_password(
        self,
        username: str | None = None,
        password: str | None = None,
        bd_id: str | None = None,
        *,
        stdin: bool = False,
    ) -> tuple[str, str]:
        """Get a token from a bilibili account."""
        if not username or not password:
            if not stdin:
                raise TypeError("Password not provided but stdin is disabled.")

            username = input("Enter username: ")
            password = input("Enter password: ")

        return await self._get_access_key(username, password, bd_id=bd_id)

    async def login(
        self,
        username: str | None = None,
        password: str | None = None,
        bd_id: str | None = None,
        *,
        stdin: bool = True,
    ) -> tuple[str, str]:
        """Login with a bilibili account."""
        channel_uid, access_token = await self.get_token_from_password(username, password, bd_id, stdin=stdin)
        await self.login_with_token(channel_uid, access_token)

        if stdin:
            print(f"Channel UID: {channel_uid} Access key: {access_token}")  # noqa: T201
            print(f'Usage: login_with_token("{channel_uid}", "{access_token}")')  # noqa: T201

        return channel_uid, access_token


class LongchengAuth(Auth):
    """Authentication client for taiwan accounts."""

    distributor: typing.Literal["longcheng"]

    def __init__(
        self,
        server: typing.Literal["tw"] = "tw",
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        super().__init__(server, network=network)

    async def login_with_token(self, channel_uid: str, access_token: str) -> None:
        """Login with an access token."""
        self.session.uid, u8_token = await self._get_u8_token(channel_uid, access_token)
        await self._get_secret(self.session.uid, u8_token)


class MultiAuth(CoreAuth):
    """Authentication client for multiple sessions."""

    network: netn.NetworkSession
    """Network session."""

    # may be exceeded if multiple sessions are created at once
    max_sessions: int
    """Maximum number of concurrent sessions per server."""
    sessions: list[AuthSession]
    """Authentication sessions."""

    def __init__(
        self,
        max_sessions: int = 6,
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        self.network = network or netn.NetworkSession()
        self.max_sessions = max_sessions
        self.sessions = []

    def _get_free_session(self, server: netn.ArknightsServer) -> AuthSession | None:
        """Get a free session in a server."""
        for session in self.sessions:
            if session.server == server and not session.is_locked:
                return session

        return None

    async def _wait_for_free_session(self, server: netn.ArknightsServer) -> AuthSession:
        """Wait a session to be freed."""
        while True:
            await asyncio.sleep(0.1)
            if session := self._get_free_session(server):
                return session

    async def _create_new_session(self, server: netn.ArknightsServer) -> AuthSession:
        """Create a new session for a selected server."""
        raise RuntimeError("No method for creating new sessions specified.")

    async def request(
        self,
        domain: netn.ArknightsDomain,
        endpoint: str | None = None,
        *,
        server: netn.ArknightsServer | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send a request to an arknights server."""
        return await self.network.request(domain, endpoint, server=server, **kwargs)

    async def auth_request(
        self,
        endpoint: str,
        *,
        server: netn.ArknightsServer | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """Send an authenticated request to the arknights game server."""
        server = server or self.network.default_server
        if server is None:
            raise ValueError("No default server set.")

        session = self._get_free_session(server)
        if session is None and sum(session.server == server for session in self.sessions) >= self.max_sessions:
            session = await self._wait_for_free_session(server)
        if session is None:
            session = await self._create_new_session(server)
            self.sessions.append(session)
            LOGGER.debug("Created new session %s for server %s.", session.uid, server)

        async with session as headers:
            LOGGER.debug(
                "[GUEST UID: %s %s] Sending request #%s to %s.",
                session.uid,
                server,
                headers["seqnum"],
                endpoint,
            )
            return await self.request("gs", endpoint, headers=headers, server=server, **kwargs)

    def add_session(self, session: AuthSession | Auth | MultiAuth | None) -> None:
        """Add a session to the list of sessions."""
        if isinstance(session, AuthSession):
            self.sessions.append(session)
        elif isinstance(session, Auth):
            self.sessions.append(session.session)
        elif isinstance(session, MultiAuth):
            self.sessions.extend(session.sessions)
        else:
            raise TypeError(f"Invalid session type {type(session)}")


class GuestAuth(MultiAuth):
    """Authentication client for dynamically generating guest accounts."""

    cache_path: pathlib.Path | None
    """Location of stored guest authentication."""
    upcoming_auth: list[RawAuthMapping]
    """Upcoming accounts that are yet to be loaded."""

    def __init__(
        self,
        max_sessions: int = 6,
        cache: pathlib.Path | str | typing.Sequence[RawAuthMapping] | typing.Literal[False] | None = None,
        *,
        network: netn.NetworkSession | None = None,
    ) -> None:
        super().__init__(max_sessions=max_sessions, network=network)

        # load cache file or use provided auth
        self.upcoming_auth = []
        if cache is False:
            self.cache_path = None
        elif isinstance(cache, (pathlib.Path, str)):
            self.cache_path = pathlib.Path(cache).expanduser()
        elif cache is None:
            self.cache_path = pathlib.Path(tempfile.gettempdir()) / "arkprts_auth_cache.json"
        else:
            self.cache_path = None
            self.upcoming_auth = list(cache)

        if self.cache_path:
            self.upcoming_auth.extend(self._load_cache())

    def _load_cache(self) -> typing.Sequence[RawAuthMapping]:
        """Load cached guest accounts."""
        if not self.cache_path:
            return []

        if not self.cache_path.exists():
            return []

        with self.cache_path.open() as f:
            data = json.load(f)

        return data

    def _save_cache(self, data: typing.Sequence[RawAuthMapping]) -> None:
        """Save cached guest accounts."""
        if not self.cache_path:
            return

        with self.cache_path.open("w") as f:
            json.dump(data, f)

    def _append_to_cache(self, server: netn.ArknightsServer, channel_uid: str, token: str) -> None:
        """Append a guest account to the cache."""
        if not self.cache_path:
            return

        data = list(self._load_cache())
        data.append({"server": server, "channel_uid": channel_uid, "token": token})
        self._save_cache(data)

    async def _load_upcoming_session(self, server: netn.ArknightsServer) -> AuthSession | None:
        """Take one upcoming auth and create a session from it."""
        for i, auth in enumerate(self.upcoming_auth):
            if auth["server"] == server:
                self.upcoming_auth.pop(i)
                break
        else:
            return None

        LOGGER.debug("Loading cached auth %s for %s.", auth["channel_uid"], auth["server"])
        try:
            auth = await Auth.from_token(server, auth["channel_uid"], auth["token"], network=self.network)
        except errors.BaseArkprtsError as e:
            warnings.warn(f"Failed to load cached auth: {e}")
            # remove faulty auth from cache file
            data = list(self._load_cache())
            with contextlib.suppress(ValueError):
                data.remove(auth)
            self._save_cache(data)

            return None

        return auth.session

    async def _create_new_session(self, server: netn.ArknightsServer) -> AuthSession:
        """Create a new guest account."""
        if server not in ("en", "jp", "kr"):
            raise ValueError("Guest accounts are only supported on the global server.")

        session = await self._load_upcoming_session(server)
        if session is not None:
            return session

        auth = YostarAuth(server, network=self.network)
        channel_uid, token = await auth.login_as_guest()
        self._append_to_cache(server=server, channel_uid=channel_uid, token=token)
        return auth.session
