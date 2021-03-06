"""
Parses card data.
"""

import json
import math
import os
from typing import List, Any

from ..common import pad_util
from ..common.shared_types import AttrId, CardId, SkillId, TypeId


# The typical JSON file name for this data.
FILE_NAME = 'download_card_data.json'


class Curve(pad_util.JsonDictEncodable):
    """Describes how to scale according to level 1-10."""

    def __init__(self,
                 min_value: int,
                 max_value: int=None,
                 scale: float=1.0,
                 max_level: int=10):
        self.min_value = min_value
        self.max_value = max_value or min_value * max_level
        self.scale = scale
        self.max_level = max(max_level, 1)

    def value_at(self, level: int):
        f = 1 if self.max_level == 1 else ((level - 1) / (self.max_level - 1))
        return self.min_value + (self.max_value - self.min_value) * math.pow(f, self.scale)


class EnemySkillRef(pad_util.JsonDictEncodable):
    """Describes how this monster uses an enemy skill"""

    def __init__(self, enemy_skill_id: int, enemy_ai: int, enemy_rnd: int):
        self.enemy_skill_id = enemy_skill_id
        self.enemy_ai = enemy_ai
        self.enemy_rnd = enemy_rnd


class Enemy(pad_util.JsonDictEncodable):
    """Describes how this monster spawns as an enemy."""

    def __init__(self,
                 turns: int,
                 hp: Curve,
                 atk: Curve,
                 defense: Curve,
                 max_level: int,
                 coin: Curve,
                 xp: Curve,
                 enemy_skill_refs: List[EnemySkillRef]):
        self.turns = turns
        self.hp = hp
        self.atk = atk
        self.defense = defense
        self.max_level = max_level
        self.coin = coin
        self.xp = xp
        self.enemy_skill_refs = enemy_skill_refs


class BookCard(pad_util.JsonDictEncodable):
    """Data about a player-ownable monster."""

    def __init__(self, raw: List[Any]):
        unflatten(raw, 57, 3, replace=True)
        unflatten(raw, 58, 1, replace=True)
