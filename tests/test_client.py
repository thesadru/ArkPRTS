"""Test arkprts client."""
import arkprts


async def test_search_player(client: arkprts.Client) -> None:
    """Test searching for a player."""
    players = await client.search_player("doctor", server="en", limit=10)
    assert len(players) == 10
