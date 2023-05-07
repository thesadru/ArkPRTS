"""Arknights API data models.

Any field description prefixed with IDK means it's just a guess.
"""
import datetime
import typing

import pydantic


class Avatar(pydantic.BaseModel):
    """User display avatar."""

    type: typing.Literal["ASSISTANT", "ICON", "DEFAULT"] = "DEFAULT"
    """Avatar type."""
    id: typing.Optional[str] = None
    """Avatar ID. For example a skin ID."""


class Status(pydantic.BaseModel):
    """General user data."""

    nickname: str = pydantic.Field(alias="nickName")
    """Player nickname."""
    nick_number: str = pydantic.Field(alias="nickNumber")
    """Player nickname number after #."""
    level: int
    """Player level."""
    exp: int
    """Player experience."""
    social_point: int = pydantic.Field(alias="socialPoint")
    """IDK."""
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
    progress: int
    """IDK."""
    buy_ap_remain_times: int = pydantic.Field(alias="buyApRemainTimes")
    """Remaining pulls until guaranteed 5 star operator."""
    ap_limit_up_flag: bool = pydantic.Field(alias="apLimitUpFlag")
    """Whether the guaranteed 5 star has been pulled."""
    uid: str
    """User ID."""
    flags: typing.Mapping[str, bool]
    """Completed stories."""
    ap: int
    """Pulls made on the current banner."""
    max_ap: int = pydantic.Field(alias="maxAp")
    """IDK."""
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
    last_refresh_ts: datetime.datetime = pydantic.Field(alias="lastRefreshTs")
    """IDK."""
    last_ap_add_time: datetime.datetime = pydantic.Field(alias="lastApAddTime")
    """IDK."""
    main_stage_progress: str = pydantic.Field(alias="mainStageProgress")
    """Current main story stage ID. None if completed."""
    register_ts: datetime.datetime = pydantic.Field(alias="registerTs")
    """Account creation time."""
    server_name: str = pydantic.Field(alias="serverName")
    """Server name. Should always be Terra."""
    avatar_id: str = pydantic.Field(alias="avatarId")
    """IDK. Always 0."""
    resume: str
    """Player display bio."""
    friend_num_limit: int = pydantic.Field(alias="friendNumLimit")
    """How many friend slots are open."""
    secretary: str
    """ID of the secretary operator."""
    secretary_skin_id: str = pydantic.Field(alias="secretarySkinId")
    """ID of the secretary operator's skin."""
    global_voice_lan: str = pydantic.Field(alias="globalVoiceLan")
    """Default voice-over language."""
    avatar: Avatar
    """Selected avatar."""


class SquadSlot(pydantic.BaseModel):
    """Squad slot."""

    char_inst_id: int = pydantic.Field(alias="charInstId")
    """Operator index."""
    skill_index: int = pydantic.Field(alias="skillIndex")
    """Index of chosen skill."""
    current_equip: typing.Optional[str] = None
    """Currently equipped module ID."""


class Squads(pydantic.BaseModel):
    """Operator squad data."""

    squad_id: str = pydantic.Field(alias="squadId")
    """Squad ID."""
    name: str
    """Squad name."""
    slots: typing.Sequence[typing.Optional[SquadSlot]]
    """Equipped operators."""


class Skill(pydantic.BaseModel):
    """Operator skill data."""

    skill_id: str = pydantic.Field(alias="skillId")
    """Skill ID."""
    unlock: bool
    """Whether the skill is unlocked."""
    state: bool
    """IDK."""
    specialize_lvl: int = pydantic.Field(alias="specializeLvl")
    """Skill mastery level."""
    complete_upgrade_time: datetime.datetime = pydantic.Field(alias="completeUpgradeTime")
    """IDK. Time left until skill upgrade is complete."""


class Equip(pydantic.BaseModel):
    """Operator module data."""

    hide: bool
    """Whether the module is hidden."""
    locked: bool
    """Whether the module is locked."""
    level: int
    """Module level."""


class Character(pydantic.BaseModel):
    """Operator data."""

    inst_id: int = pydantic.Field(alias="instId")
    """Index of the operator."""
    char_id: str = pydantic.Field(alias="charId")
    """Operator ID."""
    favor_point: int = pydantic.Field(alias="favorPoint")
    """Operator trust."""
    potential_rank: int = pydantic.Field(alias="potentialRank")
    """Operator potential. Starts at 0."""
    main_skill_lvl: int = pydantic.Field(alias="mainSkillLvl")
    """Operator skill level."""
    skin: str
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
    current_equip: typing.Optional[str] = None
    """Currently equipped module."""
    equip: typing.Mapping[str, Equip]


class CharGroup(pydantic.BaseModel):
    """Operator group data."""

    favor_point: int = pydantic.Field(alias="favorPoint")
    """Operator trust."""


class Troops(pydantic.BaseModel):
    """Operator data."""

    cur_char_inst_id: int = pydantic.Field(alias="curCharInstId")
    """Amount of owned operators."""
    cur_squad_count: int = pydantic.Field(alias="curSquadCount")
    """Amount of squads. Should be always 4."""
    squads: typing.Mapping[str, Squads]
    """Squad data."""
    chars: typing.Mapping[str, Character]
    """Operator data."""
    char_group: typing.Mapping[str, CharGroup] = pydantic.Field(alias="charGroup")
    """Operator group data."""
    char_mission: typing.Mapping[str, typing.Mapping[str, bool]] = pydantic.Field(alias="charMission")
    """Special operation missions."""
    addon: typing.Any
    """IDK."""


class Skins(pydantic.BaseModel):
    """Operator skin data."""

    character_skins: typing.Mapping[str, bool] = pydantic.Field(alias="characterSkins")
    """Owned skins."""
    skin_ts: datetime.datetime = pydantic.Field(alias="skinTs")
    """When the skin was obtained."""


class ConsumableExpire(pydantic.BaseModel):
    """Consumable expiration data."""

    ts: datetime.datetime
    """When the consumable expires."""
    count: int
    """Amount of consumables."""


class User(pydantic.BaseModel):
    """User sync data. Not fully modeled."""

    status: Status
    """General user data."""
    troop: Troops
    """Operator data."""
    skin: Skins
    """Operator skin data."""
    cosumable: typing.Mapping[str, typing.Mapping[int, ConsumableExpire]]
    """Consumable data."""
    inventory: typing.Mapping[int, int]
    """Inventory data. Item ID to amount."""
