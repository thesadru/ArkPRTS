"""Automation client. Potentially bannable."""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import random
import string
import time
import typing
import zipfile

from . import assets as assetsn
from . import auth as authn
from . import network as netn
from .client import CoreClient

__all__ = ["AutomationClient"]


def recursively_update_dict(
    target: typing.MutableMapping[typing.Any, typing.Any],
    source: typing.Mapping[typing.Any, typing.Any],
) -> None:
    """Recursively update a dictionary.

    This is used to update the player data.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            recursively_update_dict(target[key], typing.cast("dict[object, object]", value))
        elif isinstance(value, list):
            for i, v in enumerate(typing.cast("list[object]", value)):
                if isinstance(v, dict):
                    recursively_update_dict(target[key][i], typing.cast("dict[object, object]", v))
        else:
            target[key] = value


def recursively_delete_dict(
    target: typing.MutableMapping[typing.Any, typing.Any],
    source: typing.Mapping[typing.Any, typing.Any],
) -> None:
    """Recursively delete items from a dictionary.

    This is used to update the player data.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            recursively_delete_dict(target[key], typing.cast("dict[object, object]", value))
        elif isinstance(value, list):
            for i, v in enumerate(typing.cast("list[object]", value)):
                if isinstance(v, dict):
                    recursively_delete_dict(target[key][i], typing.cast("dict[object, object]", v))
                else:
                    target[key].remove(v)
        else:
            del target[key]


# https://github.com/Rhine-Department-0xf/Rhine-DFramwork/blob/main/client/encryption.py


def get_md5(data: str | bytes) -> str:
    """Get the MD5 hash of a string or bytes object."""
    if isinstance(data, str):
        data = data.encode()

    return hashlib.md5(data).hexdigest()


def rijndael_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Encrypt with AES CBC."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

    aes_obj = AES.new(key, AES.MODE_CBC, iv)  # pyright: ignore[reportUnknownMemberType]
    encrypt_buf = aes_obj.encrypt(pad(data, AES.block_size))
    return encrypt_buf


def rijndael_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt with AES CBC."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    aes_obj = AES.new(key, AES.MODE_CBC, iv)  # pyright: ignore[reportUnknownMemberType]
    decrypt_buf = aes_obj.decrypt(data)
    return unpad(decrypt_buf, AES.block_size)


def encrypt_battle_data(data: str, login_time: int) -> str:
    """Encrypt battle data with AES."""
    iv = "".join(random.choices(string.ascii_letters + string.digits, k=16)).encode()
    key_array = bytearray.fromhex(get_md5(f"pM6Umv*^hVQuB6t&{login_time}"))
    return binascii.hexlify(rijndael_encrypt(data.encode(), key_array, iv) + iv).decode().upper()


def decrypt_battle_data(data: str, login_time: int) -> typing.Any:
    """Decrypt battle data with AES."""
    battle_data = data[:-32:]
    battle_data_array = bytearray.fromhex(battle_data)
    iv = data[-32::]
    iv_array = bytearray.fromhex(iv)
    key_array = bytearray.fromhex(get_md5(f"pM6Umv*^hVQuB6t&{login_time}"))
    decrypted_data = rijndael_decrypt(battle_data_array, key_array, iv_array)
    return json.loads(decrypted_data)


def decrypt_battle_replay(battle_replay: str) -> typing.Any:
    """Decrypt a battle replay to get battle_id.

    op: 0 = place, 1 = retreat, 2 = skill
    direction: 0 = up, 1 = right 2 = down, 3 = left
    pos: 1,1 = bottom left (cartesian)
    """
    data = base64.b64decode(battle_replay)
    with zipfile.ZipFile(io.BytesIO(data), "r") as z, z.open("default_entry") as f:
        return json.load(f)


def get_battle_data_access(login_time: int, hash_key: str) -> str:
    """Get battle data access for battle finish stats."""
    # I have no idea what this is for actually
    return get_md5(f"{hash_key}{login_time}").upper()


def encrypt_battle_id(battle_id: str) -> str:
    """Encrypt a battle ID to get is_cheat."""
    data = bytearray(i + 7 for i in battle_id.encode())
    return base64.b64encode(data).decode()


