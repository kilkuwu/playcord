from cogs.Battle.classes.Inventory.item._Item import _Equipment

class _Defensive(_Equipment):
    def __init__(self):
        super().__init__()
        self._defense = 0
        self._true_defense = 0
    
    @property
    def defense(self):
        return self._defense+self.hot_potato_books*2
    
    @property
    def true_defense(self):
        return self._true_defense+self.hot_potato_books
    
    @staticmethod
    def slot():
        return 'defensive'