import discord
from discord.ext import commands
import asyncio
from cogs.Battle.classes.Inventory.item import get_default_item_by_name
from utils.functions import get_max_size
from views import Confirm, Pagelist
from utils.constants import USERS_DB as DB
from utils.functions import get_default_embed, verify_and_get_user
from .functions import *
from .classes.User import User, FightingUser
from classes import Bot


# BuyableWeapons = ["Broken Brick", "Cactus Sword","Kunai", "Shuriken", "Katana",
#                   "Knight Sword", "AWM", "Light Saber", "Pigman's Sword", "Desert Eagle"]
# BuyableArmors = ["Adidas Clothes", "Nike Clothes", "Gucci Clothes", "Supreme Clothes", "Knight Armor",
#                  "Royal Armor", "Midas' Armor", "Forged Iron Armor", "Obsidian Armor", "Superior Dragon Armor"]
PLAYER_DODGE_RESPONSE = [
    "**What the...**",
    "**How?**",
    "Why you are **so fast**?"
]
OPPONENT_DODGE_RESPONSE = [
    "**Hehe!**",
    "I am **speed!**",
    "You **can't catch** me!"
]
PLAYER_CRIT_RESPONSE = [
    "_How does that feel **huh?**_",
    "That **hurts** a lot, isn't it.",
    "No way you **survive** that!"
]
OPPONENT_CRIT_RESPONSE = [
    "Urgh.. **What the...**",
    "**That hurts!**",
    "Urgh.. **How is that possible**!?!"
]


def get_dodge_commentary(player1: User, player2: User):
    return random.choice([
        f"**[DODGE!]** {player1.user.mention} tried using **{player1.inventory.weapon or 'nothing'}** to deal some damage but {player2.user.mention} dodged the attack. ",
        f"**[DODGE!]** Being so fast, {player2.user.mention} dodged {player1.user.mention}'s attack completely! ",
        f"**[DODGE!]** On the point of being hit by {player1.user.mention}'s **{player1.inventory.weapon or 'nothing'}**, {player2.user.mention} magically dodged the attack somehow. "
    ])


def get_dodge_dialog(player1: User, player2: User):
    return f"\n\n{player1.user.mention}: {random.choice(PLAYER_DODGE_RESPONSE)}\n{player2.user.mention}: {random.choice(OPPONENT_DODGE_RESPONSE)}"


def get_crit_commentary(player1: User, player2: User, damage=0):
    return random.choice([
        f"**[CRITICAL!]** {player1.user.mention} grabbed **{player1.inventory.weapon or 'nothing'}** and dealt a critical hit on {player2.user.mention}, completely ignored {player2.user.mention}'s protection and brutally caused **{damage:.2f}** damage to {player2.user.mention}.",
        f"**[CRITICAL!]** {player1.user.mention} did a 360 and landed a brutal hit on {player2.user.mention}, causing {player2.user.mention} to lose focus and ultimately lose **{damage:.2f}** health."
    ])


def get_crit_dialog(player1: User, player2: User):
    return f"\n\n{player1.user.mention}: {random.choice(PLAYER_CRIT_RESPONSE)}\n{player2.user.mention}: {random.choice(OPPONENT_CRIT_RESPONSE)}"


def get_normal_commentary(player1: User, player2, damage_dealt, damage_blocked):
    damage = damage_dealt + damage_blocked
    return random.choice([
        f"{player1.user.mention} grabbed **{player1.inventory.weapon or 'nothing'}** and smashed {player2.user.mention}, dealing **{(damage):.2f}** damage. {player2.user.mention} managed to block **{damage_blocked:.2f}** damage, and so lost **{damage_dealt:.2f}** health.",
        f"{player1.user.mention} used **{player1.inventory.weapon or 'nothing'}** to deal **{(damage):.2f}** damage while {player2.user.mention} blocked **{damage_blocked:.2f}** damage with their armor, losing **{damage_dealt:.2f}** health.",
        f"{player1.user.mention} suddenly attacked {player2.user.mention} from behind with **{player1.inventory.weapon or 'nothing'}**, dealing {(damage):.2f} damage. However, {player2.user.mention} quickly hid inside the armor; thus, blocking **{damage_blocked:.2f}** damage and lost **{damage_dealt:.2f}** health.",
        f"{player1.user.mention} did a sneak attack behind {player2.user.mention} with **{player1.inventory.weapon or 'nothing'}** and dealt **{(damage):.2f}** damage. {player2.user.mention} shield themselves with their armor blocking **{damage_blocked:.2f}** damage, eventually losing **{damage_dealt:.2f}** health.",
        f"Out of nowhere, {player1.user.mention} magically appeared with **{player1.inventory.weapon or 'nothing'}** and dealt {(damage):.2f} damage on {player2.user.mention}. The poor {player2.user.mention} set the hope on their armor which helped blocking {damage_blocked:.2f} damage. After all, {player2.user.mention} still took **{damage_dealt:.2f}** damage.",
        f"With **{player1.inventory.weapon or 'nothing'}** in hand, {player1.user.mention} directly attacked {player2.user.mention} and expected to deal {(damage):.2f} damage. {player2.user.mention} tried to stop the onslaught with their armor, which reduced the damage taken by **{round((damage_blocked/damage)*100, 2) if damage else 100}%**. With this move, {player2.user.mention} took **{damage_dealt:.2f}** damage.",
        f"{player1.user.mention} quickly approached {player2.user.mention} with their **{player1.inventory.weapon or 'nothing'}** and dealt {(damage):.2f} damage. Surprised, {player2.user.mention} hid behind their their armor, which protected them from {damage_blocked:.2f} damage. {player2.user.mention} lost **{damage_dealt:.2f}** health in the end."
    ])


