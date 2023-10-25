from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
import requests

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

#Heuristics
def e(game:Game)->int:
    '''choose and call heuristic based on game options'''
    if game.options.heuristic == 0:        
        return e0(game)
    elif game.options.heuristic == 1:        
        return e1(game)
    elif game.options.heuristic == 2:        
        return e2(game)
    else:
        return e0(game)


def e0(game) -> int:
    '''This heuristic give score to each player by rewarding the number and type of units'''
    count_attacker=0
    for (_,unit) in game.player_units(Player.Attacker):
        if unit.type in {UnitType.Virus, UnitType.Tech,UnitType.Firewall,UnitType.Program}:
            count_attacker+=3
        elif unit.type == UnitType.AI:
            count_attacker+=9999
    count_defender=0
    for (_,unit) in game.player_units(Player.Defender):
        if unit.type in {UnitType.Virus, UnitType.Tech,UnitType.Firewall,UnitType.Program}:
            count_defender+=3
        elif unit.type == UnitType.AI:
            count_defender+=9999
    return count_attacker-count_defender


def e1(game) -> int:
    '''This heuristic give score to each player by rewarding the number, type and healths of units'''
    count_attacker=0
    for (_,unit) in game.player_units(Player.Attacker):
        if unit.type in {UnitType.Virus, UnitType.Tech,UnitType.Firewall,UnitType.Program}:
            count_attacker+=3*unit.health
        elif unit.type == UnitType.AI:
            count_attacker+=999*unit.health
    count_defender=0
    for (_,unit) in game.player_units(Player.Defender):
        if unit.type in {UnitType.Virus, UnitType.Tech,UnitType.Firewall,UnitType.Program}:
            count_defender+=3*unit.health     
        elif unit.type == UnitType.AI:            
            count_defender+=999*unit.health
    return count_attacker-count_defender

def e2(game:Game) -> int:
    '''This heuristic give score to each player by rewarding: 
            - The number of units
            - The type of units
            - The healths of units
            - The danger risk given by surrounding adversary units
            - The defense effect of friendly units surrounding the AI unit
            - The repair effect of friendly units   
    '''
    
    count_attacker=0                        
    count_defender=0
    
    count_attacker = helper_e2(game,Player.Attacker)
    count_defender = helper_e2(game,Player.Defender)

    return count_attacker-count_defender


def helper_e2(game:Game, player:Player) -> int:
    '''Calculation of score e2 by player'''
    count=0
    for (coord,unit) in game.player_units(player):
        if unit.type in {UnitType.Firewall,UnitType.Program}:
            count+=3*unit.health
        elif unit.type in {UnitType.Virus, UnitType.Tech}:
            count+=9*unit.health
        elif unit.type == UnitType.AI:
            count+=99999*unit.health

        for coord_adj in coord.iter_range(1):
            unit_adj = game.get(coord_adj)
            #If in danger reduce score
            #If there is an adversary closed to the unit
            if(unit_adj is not None and unit_adj.player != game.next_player):
                #It can kill the unit then unit is in danger
                if (unit_adj.damage_amount(unit) >= unit.health):
                    if unit.type in {UnitType.Firewall,UnitType.Program}:
                        count-=2*unit.health
                    elif unit.type in {UnitType.Virus, UnitType.Tech}:
                        count-=5*unit.health
                    elif unit.type == UnitType.AI:
                        count-=9999*unit.health
            #if the unit is surronded by friendly units          
            elif(unit_adj is not None and unit_adj.player == game.next_player):
                #for every friendly unit adjacent to the AI increase score
                if unit.type == UnitType.AI:
                        count+=999
                #If this friendly adjacent unit can repair the increase score
                repair = unit_adj.repair_amount(unit)
                if ( repair > 0 and unit.health<9):
                    if unit.type in {UnitType.Firewall,UnitType.Program}:
                        count+=2*repair
                    elif unit.type in {UnitType.Virus, UnitType.Tech}:
                        count+=5*repair
                    elif unit.type == UnitType.AI:
                        count+=9999*repair            
    return count    

class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4


class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker


class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3


