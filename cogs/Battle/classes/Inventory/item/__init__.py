import inspect

from .weapons import *
from .defensives import *
from .armors import *

ITEMS = {}
glo = globals().copy()

from ._Item import _Item
for key, value in glo.items():
    if inspect.isclass(value) and issubclass(value, _Item):
        print(key)
        ITEMS[key] = value


def get_item(data):
    if not data:
        return None
    item_class = ITEMS.get(data.get('class', 'Not A Class'), None)
    if not item_class:
        return None
    return item_class.from_data(data)

def process_item_name(name):
    return ''.join([word.capitalize() for word in name.split()])

def get_default_item_by_name(name):
    return get_item({
        'class': process_item_name(name)
    })