from re import A
from typing import List
from cogs.Battle.classes.Inventory.item.weapons._Weapon import _Weapon
from cogs.Battle.classes.Inventory.item.defensives._Defensive import _Defensive
from cogs.Battle.classes.Inventory.item.armors._Armor import _Helmet, _Chestplate, _Leggings, _Boots
from cogs.Battle.classes.Inventory.item.accessories._Accessory import _Accessory
from cogs.Battle.classes.Inventory.item import _Item, Stick, LeatherHelmet, LeatherChestplate, LeatherLeggings, LeatherBoots, defensives, get_item, get_default_item_by_name
from discord.ext.commands import BadArgument



class Inventory:
    def __init__(self):
        self.weapon: _Weapon = Stick()
        self.defensive: _Defensive = None
        self.helmet: _Helmet = LeatherHelmet()
        self.chestplate: _Chestplate = LeatherChestplate()
        self.leggings: _Leggings = LeatherLeggings()
        self.boots: _Boots = LeatherBoots()
        self.accessories: List[List[_Accessory, int]] = []
        self.items: List[_Item, int] = []

    @classmethod
    def from_data(cls, data):
        inventory = cls()
        inventory.weapon = get_item(data['weapon'])
        inventory.defensive = get_item(data['defensive'])
        inventory.helmet = get_item(data['helmet'])
        inventory.chestplate = get_item(data['chestplate'])
        inventory.leggings = get_item(data['leggings'])
        inventory.boots = get_item(data['boots'])
        inventory.accessories = [
            [get_item(accessory[0]), accessory[1]] for accessory in data['accessories']]
        inventory.items = [[get_item(item[0]), item[1]]
                           for item in data['items']]
        return inventory

    def __repr__(self) -> str:
        return f"<Inventory weapon={self.weapon!r} defensive={self.defensive!r} helmet={self.helmet!r} chestplate={self.chestplate!r} leggings={self.leggings!r} boots={self.boots!r} accessories={self.accessories!r} items={self.items!r}>"

    def dict(self):
        return {
            'weapon': self.weapon.dict() if self.weapon is not None else None,
            'defensive': self.defensive.dict() if self.defensive is not None else None,
            'helmet': self.helmet.dict() if self.helmet is not None else None,
            'chestplate': self.chestplate.dict() if self.chestplate is not None else None,
            'leggings': self.leggings.dict() if self.leggings is not None else None,
            'boots': self.boots.dict() if self.boots is not None else None,
            'accessories': [[accessory.dict(), count] for accessory, count in self.accessories],
            'items': [[item.dict(), count] for item, count in self.items]
        }

    def get_base_class(self, item):
        if isinstance(item, _Weapon):
            return _Weapon
        if isinstance(item, _Defensive):
            return _Defensive
        if isinstance(item, _Helmet):
            return _Helmet
        if isinstance(item, _Chestplate):
            return _Chestplate
        if isinstance(item, _Leggings):
            return _Leggings
        if isinstance(item, _Boots):
            return _Boots
        if isinstance(item, _Accessory):
            return _Accessory
        return _Item

    def get_position(self, _items_list, item):
        for i in range(len(_items_list)):
            if _items_list[i][0] == item:
                return i
        return None

    def get_position_by_name(self, _items_list, name: str):
        for i in range(len(_items_list)):
            if str(_items_list[i][0]) == name:
                return i

        return None

    def add(self, _items_list, item, count=1):
        existed = False
        for i in range(len(_items_list)):
            if _items_list[i][0] == item:
                existed = True
                _items_list[i][1] += count
                break
        if not existed:
            _items_list.append([item, count])
        return existed

    def add_by_name(self, _items_list, name: str, count=1):
        item = get_default_item_by_name(name)
        if not item:
            raise BadArgument('Cannot find an item with such name')
        self.add(_items_list, item, count)

    def remove_by_pos(self, _items_list, pos, count=1):
        if count >= _items_list[pos][1]:
            count = _items_list[pos][1]
            _items_list.pop(pos)
        else:
            _items_list[pos][1] -= count
        return True, count

    def remove(self, _items_list, item, count=1):
        pos = self.get_position(_items_list, item)
        if pos is None:
            return False, 0
        return self.remove_by_pos(_items_list, pos, count)

    def remove_by_name(self, _items_list, name, count=1):
        pos = self.get_position_by_name(_items_list, name)
        if pos is None:
            return False, 0
        return self.remove_by_pos(_items_list, pos, count)

    def use_by_pos(self, _items_list, pos):
        item = _items_list[pos][0]
        slot = item.slot()
        if(slot is False):
            raise BadArgument("Cannot use the specified item")
        elif slot == 'accessories':
            pos = self.get_position(self.accessories, item)
            if pos:
                raise BadArgument(
                    "There is already a similar accessory in your accessory bag")
            self.add(self.accessories, item)
        else:
            previous_item = getattr(self, slot, None)
            setattr(self, slot, item)
            if previous_item:
                self.add(_items_list, previous_item)
        self.remove_by_pos(_items_list, pos)
        return item

    def use(self, _items_list, item):
        pos = self.get_position(_items_list, item)
        if pos is None:
            raise BadArgument('Cannot find such item')
        return self.use_by_pos(_items_list, pos)

    def use_by_name(self, _items_list, name):
        pos = self.get_position_by_name(_items_list, name)
        if pos is None:
            raise BadArgument('Cannot find an item with such name')
        return self.use_by_pos(_items_list, pos)

    def trigger_special_effect(self, is_crit, damage_dealt, reduced_damage, attacker, defender):
        is_crit, damage_dealt, reduced_damage = self.weapon.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)
        is_crit, damage_dealt, reduced_damage = self.defensive.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)
        is_crit, damage_dealt, reduced_damage = self.helmet.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)
        is_crit, damage_dealt, reduced_damage = self.chestplate.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)
        is_crit, damage_dealt, reduced_damage = self.leggings.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)
        is_crit, damage_dealt, reduced_damage = self.boots.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)
        for accessory, _ in self.accessories:
            is_crit, damage_dealt, reduced_damage = accessory.trigger_special_effect(is_crit, damage_dealt, reduced_damage, attacker, defender)


    @property
    def damage(self):
        result = 0
        result += self.weapon.damage if self.weapon else 0
        result += self.defensive.damage if self.defensive else 0
        result += self.helmet.damage if self.helmet else 0
        result += self.chestplate.damage if self.chestplate else 0
        result += self.leggings.damage if self.leggings else 0
        result += self.boots.damage if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.damage
        return result

    @property
    def true_damage(self):
        result = 0
        result += self.weapon.true_damage if self.weapon else 0
        result += self.defensive.true_damage if self.defensive else 0
        result += self.helmet.true_damage if self.helmet else 0
        result += self.chestplate.true_damage if self.chestplate else 0
        result += self.leggings.true_damage if self.leggings else 0
        result += self.boots.true_damage if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.true_damage
        return result

    @property
    def health(self):
        result = 0
        result += self.weapon.health if self.weapon else 0
        result += self.defensive.health if self.defensive else 0
        result += self.helmet.health if self.helmet else 0
        result += self.chestplate.health if self.chestplate else 0
        result += self.leggings.health if self.leggings else 0
        result += self.boots.health if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.health
        return result

    @property
    def strength(self):
        result = 0
        result += self.weapon.strength if self.weapon else 0
        result += self.defensive.strength if self.defensive else 0
        result += self.helmet.strength if self.helmet else 0
        result += self.chestplate.strength if self.chestplate else 0
        result += self.leggings.strength if self.leggings else 0
        result += self.boots.strength if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.strength
        return result

    @property
    def speed(self):
        result = 0
        result += self.weapon.speed if self.weapon else 0
        result += self.defensive.speed if self.defensive else 0
        result += self.helmet.speed if self.helmet else 0
        result += self.chestplate.speed if self.chestplate else 0
        result += self.leggings.speed if self.leggings else 0
        result += self.boots.speed if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.speed
        return result

    @property
    def defense(self):
        result = 0
        result += self.weapon.defense if self.weapon else 0
        result += self.defensive.defense if self.defensive else 0
        result += self.helmet.defense if self.helmet else 0
        result += self.chestplate.defense if self.chestplate else 0
        result += self.leggings.defense if self.leggings else 0
        result += self.boots.defense if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.defense
        return result

    @property
    def true_defense(self):
        result = 0
        result += self.weapon.true_defense if self.weapon else 0
        result += self.defensive.true_defense if self.defensive else 0
        result += self.helmet.true_defense if self.helmet else 0
        result += self.chestplate.true_defense if self.chestplate else 0
        result += self.leggings.true_defense if self.leggings else 0
        result += self.boots.true_defense if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.true_defense
        return result

    @property
    def crit_chance(self):
        result = 0
        result += self.weapon.crit_chance if self.weapon else 0
        result += self.defensive.crit_chance if self.defensive else 0
        result += self.helmet.crit_chance if self.helmet else 0
        result += self.chestplate.crit_chance if self.chestplate else 0
        result += self.leggings.crit_chance if self.leggings else 0
        result += self.boots.crit_chance if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.crit_chance
        return result

    @property
    def crit_damage(self):
        result = 0
        result += self.weapon.crit_damage if self.weapon else 0
        result += self.defensive.crit_damage if self.defensive else 0
        result += self.helmet.crit_damage if self.helmet else 0
        result += self.chestplate.crit_damage if self.chestplate else 0
        result += self.leggings.crit_damage if self.leggings else 0
        result += self.boots.crit_damage if self.boots else 0
        for accessory, _ in self.accessories:
            result += accessory.crit_damage
        return result
