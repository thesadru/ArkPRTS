# ArkPRTS

Arknights python wrapper.

This project aims to purely allow for data collection, no account automation is planned.

---

Source Code: <https://github.com/thesadru/arkprts>

---

## Usage

```py
import arkprts

async def main() -> None:
    client = arkprts.Client()
    await client.login_with_email("user@gmail.com")
    # or client.login_with_token("123456", "abcdefg")

    # get logged-in user data
    data = await client.get_data()
    print("Level: ", data.status.level)

    # get data of other users
    users = await client.search_user("UserName")
    print("Level: ", users[0].level)
```

Returned data is in the form of pydantic models, however you can also request raw json with `client.get_raw_data()` to access even untyped data.

For convenience, static game data is automatically downloaded and updated on login. You can access the static data directly or through the models. This is useful for getting names and descriptions of objects.

```py
users = await client.search_user("UserName")
operator = users[0].assist_char_list[0]  # type: arkprts.models.Character
print(f"Assist operator {operator.static.name} is level {operator.level}")
```

To disable downloading static data use `arkprts.Client(pure=True)`. To choose the data download location set `client.gamedata = akprts.GameData("/path/to/data")`.

If you do not trust logging in with your account but still wish to request public game data you may log in as a guest.
Remember to save the generated credentials to not spam Arknights servers.

```py
client = arkprts.Client()
uid, token = await client.login_as_guest()
print(f"Please save uid {uid} and token {token}")

users = await client.search_user("Doctor")

# and later if you wish to use the same guest account again
client = arkprts.Client()
await client.login_with_token(uid, token)

users = await client.search_user("Doctor")
```

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

## Contributing

Any kind of contribution is welcome.
Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for more information.
