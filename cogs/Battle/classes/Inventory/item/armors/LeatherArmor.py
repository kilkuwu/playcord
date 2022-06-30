from ._Armor import _Helmet, _Chestplate, _Leggings, _Boots

class LeatherHelmet(_Helmet):
    def __init__(self):
        super().__init__()
        self._name = "Leather Helmet"
        self._price = 10
        self._defense = 1
    
class LeatherChestplate(_Chestplate):
    def __init__(self):
        super().__init__()
        self._name = "Leather Chestplate"
        self._price = 10
        self._defense = 2
    
class LeatherLeggings(_Leggings):
    def __init__(self):
        super().__init__()
        self._name = "Leather Leggings"
        self._price = 10
        self._defense = 2

class LeatherBoots(_Boots):
    def __init__(self):
        super().__init__()
        self._name = "Leather Boots"
        self._price = 10
        self._defense = 1