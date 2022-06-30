from ._Weapon import _Melee

class BrokenBrick(_Melee):
    def __init__(self):
        super().__init__()
        self._name = 'Broken Brick'
        self._price = 15
        self._damage = 2
        self._image_url = 'https://i.imgur.com/vJQRDED.png'