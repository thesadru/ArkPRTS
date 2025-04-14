"""Test authentication."""

from __future__ import annotations

import asyncio
import collections
import os
import typing
import warnings

import pytest

import arkprts


@pytest.fixture(scope="session")
async def network() -> typing.AsyncIterator[arkprts.NetworkSession]:
    """Network session."""
    network = arkprts.NetworkSession()
    yield network
    await network.close()


async def test_config(network: arkprts.NetworkSession) -> None:
    await network.load_version_config("all")


@pytest.fixture(scope="session")
async def client(network: arkprts.NetworkSession) -> arkprts.Client:
    """Public global client."""
    return arkprts.Client(arkprts.GuestAuth(max_sessions=1, cache=os.environ.get("GUEST_AUTH_CACHE"), network=network))


@pytest.fixture(scope="session")
async def en_client(pytestconfig: pytest.Config, network: arkprts.NetworkSession) -> arkprts.Client:
    """Private en client."""
    channel_uid, yostar_token = os.environ.get("EN_CHANNEL_UID"), os.environ.get("EN_YOSTAR_TOKEN")
    if not channel_uid or not yostar_token:
        if pytestconfig.getoption("--runblocking") and os.environ.get("EN_EMAIL"):
            auth = arkprts.YostarAuth("en", network=network)
            channel_uid, yostar_token = await auth.login_with_email_code(os.environ["EN_EMAIL"])
            warnings.warn(f"Please use EN_CHANNEL_UID={channel_uid} EN_YOSTAR_TOKEN={yostar_token}")
            return arkprts.Client(auth)

        pytest.skip("EN_CHANNEL_UID or EN_YOSTAR_TOKEN not set (use --runblocking if you want to use email)")

    auth = await arkprts.Auth.from_token("en", channel_uid, yostar_token, network=network)
    return arkprts.Client(auth)


@pytest.fixture(scope="session")
async def jp_client(pytestconfig: pytest.Config, network: arkprts.NetworkSession) -> arkprts.Client:
    """Private jp client."""
    channel_uid, yostar_token = os.environ.get("JP_CHANNEL_UID"), os.environ.get("JP_YOSTAR_TOKEN")
    if not channel_uid or not yostar_token:
        if pytestconfig.getoption("--runblocking") and os.environ.get("JP_EMAIL"):
            auth = arkprts.YostarAuth("jp", network=network)
            channel_uid, yostar_token = await auth.login_with_email_code(os.environ["JP_EMAIL"])
            warnings.warn(f"Please use JP_CHANNEL_UID={channel_uid} JP_YOSTAR_TOKEN={yostar_token}")
            return arkprts.Client(auth)

        pytest.skip("JP_CHANNEL_UID or JP_YOSTAR_TOKEN not set")

    auth = await arkprts.Auth.from_token("jp", channel_uid, yostar_token, network=network)
    return arkprts.Client(auth)


@pytest.fixture(scope="session")
async def kr_client(pytestconfig: pytest.Config, network: arkprts.NetworkSession) -> arkprts.Client:
    """Private kr client."""
    channel_uid, yostar_token = os.environ.get("KR_CHANNEL_UID"), os.environ.get("KR_YOSTAR_TOKEN")
    if not channel_uid or not yostar_token:
        if pytestconfig.getoption("--runblocking") and os.environ.get("KR_EMAIL"):
            auth = arkprts.YostarAuth("kr", network=network)
            channel_uid, yostar_token = await auth.login_with_email_code(os.environ["KR_EMAIL"])
            warnings.warn(f"Please use KR_CHANNEL_UID={channel_uid} KR_YOSTAR_TOKEN={yostar_token}")
            return arkprts.Client(auth)

        pytest.skip("KR_CHANNEL_UID or KR_YOSTAR_TOKEN not set")

    auth = await arkprts.Auth.from_token("kr", channel_uid, yostar_token, network=network)
    return arkprts.Client(auth)


# @pytest.fixture(scope="session")
# async def cn_client(network: arkprts.NetworkSession) -> arkprts.Client:
#     """Private cn client."""
#     channel_uid, access_token = os.environ.get("CN_CHANNEL_UID"), os.environ.get("CN_ACCESS_TOKEN")
#     if not channel_uid or not access_token:
#         cn_username, cn_password = os.environ.get("CN_USERNAME"), os.environ.get("CN_PASSWORD")
#         if cn_username:
#             auth = arkprts.HypergryphAuth(network=network)
#             channel_uid, access_token = await auth.login(cn_username, cn_password)
#             warnings.warn(f"Please use CN_CHANNEL_UID={channel_uid} CN_ACCESS_TOKEN={access_token}")
#             return arkprts.Client(auth)

