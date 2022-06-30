from cogs.Battle.classes.Inventory.item._Item import _Equipment

class _Weapon(_Equipment):
    def __init__(self):
        super().__init__()
        self._damage = 0
        self._true_damage = 0
        self._strength = 0
        self._crit_chance = 0
        self._crit_damage = 0
    
    @property
    def damage(self):
        return self._damage+self.hot_potato_books*2
    
    @property
    def true_damage(self):
        return self._true_damage+self.hot_potato_books*2
    
    @property
    def strength(self):
        return self._strength+self.hot_potato_books*2
    
    @property
    def crit_chance(self):
        return self._crit_chance
    
    @property
    def crit_damage(self):
        return self._crit_damage
    
    @staticmethod
    def slot():
        return 'weapon'

class _Melee(_Weapon):
    def __init__(self):
        super().__init__()