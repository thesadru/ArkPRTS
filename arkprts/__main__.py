"""Entry-point."""
import argparse
import asyncio
import datetime

from .client import Client

parser = argparse.ArgumentParser(description="Get user info from Arknights API.")
parser.add_argument("nickname", type=str, help="User nickname")
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

    data = await client.search_nickname(args.nickname)
    user_uids = sorted(data["result"], key=lambda x: x["level"], reverse=True)
    users = await client.get_friend_info([i["uid"] for i in user_uids[:10]])
    for user in users["friends"]:
        print(  # noqa: T201
            f"""
{user["nickName"]}#{user["nickNumber"]} ({user["uid"]}) Lvl {user["level"]}
Current stage: {user["mainStageProgress"]} | Characters: {user["charCnt"]} | Secretery: {user["secretary"]}
Playing since: {datetime.datetime.fromtimestamp(user["registerTs"], tz=datetime.timezone.utc).isoformat()}
Last Online: {datetime.datetime.fromtimestamp(user["lastOnlineTime"], tz=datetime.timezone.utc).isoformat()}
Support Characters: {", ".join(
f'{i["charId"]} E{i["evolvePhase"]}L{i["level"]} S{i["skillIndex"]+1}M{i["skills"][i["skillIndex"]]["specializeLevel"]}'
for i in user["assistCharList"] if i
)}
        """.strip()
            + "\n",
        )


if __name__ == "__main__":
    asyncio.run(main())