#         pytest.skip("CN_CHANNEL_UID or CN_ACCESS_TOKEN not set")

#     auth = await arkprts.Auth.from_token("cn", channel_uid, access_token, network=network)
#     return arkprts.Client(auth)


@pytest.fixture(scope="session")
async def bili_client(network: arkprts.NetworkSession) -> arkprts.Client:
    """Private bili client."""
    channel_uid, access_token = os.environ.get("BILI_CHANNEL_UID"), os.environ.get("BILI_ACCESS_TOKEN")
    if not channel_uid or not access_token:
        bili_username, bili_password = os.environ.get("BILI_USERNAME"), os.environ.get("BILI_PASSWORD")
        bili_bd_id = os.environ.get("BILI_BD_ID")
        if bili_username:
            auth = arkprts.BilibiliAuth(network=network)
            channel_uid, access_token = await auth.login(bili_username, bili_password, bd_id=bili_bd_id)
            warnings.warn(f"Please use BILI_CHANNEL_UID={channel_uid} BILI_ACCESS_TOKEN={access_token}")
            return arkprts.Client(auth)

        pytest.skip("BILI_CHANNEL_UID or BILI_ACCESS_TOKEN not set")

    auth = await arkprts.Auth.from_token("bili", channel_uid, access_token, network=network)
    return arkprts.Client(auth)


@pytest.fixture(scope="session")
async def tw_client(network: arkprts.NetworkSession) -> arkprts.Client:
    """Private tw client."""
    channel_uid, access_token = os.environ.get("TW_CHANNEL_UID"), os.environ.get("TW_ACCESS_TOKEN")
    if not channel_uid or not access_token:
        pytest.skip("TW_CHANNEL_UID or TW_ACCESS_TOKEN not set")

    auth = await arkprts.Auth.from_token("tw", channel_uid, access_token, network=network)
    return arkprts.Client(auth)


def test_jp_client(jp_client: arkprts.Client) -> None:
    assert isinstance(jp_client.auth, arkprts.Auth)
    assert jp_client.auth.server == "jp"
    assert jp_client.auth.session.uid


def test_kr_client(kr_client: arkprts.Client) -> None:
    assert isinstance(kr_client.auth, arkprts.Auth)
    assert kr_client.auth.server == "kr"
    assert kr_client.auth.session.uid


# def test_cn_client(cn_client: arkprts.Client) -> None:
#     assert isinstance(cn_client.auth, arkprts.Auth)
#     assert cn_client.auth.server == "cn"
#     assert cn_client.auth.session.uid


def test_bili_client(bili_client: arkprts.Client) -> None:
    assert isinstance(bili_client.auth, arkprts.Auth)
    assert bili_client.auth.server == "bili"
    assert bili_client.auth.session.uid


def test_tw_client(tw_client: arkprts.Client) -> None:
    assert isinstance(tw_client.auth, arkprts.Auth)
    assert tw_client.auth.server == "tw"
    assert tw_client.auth.session.uid


class MockGuestAuth(arkprts.GuestAuth):
    async def request(
        self,
        domain: arkprts.ArknightsDomain,
        endpoint: str | None = None,
        **kwargs: typing.Any,
    ) -> typing.Any:
        if endpoint == "...":
            return await super().request("rc", **kwargs)

        return await super().request(domain, endpoint, **kwargs)


async def test_guest_auth(network: arkprts.NetworkSession) -> None:
    auth = MockGuestAuth(max_sessions=2, cache=os.environ.get("GUEST_AUTH_CACHE"), network=network)

    def count() -> collections.Counter[str]:
        return collections.Counter(session.server for session in auth.sessions)

    assert len(auth.sessions) == 0

    await auth.auth_request("...", server="en")
    assert len(auth.sessions) == 1
    assert count()["en"] == 1

    await auth.auth_request("...", server="jp")
    assert len(auth.sessions) == 2
    assert count()["jp"] == 1

    await auth.auth_request("...", server="en")
    assert len(auth.sessions) == 2
    assert count()["en"] == 1

    await asyncio.gather(
        auth.auth_request("...", server="en"),
        auth.auth_request("...", server="en"),
    )
    assert len(auth.sessions) == 3
    assert count()["en"] == 2
