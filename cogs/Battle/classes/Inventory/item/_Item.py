RARITIES = {
    0: 'Common',
    1: 'Uncommon',
    2: 'Rare',
    3: 'Epic',
    4: 'Legendary',
    5: 'Mythic',
    6: 'Galactic',
    7: 'Admin'
}

from pickle import dumps

class _Item:
    def __init__(self):
        self._name = None
        self._rarity = 0
        self._image_url = None
        self._price = 0

    @classmethod
    def from_data(cls, _):
        return cls()

    def __str__(self) -> str:
        return f"{self.name} [{self.rarity}]"
    
    def text_markup(self):
        return f"**{self.name}** [*{self.rarity}*]"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__!r} name={self.name!r} rarity={self._rarity!r}>"

    def __eq__(self, __o: '_Item') -> bool:
        return dumps(self) == dumps(__o)

    def dict(self):
        return {
            'class': self.__class__.__name__,
        }
    
    def trigger_special_effect(self, is_crit, damage_dealt, reduced_damage, attacker, defender):
        return is_crit, damage_dealt, reduced_damage
    
    @property
    def name(self):
        return self._name

    @property
    def rarity(self):
        return RARITIES[self._rarity]
    
    @property
    def image_url(self):
        return self._image_url
    
    @property
    def price(self):
        return self._price

    @property
    def damage(self):
        return 0

    @property
    def true_damage(self):
        return 0

    @property
    def strength(self):
        return 0
    
    @property
    def health(self):
        return 0

    @property
    def defense(self):
        return 0

    @property
    def true_defense(self):
        return 0

    @property
    def speed(self):
        return 0

    @property
    def crit_chance(self):
        return 0

    @property
    def crit_damage(self):
        return 0
    
    @staticmethod
    def slot():
        return False


class _HotPotatoBookable(_Item):
    def __init__(self):
        super().__init__()
        self._hot_potato_books = 0

    def dict(self):
        ret = super().dict()
        if self._hot_potato_books > 0:
            ret['hot_potato_books'] = self.hot_potato_books
        return ret

    @classmethod
    def from_data(cls, data):
        item = cls()
        item.hot_potato_books = data.get('hot_potato_books', 0)
        return item

    @property
    def name(self):
        return f"{f'(+{self.hot_potato_books}) ' if self.hot_potato_books > 0 else ''}{self._name}"
    
    @property
    def hot_potato_books(self):
        return self._hot_potato_books
    
    @hot_potato_books.setter
    def hot_potato_books(self, value):
        self._hot_potato_books = min(max(value, 0), 10)


class _Equipment(_HotPotatoBookable):
    def __init__(self):
        super().__init__()
