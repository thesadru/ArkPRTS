"""Arknights API battle models.

Any field description prefixed with IDK means it's just a guess.
"""

import datetime
import typing

import pydantic

from . import base


class Metadata(base.BaseModel):
    """Battle metadata shown for annihilation."""

    standard_play_time: float = pydantic.Field(alias="standardPlayTime")
    """Length of battle in seconds."""
    game_result: bool = pydantic.Field(alias="gameResult")
    """Whether victory was achieved."""
    save_time: datetime.datetime = pydantic.Field(alias="saveTime")
    """When the battle replay was recorded."""
    remaining_cost: int = pydantic.Field(alias="remainingCost")
    """Remaining DP."""
    remaining_life_point: int = pydantic.Field(alias="remainingLifePoint")
    """Remaining life points."""
    killed_enemies_cnt: int = pydantic.Field(alias="killedEnemiesCnt")
    """Amount of killed enemies."""
    missed_enemies_cnt: int = pydantic.Field(alias="missedEnemiesCnt")
    """Amount of leaked enemies."""
    level_id: str = pydantic.Field(alias="levelId")
    """Level ID in the format of Obt/Main/level_main_01-01."""
    stage_id: str = pydantic.Field(alias="stageId")
    """Stage ID in the format of main_01-01."""
    valid_killed_enemies_cnt: int = pydantic.Field(alias="validKilledEnemiesCnt")
    """Amount of killed enemies that count towards the kill count."""


class Character(base.BaseModel):
    """Character taken to the squad."""

    char_inst_id: int = pydantic.Field(alias="charInstId")
    """Instance ID of the character. Refer to user data."""
    skin_id: str = pydantic.Field(alias="skinId")
    """Skin ID."""
    tmpl_id: typing.Optional[str] = pydantic.Field(alias="tmplId", repr=False)
    """Chosen class for Amiya."""
    skill_id: str = pydantic.Field(alias="skillId")
    """Selected skill ID."""
    skill_index: int = pydantic.Field(alias="skillIndex")
    """Selected skill index."""
    skill_lvl: int = pydantic.Field(alias="skillLvl")
    """Skill level."""
    level: int
    """Character level."""
    phase: int
    """Character elite phase."""
    potential_rank: int = pydantic.Field(alias="potentialRank")
    """Character potential. Starts at 0."""
    favor_battle_phase: int = pydantic.Field(alias="favorBattlePhase")
    """Character trust percentage up to 100."""
    is_assist_char: bool = pydantic.Field(alias="isAssistChar")
    """Whether the character is an assist character. Should always be false."""
    uniequip_id: str = pydantic.Field(alias="uniequipId")
    """Selected module ID."""
    uniequip_level: int = pydantic.Field(alias="uniequipLevel")
    """Module level."""

    tmpl: typing.Mapping[str, base.DDict] = pydantic.Field(default_factory=base.DDict, repr=False)
    """Alternative operator class data. Only for Amiya."""
    variations: typing.Mapping[str, "Character"] = pydantic.Field(default_factory=dict, repr=False)
    """All representations of amiya."""


class Signature(base.BaseModel):
    """Object signature."""

    unique_id: int = pydantic.Field(alias="uniqueId")
    """Unique placement ID."""
    char_id: str = pydantic.Field(alias="charId")
    """Character or object ID."""

    @property
    def static(self) -> base.DDict:
        """Static data for this character."""
        return self.client.assets.char_table[self.char_id]


class Pos(base.BaseModel):
    """Position of the character 1,1 = bottom left (cartesian)."""

    row: int
    """Row starting from bottom as 1."""
    col: int
    """Column starting from left as 1."""


class Log(base.BaseModel):
    """Steps taken in the battle."""

    timestamp: float
    """Time in seconds since the battle started."""
    signiture: Signature
    """Character that took the step."""
    op: int
    """What the character did. 0 = deploy, 1 = retreat, 2 = skill."""
    direction: int
    """Direction the character is facing. 0 = up, 1 = right 2 = down, 3 = left."""
    pos: Pos
    """Position of the character 1,1 = bottom left (cartesian)."""


class Journal(base.BaseModel):
    """Battle replay record."""

    metadata: Metadata
    """General battle replay metadata."""
    squad: typing.Sequence[Character]
    """Squad used in the battle."""
    logs: typing.Sequence[Log]
    """Steps taken in the battle."""
    random_seed: int = pydantic.Field(alias="randomSeed")
    """Random seed used in the battle."""
    rune_list: typing.Any = pydantic.Field(alias="runeList")
    """IDK."""


class BattleReplay(base.BaseModel):
    """Battle replay model."""

    campaign_only_version: bool = pydantic.Field(alias="campaignOnlyVersion")
    """IDK."""
    timestamp: base.ArknightsTimestamp
    """When the battle replay was recorded."""
    journal: Journal
    """Battle replay record."""
