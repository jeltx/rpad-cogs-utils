"""
Parses limited time event data.

Data files can be different depending on the account; all 5 groups (and
potentially all 3 starters) need to be parsed and then deduped against
each other to get the full list.
"""

import json
import os
import time
from typing import Dict, List, Any

from ..common import pad_util
from ..common.pad_util import ghmult_plain, ghchance_plain
from ..common.shared_types import DungeonId, DungeonFloorId


# The typical JSON file name for this data.
FILE_NAME = 'download_limited_bonus_data_{}.json'


class Bonus(pad_util.JsonDictEncodable):
    """Basically any type of modifier text shown in a menu."""

    types = {
        # EXP multiplier.
        1: {'name': 'Exp Boost', 'mod_fn': ghmult_plain},

        # Coin multiplier.
        2: {'name': 'Coin Boost', 'mod_fn': ghmult_plain},

        # Drop rate increased.
        3: {'name': 'Drop Boost', 'mod_fn': ghmult_plain},

        # Stamina reduced.
        5: {'name': 'Stamina Reduction', 'mod_fn': ghmult_plain},

        # Special/co-op dungeon list.
        6: {'name': 'dungeon'},

        # PEM text.
        8: {'name': 'pem_event', },

        # REM text.
        9: {'name': 'rem_event', },

        # Current PEM pal point cost.
        10: {'name': 'pem_cost', 'mod_fn': int},

        # Feed XP modifier.
        11: {'name': 'Feed Exp Bonus Chance', 'mod_fn': ghmult_plain},

        # Increased plus rate 1?
        12: {'name': '+Egg Drop Rate 1', 'mod_fn': ghchance_plain},

        # ?
        14: {'name': 'gf_?', },

        # Increased plus rate 2?
        16: {'name': '+Egg Drop Rate 2', 'mod_fn': ghmult_plain},

        # Increased skillup chance
        17: {'name': 'Feed Skill-Up Chance', 'mod_fn': ghmult_plain},

        # "tourney is over, results pending"?
        20: {'name': 'tournament_active', },

        # "tourney is over, results pending"?
        21: {'name': 'tournament_closed', },

        # ?
        22: {'name': 'score_announcement', },

        # metadata?
        23: {'name': 'meta?', },

        # Gift dungeon with special text?
        # e.g. Mysterious Visitors dungeon with [+297] will be added to + Points message
        # Has a huge timestamp range, so reward probably
        24: {'name': 'gift_dungeon_with_reward', },

        # Seems to contain random text in the comment
        25: {'name': 'dungeon_special_event'},

        # Limited Time Dungeon arrives! (on multiplayer mode button)
        29: {'name': 'multiplayer_announcement'},

        # Multiplayer dungeon announcement?
        # TAMADRA Invades in Multiplayer Evo Rush!?
        31: {'name': 'multiplayer_dungeon_text'},

        # Tournament dungeon announcement?
        # Rank into the top 30% to get a Dragonbound, Rikuu
        32: {'name': 'tournament_text'},

        # Daily XP dragon
        36: {'name': 'daily_dragons'},

        37: {'name': 'monthly_quest_dungeon'},

        # Reward: Jewel of Creation
        # Latent TAMADRA (Skill Delay Resist.) invades guaranteed!
        39: {'name': 'dungeon_floor_text'},

        # https://bit.ly/2zWWGPd - #Q#6th Year Anniversary Quest 1
        43: {'name': 'monthly_quest_info'},
    }

    keys = 'sebiadmf'

    def __init__(self, raw: Dict[str, Any], server: str):
        if not set(raw) <= set(Bonus.keys):
            raise ValueError('Unexpected keys: ' + str(set(raw) - set(Bonus.keys)))

        # Start time as gungho time string
        self.start_time_str = str(raw['s'])
        self.start_timestamp = pad_util.gh_to_timestamp(self.start_time_str, server)

        # End time as gungho time string
        self.end_time_str = str(raw['e'])
        self.end_timestamp = pad_util.gh_to_timestamp(self.end_time_str, server)

        # Optional DungeonId
        self.dungeon_id = None  # type: DungeonId
        if 'd' in raw:
            self.dungeon_id = DungeonId(raw['d'])

        # Optional DungeonFloorId
        # Stuff like rewards text in monthly quests
        self.dungeon_floor_id = None  # type: DungeonFloorId
        if 'f' in raw:
            self.dungeon_floor_id = DungeonFloorId(raw['f'])

        # If REM/PEM, the ID of the machine
        self.egg_machine_id = None  # type: int
        if 'i' in raw:
            self.egg_machine_id = int(raw['i'])

        # Optional human-readable message (with formatting)
        self.message = None  # type: str
        # Optional human-readable message (no formatting)
        self.clean_message = None  # type: str
        if 'm' in raw:
            self.message = str(raw['m'])
            self.clean_message = pad_util.strip_colors(self.message)

        bonus_id = int(raw['b'])
        bonus_info = Bonus.types.get(bonus_id, {'name': 'unknown_id:{}'.format(bonus_id)})

        # Bonus value, if provided, optionally processed
        self.bonus_value = None  # type: number
        if 'a' in raw:
            self.bonus_value = raw['a']
            if 'mod_fn' in bonus_info:
                self.bonus_value = bonus_info['mod_fn'](self.bonus_value)

        # Human readable name for the bonus
        self.bonus_name = bonus_info['name']
        self.bonus_id = bonus_id

    def is_open(self):
        current_time = int(time.time())
        return self.start_timestamp < current_time and current_time < self.end_timestamp

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return 'Bonus({} - {} - {}/{})'.format(self.bonus_name, self.clean_message, self.dungeon_id, self.dungeon_floor_id)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def load_bonus_data(data_dir: str=None, data_group: str=None,
                    json_file: str=None, server: str=None) -> List[Bonus]:
    """Load Bonus objects from the PAD json file."""
    if json_file is None:
        json_file = os.path.join(data_dir, FILE_NAME.format(data_group))

    if not server:
        if '/na/' in json_file or '\\na\\' in json_file:
            server = 'na'
        elif '/jp/' in json_file or '\\jp\\' in json_file:
            server = 'jp'
        else:
            raise Exception('Server not supplied and not automatically detected from path')

    with open(json_file) as f:
        data_json = json.load(f)

    if data_json['v'] > 2:
        print('Warning! Version of bonus file is not tested: {}'.format(data_json['v']))

    return [Bonus(item, server) for item in data_json['bonuses']]
