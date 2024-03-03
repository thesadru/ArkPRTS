"""Test game assets."""

import arkprts


async def test_update(client: arkprts.Client) -> None:
    # we could force, but that takes up a lot of time
    await client.update_assets()


async def test_bundle_assets() -> None:
    assets = arkprts.BundleAssets()
    await assets.update_assets()

    await assets.network.close()


async def test_git_assets() -> None:
    assets = arkprts.GitAssets()
    await assets.update_assets()


def test_access(client: arkprts.Client) -> None:
    operator = client.assets.character_table["char_002_amiya"]
    assert operator.name == "Amiya"


def calculate_trust(client: arkprts.Client) -> None:
    # 9915 - 10069
    assert client.assets.calculate_trust_level(10000) == 99