class AutomationClient(CoreClient):
    """Automation client. Potentially bannable.

    Does not use any models.
    """

    data: typing.Any
    """Player data."""
    time_offset: int
    """Time offset in seconds."""

    def __init__(
        self,
        auth: authn.Auth | None = None,
        *,
        assets: assetsn.Assets | str | typing.Literal[False] | None = None,
        network: netn.NetworkSession | None = None,
        server: netn.ArknightsServer | None = None,
    ) -> None:
        super().__init__(auth, assets=assets, network=network, server=server)
        self.data = {}

    def update_player_data_delta(
        self,
        delta: typing.Mapping[typing.Literal["deleted", "modified"], typing.Any],
    ) -> None:
        """Take a player data delta and update the player data.

        Does not implement deleted as it is often overwritten with "modified".
        """
        recursively_delete_dict(self.data, delta["deleted"])
        recursively_update_dict(self.data, delta["modified"])

    async def request(self, endpoint: str, json: typing.Mapping[str, object] = {}, **kwargs: typing.Any) -> typing.Any:
        """Send an authenticated request to the arknights game server."""
        data = await super().request(endpoint, json=json, method="POST", **kwargs)
        self.update_player_data_delta(data["playerDataDelta"])
        if data.get("ts"):
            self.time_offset = data["ts"] - time.time()

        return data

    async def account_sync_data(self) -> typing.Any:
        """Sync player data.

        APP behavior: Called right after login.
        """
        data = await super().request("account/syncData", json={"platform": 1})
        self.data = data["user"]
        return data

    async def account_sync_status(self, modules: int = 95) -> typing.Any:
        """Sync progress status.

        I have literally no idea what modules means.
        I personally get 1759 after launch, 95 normally and sometimes 7.

        APP behavior: Called periodically after most actions.
        """
        data = {
            "modules": modules,
            "params": {
                "16": {"goodIdMap": {"LS": [], "HS": [], "ES": [], "CASH": [], "GP": ["GP_Once_1"], "SOCIAL": []}},
            },
        }
        return await self.request("account/syncStatus", json=data)

    async def user_check_in(self) -> typing.Any:
        """Claim daily login rewards.

        APP behavior: Called when claiming daily login rewards.
        """
        return await self.request("user/checkIn")

    async def mission_auto_confirm_missions(self, type: str) -> typing.Any:
        """Claim daily or weekly mission rewards,.

        type: Mission type. Either DAILY or WEEKLY.

        APP behavior: Called when batch completing daily or weekly mission rewards.
        """
        data = {
            "type": type,
        }
        return await self.request("mission/autoConfirmMissions", json=data)

    async def building_sync(self) -> typing.Any:
        """Sync base data.

        APP behavior: Called when entered the base.
        """
        return await self.request("building/sync")

    async def building_get_assist_report(self) -> typing.Any:
        """Get base report.

        APP behavior: Called when viewing base report in the control center.
        """
        return await self.request("building/getAssistReport")

    async def building_assign_char(self, room_slot_id: str, char_inst_id_list: typing.Sequence[int]) -> typing.Any:
        """Assign operators to a room.

        room_slot_id: Room slot ID to assign to.
        char_inst_id_list: List of operator instance IDs to assign. -1 for an empty slot.

        APP behavior: Called when assigning operators to a room.
        """
        data = {
            "roomSlotId": room_slot_id,
            "charInstIdList": char_inst_id_list,
        }
        return await self.request("building/assignChar", json=data)

    async def building_settle_manufacture(
        self,
        room_slot_id_list: typing.Sequence[str],
        supplement: bool = True,
    ) -> typing.Any:
        """Claim factory products.

        room_slot_id_list: List of room slot IDs to claim.
        supplement: Whether to supplement (restock) the materials back to the max.

        APP behavior: Called when claiming factory products.
        """
        data = {
            "roomSlotIdList": room_slot_id_list,
            "supplement": int(supplement),
        }
        return await self.request("building/settleManufacture", json=data)

    async def building_delivery_order(self, slot_id: str, order_id: int) -> typing.Any:
        """Claim trading post products.

        slot_id: Room slot ID to claim.
        order_id: Order ID to claim.

        APP behavior: Called when claiming individual trading post products.
        """
        data = {
            "slotId": slot_id,
            "orderId": order_id,
        }
        return await self.request("building/deliveryOrder", json=data)

    async def building_delivery_batch_order(self, slot_list: typing.Sequence[str]) -> typing.Any:
        """Claim all trading post products.

        slot_list: List of room slot IDs to claim.

        APP behavior: Called when claiming all trading post products.
        """
        data = {
            "slotList": slot_list,
        }
        return await self.request("building/deliveryBatchOrder", json=data)

    async def building_gain_all_intimacy(self) -> typing.Any:
        """Claim trust increase of all operators stationed in the base.

        APP behavior: Called when claiming trust of all operators in the base every 12h.
        """
        return await self.request("building/gainAllIntimacy")

    async def building_accelerate_solution(self, slot_id: str, cost: int) -> typing.Any:
        """Accelerate a room with drones.

        slot_id: Room slot ID to accelerate.
        cost: Amount of drones to use.

        APP behavior: Called when using drones.
        """
        data = {
            "slotId": slot_id,
            "cost": cost,
        }
        return await self.request("building/accelerateSolution", json=data)

    async def building_get_clue_box(self) -> typing.Any:
        """View clues gifted to your base by your friends.

        APP behavior: Called when opening the gifted clue box in the meeting room.
        """
        return await self.request("building/getClueBox")

    async def building_get_daily_clue(self) -> typing.Any:
        """Get a daily clue.

        APP behavior: Called when claiming the daily clue in the meeting room.
        """
        return await self.request("building/getDailyClue")

    async def building_receive_clue_to_stock(self, clues: typing.Sequence[str]) -> typing.Any:
        """Claim clues gifted to your base by your friends.

        clues: List of clue IDs to claim.

        APP behavior: Called when claiming clues from the gifted clue box.
        """
        data = {
            "clues": clues,
        }
        return await self.request("building/receiveClueToStock", json=data)

    async def building_put_clue_to_the_board(self, clue_id: str) -> typing.Any:
        """Put a clue on the board or swap to the clue if there already is one.

        clue_id: Clue ID to put on the board.

        APP behavior: Called when putting a clue on the board.
        """
        data = {
            "clueId": clue_id,
        }
        return await self.request("building/putClueToTheBoard", json=data)

    async def building_take_clue_from_board(self, type: str) -> typing.Any:
        """Take a clue from the board.

        type: Clue type as a string. For example RHODES.

        APP behavior: Called when taking a clue from the board.
        """
        data = {
            "type": type,
        }
        return await self.request("building/takeClueFromBoard", json=data)

    async def building_visit_building(self, friend_id: str) -> typing.Any:
        """Visit a friend's base.

        friend_id: Friend's ID.

        APP behavior: Called when visiting a friend's base.
        """
        data = {
            "friendId": friend_id,
        }
        return await self.request("building/visitBuilding", json=data)

    async def building_get_clue_friend_list(self, id_list: typing.Sequence[str]) -> typing.Any:
        """Get a list of friends able to receive clues.

        APP behavior: Called when viewing the clue board in the meeting room.
        """
        return await self.request("building/getClueFriendList")

    async def building_send_clue(self, friend_id: str, clue_id: str) -> typing.Any:
        """Send a clue to a friend.

        friend_id: Friend's ID.
        clue_id: Clue ID to send.

        APP behavior: Called when sending a clue to a friend.
        """
        data = {
            "friendId": friend_id,
            "clueId": clue_id,
        }
        return await self.request("building/sendClue", json=data)

    async def building_start_info_share(self) -> typing.Any:
        """Start a clue exchange.

        APP behavior: Called when starting a clue exchange in the meeting room after gathering all clues.
        """
        return await self.request("building/startInfoShare")

    async def building_get_meetingroom_reward(self, type: typing.Sequence[int]) -> typing.Any:
        """Get rewards from a clue exchange and such.

        type: Array of booleans. No idea what they correspond to. I got [0, 1]

        APP behavior: Called when entering the base.
        """
        data = {
            "type": type,
        }
        return await self.request("building/getMeetingroomReward", json=data)

    async def social_get_friend_list(self, id_list: typing.Sequence[str]) -> typing.Any:
        """Get a list of friends by ID.

        APP behavior: Called after any request for friend IDs.
        """
        data = {
            "idList": id_list,
        }
        return await self.request("social/getFriendList", json=data)

    async def social_receive_social_point(self) -> typing.Any:
        """Claim daily social shop points.

        APP behavior: Called when claiming the daily social shop points.
        """
        return await self.request("social/receiveSocialPoint")

    async def shop_get_social_good_list(self) -> typing.Any:
        """Get the social shop product list.

        APP behavior: Called when entering the social shop.
        """
        return await self.request("shop/getSocialGoodList")

    async def shop_buy_social_good(self, good_id: str, count: int = 1) -> typing.Any:
        """Buy a social shop product.

        good_id: Product ID.
        count: Probably amount to buy. This should always be 1.

        APP behavior: Called when buying a social shop product.
        """
        data = {
            "goodId": good_id,
            "count": count,
        }
        return await self.request("shop/buySocialGood", json=data)

    async def gacha_sync_normal_gacha(self) -> typing.Any:
        """Sync recruitment data.

        APP behavior: Called when entering the recruitment page.
        """
        return await self.request("gacha/syncNormalGacha")

    async def gacha_refresh_tags(self, slot_id: int) -> typing.Any:
        """Refresh recruitment tags.

        slot_id: Recruitment slot ID.

        APP behavior: Called when refreshing recruitment tags.
        """
        data = {
            "slotId": slot_id,
        }
        return await self.request("gacha/refreshTags", json=data)

    async def gacha_normal_gacha(
        self,
        slot_id: int,
        tag_list: typing.Sequence[int],
        duration: int,
        special_tag_id: int = -1,
    ) -> typing.Any:
        """Start a recruitment.

        slot_id: Recruitment slot ID.
        tag_list: List of tag IDs to use.
        duration: Recruitment duration in seconds.
        special_tag_id: Unknown, always -1.

        APP behavior: Called when starting a recruitment.
        """
        data = {
            "slotId": slot_id,
            "tagList": tag_list,
            "specialTagId": special_tag_id,
            "duration": duration,
        }
        return await self.request("gacha/normalGacha", json=data)

    async def gacha_finish_normal_gacha(self, slot_id: int) -> typing.Any:
        """Finish a recruitment.

        slot_id: Recruitment slot ID.

        APP behavior: Called when finishing a recruitment.
        """
        data = {
            "slotId": slot_id,
        }
        return await self.request("gacha/finishNormalGacha", json=data)

    async def battle_get_battle_replay(self, battle_type: str, stage_id: str) -> typing.Any:
        """Get a replay of a stage.

        Needs to be decrypted with decrypt_battle_replay.

        stage_id: Stage ID.

        APP behavior: Called when entering the squad selection screen with auto-deploy enabled.
        """
        data = {
            "stageId": stage_id,
        }
        return await self.request(f"{battle_type}/getBattleReplay", json=data)

    async def battle_start(
        self,
        battle_type: str,
        stage_id: str,
        squad: typing.Sequence[typing.Mapping[str, typing.Any]],
        use_practice_ticket: bool = False,
        is_replay: bool = True,
        pry: bool = False,
        is_retro: bool = False,
        assist_friend: typing.Any | None = None,
    ) -> typing.Any:
        """Start a stage.

        stage_id: Stage ID.
        squad: List of operators to deploy. Requires charInstId, currentEquip and skillIndex.
        use_practice_ticket: Whether to use a practice ticket.
        is_replay: Whether auto-deploy is being used.
        pry: Uknonwn, always false.
        is_retro: Unknown, always false.
        assist_friend: Unknown. None for no support.

        APP behavior: Called when starting a stage.
        """
        data = {
            "stageId": stage_id,
            "squad": squad,
            "usePracticeTicket": int(use_practice_ticket),
            "isReplay": int(is_replay),
            "pry": int(pry),
            "isRetro": int(is_retro),
            "assistFriend": assist_friend,
        }
        return await self.request(f"{battle_type}/battleStart", json=data)

    async def battle_finish(
        self,
        battle_type: str,
        stage_id: str,
        complete_time: int,
        is_cheat: str,
        stats: typing.Mapping[str, typing.Any],
        data: str,
    ) -> typing.Any:
        """Finish a stage. This is where you are most likely to get banned.

        stage_id: Stage ID.
        complete_time: Time taken to complete the stage in seconds.
        is_cheat: Encrypted battle id.
        stats: Unknown, always empty dict.
        data: Encrypted battle data.

        APP behavior: Called when finishing a stage.
        """
        d = {
            "battleData": {
                "stageId": stage_id,
                "completeTime": complete_time,
                "isCheat": is_cheat,
                "stats": stats,
            },
            "data": data,
        }
        return await self.request(f"{battle_type}/battleFinish", json=d)

    async def battle_sweep(
        self,
        battle_type: str,
        stage_id: str,
        item_id: str,
        inst_id: int,
    ) -> typing.Any:
        """Use a proxy to instantly do a battle.

        battle_type: Type of stage being done. Likely CampaignV2 (annihilation).
        stage_id: Stage ID.
        item_id: Item used to instantly do the battle. EXTERMINATION_AGENT.
        inst_id: Item instance ID. Ideally the one that expires earlier.
        """
        data = {
            "stageId": stage_id,
            "itemId": item_id,
            "itemInstId": inst_id,
        }

        return await self.request(f"{battle_type}/battleSweep", json=data)