def get_normal_dialog(player1: User, player2: User):
    return f"\n\n{player1.user.mention}: {random.choice(player1.sayings)}\n{player2.user.mention}: {random.choice(player2.sayings)}"


class ActionViewButton(discord.ui.Button["ActionView"]):
    def __init__(self, label: str, style: int, disabled=False):
        super().__init__(label=label, style=style, disabled=disabled)
        self.action = label

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.view.id:
            return
        self.view.action = self.action
        self.view.stop()


class ActionView(discord.ui.View):
    def __init__(self, *, timeout=180, player=None):
        super().__init__(timeout=timeout)
        self.action = None
        self.id = player.id
        self.add_item(ActionViewButton("CHARGE", 1))
        self.add_item(ActionViewButton("DEFENSE", 2))
        self.add_item(ActionViewButton("DODGE", 3))
        self.add_item(ActionViewButton("SKILL", 4, disabled=True))


class InventoryView(discord.ui.View):
    def __init__(self, *, timeout=180, player=None):
        super().__init__(timeout=timeout)
        self.action = None
        self.id = player.id
        self.add_item(ActionViewButton("EQUIPPED", 1))
        self.add_item(ActionViewButton("ACCESSORIES", 3))
        self.add_item(ActionViewButton("ITEMS", 4))

# class BossReactionButton(discord.ui.Button["BossReaction"]):
#     def __init__(self, label):
#         super().__init__(style=random.randint(1, 4), label=label)
#         self.action = label

#     async def callback(self, interaction: discord.Interaction):
#         await interaction.response.defer()
#         if interaction.user != self.view.player:
#             return
#         view: BossReaction = self.view
#         view.action = self.action
#         view.stop()

# class BossReaction(discord.ui.View):
#     def __init__(self, possible_outcome, player, timeout=2):
#         super().__init__(timeout=timeout)
#         self.action = None
#         self.player = player
#         random.shuffle(possible_outcome)
#         self.possible_outcome = possible_outcome
#         for outcome in self.possible_outcome:
#             self.add_item(BossReactionButton(outcome))


