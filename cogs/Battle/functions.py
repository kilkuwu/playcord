import random

def P(chance):
    return random.random() <= float(chance/100)

def drop_check(winner_level):
    i = random.random()
    if i <= 1/1000000 and winner_level >= 50:
        return "ADMIN"
    if i <= float(1/5000) and winner_level >= 25:
        return "MYTHIC"
    if i <= float(1/250) and winner_level >= 20:
        return "LEGENDARY"
    if i <= float(1/100) and winner_level >= 15:
        return "EPIC"
    if i <= float(1/30) and winner_level >= 10:
        return "RARE"
    if i <= float(1/10) and winner_level >= 5:
        return "UNCOMMON"
    if i <= float(1/4):
        return "COMMON"
    return None

def dungeon_drop_check(floor):
    i = random.random()
    if i <= 1/1000000:
        return "ADMIN"
    if i <= float(1/(5000*(2**(-floor)))-1/500):
        return "MYTHIC"
    if i <= float(1/(250*(2**(-floor)))-1/25):
        return "LEGENDARY"
    if i <= float(1/(100*(2**(-floor)))-1/10):
        return "EPIC"
    if i <= float(1/(30*(2**(-floor)))-1/3):
        return "RARE"
    if i <= float(1/(10*(2**(-floor)))):
        return "UNCOMMON"
    if i <= float(1/(4*(2**(-floor)))):
        return "COMMON"
    return None


def check_monster_rarity():
    i = random.random()
    if i <= float(1/100):
        return "LEGENDARY"
    if i <= float(1/30):
        return "EPIC"
    if i <= float(1/10):
        return "RARE"
    if i <= float(1/5):
        return "UNCOMMON"
    return "COMMON"