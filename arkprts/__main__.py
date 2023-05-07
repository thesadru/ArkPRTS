"""Entry-point."""
import argparse
import asyncio

from .client import Client

parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Get user info from Arknights API.")
parser.add_argument("nickname", type=str, nargs="?", default=None, help="User nickname")
parser.add_argument("--uid", type=str, default=None, help="Channel UID")
parser.add_argument("--token", type=str, default="", help="Yostar Token")


async def main() -> None:
    """Entry-point."""
    args = parser.parse_args()

    client = Client()

    if args.uid and args.token:
        await client.login_with_token(args.uid, args.token)
    else:
        await client.login_with_email()

    if args.nickname:
        users = await client.search_player(args.nickname, limit=10)
    else:
        users = await client.get_friends()
        print("Friends:", end="\n\n")

    for user in users:
        print(f"{user.nickname}#{user.nick_number} ({user.uid}) Lvl {user.level}")
        print(f"Current stage: {user.main_stage_progress} | Characters: {user.char_cnt} | Secretery: {user.secretary}")
        print(f"Playing since: {user.register_ts.isoformat()}")
        print(f"Last Online: {user.last_online_time.isoformat()}")

        print("Support Operators: ", end="")
        for char in user.assist_char_list:
            if not char:
                continue
            print(f"{char.char_id} E{char.evolve_phase}L{char.level}", end="")
            if char.skills:
                print(f" S{char.skill_index+1}M{char.skills[char.skill_index].specialize_level}", end="")

            print("   ", end="")

        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