class battle(commands.Cog):
    def __init__(self, bot: 'Bot'):
        self.bot = bot
    #     self.changestore.start()

    # @tasks.loop(hours=3)
    # async def changestore(self):
    #     with open('data/Weapons.json', 'r') as f:
    #         wea = json.load(f)['Weapons']
    #     with open('data/Armors.json', 'r') as f:
    #         arm = json.load(f)['Armors']
    #     weapons = [weapon for weapon in wea if not weapon['name']
    #                in BuyableWeapons and weapon['name'] != "Fist"]
    #     armors = [armor for armor in arm if not armor['name']
    #               in BuyableArmors and armor['name'] != "Skin"]
    #     global SpecialDealWeapon
    #     global SpecialDealArmor
    #     SpecialDealWeapon = random.choice(weapons)
    #     SpecialDealArmor = random.choice(armors)

    @commands.hybrid_command(name='start')
    async def start_command(self, ctx: commands.Context):
        """
        Starts your adventure. (Required)

        Starts your journey as a warrior.
        This needs to be done before using any Battle commands.
        """
        status = DB.find_one({'_id': ctx.author.id})
        if status == None:
            user = User(ctx.author)
            user.update_all()
            return await ctx.reply(embed=get_default_embed(ctx, 'You have started your journey!'), mention_author=False)
        else:
            return await ctx.reply(embed=get_default_embed(ctx, 'You have already started your journey!'), mention_author=False)

    @commands.hybrid_command(name="fight")
    @discord.app_commands.describe(
        opponent='The opponent you want to fight.'
    )
    async def fight_command(self, ctx: commands.Context, opponent: discord.Member):
        """
        Challenges someone to a fight.
        """
        if not 'battle-arena' in ctx.channel.name:
            return await ctx.reply(embed=get_default_embed(ctx, 'This command should be used in #battle-arena channel!'))
        
        if opponent.id == ctx.author.id:
            return await ctx.reply(embed=get_default_embed(ctx, "You can't fight yourself!"))

        player1_data = DB.find_one({'_id': ctx.author.id})
        if player1_data == None:
            return await ctx.reply(embed=get_default_embed(ctx, f"Start your journey by using *{self.bot.cmd_pre}start*."))
        player2_data = DB.find_one({'_id': opponent.id})
        if player2_data == None:
            return await ctx.reply(embed=get_default_embed(ctx, f"Your opponent might not have started their journey."))

        view = Confirm(opponent)
        confirmation_message = await ctx.reply(embed=get_default_embed(
            ctx,
            "Fight challenge!",
            f"Hey {opponent.mention}, you were challenged to a fight by {ctx.author.mention}, would you want to accept the fight?"
        ),
            view=view,
            mention_author=False
        )
        timeout = await view.wait()
        if timeout or not view.value:
            return await confirmation_message.edit(
                embed=get_default_embed(
                    ctx,
                    "Fight challenge!",
                    f"Seems like {opponent.mention} doesn't want a fight..."
                ),
                view=None
            )
        await confirmation_message.edit(
            embed=get_default_embed(
                ctx,
                "Fight challenge!",
                f"Shall the fight between {ctx.author.mention} and {opponent.mention} begins..."
            ),
            view=None
        )

        async def start_fighting(player1: FightingUser, player2: FightingUser):
            who = random.choice([True, False])
            while player1.health > 0 and player2.health > 0:
                if who:
                    player = player1
                    opponent = player2
                else:
                    player = player2
                    opponent = player1

                embed = get_default_embed(
                    ctx,
                    'Choose an action:',
                    "```\n1. CHARGE (Charging straight at your opponent, dealing 100-120% your base damage)\n2. DEFEND (Preparing yourself for the next attack, granting 120-150% your defense)\n3. DODGE (Getting further away from your opponent at 150-200% your speed)\n4. SKILL (Use a skill at your disposal) [NOT YET AVAILABLE]```",
                    player.player.user.display_avatar.url
                ).set_author(name=f"@{player.player.user.display_name}'s turn...", icon_url=self.bot.user.display_avatar.url).set_footer(icon_url=None, text="NOTE: AUTO DECIDE AFTER 15 SECONDS OF NO INTERACTION.")

                view = ActionView(timeout=15, player=player.player.user)
                message = await ctx.send(embed=embed, view=view)
                timeout = await view.wait()
                if timeout:
                    choice = random.choice(['CHARGE', 'DODGE'])
                else:
                    choice = view.action

                player.damage_multiplier = 1
                player.defense_multiplier = 1
                player.speed_multiplier = 1

                embed = get_default_embed(
                    ctx, "This act's results: ", '', player.player.user.display_avatar.url).set_footer()

                if choice == 'CHARGE':
                    embed.set_author(
                        name=f"@{player.player.user.display_name} chose CHARGE...")
                    player.damage_multiplier += random.random()*0.2
                    dodged, crit, damage_dealt, damage_blocked = player.attack(opponent)
                    if dodged:
                        embed.description += get_dodge_commentary(
                            player.player, opponent.player) + get_dodge_dialog(player.player, opponent.player)
                        embed.title += '***DODGED***'
                    else:
                        if crit:
                            embed.description += get_crit_commentary(
                                player.player, opponent.player, damage=damage_dealt) + get_crit_dialog(player.player, opponent.player)
                            embed.title += '***CRITICAL***'
                        else:
                            embed.description += get_normal_commentary(
                                player.player, opponent.player, damage_dealt, damage_blocked) + get_normal_dialog(player.player, opponent.player)
                elif choice == 'DEFENSE':
                    embed.set_author(
                        name=f"@{player.player.user.display_name} chose DEFEND...")
                    player.defense_multiplier += random.random()*0.3+0.2
                    embed.description = f"Your base defense is **{player.player.defense:.2f}**\nYour defense multiplier is **{player.defense_multiplier:.2f}**\nYour current defense is **{(player.defense):.2f}**"
                elif choice == 'DODGE':
                    embed.set_author(
                        name=f"@{player.player.user.display_name} chose DODGE...")
                    player.speed_multiplier += random.random()*0.5+0.5
                    embed.description = f"Your base speed is **{player.player.speed:.2f}**\nYour speed multiplier is **{player.speed_multiplier:.2f}**\nYour current speed is **{(player.speed):.2f}**"
                else:
                    pass

                additional_commentary = '\n\n' + player.turn() + '\n\n'
                additional_commentary += opponent.turn() 

                health_block = f"\n\n```css\n@{player.player.user.display_name}'s health: {player.health:.2f} / {player.player.health:.2f}\n``````css\n@{opponent.player.user.display_name}'s health: {opponent.health:.2f} / {opponent.player.health:.2f}\n```"
                if len(additional_commentary) > 4:
                    embed.description += additional_commentary
                embed.description += health_block

                await message.edit(embed=embed, view=None)
                await asyncio.sleep(1)
                who = not who
            if player1.health <= 0:
                return player2, player1
            else:
                return player1, player2

        player1 = User.from_data(ctx.author, player1_data).get_fighting()
        player2 = User.from_data(opponent, player2_data).get_fighting()

        winner, loser = await start_fighting(player1, player2)
        await ctx.send(f'{winner.player.user.mention} wins, {loser.player.user.mention} loses')

    #                     else:
    #                         total_damage = mdamage + mstrength - oprot
    #                     ohealth -= total_damage
    #
    #                     lore = f"\n\n{ctx.author.mention} with **{player1.inventory.weapon or 'nothing'}**: {random.choice(mweapon['lore'])}\n{opponent.mention} with **{oarmor['name']}** `[{oarmor['rarity']}]`: {random.choice(oarmor['lore'])}"
    #                 else:
    #                     total_damage = int((mdamage + mstrength) * 1.5)
    #                     ohealth -= total_damage

    #                     lore = f"\n\n{ctx.author.mention} with **{mweapon['name']}** `[{mweapon['rarity']}]`: {random.choice(response_of_crit)}\n{opponent.mention} with **{oarmor['name']}** `[{oarmor['rarity']}]`: {random.choice(response_of_crit1)}"
    #             if ododgetf == True:
    #                 ododge -= 50
    #                 ododgetf = False
    #             mstrength -= buff
    #             result = random.choice(response) + lore
    #             result = random.choice(response) + lore
    #         if mhealth < 0:
    #             mhealth = 0
    #         if ohealth < 0:
    #             ohealth = 0
    #         healthsummary = f"```css\n@{ctx.author.display_name}'s health: {mhealth}\n``````css\n@{opponent.display_name}'s health: {ohealth}\n```"
    #         embed = discord.Embed(color=ctx.author.color)
    #         embed.set_author(
    #             name=header, icon_url=self.bot.user.display_avatar.url)
    #         embed.title = f"Act {turn} results:"
    #         embed.description = result + "\n\n" + healthsummary
    #         embed.set_thumbnail(url=thumbnail)
    #         await mess.edit(embed=embed, view=None)
    #         await asyncio.sleep(3)
    #         turn += 1
    #         determine += 1
    #     embed = discord.Embed(color=ctx.author.color)
    #     embed.set_author(name="Battle result: ",
    #                      icon_url=self.bot.user.display_avatar.url)
    #     if mhealth < ohealth:
    #         title = [
    #             f"MVP goes to @{opponent.display_name}!",
    #             f"@{opponent.display_name} secures the victory!",
    #             f"The crown belongs to @{opponent.display_name}!"
    #         ]
    #         embed.title = random.choice(title)
    #         embed.set_thumbnail(url=opponent.display_avatar.url)
    #         description = [
    #             f"{opponent.mention} wins the battle, completely destroyed {ctx.author.mention}.\n{ctx.author.mention} is behind with **{ostats['health'] + oarmor['health'] - ohealth}** total damage.",
    #             f"{ctx.author.mention} lost with only **{ostats['health'] + oarmor['health'] - ohealth}** total damage.\n{opponent.mention}'s' victory is indisputable.",
    #             f"{opponent.mention} being the MVP, {ctx.author.mention} bent down under {opponent.mention}'s feet"
    #         ]
    #         embed.set_footer(icon_url=ctx.author.display_avatar.url,
    #                          text="is the loser!")
    #         embed.description = random.choice(description)
    #         winner = opponent
    #         loser = ctx.author
    #     else:
    #         title = [
    #             f"MVP goes to @{ctx.author.display_name}!",
    #             f"@{ctx.author.display_name} secures the victory!",
    #             f"The crown belongs to @{ctx.author.display_name}!"
    #         ]
    #         embed.title = random.choice(title)
    #         embed.set_thumbnail(url=ctx.author.display_avatar.url)
    #         description = [
    #             f"{ctx.author.mention} wins the battle, completely destroyed {opponent.mention}.\n{opponent.mention} is behind with **{stats['health'] + marmor['health'] - mhealth}** total damage.",
    #             f"{opponent.mention} lost with only **{stats['health'] + marmor['health'] - mhealth}** total damage.\n{ctx.author.mention}'s' victory is indisputable.",
    #             f"{ctx.author.mention} being the MVP, {opponent.mention} bent down under {ctx.author.mention}'s feet."
    #         ]
    #         embed.set_footer(icon_url=opponent.display_avatar.url,
    #                          text="is the loser!")
    #         embed.description = random.choice(description)
    #         winner = ctx.author
    #         loser = opponent
    #     async with ctx.typing():
    #         await asyncio.sleep(1)
    #         await ctx.send(embed=embed)
    #     winner_stats = DB.find_one({'_id': winner.id})
    #     loser_stats = DB.find_one({'_id': loser.id})
    #     reward_rarity = drop_check(winner_stats['level'])
    #     embed = discord.Embed(
    #         title=f"@{winner.display_name}'s rewards:", color=ctx.author.color)
    #     if reward_rarity == None:
    #         embed.description = '**So sad! You drop nothing!**'
    #     else:
    #         type = ['Weapons', 'Armors']
    #         items = random.choice(type)
    #         with open(f'data/{items}.json', 'r') as f:
    #             rewards = json.load(f)[items]
    #         rewards_set = [item for item in rewards if item['rarity'] ==
    #                        reward_rarity and item['name'] != 'Fist' and item['name'] != 'Skin']
    #         reward = random.choice(rewards_set)
    #         winner_stats['inventory'][items].append(reward)
    #         DB.update_one({'_id': winner.id}, {
    #                       '$set': {'inventory': winner_stats['inventory']}})
    #         reward = f"**{reward['name']}** `[{reward_rarity}]`"
    #         congratulations = [
    #             f"_You have dropped_ {reward}!",
    #             f"{reward} _is your reward for this battle!_",
    #             f"{reward} _is now your property!_",
    #             f"_The loot you get is_ {reward}"
    #         ]
    #         if reward_rarity == "COMMON":
    #             embed.description = random.choice(congratulations)
    #         elif reward_rarity == "UNCOMMON":
    #             embed.description = "***NICE!  ***" + \
    #                 random.choice(congratulations)
    #         elif reward_rarity == "RARE":
    #             embed.description = "***LUCKY YOU!  ***" + \
    #                 random.choice(congratulations)
    #         elif reward_rarity == "EPIC":
    #             embed.description = "***RNGesus!  ***" + \
    #                 random.choice(congratulations)
    #         elif reward_rarity == "LEGENDARY":
    #             embed.description = "**PRAY RNGesus!  ***" + \
    #                 random.choice(congratulations)
    #         elif reward_rarity == "MYTHIC":
    #             embed.description = "***HOLY MOLY CRAZY SPECIES PRAY RNGesus!  ***" + \
    #                 random.choice(congratulations)
    #         else:
    #             embed.description = "***HOLY MOLY CRAZY SPECIES PRAY RNGesus! IT IS AN ADMIN ITEM!!!!  ***" + \
    #                 random.choice(congratulations)
    #     min_level = min(loser_stats['level'], winner_stats['level'])
    #     if loser_stats['level'] < winner_stats['level']:
    #         winner_xp_reward = min_level**3 - \
    #             (loser_stats['level'] - winner_stats['level']
    #              )**2 + random.randint(50, 250)
    #         winner_coins_reward = min_level**2 - \
    #             (loser_stats['level'] - winner_stats['level']
    #              )**2 + random.randint(5, 10)
    #     else:
    #         winner_xp_reward = min_level**3 + \
    #             (loser_stats['level'] - winner_stats['level']
    #              )**2 + random.randint(50, 250)
    #         winner_coins_reward = min_level**2 + \
    #             (loser_stats['level'] - winner_stats['level']
    #              )**2 + random.randint(5, 10)
    #     if winner_xp_reward < 0:
    #         winner_xp_reward = 0
    #     if winner_coins_reward < 0:
    #         winner_coins_reward = 0
    #     DB.update_one({'_id': winner.id}, {
    #                   '$inc': {'exp': winner_xp_reward, 'coins': winner_coins_reward}})
    #     embed.description += f"\n\n```css\nYou have gotten {winner_xp_reward} experience points!\n``````css\nYou have gotten {winner_coins_reward} coins!\n```"
    #     embed.set_author(name="Battle rewards: ",
    #                      icon_url=self.bot.user.display_avatar.url)
    #     embed.set_thumbnail(url=winner.display_avatar.url)
    #     embed.set_footer(icon_url=loser.display_avatar.url, text="CONGRATULATIONS!")
    #     async with ctx.typing():
    #         await asyncio.sleep(1)
    #         await ctx.send(embed=embed)
    #     embed = discord.Embed(
    #         title=f"@{loser.display_name}'s punisments:", color=ctx.author.color)
    #     if loser == ctx.author:
    #         if loser_stats['level'] < winner_stats['level']:
    #             loser_xp_punishment = min_level**3 - \
    #                 (loser_stats['level'] - winner_stats['level']
    #                  )**2 + random.randint(50, 250)
    #             loser_coins_punishment = min_level**2 - \
    #                 (loser_stats['level'] - winner_stats['level']
    #                  )**2 + random.randint(5, 10)
    #         else:
    #             loser_xp_punishment = min_level**3 + \
    #                 (loser_stats['level'] - winner_stats['level']
    #                  )**2 + random.randint(50, 250)
    #             loser_coins_punishment = min_level**2 + \
    #                 (loser_stats['level'] - winner_stats['level']
    #                  )**2 + random.randint(5, 10)
    #         if loser_xp_punishment < 0:
    #             loser_xp_punishment = 0
    #         if loser_coins_punishment < 0:
    #             loser_coins_punishment = 0
    #         embed.description = f"**Being the one to start the fight, {loser.mention} deserved the punishment to lose {loser_xp_punishment} experience points and {loser_coins_punishment} coins.**"
    #     else:
    #         loser_xp_punishment = random.randint(10, 50)
    #         loser_coins_punishment = 0
    #         embed.description = f"**The battle got invoked by {ctx.author.mention}, it's not a shame to lose.** \nThus, your punishment is only to lose `{loser_xp_punishment}` experience points."
    #     DB.update_one({'_id': loser.id}, {
    #                   '$inc': {'exp': -loser_xp_punishment, 'coins': -loser_coins_punishment}})
    #     embed.set_author(name="Battle punishments: ",
    #                      icon_url=self.bot.user.display_avatar.url)
    #     embed.set_thumbnail(url=loser.display_avatar.url)
    #     embed.set_footer(icon_url=winner.display_avatar.url, text="POOR YOU!")
    #     async with ctx.typing():
    #         await asyncio.sleep(1)
    #         await ctx.send(embed=embed)
    #     await Bot.level_up(self, winner, ctx.channel, ctx.message)

    def get_equipped_item_embed(self, ctx, inventory):
        embed = get_default_embed(
            ctx,
            'EQUIPPED ITEMS:',
            thumbnail=ctx.author.display_avatar.url
        ).set_author(name=f"@{ctx.author}'s inventory...")
        embed.add_field(name=f'{self.bot.get_emoji(988707973192896532)} Weapon',
                        value=f"```css\n{inventory.weapon}```", inline=False)
        embed.add_field(name=f'{self.bot.get_emoji(988707947733454858)} Defensive',
                        value=f"```css\n{inventory.defensive}```", inline=False)
        embed.add_field(name=f'{self.bot.get_emoji(988707925054853130)} Helmet',
                        value=f"```css\n{inventory.helmet}```", inline=False)
        embed.add_field(name=f'{self.bot.get_emoji(988707900606259250)} Chestplate',
                        value=f"```css\n{inventory.chestplate}```", inline=False)
        embed.add_field(name=f'{self.bot.get_emoji(988707878296780810)} Leggings',
                        value=f"```css\n{inventory.leggings}```", inline=False)
        embed.add_field(name=f'{self.bot.get_emoji(988707861041401886)} Boots',
                        value=f"```css\n{inventory.boots}```", inline=False)
        return embed

    def get_items_list_embeds(self, ctx, items, heading='ITEMS'):
        length = len(items)
        if not length:
            embed = get_default_embed(
                ctx,
                f'{heading}: ',
                '```css\nNone```',
                thumbnail=ctx.author.display_avatar.url
            ).set_author(name=f"@{ctx.author}'s inventory...")
            return [embed]
        embeds = []
        for i in range(0, length, 10):
            embed = get_default_embed(
                ctx,
                f'{heading}: ',
                '',
                thumbnail=ctx.author.display_avatar.url
            ).set_author(name=f"@{ctx.author}'s inventory...")
            for j in range(i, min(i+10, length)):
                embed.description += f"```css\n{f'{items[j][1]} x ' if items[j][1] > 1 else ''}{items[j][0]}```"
            embeds.append(embed)
        return embeds

    async def edit_equipped_items_message(self, ctx, message, user):
        embed = self.get_equipped_item_embed(ctx, user.inventory)
        await message.edit(embed=embed, view=None)

    async def edit_items_list_message(self, ctx, message, items, type='ITEMS'):
        items_embeds = self.get_items_list_embeds(ctx, items, type)
        if len(items_embeds) <= 1:
            return await message.edit(embed=items_embeds[0], view=None)
        view = Pagelist(items_embeds, 180)
        await message.edit(embed=items_embeds[0], view=view)
        timeout = await view.wait()
        if timeout:
            await message.edit(view=None)

    @commands.hybrid_group(name='inventory', aliases=['inv'])
    async def inventory_command(self, ctx: commands.Context):
        """
        Shows your inventory.

        Shows your default equipments, coins, and inventory.
        """
        if ctx.invoked_subcommand is not None:
            return

        user, message = await verify_and_get_user(ctx, ctx.author.id)
        
        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Start your journey by using *{ctx.bot.cmd_pre}start*."))

        embed = get_default_embed(
            ctx,
            title=f"WHICH ?",
            description="```EQUIPPED    | See your equipped items``````ACCESSORIES | See all your unique accessories``````ITEMS       | See all your possessings```",
            thumbnail=ctx.author.display_avatar.url
        ).set_author(name=f"@{ctx.author}'s inventory...")

        view = InventoryView(player=ctx.author)
        await message.edit(embed=embed, view=view)
        timeout = await view.wait()
        if timeout:
            await message.edit(view=None)
        else:
            if view.action == 'EQUIPPED':
                await self.edit_equipped_items_message(ctx, message, user)
            elif view.action == 'ACCESSORIES':
                await self.edit_items_list_message(ctx, message, user.inventory.accessories, 'ACCESSORIES')
            else:
                await self.edit_items_list_message(ctx, message, user.inventory.items)

    @inventory_command.command(name='equipped', aliases=['e', 'equip'])
    async def equipped_command(self, ctx):
        user, message = await verify_and_get_user(ctx, ctx.author.id)
        
        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Start your journey by using *{ctx.bot.cmd_pre}start*."))

        await self.edit_equipped_items_message(ctx, message, user)

    @inventory_command.command(name='accessories', aliases=['a', 'acc', 'accessory'])
    async def accessories_command(self, ctx):
        user, message = await verify_and_get_user(ctx, ctx.author.id)

        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Start your journey by using *{ctx.bot.cmd_pre}start*."))

        await self.edit_items_list_message(ctx, message, user.inventory.accessories, 'ACCESSORIES')

    @inventory_command.command(name='items', aliases=['i', 'item'])
    async def items_command(self, ctx):
        user, message = await verify_and_get_user(ctx, ctx.author.id)
        
        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Start your journey by using *{ctx.bot.cmd_pre}start*."))

        await self.edit_items_list_message(ctx, message, user.inventory.items)

    @commands.hybrid_command(name='item')
    async def item_command(self, ctx, *, item: str):
        def get_item_embed(item):
            embed = get_default_embed(
                ctx,
                f"{item.text_markup()}",
            ).set_image(url=item.image_url)
            properties = {
                'damage': '⚔',
                'true_damage': '✎',
                'strength': '❁',
                'health': "❤",
                'defense': "❈",
                'true_defense': '❂',
                'speed': '✦',
                'crit_chance': '☣',
                'crit_damage': '☠'
            }
            attributes = {}
            for property in properties:
                if (attribute := getattr(item, property, 0)):
                    attributes[property] = attribute

            max_size = get_max_size(
                [' '.join([word.upper() for word in key.split('_')]) for key in attributes])

            entry = ''
            for key, attribute in attributes.items():
                modified_key = ' '.join([word.upper()
                                        for word in key.split('_')])
                width = max_size - \
                    discord.utils._string_width(
                        modified_key) + len(modified_key)
                entry += f"```{random.choice(['ml', 'prolog'])}\n{modified_key:<{width}} | {attribute:,.2f} {properties[key]}```"
            embed.add_field(name='✨ *Attributes*', value=entry, inline=False).add_field(
                name='🪙 *Price*', value=f"```cpp\n{item.price:,.0f} 💸```")
            return embed
        item = get_default_item_by_name(item)
        if not item:
            embed = get_default_embed(
                ctx, 'ITEM NOT FOUND', "***The item you're trying to look for doesn't exist!***")
        else:
            embed = get_item_embed(item)
        await ctx.reply(embed=embed, mention_author=False)
    
    @commands.hybrid_command(name='use')
    async def use_command(self, ctx, *, item: str):
        user, message = await verify_and_get_user(ctx, ctx.author.id)

        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Start your journey by using *{ctx.bot.cmd_pre}start*."))
        
        item = user.inventory.use_by_name(user.inventory.items, item)
        user.update_inventory()
        await message.edit(embed=get_default_embed(ctx, 'SUCCESSFUL COMMAND', f"***Used {item}***"))

    # @commands.command()
    # async def rank(self, ctx, member: discord.Member = None):
    #     """
    #     Shows your or another's rank.

    #     Shows your rank or another member's rank. And more info.

    #     Attributes:
    #         <member> : Optional. The member to show the rank.
    #     """
    #     if member == None:
    #         stats = DB.find_one({"_id": ctx.author.id})
    #         finder = ctx.author
    #     else:
    #         stats = DB.find_one({"_id": member.id})
    #         finder = member
    #     if stats == None:
    #         return await ctx.send(embed=discord.Embed(description='**Member not found!**'))
    #     exp = stats['exp']
    #     level = stats['level']
    #     role = finder.top_role
    #     if exp - level**4 <= 0:
    #         number = 0
    #     else:
    #         number = int(((exp - level**4)/((level+1)**4 - level**4))*20)
    #     rank = 0
    #     rankings = DB.find().sort('exp', DESCENDING)
    #     for x in rankings:
    #         rank += 1
    #         if stats['_id'] == x['_id']:
    #             break
    #     description = f'**Progress: {exp -  level**4} / {(level+1)**4 - level**4}**\n' + \
    #         ':red_circle:'*number+':white_large_square:'*(20-number)
    #     embed = discord.Embed(
    #         title=f"**༼ つ ◕_◕ ༽つ 😃 {finder.display_name}👌's warrior road: (⌐■_■)**", description=description, color=finder.color)
    #     embed.set_thumbnail(url=finder.display_avatar.url)
    #     embed.add_field(name='**Level: **', value=f'**{level}**')
    #     embed.add_field(name='\u200b', value='\u200b')
    #     embed.add_field(name="**Ranking: **", value=f'**#{rank}**')
    #     embed.add_field(name='**Member: **', value=f'**{finder.mention}**')
    #     embed.add_field(name='\u200b', value='\u200b')
    #     embed.add_field(name='**Role: **', value=f'**{role}**')
    #     embed.set_footer(icon_url=ctx.author.display_avatar.url,
    #                      text=f'Requested by {ctx.author}')
    #     await ctx.send(embed=embed)

    # @commands.command()
    # async def leaderboard(self, ctx : commands.Context):
    #     """
    #     Shows the leaderboard.

    #     Shows the leaderboard of all people with highest exp.

    #     Attributes: None.
    #     """
    #     rank = 0
    #     rankings = DB.find().sort('exp', DESCENDING)
    #     rankings_ = list(rankings)[:10]
    #     description = ''
    #     memberidexp = {mem['_id'] : mem['exp'] for mem in rankings_}
    #     memberlist = []
    #     for guild in ctx.bot.guilds:
    #         memberlist.extend(member for member in guild.members if member.id in memberidexp.keys() and not member in memberlist)
    #     memberlist = reversed(sorted(memberlist, key=lambda m: memberidexp[m.id])[:10])
    #     for member in memberlist:
    #         try:
    #             rank+=1
    #             description += f"**#{rank}**. (☞ﾟヮﾟ)☞ **{member.display_name}** _with {memberidexp[member.id]} total experience points._\n\n"
    #         except Exception as e:
    #             pass
    #     for i, x in enumerate(rankings_):
    #         if ctx.author.id == x['_id']:
    #             rank = i + 1
    #             exp = x['exp']
    #             break
    #     description += f"\n**Your rank:** (☞ﾟヮﾟ)☞ ***#{rank}*** _with {exp} total experience points._\n\n"
    #     description += '\n**Message more to get on the leader board!**'
    #     embed = discord.Embed(title="( ﾉ ﾟｰﾟ)ﾉ     _Leaderboard!_     😥",
    #                           description=description, color=ctx.author.color)
    #     embed.set_footer(icon_url=ctx.author.display_avatar.url,
    #                      text='Requested by {0}'.format(ctx.author))
    #     if ctx.guild.icon: embed.set_thumbnail(url=ctx.guild.icon.url)
    #     await ctx.send(embed=embed)


async def setup(client):
    await client.add_cog(battle(client))
