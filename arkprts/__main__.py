"""Entry-point."""

import argparse
import asyncio
import json
import logging
import sys
import typing

import arkprts

parser: argparse.ArgumentParser = argparse.ArgumentParser("Use the arknights API")
parser.add_argument("--log-level", type=str, default="ERROR", help="Logging level")
parser.add_argument("--channel-uid", type=str, default=None, help="Yostar UID")
parser.add_argument("--token", type=str, default="", help="Yostar Token")
parser.add_argument("--server", type=str, default="en", help="Server to use")
parser.add_argument("--guest", action="store_true", help="Whether to use a guest account.")

subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]" = parser.add_subparsers(dest="command", required=True)

parser_search: argparse.ArgumentParser = subparsers.add_parser("search", description="Get user info.")
parser_search.add_argument(
    "nickname",
    type=str,
    nargs="?",
    default=None,
    help="User nickname, gives your friends by default",
)

parser_api: argparse.ArgumentParser = subparsers.add_parser("api", description="Make a request towards the API.")
parser_api.add_argument("endpoint", type=str, nargs="?", help="Endpoint path, not full url")
parser_api.add_argument("payload", type=str, nargs="?", default=r"{}", help="JSON payload")


async def search(client: arkprts.Client, nickname: typing.Optional[str] = None) -> None:
    """Get user info."""
    if nickname:
        players = await client.search_players(nickname, limit=10)
    else:
        players = await client.get_friends()
        print("Friends:", end="\n\n")

    for player in players:
        if player.level < 5:
            continue

        print(f"{player.nickname}#{player.nick_number} ({player.uid}) Lvl {player.level}")
        print(f"Resume: {player.resume}")
        print(
            f"Current stage: {player.main_stage_progress} | Characters: {player.char_cnt} | Furniture: {player.furn_cnt} | "
            f"Secretary: {client.assets.full_character_table[player.secretary].name}",
        )
        print(f"Playing since: {player.register_ts.isoformat()}")
        print(f"Last Online: {player.last_online_time.isoformat()}")

        print("Support Operators: ", end="")
        for char in player.assist_char_list:
            if not char:
                continue
            print(f"{char.static.name} E{char.evolve_phase}L{char.level}", end="")
            if char.skills:
                print(f" S{char.skill_index+1}M{char.skills[char.skill_index].specialize_level}", end="")

            print("  ", end="")

        print("\n")

    await client.network.close()


async def api(client: arkprts.Client, endpoint: str, payload: typing.Optional[str] = None) -> None:
    """Make a request."""
    try:
        data = await client.auth.auth_request(endpoint, json=payload and json.loads(payload), handle_errors=False)
        json.dump(data, sys.stdout, indent=4, ensure_ascii=False)
    finally:
        await client.auth.network.close()

    sys.stdout.write("\n")


async def main() -> None:
    """Entry-point."""
    args = parser.parse_args()

    logging.basicConfig()
    logging.getLogger("arkprts").setLevel(args.log_level.upper())

    if args.channel_uid and args.token:
        auth = arkprts.YostarAuth(args.server)
        await auth.login_with_token(args.channel_uid, args.token)
    elif args.guest or (args.command == "search" and args.nickname):
        auth = arkprts.GuestAuth(max_sessions=1)
        auth.network.default_server = args.server
    else:
        auth = arkprts.YostarAuth(args.server)
        await auth.login_with_email_code()

    client = arkprts.Client(auth)

    if args.command == "search":
        await search(client, args.nickname)
    elif args.command == "api":
        await api(client, args.endpoint, args.payload)


if __name__ == "__main__":
    asyncio.run(main())
