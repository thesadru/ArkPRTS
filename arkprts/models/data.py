"""Arknights API data models.

Any field description prefixed with IDK means it's just a guess.
"""

import datetime
import typing

import pydantic

from . import base


class Avatar(base.BaseModel):
    """User display avatar."""

    type: typing.Literal["ASSISTANT", "ICON", "DEFAULT"] = "DEFAULT"
    """Avatar type."""
    id: typing.Optional[str] = None
    """Avatar ID. For example a skin ID."""


class Status(base.BaseModel):
    """General user data."""

    nickname: str = pydantic.Field(alias="nickName")
    """Player nickname."""
    nick_number: typing.Annotated[str, pydantic.PlainValidator(str)] = pydantic.Field(alias="nickNumber")
    """Player nickname number after #."""
    level: int
    """Player level."""
    exp: int
    """Player experience."""
    social_point: int = pydantic.Field(alias="socialPoint")
    """Credit shop credits."""
    gacha_ticket: int = pydantic.Field(alias="gachaTicket")
    """Amount of single headhunting permits."""
    ten_gacha_ticket: int = pydantic.Field(alias="tenGachaTicket")
    """Amount of 10-headhunting permits."""
    instant_finish_ticket: int = pydantic.Field(alias="instantFinishTicket")
    """Amount of expedited completion permits."""
    hgg_shard: int = pydantic.Field(alias="hggShard")
    """Amount of yellow distinction certificates."""
    lgg_shard: int = pydantic.Field(alias="lggShard")
    """Amount of green commendation certificates.."""
    recruit_license: int = pydantic.Field(alias="recruitLicense")
    """Amount of recruitment permit."""
    progress: int = pydantic.Field(repr=False)
    """IDK. Seems to always be 3000."""
    buy_ap_remain_times: int = pydantic.Field(alias="buyApRemainTimes", repr=False)
    """How many more times you can refresh sanity with originite prime."""
    ap_limit_up_flag: bool = pydantic.Field(alias="apLimitUpFlag", repr=False)
    """IDK. Ap refers to sanity. Always zero."""
    uid: str
    """User ID."""
    flags: typing.Mapping[str, bool] = pydantic.Field(repr=False)
    """Completed stories."""
    ap: int
    """Sanity value when last incrememnted. See current_sanity for true value."""
    max_ap: int = pydantic.Field(alias="maxAp")
    """Max sanity."""
    pay_diamond: int = pydantic.Field(alias="payDiamond")
    """Bough originium prime."""
    free_diamond: int = pydantic.Field(alias="freeDiamond")
    """Earned originium prime."""
    diamond_shard: int = pydantic.Field(alias="diamondShard")
    """Amount of orundum."""
    gold: int
    """Amount of LMD."""
    practice_ticket: int = pydantic.Field(alias="practiceTicket")
    """Amount of training permits."""
    last_refresh_ts: base.ArknightsTimestamp = pydantic.Field(alias="lastRefreshTs")
    """Last time a sanity refresh was used. IDK the influence on ap calculation."""
    last_ap_add_time: base.ArknightsTimestamp = pydantic.Field(alias="lastApAddTime")
    """Last time AP was incremented/calculated."""
    last_online_ts: base.ArknightsTimestamp = pydantic.Field(alias="lastOnlineTs")
    """When the player was last online."""
    main_stage_progress: typing.Optional[str] = pydantic.Field(alias="mainStageProgress")
    """Current main story stage ID. None if completed."""
    register_ts: base.ArknightsTimestamp = pydantic.Field(alias="registerTs")
    """Account creation time."""
    server_name: str = pydantic.Field(alias="serverName")
    """Server name. Should always be Terra."""
    avatar_id: str = pydantic.Field(alias="avatarId", repr=False)
    """IDK. Always "0"."""
    resume: str
    """Player display bio."""
    friend_num_limit: int = pydantic.Field(alias="friendNumLimit")
    """How many friend slots are open."""
    secretary: str
    """ID of the secretary operator."""
    secretary_skin_id: str = pydantic.Field(alias="secretarySkinId")
    """ID of the secretary operator's skin."""
    global_voice_lan: typing.Optional[str] = pydantic.Field(None, alias="globalVoiceLan")
    """Default voice-over language."""
    avatar: typing.Optional[Avatar] = pydantic.Field(None)
    """Selected avatar."""

    # fmt: off
    # optional:
    monthly_subscription_start_time: typing.Optional[base.ArknightsTimestamp] = pydantic.Field(None, alias="monthlySubscriptionStartTime")
    """When the monthly subscription started."""
    monthly_subscription_end_time: typing.Optional[base.ArknightsTimestamp] = pydantic.Field(None, alias="monthlySubscriptionEndTime")
    """When the monthly subscription is ending."""
    tip_monthly_card_expire: typing.Optional[base.ArknightsTimestamp] = pydantic.Field(None, alias="tipMonthlyCardExpire")
    """IDK. Seems to be close to register time, so likely the first the monthly card was used?"""
    # fmt: on

    @property
    def current_ap(self) -> int:
        """Current sanity."""
        last_calculation = max(self.last_refresh_ts, self.last_ap_add_time)
        since_calculation = last_calculation - datetime.datetime.now(tz=datetime.timezone.utc)
        ap_add_amount = since_calculation // datetime.timedelta(minutes=6)
        return self.ap + ap_add_amount

    @property
    def basic_item_inventory(self) -> typing.Mapping[str, int]:
        """Basic item inventory. These are not shown in the inventory object."""
        return {
            "SOCIAL_PT": self.social_point,
            "AP_GAMEPLAY": self.ap,
            "4001": self.gold,
            "4002": self.pay_diamond + self.free_diamond,
            "4003": self.diamond_shard,
            "4004": self.hgg_shard,
            "4005": self.lgg_shard,
            "5001": self.exp,
            "6001": self.practice_ticket,
            "7001": self.recruit_license,
            "7002": self.instant_finish_ticket,
            "7003": self.gacha_ticket,
            "7004": self.ten_gacha_ticket,
        }


