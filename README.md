# ArkPRTS

Arknights python wrapper.

Interacts directly with the game servers, no delays.

支持**中文和B站**账户!

<!-- Supports Chinese and BiliBili accounts -->

---

Source Code: <https://github.com/thesadru/arkprts>

---

## Installation

```sh
pip install -U arkprts
```

There are some optional requirements, you can install them all with `all`.

```sh
pip install -U arkprts[all]
```

## Usage

```py
import arkprts

async def main() -> None:
    client = arkprts.Client(assets=False)

    # search users by nickname
    users = await client.search_players("Doctor", server="en")
    print("User level: ", users[0].level)


    # =======

    # login with email or token
    auth = arkprts.YostarAuth("en")
    await auth.login_with_email_code("doctor@gmail.com")
    # or auth.login_with_token("123456", "abcdefg")
    client = arkprts.Client(auth=auth, assets=False)

    # get logged-in user data
    data = await client.get_data()
    print("Level: ", data.status.level)
```

Returned data is in the form of pydantic models, however you can also request raw json with `client.get_raw_player_info()`/`client.get_raw_data()`/... to access even untyped data.

For convenience, static game data is automatically downloaded and updated on login. You can access the static data directly or through the models. This is useful for getting names and descriptions of objects.

```py
users = await client.search_user("UserName")
operator = users[0].assist_char_list[0]  # type: arkprts.models.Character
print(f"Assist operator {operator.static.name} is level {operator.level}")
```

To disable downloading static data use `arkprts.Client(assets=False)`. To choose the data download location set `arkprts.Client(assets="/path/to/data")` (`/tmp`/`%TEMP%` is chosen by default).

ArkPRTS supports en, jp, kr, cn and bili servers. However only global/yostar servers (en, jp and kr) can be used without logging in.

### Frequent usage cases

Get all of my operators.

```py
data = await client.get_data()
for char in data.troop.chars.values():
    print(char.char_id)
```

Get my inventory.

```py
data = await client.get_data()
# normal inventory items
for item_id, count in user.inventory.items():
    if count > 0:
        print(item_id, count)
# basic items like originium or green certificates
for item_id, count in user.status.basic_item_inventory.items():
    if count > 0:
        print(item_id, count)
# consumable expirable items
for item_id, subitems in user.consumable.items():
    for item in subitems.values():
        if count > 0:
            print(item_id, item.ts, item.count)
```

Logging in with email and password to the cn server.

```py
auth = arkprts.HypergryphAuth()
await auth.login("doctor@qq.com", "wordpass12")
client = arkprts.Client(auth=auth)

await client.get_data()
```

Making a new client when a global guest client already exists; without excess overhead.

```py
public_client = arkprts.Client()

# ----
auth = arkprts.YostarAuth("en", network=public_client.network)
await auth.login_with_token("123456", "abcdefg")
private_client = arkprts.Client(auth=auth, assets=public_client.assets)
```

Programmatically getting auth tokens from a user on your website.

```py
@route("/code")
def code(request):
    auth = arkprts.YostarAuth(request.query["server"], network=...)
    await auth.send_email_code(request.query["email"])

    return "Code sent!"


@route("/login")
def login(request):
    auth = arkprts.YostarAuth(request.query["server"], network=...)
    channel_uid, yostar_token = await auth.get_token_from_email_code(request.query["email"], request.query["code"])

    return {"channel_uid": channel_uid, "yostar_token": yostar_token}
```

## Contributing

Any kind of contribution is welcome.
Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for more information.
