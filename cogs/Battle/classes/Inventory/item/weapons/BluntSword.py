from ._Weapon import _Melee

class BluntSword(_Melee):
    def __init__(self):
        super().__init__()
        self._name = 'Blunt Sword'
        self._price = 20
        self._damage = 2
        self._strength = 1
        self._image_url = 'https://i.imgur.com/G4PPRw1.png'