class SquadSlot(base.BaseModel):
    """Squad slot."""

    char_inst_id: int = pydantic.Field(alias="charInstId")
    """Operator index."""
    skill_index: int = pydantic.Field(alias="skillIndex")
    """Index of chosen skill."""
    current_equip: typing.Optional[str] = None
    """Currently equipped module ID."""
    tmpl: typing.Mapping[str, base.DDict] = pydantic.Field(default_factory=base.DDict, repr=False)
    """Alternative operator class data. Only for Amiya."""


class Squads(base.BaseModel):
    """Operator squad data."""

    squad_id: str = pydantic.Field(alias="squadId")
    """Squad ID."""
    name: str
    """Squad name."""
    slots: typing.Sequence[typing.Optional[SquadSlot]]
    """Equipped operators."""


class Skill(base.BaseModel):
    """Operator skill data."""

    skill_id: str = pydantic.Field(alias="skillId")
    """Skill ID."""
    unlock: bool
    """Whether the skill is unlocked."""
    state: bool = pydantic.Field(repr=False)
    """IDK. Always false."""
    specialize_level: int = pydantic.Field(alias="specializeLevel")
    """Skill mastery level."""
    complete_upgrade_time: typing.Optional[base.ArknightsTimestamp] = pydantic.Field(alias="completeUpgradeTime")
    """IDK. Time of mastery upgrade completion. Is raw -1 if not upgrading."""

    @property
    def static(self) -> base.DDict:
        """Static data for this skill."""
        return self.client.assets.skill_table[self.skill_id]


class Equip(base.BaseModel):
    """Operator module data."""

    hide: bool
    """Whether the module is hidden."""
    locked: bool
    """Whether the module is locked."""
    level: int
    """Module level."""


class Character(base.BaseModel):
    """Operator data."""

    inst_id: int = pydantic.Field(alias="instId")
    """Index of the operator."""
    char_id: str = pydantic.Field(alias="charId")
    """Operator ID."""
    favor_point: int = pydantic.Field(alias="favorPoint")
    """Operator trust points."""
    potential_rank: int = pydantic.Field(alias="potentialRank")
    """Operator potential. Starts at 0."""
    main_skill_lvl: int = pydantic.Field(alias="mainSkillLvl")
    """Operator skill level."""
    skin: str = pydantic.Field(validation_alias=pydantic.AliasChoices("skinId", "skin"))
    """Operator skin ID."""
    level: int
    """Operator level."""
    exp: int
    """Operator experience."""
    evolve_phase: int = pydantic.Field(alias="evolvePhase")
    """Elite phase."""
    default_skill_index: int = pydantic.Field(alias="defaultSkillIndex")
    """Index of the default skill."""
    skills: typing.Sequence[Skill]
    """Operator skills."""
    voice_lan: str = pydantic.Field(alias="voiceLan")
    """Operator voice-over language."""
    current_equip: typing.Optional[str] = pydantic.Field(alias="currentEquip")
    """Currently equipped module."""
    equip: typing.Mapping[str, Equip]
    """Operator modules."""
    star_mark: bool = pydantic.Field(False, alias="starMark")
    """Whether the operator is marked as favorite."""
    tmpl: typing.Mapping[str, base.DDict] = pydantic.Field(default_factory=base.DDict, repr=False)
    """Alternative operator class data. Only for Amiya."""

    @property
    def static(self) -> base.DDict:
        """Static data for this operator."""
        return self.client.assets.character_table[self.char_id]

    @property
    def trust(self) -> int:
        """Trust calculated from favor_point."""
        return self.client.assets.calculate_trust_level(self.favor_point)


