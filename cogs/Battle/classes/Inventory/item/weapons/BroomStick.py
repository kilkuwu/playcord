from ._Weapon import _Melee

class BroomStick(_Melee):
    def __init__(self):
        super().__init__()
        self._name = 'Broom Stick'
        self._price = 15
        self._damage = 1
        self._strength = 1
        self.image_url = 'https://i.imgur.com/CPBZYMW.png'