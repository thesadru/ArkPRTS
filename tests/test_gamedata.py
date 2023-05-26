"""Test game data."""
import arkprts


async def test_download(client: arkprts.Client) -> None:
    # we could force, but that takes up a lot of time
    await client.gamedata.download_gamedata()


def test_access(client: arkprts.Client) -> None:
    operator = client.gamedata.character_table["char_002_amiya"]
    assert operator.name == "Amiya"