class CharGroup(base.BaseModel):
    """Additional operator data."""

    favor_point: int = pydantic.Field(alias="favorPoint")
    """Operator trust points."""

    @property
    def trust(self) -> int:
        """Trust calculated from favor_point."""
        return self.client.assets.calculate_trust_level(self.favor_point)


class Troops(base.BaseModel):
    """Operator data."""

    cur_char_inst_id: int = pydantic.Field(alias="curCharInstId")
    """Amount of owned operators."""
    cur_squad_count: int = pydantic.Field(alias="curSquadCount")
    """Amount of squads. Should be always 4."""
    squads: typing.Mapping[int, Squads]
    """Squad data."""
    chars: typing.Mapping[int, Character]
    """Operator data."""
    char_group: typing.Mapping[str, CharGroup] = pydantic.Field(alias="charGroup")
    """Additional operator data."""
    char_mission: typing.Mapping[str, typing.Mapping[str, int]] = pydantic.Field(alias="charMission", repr=False)
    """IDK. Special operation missions."""
    addon: base.DDict = pydantic.Field(default_factory=base.DDict, repr=False)
    """IDK. Unlockable character story and stage."""


class Skins(base.BaseModel):
    """Operator skin data."""

    character_skins: typing.Mapping[str, bool] = pydantic.Field(alias="characterSkins")
    """Owned skins."""
    skin_ts: typing.Mapping[str, base.ArknightsTimestamp] = pydantic.Field(default={}, alias="skinTs")
    """When the skins were obtained."""


class AssistChar(base.BaseModel):
    """Assist operator data."""

    char_inst_id: int = pydantic.Field(alias="charInstId")
    """Index of the operator."""
    skill_index: int = pydantic.Field(alias="skillIndex")
    """Index of the selected skill."""
    current_equip: typing.Optional[str] = pydantic.Field(alias="currentEquip")
    """Currently equipped module."""
    tmpl: typing.Mapping[str, base.DDict] = pydantic.Field(default_factory=base.DDict, repr=False)
    """Alternative operator class data. Only for Amiya."""


class Social(base.BaseModel):
    """Social data."""

    assist_char_list: typing.Sequence[typing.Optional[AssistChar]] = pydantic.Field(alias="assistCharList")
    """Support operators."""
    yesterday_reward: base.DDict = pydantic.Field(alias="yesterdayReward")
    """IDK. Clue exchange data."""
    y_crisis_ss: typing.Union[str, typing.Any] = pydantic.Field(alias="yCrisisSs", repr=False)
    """IDK. Crisis refers to contingency contract. Always empty string."""
    medal_board: base.DDict = pydantic.Field(default_factory=base.DDict, alias="medalBoard")
    """Medal board."""


class ConsumableExpire(base.BaseModel):
    """Consumable expiration data."""

    ts: typing.Optional[base.ArknightsTimestamp]
    """When the consumable expires. Some consumables do not expire."""
    count: int
    """Amount of consumables."""


class User(base.BaseModel, extra="ignore"):
    """User sync data. Not fully modeled."""

    status: Status
    """General user data."""
    troop: Troops
    """Operator data."""
    skin: Skins
    """Operator skin data."""
    social: Social
    """Data related to friends."""
    consumable: typing.Mapping[str, typing.Mapping[int, ConsumableExpire]] = {}
    """Consumable data."""
    inventory: typing.Mapping[str, int]
    """Inventory data. Item ID to amount.

    To access the static data for an item, use `client.assets.get_item(item_id)`.
    """
