"""Test arkprts client."""
import arkprts


async def test_search_players(client: arkprts.Client) -> None:
    players = await client.search_players("doctor", server="en", limit=10)
    assert len(players) == 10


async def test_get_data(client: arkprts.Client) -> None:
    # this is purposefully not allowed because it's useless for public clients
    # do it anyways
    data = await client.request("account/syncData", json={"platform": 1}, server="en")
    user = arkprts.models.User(client=client, **data["user"])
    assert user.status.nickname == "Doctor"  # default guest name
