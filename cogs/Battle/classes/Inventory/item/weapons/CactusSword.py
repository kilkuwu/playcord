from ._Weapon import _Melee

class CactusSword(_Melee):
    def __init__(self):
        super().__init__()
        self._name = 'Military Shovel'
        self._price = 25
        self._damage = 2
        self._strength = 2
        self.image_url = 'https://i.imgur.com/FCWyhai.png'
    