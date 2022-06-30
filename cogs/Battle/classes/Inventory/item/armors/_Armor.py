from cogs.Battle.classes.Inventory.item._Item import _Equipment


class _Armor(_Equipment):
    def __init__(self):
        super().__init__()
        self._health = 0
        self._defense = 0
        self._speed = 0

    @property
    def health(self):
        return self._health+self.hot_potato_books*4

    @property
    def defense(self):
        return self._defense+self.hot_potato_books*2


class _Helmet(_Armor):
    def __init__(self):
        super().__init__()

    @staticmethod
    def slot():
        return 'helmet'


class _Chestplate(_Armor):
    def __init__(self):
        super().__init__()

    @staticmethod
    def slot():
        return 'chestplate'


class _Leggings(_Armor):
    def __init__(self):
        super().__init__()

    @staticmethod
    def slot():
        return 'leggings'


class _Boots(_Armor):
    def __init__(self):
        super().__init__()

    @staticmethod
    def slot():
        return 'boots'
