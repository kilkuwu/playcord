from ._Defensive import _Defensive

class Shield(_Defensive):
    def __init__(self):
        super().__init__()
        self._name = 'Shield'
        self._price = 30
        self._defense = 1