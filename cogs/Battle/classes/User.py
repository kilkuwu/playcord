from utils.constants import USERS_DB as DB
from bson.int64 import Int64
from .Inventory import Inventory
from .SkillSet import SkillSet
from queue import Empty, Queue
import random


class FightingUser:
    def __init__(self, player: 'User') -> None:
        self.player = player
        self._damage = player.damage
        self._true_damage = player.true_damage
        self._health = player.health
        self._strength = player.strength
        self._speed = player.speed
        self._defense = player.defense
        self._true_defense = player.true_defense
        self._crit_chance = player.crit_chance
        self._crit_damage = player.crit_damage
        self.damage_multiplier = 1
        self.true_damage_multiplier = 1
        self.health_multiplier = 1
        self.strength_multiplier = 1
        self.speed_multiplier = 1
        self.defense_multiplier = 1
        self.true_defense_multiplier = 1
        self.crit_chance_multiplier = 1
        self.crit_damage_multiplier = 1
        self.effect_queue = Queue()

    @property
    def damage(self):
        return self._damage*self.damage_multiplier

    @property
    def true_damage(self):
        return self._true_damage*self.true_damage_multiplier

    @property
    def health(self):
        return self._health*self.health_multiplier
    
    @health.setter
    def health(self, value):
        self._health = value/self.health_multiplier
    
    @property
    def strength(self):
        return self._strength*self.strength_multiplier

    @property
    def speed(self):
        return self._speed*self.speed_multiplier

    @property
    def defense(self):
        return self._defense*self.defense_multiplier

    @property
    def true_defense(self):
        return self._true_defense*self.true_defense_multiplier

    @property
    def crit_chance(self):
        return self._crit_chance*self.crit_chance_multiplier

    @property
    def crit_damage(self):
        return self._crit_damage*self.crit_damage_multiplier
    
    def turn(self):
        try:
            callback = self.effect_queue.get()
            callback(self)
        except Empty:
            pass

    def get_damage(self):
        damage = self.damage*(1+1.0*self.strength/100)
        true_damage = self.true_damage
        is_crit = self.crit_chance > random.random()*100
        if is_crit:
            damage *= (1+self.crit_damage/100)
            true_damage *= (1+self.crit_damage/100)
        return is_crit, damage, self.true_damage

    def attack(self, opponent: 'FightingUser'):
        has_dodged = opponent.dodge(self)
        if has_dodged:
            return True, False, 0.0, 0.0
        is_crit, damage, true_damage = self.get_damage()
        damage_dealt, reduced_damage = opponent.receive_damage(
            damage, true_damage, is_crit)
        self.player.inventory.trigger_special_effect(is_crit, damage_dealt, reduced_damage, self, opponent)
        return False, is_crit, damage_dealt, reduced_damage

    def receive_damage(self, damage, true_damage=0, is_crit=False):
        reduced_damage = 0.0
        if not is_crit:
            reduced_damage = (1.0*damage*self.defense)/(self.defense+100)
            damage -= reduced_damage
        reduced_true_damage = (
            1.0*true_damage*self.true_defense)/(self.true_defense+100)
        true_damage -= reduced_true_damage
        self.health = max(0, self.health-damage)
        self.health = max(0, self.health-true_damage)
        return damage+true_damage, reduced_damage

    def dodge(self, opponent: 'FightingUser'):
        return self.speed/opponent.speed+random.random() > 2


class User:
    BASE_DAMAGE = 5

    def __init__(self, user) -> None:
        self.user = user
        self._id = user.id
        self._exp = Int64(0)
        self._health = 100
        self._strength = 0
        self._speed = 100
        self._defense = 0
        self._true_defense = 0
        self._crit_chance = 30
        self._crit_damage = 50
        self._skill_points = 0
        self.sayings = ['Yeet!', 'Swoosh!']
        self.inventory = Inventory()
        self.skills = SkillSet()

    @classmethod
    def from_data(cls, user, data: dict):
        user = cls(user)
        user._exp = data['exp']
        user._health = data['health']
        user._strength = data['strength']
        user._speed = data['speed']
        user._defense = data['defense']
        user._true_defense = data['true_defense']
        user._crit_chance = data['crit_chance']
        user._crit_damage = data['crit_damage']
        user._skill_points = data['skill_points']
        user.sayings = data['sayings']
        user.inventory = Inventory.from_data(data['inventory'])
        user.skills = SkillSet.from_data(data['skills'])
        return user

    def get_fighting(self):
        return FightingUser(self)

    def update_all(self):
        user = {
            '_id': self._id,
            'exp': self._exp,
            'health': self._health,
            'strength': self._strength,
            'speed': self._speed,
            'defense': self._defense,
            'true_defense': self._true_defense,
            'crit_chance': self._crit_chance,
            'crit_damage': self._crit_damage,
            'skill_points': self._skill_points,
            'sayings': self.sayings,
            'inventory': self.inventory.dict(),
            'skills': self.skills.dict()
        }
        DB.replace_one({'_id': self._id}, user, True)
    
    def update_sayings(self):
        DB.update_one({'_id': self._id}, {'$set': {'sayings': self.sayings}})

    def update_inventory(self):
        DB.update_one({'_id': self._id}, {'$set': {'inventory': self.inventory.dict()}})

    def update_skills(self):
        DB.update_one({'_id': self._id}, {'$set': {'sayings': self.skills}})

    @property
    def exp(self):
        return self._exp

    @exp.setter
    def exp(self, _exp):
        self._exp = Int64(_exp)
        DB.update_one({'_id': self._id}, {'$set': {'exp': self._exp}})

    @property
    def health(self):
        return self._health + self.inventory.health

    @property
    def strength(self):
        return self._strength + self.inventory.strength

    @property
    def speed(self):
        return self._speed + self.inventory.speed

    @property
    def defense(self):
        return self._defense + self.inventory.defense

    @property
    def true_defense(self):
        return self._true_defense + self.inventory.true_defense

    @property
    def crit_chance(self):
        return self._crit_chance + self.inventory.crit_chance

    @property
    def crit_damage(self):
        return self._crit_damage + self.inventory.crit_damage

    @property
    def damage(self):
        return self.BASE_DAMAGE + self.inventory.damage

    @property
    def true_damage(self):
        return self.inventory.true_damage