#         unflatten(raw, 59, 1, replace=True)

        self.card_id = CardId(raw[0])
        self.name = str(raw[1])
        self.attr_id = AttrId(raw[2])
        self.sub_attr_id = AttrId(raw[3])
        self.is_ult = bool(raw[4])  # True if ultimate, False if normal evo
        self.type_1_id = TypeId(raw[5])
        self.type_2_id = TypeId(raw[6])
        self.rarity = int(raw[7])
        self.cost = int(raw[8])

        # Appears to be related to the size of the monster.
        # If 5, the monster always spawns alone. Needs more research.
        self.unknown_009 = int(raw[9])

        self.max_level = int(raw[10])
        self.feed_xp_at_lvl_4 = int(raw[11])
        self.released_status = raw[12] == 100
        self.sell_price_at_lvl_10 = raw[13]

        self.min_hp = int(raw[14])
        self.max_hp = int(raw[15])
        self.hp_scale = float(raw[16])

        self.min_atk = int(raw[17])
        self.max_atk = int(raw[18])
        self.atk_scale = float(raw[19])

        self.min_rcv = int(raw[20])
        self.max_rcv = int(raw[21])
        self.rcv_scale = float(raw[22])

        self.xp_max = int(raw[23])
        self.xp_scale = float(raw[24])

        self.active_skill_id = SkillId(raw[25])
        self.leader_skill_id = SkillId(raw[26])

        # Enemy turn timer for normal dungeons, and techs where enemy_turns_alt is not populated.
        self.enemy_turns = int(raw[27])

        # Min = lvl 1 and Max = lvl 10
        self.enemy_hp_min = int(raw[28])
        self.enemy_hp_max = int(raw[29])
        self.enemy_hp_scale = float(raw[30])

        self.enemy_atk_min = int(raw[31])
        self.enemy_atk_max = int(raw[32])
        self.enemy_atk_scale = float(raw[33])

        self.enemy_def_min = int(raw[34])
        self.enemy_def_max = int(raw[35])
        self.enemy_def_scale = float(raw[36])

        self.enemy_max_level = int(raw[37])
        self.enemy_coins_at_lvl_2 = int(raw[38])
        self.enemy_xp_at_lvl_2 = int(raw[39])

        self.ancestor_id = CardId(raw[40])

        self.evo_mat_id_1 = CardId(raw[41])
        self.evo_mat_id_2 = CardId(raw[42])
        self.evo_mat_id_3 = CardId(raw[43])
        self.evo_mat_id_4 = CardId(raw[44])
        self.evo_mat_id_5 = CardId(raw[45])

        self.un_evo_mat_1 = CardId(raw[46])
        self.un_evo_mat_2 = CardId(raw[47])
        self.un_evo_mat_3 = CardId(raw[48])
        self.un_evo_mat_4 = CardId(raw[49])
        self.un_evo_mat_5 = CardId(raw[50])

        # When >0, the enemy turn timer for technical dungeons.
        self.enemy_turns_alt = int(raw[51])

        self.unknown_052 = raw[52]

        # Usage modified by enemy_skill_effect_type.
        self.enemy_skill_effect = int(raw[53])

        # The vast majority of these are:
        # 0: (unknown atm; lot of monsters have this, with large numbers or bitmaps in 53)
        # 1: Use 53 as countdown, when expired reset one-time skills.
        # 2: (not sure, only used for deus ex machina, has 53=2)
        # 5: (only used by a monster that never appears in a dungeon)
        # 7: (not sure, only used by kanna, 53=7 as well)
        self.enemy_skill_effect_type = int(raw[54])

        # Boolean, unlikely to be anything useful, only populated for 495 and 111.
        self.unknown_055 = raw[55]

        # Unused
        self.unknown_056 = raw[56]

        # self.enemy_skills = raw[57]
        self.enemy_skill_refs = [EnemySkillRef(
            int(raw[57][i]), raw[57][i + 1], raw[57][i + 2]) for i in range(0, len(raw[57]) - 2, 3)]

        self.awakenings = raw[58]  # List[int]
        self.super_awakenings = list(map(int, filter(str.strip, raw[59].split(','))))  # List[int]

        self.base_id = CardId(raw[60])  # ??
        self.group_id = raw[61]  # ??
        self.type_3_id = TypeId(raw[62])

        self.sell_mp = int(raw[63])
        self.latent_on_feed = int(raw[64])
        self.collab_id = int(raw[65])

        self.random_flags = raw[66]
        self.inheritable = bool(self.random_flags & 1)
        self.is_collab = bool(self.random_flags & 4)

        self.furigana = str(raw[67])  # JP data only?
        self.limit_mult = int(raw[68])

        self.voice_id = int(raw[69])  # Number of the voice file, 1-indexed, 0 if no voice

        self.other_fields = raw[70:]

    def enemy(self):
        return Enemy(self.enemy_turns,
                     Curve(self.enemy_hp_min,
                           self.enemy_hp_max,
                           self.enemy_hp_scale,
                           self.enemy_max_level),
                     Curve(self.enemy_atk_min,
                           self.enemy_atk_max,
                           self.enemy_atk_scale,
                           self.enemy_max_level),
                     Curve(self.enemy_def_min,
                           self.enemy_def_max,
                           self.enemy_def_scale,
                           self.enemy_max_level),
                     self.enemy_max_level,
                     Curve(self.enemy_coins_at_lvl_2 / 2,
                           max_level=self.enemy_max_level),
                     Curve(self.enemy_xp_at_lvl_2 / 2,
                           max_level=self.enemy_max_level),
                     self.enemy_skill_refs)

    def hp_curve(self):
        return Curve(self.min_hp, self.max_hp, self.hp_scale)

    def atk_curve(self):
        return Curve(self.min_atk, self.max_atk, self.atk_scale)

    def rcv_curve(self):
        return Curve(self.min_rcv, self.max_rcv, self.rcv_scale)

    def xp_curve(self):
        return Curve(0, self.xp_max, self.xp_scale)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return 'Card({} - {})'.format(self.card_id, self.name)


def unflatten(raw: List[Any], idx: int, width: int, replace: bool=False):
    """Unflatten a card array.

    Index is the slot containing the item count.
    Width is the number of slots per item.
    If replace is true, values are moved into an array at idx.
    If replace is false, values are deleted.
    """
    item_count = raw[idx]
    if item_count == 0:
        if replace:
            raw[idx] = list()
            return

    data_start = idx + 1
    flattened_item_count = width * item_count
    flattened_data_slice = slice(data_start, data_start + flattened_item_count)

    data = list(raw[flattened_data_slice])
    del raw[flattened_data_slice]

    if replace:
        raw[idx] = data


def load_card_data(data_dir: str=None, card_json_file: str=None) -> List[BookCard]:
    """Load BookCard objects from PAD JSON file."""
    if card_json_file is None:
        card_json_file = os.path.join(data_dir, FILE_NAME)

    with open(card_json_file) as f:
        card_json = json.load(f)

    if card_json['v'] > 1600:
        print('Warning! Version of card file is not tested: {}'.format(card_json['v']))

    return [BookCard(r) for r in card_json['card']]
