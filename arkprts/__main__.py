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
        users = await client.search_player(args.nickname, limit=10)
    else:
        users = await client.get_friends()
        print("Friends:", end="\n\n")

    for user in users:
        if user.level < 5:
            continue

        print(f"{user.nickname}#{user.nick_number} ({user.uid}) Lvl {user.level}")
        print(f"Resume: {user.resume}")
        print(
            f"Current stage: {user.main_stage_progress} | Characters: {user.char_cnt} | Furniture: {user.furn_cnt} | "
            f"Secretary: {client.gamedata.character_table[user.secretary].name}",
        )
        print(f"Playing since: {user.register_ts.isoformat()}")
        print(f"Last Online: {user.last_online_time.isoformat()}")

        print("Support Operators: ", end="")
        for char in user.assist_char_list:
            if not char:
                continue
            print(f"{char.static.name} E{char.evolve_phase}L{char.level}", end="")
            if char.skills:
                print(f" S{char.skill_index+1}M{char.skills[char.skill_index].specialize_level}", end="")

            print("  ", end="")

        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
