from ._Weapon import _Melee

class OverHeavenKatana(_Melee):
    def __init__(self):
        super().__init__()
        self._name = 'Over Heaven Katana'
        self._price = 2147483647
        self._damage = 2147483647
        self._true_damage = 2147483647
        self._strength = 2147483647
        self._crit_chance = 100
        self._crit_damage = 1000
        self._rarity = 7
        self._image_url = 'https://static.wikia.nocookie.net/jjba/images/f/fb/The_world_over_heaven.png/revision/latest?cb=20200211190745'