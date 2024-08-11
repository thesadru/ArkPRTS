"""Arknights API social models.

Any field description prefixed with IDK means it's just a guess.
"""

import typing

import pydantic

from . import base


class Avatar(base.BaseModel):
    """User display avatar."""

    type: typing.Literal["ASSISTANT", "ICON", "DEFAULT"] = "DEFAULT"
    """Avatar type."""
    id: typing.Optional[str] = None
    """Avatar ID. For example a skin ID."""


class Skill(base.BaseModel):
    """Skill of a character."""

    skill_id: str = pydantic.Field(alias="skillId")
    """Skill ID."""
    unlock: bool
    """Whether the skill is unlocked."""
    state: bool = pydantic.Field(repr=False)
    """IDK. Always false."""
    specialize_level: int = pydantic.Field(alias="specializeLevel")
    """Skill mastery level."""
    complete_upgrade_time: typing.Optional[base.ArknightsTimestamp] = pydantic.Field(alias="completeUpgradeTime")
    """IDK. Time left until skill upgrade is complete. Is raw -1 if not upgrading."""

    @property
    def static(self) -> base.DDict:
        """Static data for this skill."""
        return self.client.assets.skill_table[self.skill_id]


class UniEquip(base.BaseModel):
    """Equipped modules."""

    hide: bool
    """Whether the player may see the modules. For operators below E2."""
    locked: bool
    """Whether module access is locked."""
    level: int
    """Module level."""


class AssistChar(base.BaseModel):
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
    """Operator trust points."""
    potential_rank: int = pydantic.Field(alias="potentialRank")
    """Operator potential. Starts at 0."""
    level: int
    """Operator level."""
    crisis_record: typing.Mapping[str, int] = pydantic.Field(alias="crisisRecord")
    """Maximum risk this operator was used as a support in. Only for operations (before Pinch-Out). -1 if never used."""
    crisis_v2_record: typing.Mapping[str, int] = pydantic.Field(alias="crisisV2Record")
    """Maximum risk this operator was used as a support in. Only for battleplans (after Pinch-Out). -1 if never used."""
    current_equip: typing.Optional[str] = pydantic.Field(alias="currentEquip")
    """ID of the currently equipped module."""
    equip: typing.Mapping[str, UniEquip]
    """Equipped modules. Module ID to module info."""
    tmpl: typing.Mapping[str, base.DDict] = pydantic.Field(default_factory=base.DDict, repr=False)
    """Alternative operator class data. Only for Amiya."""
    variations: typing.Mapping[str, "AssistChar"] = pydantic.Field(default_factory=dict, repr=False)
    """All representations of amiya."""

    @property
    def static(self) -> base.DDict:
        """Static data for this operator."""
        return self.client.assets.full_character_table[self.char_id]

    @property
    def trust(self) -> int:
        """Trust calculated from favor_point."""
        return self.client.assets.calculate_trust_level(self.favor_point)


class PlacedMedal(base.BaseModel):
    """A single medal on a board."""

    id: str
    """Medal ID."""
    pos: typing.Tuple[int, int]
    """Medal position on the board."""

    @property
    def static(self) -> base.DDict:
        """Static data for this medal."""
        return self.client.assets.medal_table.medal_list[self.id]


class MedalBoardCustom(base.BaseModel):
    """Custom medal board layout."""

    layout: typing.Sequence[PlacedMedal]
    """Medals on the board."""


class MedalBoardTemplate(base.BaseModel):
    """Template medal board layout."""

    group_id: str = pydantic.Field(alias="groupId")
    """Medal board template ID."""
    medal_list: typing.Sequence[str] = pydantic.Field(alias="medalList")
    """Medal IDs on the board."""

    @property
    def static(self) -> base.DDict:
        """Static data for this medal board."""
        groups = self.client.assets.medal_table.medal_type_data.activity_medal.group_data
        return next(i for i in groups if i.group_id == self.group_id)


class MedalBoard(base.BaseModel):
    """Medal board info."""

    type: typing.Literal["CUSTOM", "TEMPLATE", "EMPTY"]
    """Medal board layout type."""
    custom: typing.Optional[MedalBoardCustom]
    """Custom medal board layout."""
    template: typing.Optional[MedalBoardTemplate]
    """Template medal board layout."""


class PartialPlayer(base.BaseModel):
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
    avatar_id: str = pydantic.Field(alias="avatarId", repr=False)
    """IDK. Always 0."""
    avatar: typing.Optional[Avatar] = None
    """Selected avatar."""
    assist_char_list: typing.Sequence[typing.Optional[AssistChar]] = pydantic.Field(alias="assistCharList")
    """Assist operator list."""
    last_online_time: base.ArknightsTimestamp = pydantic.Field(alias="lastOnlineTime")
    """Last online time."""
    medal_board: MedalBoard = pydantic.Field(alias="medalBoard")
    """Medal board."""


class Player(PartialPlayer):
    """Player info."""

    register_ts: base.ArknightsTimestamp = pydantic.Field(alias="registerTs")
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
    """Owned clues in the meeting room."""
    info_share: typing.Optional[base.ArknightsTimestamp] = pydantic.Field(alias="infoShare")
    """Last time clue exchange was activated."""
    recent_visited: bool = pydantic.Field(alias="recentVisited")
    """IDK. Whether the player base has recently been visited."""
    info_share_visited: typing.Optional[int] = pydantic.Field(None, alias="infoShareVisited")
    """IDK. Whether the last player base visit yielded any credit shop credits."""
