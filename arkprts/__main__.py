"""Entry-point."""

import argparse
import asyncio
import logging

import arkprts

parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Get user info from Arknights API.")
parser.add_argument("nickname", type=str, nargs="?", default=None, help="User nickname")
parser.add_argument("--uid", type=str, default=None, help="Channel UID")
parser.add_argument("--token", type=str, default="", help="Yostar Token")
parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
parser.add_argument("--server", type=str, default="en", help="Server to use, global only")


async def main() -> None:
    """Entry-point."""
    args = parser.parse_args()

    logging.basicConfig()
    logging.getLogger("arkprts").setLevel(args.log_level.upper())

    if args.uid and args.token:
        auth = arkprts.YostarAuth(args.server)
        await auth.login_with_token(args.uid, args.token)
    elif args.nickname:
        auth = arkprts.GuestAuth(max_sessions=1)
        auth.network.default_server = args.server
    else:
        auth = arkprts.YostarAuth(args.server)
        await auth.login_with_email_code()

    client = arkprts.Client(auth)

    if args.nickname:
        players = await client.search_players(args.nickname, limit=10)
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
            f"Secretary: {client.assets.character_table[player.secretary].name}",
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


if __name__ == "__main__":
    asyncio.run(main())
