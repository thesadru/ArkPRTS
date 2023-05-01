"""Pytest configuration."""
import asyncio
import typing
import warnings

import pytest

import arkprts


@pytest.fixture(scope="session")
def event_loop() -> typing.Iterator[asyncio.AbstractEventLoop]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        loop = asyncio.get_event_loop()

    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client() -> arkprts.Client:
    # TODO: Add default tokens
    return arkprts.Client()
