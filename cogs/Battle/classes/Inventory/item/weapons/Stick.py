from ._Weapon import _Melee

class Stick(_Melee):
    def __init__(self):
        super().__init__()
        self._name = 'Stick'
        self._price = 10
        self._damage = 1
        self.image_url = 'https://i.imgur.com/EuNcuFB.png'