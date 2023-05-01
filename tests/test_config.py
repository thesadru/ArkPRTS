"""Test configs."""
import arkprts


async def test_config(client: arkprts.Client) -> None:
    await client._load_network_config()
    await client._load_version_config()

    assert client.config.network_version == "1"
    assert client.config.client_version >= "1.5.0"
