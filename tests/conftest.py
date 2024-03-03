"""Pytest configuration."""

import asyncio
import typing
import warnings

import pytest


@pytest.fixture(scope="session")
def event_loop() -> typing.Iterator[asyncio.AbstractEventLoop]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        loop = asyncio.get_event_loop()

    yield loop
    loop.close()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--runblocking", action="store_true", default=False, help="run blocking tests")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "blocking: mark test as blocking")


def pytest_collection_modifyitems(config: pytest.Config, items: typing.Sequence[pytest.Item]) -> None:
    if config.getoption("--runblocking"):
        return

    marker = pytest.mark.skip(reason="Test is blocking")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(marker)


# force to run auth first
from tests.test_auth import *  # noqa: F403 E402
