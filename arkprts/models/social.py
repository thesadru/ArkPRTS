"""Arknights API social models.

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


class Skill(pydantic.BaseModel):
    """Skill of a character."""

    skill_id: str = pydantic.Field(alias="skillId")
    """Skill ID."""
    unlock: bool
    """Whether the skill is unlocked."""
    state: bool
    """IDK. Skill state."""
    specialize_level: int = pydantic.Field(alias="specializeLevel")
    """Skill mastery level."""
    complete_upgrade_time: int = pydantic.Field(alias="completeUpgradeTime")
    """IDK. Time left until skill upgrade is complete."""


class UniEquip(pydantic.BaseModel):
    """Equipped modules."""

    hide: bool
    """IDK. Whether the module is publicly hidden."""
    locked: bool
    """Whether module access is locked."""
    level: int
    """Module level."""


class AssistChar(pydantic.BaseModel):
    """Publicly visible operator info."""

    char_id: str = pydantic.Field(alias="charId")
    """Character ID."""
    skin_id: str = pydantic.Field(alias="skinId")
    """Equipped skin ID."""
    skills: typing.Sequence[Skill]
    """Operator skills."""
    main_skill_lvl: int = pydantic.Field(alias="mainSkillLvl")
    """Level of the equipped skill."""
    skill_index: int = pydantic.Field(alias="skillIndex")
    """Index of the equipped skill."""
    evolve_phase: int = pydantic.Field(alias="evolvePhase")
    """Elite phase."""
    favor_point: int = pydantic.Field(alias="favorPoint")
    """Raw trust points (25570 is 200% Trust)"""
    potential_rank: int = pydantic.Field(alias="potentialRank")
    """Operator potential. Starts at 0."""
    level: int
    """Operator level."""
    crisis_record: typing.Any = pydantic.Field(alias="crisisRecord")
    """IDK. selectedCrisis is used for contingency contracts elsewhere."""
    current_equip: typing.Optional[str] = pydantic.Field(alias="currentEquip")
    """ID of the currently equipped module."""
    equip: typing.Mapping[str, UniEquip]
    """Equipped modules. Module ID to module info."""


class PlacedMedal(pydantic.BaseModel):
    """A single medal on a board."""

    id: str
    """Medal ID."""
    pos: typing.Tuple[int, int]
    """Medal position on the board."""


class MedalBoardCustom(pydantic.BaseModel):
    """Custom medal board layout."""

    layout: typing.Sequence[PlacedMedal]
    """Medals on the board."""


class MedalBoardTemplate(pydantic.BaseModel):
    """Template medal board layout."""

    group_id: str = pydantic.Field(alias="groupId")
    """Medal board template ID."""
    medal_list: typing.Sequence[str] = pydantic.Field(alias="medalList")
    """Medal IDs on the board."""


class MedalBoard(pydantic.BaseModel):
    """Medal board info."""

    type: typing.Literal["CUSTOM", "TEMPLATE", "EMPTY"]
    """Medal board layout type."""
    custom: typing.Optional[MedalBoardCustom]
    """Custom medal board layout."""
    template: typing.Optional[MedalBoardTemplate]
    """Template medal board layout."""


class PartialPlayer(pydantic.BaseModel):
    """Partial player info from search."""

    nickname: str = pydantic.Field(alias="nickName")
    """Player nickname."""
    nick_number: str = pydantic.Field(alias="nickNumber")
    """Player nickname number after #."""
    uid: str
    """Player UID."""
    friend_num_limit: int = pydantic.Field(alias="friendNumLimit")
    """How many friend slots are open."""
    server_name: str = pydantic.Field(alias="serverName")
    """Server name. Should always be Terra."""
    level: int
    """Player level."""
    avatar_id: str = pydantic.Field(alias="avatarId")
    """IDK. Always 0."""
    avatar: typing.Optional[Avatar] = None
    """Selected avatar."""
    assist_char_list: typing.Sequence[typing.Optional[AssistChar]] = pydantic.Field(alias="assistCharList")
    """Assist operator list."""
    last_online_time: datetime.datetime = pydantic.Field(alias="lastOnlineTime")
    """Last online time."""
    medal_board: MedalBoard = pydantic.Field(alias="medalBoard")
    """Medal board."""


class Player(PartialPlayer):
    """Player info."""

    register_ts: datetime.datetime = pydantic.Field(alias="registerTs")
    """Account creation time."""
    main_stage_progress: typing.Optional[str] = pydantic.Field(alias="mainStageProgress")
    """Current main story stage ID. None if completed."""
    char_cnt: int = pydantic.Field(alias="charCnt")
    """Number of operators owned."""
    furn_cnt: int = pydantic.Field(alias="furnCnt")
    """Number of furniture owned."""
    secretary: str
    """ID of the secretary operator."""
    secretary_skin_id: str = pydantic.Field(alias="secretarySkinId")
    """ID of the secretary operator's skin."""
    resume: str
    """Player display bio."""
    team_v2: typing.Mapping[str, int] = pydantic.Field(alias="teamV2")
    """Amount of characters owned in each faction."""
    board: typing.Sequence[str]
    """IDK. Factions will full trust. Shows up blue in-game."""
    info_share: datetime.datetime = pydantic.Field(alias="infoShare")
    """IDK."""
    recent_visited: bool = pydantic.Field(alias="recentVisited")
    """Whether the player has been recently visited."""
    info_share_visited: typing.Optional[int] = pydantic.Field(None, alias="infoShareVisited")
    """IDK."""