##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health: int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table: ClassVar[list[list[int]]] = [
        [3, 3, 3, 3, 1],  # AI
        [1, 1, 6, 1, 1],  # Tech
        [9, 6, 1, 6, 1],  # Virus
        [3, 3, 3, 3, 1],  # Program
        [1, 1, 1, 1, 1],  # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table: ClassVar[list[list[int]]] = [
        [0, 1, 1, 0, 0],  # AI
        [3, 0, 0, 3, 3],  # Tech
        [0, 0, 0, 0, 0],  # Virus
        [0, 0, 0, 0, 0],  # Program
        [0, 0, 0, 0, 0],  # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0

    def mod_health(self, health_delta: int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"

    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()

    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount


##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row: int = 0
    col: int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
            coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
            coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string() + self.col_string()

    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()

    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row - dist, self.row + 1 + dist):
            for col in range(self.col - dist, self.col + 1 + dist):
                yield Coord(row, col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row - 1, self.col)
        yield Coord(self.row, self.col - 1)
        yield Coord(self.row + 1, self.col)
        yield Coord(self.row, self.col + 1)

    @classmethod
    def from_string(cls, s: str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
            s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None


##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src: Coord = field(default_factory=Coord)
    dst: Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string() + " " + self.dst.to_string()

    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row, self.dst.row + 1):
            for col in range(self.src.col, self.dst.col + 1):
                yield Coord(row, col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0, col0), Coord(row1, col1))

    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0, 0), Coord(dim - 1, dim - 1))

    @classmethod
    def from_string(cls, s: str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
            s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None


##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth: int | None = 4
    min_depth: int | None = 2
    max_time: float | None = 5.0
    max_time_adjusted: float | None = 5.0
    game_type: GameType = GameType.AttackerVsDefender
    alpha_beta: bool = True
    max_turns: int | None = 100
    randomize_moves: bool = True
    broker: str | None = None
    heuristic: int = 0

##############################################################################################################

@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth: dict[int, int] = field(default_factory=dict)
    total_seconds: float = 0.0
    average_branching_factor: float = 0.0
    average_branching_size: int = 0


##############################################################################################################

@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker
    turns_played: int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai: bool = True
    _defender_has_ai: bool = True

    actions: list[str] = field(default_factory=list)  # Store game actions
    #indicate if a suggestion move in progress is time out
    is_time_out: bool = False
    current_start_time: datetime = field(init=False)
    current_depth : int = 0

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""

        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim - 1
        self.set(Coord(0, 0), Unit(player=Player.Defender, type=UnitType.AI)),
        self.set(Coord(1, 0), Unit(player=Player.Defender, type=UnitType.Tech)),
        self.set(Coord(0, 1), Unit(player=Player.Defender, type=UnitType.Tech)),
        self.set(Coord(2, 0), Unit(player=Player.Defender, type=UnitType.Firewall)),
        self.set(Coord(0, 2), Unit(player=Player.Defender, type=UnitType.Firewall)),
        self.set(Coord(1, 1), Unit(player=Player.Defender, type=UnitType.Program)),
        self.set(Coord(md, md), Unit(player=Player.Attacker, type=UnitType.AI)),
        self.set(Coord(md - 1, md), Unit(player=Player.Attacker, type=UnitType.Virus)),
        self.set(Coord(md, md - 1), Unit(player=Player.Attacker, type=UnitType.Virus)),
        self.set(Coord(md - 2, md), Unit(player=Player.Attacker, type=UnitType.Program)),
        self.set(Coord(md, md - 2), Unit(player=Player.Attacker, type=UnitType.Program)),
        self.set(Coord(md - 1, md - 1), Unit(player=Player.Attacker, type=UnitType.Firewall)),

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord: Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord: Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord: Coord, unit: Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord, None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord: Coord, health_delta: int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def is_valid_move(self, coords: CoordPair) -> bool:
        """Validate a move expressed as a CoordPair"""
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        unit = self.get(coords.src)
        if unit is None or unit.player != self.next_player:
            return False
        unit = self.get(coords.dst)
        
        #Verify free destination
        if unit is not None:
            return False
               
        #Verify move up or left
        unit = self.get(coords.src)
        if unit.player == Player.Attacker:
            if unit.type in {UnitType.AI, UnitType.Firewall, UnitType.Program}:
                if coords.dst.row > coords.src.row or coords.dst.col > coords.src.col:
                    return False 

        #Verify move down or right
        if unit.player == Player.Defender:
            if unit.type in {UnitType.AI, UnitType.Firewall, UnitType.Program}:
                if coords.dst.row < coords.src.row or coords.dst.col < coords.src.col:
                    return False
                
        #Verify engagment in combat 
        for adj_coord in coords.src.iter_adjacent():
            adj_unit = self.get(adj_coord)
            if unit.type in {UnitType.AI, UnitType.Firewall, UnitType.Program} and adj_unit is not None and adj_unit.player!=unit.player:
                return False
            
        #verify it is adjacent to prevent diagonal move and more than one unit move
        for adj_coord in coords.src.iter_adjacent():            
            if coords.dst == adj_coord:
                return True
                        
        return False  

    def is_valid_attack(self, coords: CoordPair) -> bool:
        """Validate if a move is a valid attack"""
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        unit_s = self.get(coords.src)
        unit_t = self.get(coords.dst)
        # validate if s and t are adversaries
        if unit_s is None or unit_t is None:
            return False
        if unit_s.player == unit_t.player:
            return False
        # Validate if T is adjacent to S
        for adj in coords.src.iter_adjacent():
            if coords.dst == adj:
                return True
        return False

    def is_valid_repair(self, coords: CoordPair) -> bool:
        """Validate if a move is a valid repair"""
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        unit_s = self.get(coords.src)
        unit_t = self.get(coords.dst)
        if unit_s is None or unit_t is None:
            return False
        # validate if s and t are friendly
        if unit_s.player != unit_t.player:
            return False
        # validate if S can repair T
        repair_on_t = unit_s.repair_amount(unit_t)
        if repair_on_t == 0:
            return False
        # Validate if T is adjacent to S
        for adj in coords.src.iter_adjacent():
            if coords.dst == adj:
                return True
        return False

    def can_self_destruct(self, coords: CoordPair) -> bool:
        """Validate for self-destruction"""
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        unit = self.get(coords.src)
        if unit is None:
            return False
        if coords.src == coords.dst:
            return True
        return False

    def perform_move(self, coords: CoordPair) -> Tuple[bool, str]:
        """Validate and perform a move expressed as a CoordPair."""
        if self.is_valid_move(coords):
            self.set(coords.dst, self.get(coords.src))
            self.set(coords.src, None)
            action_taken_str = f"{self.next_player.name} - turn #{self.turns_played+1}: move {coords.src} -> {coords.dst}"            
            return (True, action_taken_str)

        elif self.is_valid_attack(coords):
            unit_s = self.get(coords.src)
            unit_t = self.get(coords.dst)
            damage_on_t = unit_s.damage_amount(unit_t)
            damage_on_s = unit_t.damage_amount(unit_s)
            self.mod_health(coords.src, -damage_on_s)
            self.mod_health(coords.dst, -damage_on_t)
            action_taken_str = f"{self.next_player.name} - turn #{self.turns_played+1}: attack {coords.src} -> {coords.dst}"
            return (True, action_taken_str)

        elif self.is_valid_repair(coords):
            unit_s = self.get(coords.src)
            unit_t = self.get(coords.dst)
            repair_on_t = unit_s.repair_amount(unit_t)
            self.mod_health(coords.dst, repair_on_t)
            action_taken_str = f"{self.next_player.name} - turn #{self.turns_played+1}: repair {coords.src} -> {coords.dst}"
            return (True, action_taken_str)
        elif self.can_self_destruct(coords):
            self.mod_health(coords.src, -9)
            for surrounding_coord in coords.src.iter_range(1):
                self.mod_health(surrounding_coord, -2)
            action_taken_str = f"{self.next_player.name} - turn #{self.turns_played+1}: self-destruct {coords.src} -> {coords.dst}"            
            return (True, action_taken_str)
        
        action_taken_str = f"{self.next_player.name} performed an invalid move {coords.src} -> {coords.dst}"
        return (False, action_taken_str)

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output
    
    def get_configuration(self) -> str:
        """Pretty text representation of the game configuration."""
        dim = self.options.dim
        output = ""      
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()

    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')

    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success, result) = self.perform_move(mv)
                    self.actions.append(result)
                    print(f"Broker {self.next_player.name}: ", end='')                    
                    print(result)                    
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success, result) = self.perform_move(mv)
                self.actions.append(result)
                if success:
                    print(f"Player {self.next_player.name}: ", end='')
                    print(result)
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is not None:
            (success, result) = self.perform_move(mv)
            self.actions.append(result)
            if success:
                print(f"Computer {self.next_player.name}: ", end='')
                print(result)
                self.next_turn()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord, Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord, unit)

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        if self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker    
        return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src, _) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def get_children(self) -> Iterable[Tuple[Game,CoordPair]]:
        """Generate valid game state candidates from a parent"""
        move = CoordPair()        
        for (src, _) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                nodeClone = self.clone()
                (success,_) = nodeClone.perform_move(move.clone())
                if success:
                    nodeClone.next_turn()
                    yield (nodeClone.clone(),move.clone())

            #selfmove
            move.dst = src
            nodeClone = self.clone()
            (success,_) = nodeClone.perform_move(move)
            if success:
                nodeClone.next_turn()
                yield (nodeClone.clone(),move)


    def random_move(self) -> Tuple[int, CoordPair | None]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0])
        else:
            return (0, None)
    
  
    def alpha_beta_move(self) -> Tuple[int, CoordPair | None]:
        """Alpha beta move"""
        origin = self
        max_depth = self.options.max_depth
        alpha = MIN_HEURISTIC_SCORE
        beta = MAX_HEURISTIC_SCORE
        maximizingPlayer = origin.next_player==Player.Attacker
        
        #Iterate depth from 1 to max_depth if time permit
        #The loop will be interrupted if the max_time is up
        #Each depth will give a better move and score        
        for depth in range(1,max_depth+1):
            self.current_depth = depth
            (score, move) = self.alpha_beta(origin, depth, alpha, beta , maximizingPlayer)
            if self.is_time_out:
                self.is_time_out = False                
                return (best_score, best_move)
            else:            
                (best_score, best_move) = (score,move)
                
        return (best_score, best_move)
    
    def alpha_beta(self, node:Game ,depth:int, alpha:int, beta:int, maximizingPlayer:bool) -> Tuple[int,CoordPair]:
        
        #Validate if time is up
        elapsed_seconds = (datetime.now() - self.current_start_time).total_seconds()
        if(elapsed_seconds >= self.options.max_time_adjusted):
            self.is_time_out = True
            #Interrupt process
            return (0,None)

        #If node has_winner it's an end node
        if depth==0 or node.is_finished():
            #add one count to the eval for the current depth in progress
            self.update_evaluations_per_depth()         
            return (e(node),None)
              
        if maximizingPlayer:

            value_bestmove = (MIN_HEURISTIC_SCORE,None)
            
            branch_factor=0
            for (child,move) in node.get_children():
                branch_factor+=1
                #store the alpha_beta evaluation value
                (alpha_beta_result,_) = self.alpha_beta(child, depth-1,alpha, beta, False)
                #check time_out and break
                if(self.is_time_out):
                    return (alpha_beta_result,_)
                #update value with max(alpha_beta_result,value_bestmove[0]) and best move
                if(alpha_beta_result > value_bestmove[0]):
                    value_bestmove = (alpha_beta_result,move)
                #update alpha with max(value_bestmove[0],alpha)    
                if(value_bestmove[0] > alpha):
                    alpha = value_bestmove[0]
                #pruning
                if beta <= alpha:
                    break
            self.update_average_branching(branch_factor)
            return value_bestmove        
        else:
            value_bestmove = (MAX_HEURISTIC_SCORE,None)

            for (child,move) in node.get_children():
                branch_factor=0
                #store the alpha_beta evaluation value
                (alpha_beta_result,_) = self.alpha_beta(child, depth-1,alpha, beta, True)
                #check time_out
                if(self.is_time_out):
                    return (alpha_beta_result,_)
                #update value with min(alpha_beta_result,value_bestmove[0]) and the best move
                if(alpha_beta_result < value_bestmove[0]):
                    value_bestmove = (alpha_beta_result, move)                    
                #update beta with min(value_bestmove[0],beta)
                if(value_bestmove[0] < beta):
                    beta = value_bestmove[0]
                #pruning
                if beta <= alpha:
                    break
            self.update_average_branching(branch_factor)    
            return value_bestmove
    
    def minimax(self,game:Game, depth:int, maximizing_player:bool)->Tuple[int,CoordPair]:
        '''minmax algorithm'''                
        #Validate if time is up
        elapsed_seconds = (datetime.now() - self.current_start_time).total_seconds()
        if(elapsed_seconds >= self.options.max_time_adjusted):
            self.is_time_out = True
            return (0,None)
        
        if depth == 0 or game.is_finished():
            self.update_evaluations_per_depth()
            return (e(game),None)

        if maximizing_player:
            max_eval = MIN_HEURISTIC_SCORE
            best_move = None

            branch_factor=0
            for(child, move) in game.get_children():
                branch_factor+=1

                (eval,_) = self.minimax(child, depth - 1, False)
                #check time_out
                if(self.is_time_out):
                    return (eval,_)
                #update max eval and best move   
                if(eval > max_eval):
                    max_eval = eval
                    best_move = move

            self.update_average_branching(branch_factor)
            return (max_eval, best_move)
        else:            
            min_eval = MAX_HEURISTIC_SCORE
            best_move = None

            branch_factor=0
            for(child, move) in game.get_children():
                branch_factor+=1
                (eval,_) = self.minimax(child, depth - 1, True)

                #check time_out
                if(self.is_time_out):
                    return (eval,_)
                #update min eval and best move
                if( eval < min_eval):
                    min_eval = eval
                    best_move = move
            self.update_average_branching(branch_factor)
            return ( min_eval, best_move)


    def minimax_move(self) -> Tuple[int, CoordPair | None]:
        '''Minimax move'''        
        #Attacker is max player and defender is min
        maximizing_player = self.next_player==Player.Attacker
        max_depth = self.options.max_depth
        
        #Iterate depth from 1 to max_depth if time permit
        #The loop will be interrupted if the max_time is up
        #Each depth will give a better move and score
        for depth in range(1,max_depth+1):
            self.current_depth = depth
            (score, move) = self.minimax(self, depth,maximizing_player)
            if self.is_time_out:
                self.is_time_out = False                
                return (best_score, best_move)
            else:            
                (best_score, best_move) = (score,move)
        
        return (best_score, best_move)

    def update_average_branching(self, branch_factor):
        '''update average branching'''
        self.stats.average_branching_factor = (self.stats.average_branching_factor*self.stats.average_branching_size + branch_factor) / (self.stats.average_branching_size+1)
        self.stats.average_branching_size +=1
    
    def update_evaluations_per_depth(self):
        '''Add 1 count to the evaliation at depth'''
        #initialize depth in dictionary
        if self.stats.evaluations_per_depth.get(self.current_depth) is None:
                self.stats.evaluations_per_depth[self.current_depth] = 0
        #update evaluation to current depth by adding one
        self.stats.evaluations_per_depth[self.current_depth] += 1
    
    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta."""
        start_time = datetime.now()

        self.current_start_time = start_time
        
        if self.options.alpha_beta:            
            (score, move) = self.alpha_beta_move()
        #minimax
        else:
            (score, move) = self.minimax_move()

        #Calculate time used by computer to suggest the move
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds

        
        print(f"Heuristic score: {score}")
        self.actions.append(f"Heuristic score: {score}")
        
        total_evals = sum(self.stats.evaluations_per_depth.values())
        print(f"Cumulative evals: {total_evals}")
        self.actions.append(f"Cumulative evals: {total_evals}")

        print(f"Evals per depth: ", end='')
        evals_per_depth_output = "Cumulative evals by depth: "
        evals_per_depth_percentage_output = "Cumulative % evals by depth: "
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            print(f"{k}:{self.stats.evaluations_per_depth[k]} ", end='')
            evals_per_depth_output += f"{k}:{self.stats.evaluations_per_depth[k]} "
            evals_per_depth_percentage_output += f"{k}:{round((self.stats.evaluations_per_depth[k]/total_evals)*100,2)} % "            
        print()

        self.actions.append(evals_per_depth_output)
        self.actions.append(evals_per_depth_percentage_output)
        print(evals_per_depth_percentage_output)
        
        if self.stats.total_seconds > 0:
            print(f"Eval perf.: {total_evals / self.stats.total_seconds / 1000:0.1f}k/s")
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        self.actions.append(f"Time for this action : {elapsed_seconds:0.1f}s")
        average_branching_factor_output = f"Average branching factor: {round(self.stats.average_branching_factor,2)}"
        print(average_branching_factor_output)
        self.actions.append(average_branching_factor_output)
        return move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played + 1:
                        move = CoordPair(
                            Coord(data['from']['row'], data['from']['col']),
                            Coord(data['to']['row'], data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None


##############################################################################################################

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default='manual', help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    parser.add_argument('--alpha_beta', type=str, default='true', help='true for alphabeta, false for minmax')
    parser.add_argument('--heuristic', type=int, default=0,help='Heuristic: 0|1|2')

    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker    
    if args.heuristic is not None:
        options.heuristic = args.heuristic


    if args.alpha_beta is not None:
        alpha_beta_str = args.alpha_beta
        if alpha_beta_str.lower() in ('true', 't'):
            options.alpha_beta = True
        elif alpha_beta_str.lower() in ('false', 'f'):
            options.alpha_beta = False

    #adjust time -- provide room to return values in case of running out of time
    max_time_adjustment_ms = 49
    #Adjust time with room
    options.max_time_adjusted = options.max_time - max_time_adjustment_ms/1000

    
    # Create an empty list to store game actions
    game_actions = []

    # create a new game
    game = Game(options=options)

    # the main game loop
    while True:
        print()
        print(game)
        #add configuration for output file to the list
        game.actions.append(game.get_configuration())

        winner = game.has_winner()
        if winner is not None:
            print(f"{winner.name} wins!")
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn()
        else:
            player = game.next_player
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)

    # Append the actions taken in this turn to the list
    game_actions.extend(game.actions)

    max_time_str = str(options.max_time)
    game_type_str = str(options.game_type)
    max_turns_str = str(options.max_turns)

    
    P1 = "max_time: " + max_time_str + "\n"
    P2 = "max_turns: " + max_turns_str + "\n"

    if(game.options.alpha_beta):
        alpha_beta_output = "\nalpha-beta is on"
    else:
        alpha_beta_output = "\nalpha-beta is off"

    if game_type == GameType.AttackerVsComp:
        P3 = alpha_beta_output
        P4 = "\ngame_type: Player1 = H, Player2 = AI" + "\n"
        P5 = f"\nHeuristic e{options.heuristic}"
    elif game_type == GameType.CompVsDefender:
        P3 = alpha_beta_output
        P4 = "\ngame_type: Player1 = AI, Player2 = H" + "\n"
        P5 = f"\nHeuristic e{options.heuristic}"
    elif game_type == GameType.AttackerVsDefender:
        P3 = ""
        P4 = "\ngame_type: Player1 = H, Player2 = H" + "\n"
        P5 = ""
    elif game_type == GameType.CompVsComp:
        P3 = alpha_beta_output
        P4= "\ngame_type: Player1 = AI, Player2 = AI" + "\n"
        P5 = f"\nHeuristic e{options.heuristic}"

    
    P6 =  winner.name + " wins in " + str(game.turns_played) + " turns"


    output_file_name = f"gameTrace-{str(game.options.alpha_beta).lower()}-{game.options.max_time}-{game.options.max_turns}.txt"
    with open(output_file_name, 'w') as output_file:
        output_file.write("The game parameters" + "\n" + "\n")
        output_file.write(P1 + P2 + P3 + P4 + P5 + "\n" + "\n")

        output_file.write("Initial Board Configuration" + "\n" + "\n")
        for action in game_actions:
            output_file.write(action + "\n")

        output_file.write("\n" + "\n")
        output_file.write(P6)

        # Close the output file
    output_file.close()


##############################################################################################################

if __name__ == '__main__':
    main()
