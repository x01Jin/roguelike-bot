import discord
from dotenv import load_dotenv
import os
import json
import random
import asyncio
from datetime import datetime
from discord.ext import commands
import webserver

DBFILE = 'database.json'

TOKEN = os.getenv('dctoken')
if not TOKEN:
    raise ValueError("Discord bot token not found in environment variables")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

class GameData:
    POTS = {
        'heal_pot': {'effect': 'heal', 'value': 10, 'chance': 0.5},
        'atk_pot': {'effect': 'attack', 'value': 3, 'chance': 0.6},
        'def_pot': {'effect': 'defense', 'value': 3, 'chance': 0.6},
        'dmg_pot': {'effect': 'damage', 'value': [10, 20], 'chance': 0.3}
    }

class LootSystem:
    @staticmethod
    def generate_loot(player_luck=0):
        loot = {'pots': {}, 'coins': 0}
        
        pot_chance = 0.3 + (player_luck * 0.01)
        coin_chance = 0.4 + (player_luck * 0.01)
        
        if random.random() < pot_chance:
            for pot, data in GameData.POTS.items():
                modified_chance = data['chance'] + (player_luck * 0.005)
                if random.random() < modified_chance:
                    loot['pots'][pot] = 1
        
        if random.random() < coin_chance:
            base_coins = random.randint(5, 10)
            luck_bonus = int(player_luck * 0.5)
            loot['coins'] = base_coins + luck_bonus
            
        return loot

class Utils:
    @staticmethod
    def user_has_character(user_id):
        try:
            with open(DBFILE, 'r') as f:
                data = f.read()
                if not data:
                    data = {}
                else:
                    data = json.loads(data)
        except FileNotFoundError:
            return False

        return user_id in data

    @staticmethod
    def character_name_exists(name):
        try:
            with open(DBFILE, 'r') as f:
                data = f.read()
                if not data:
                    data = {}
                else:
                    data = json.loads(data)
        except FileNotFoundError:
            return False

        for char_data in data.values():
            if char_data['name'].lower() == name.lower():
                return True

        return False

class CharCreate:
    def __init__(self, user_id, name, atk, def_, eva, luk, level=1, coins=0, pots=None, current_hp=100, max_hp=100, current_exp=0):
        if pots is None:
            pots = {}
        self.user_id = user_id
        self.name = name
        self.atk = atk
        self.def_ = def_
        self.eva = eva
        self.luk = luk
        self.level = level
        self.coins = coins
        self.pots = pots
        self.current_hp = current_hp
        self.max_hp = max_hp
        self.current_exp = current_exp

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'atk': self.atk,
            'def': self.def_,
            'eva': self.eva,
            'luk': self.luk,
            'level': self.level,
            'coins': self.coins,
            'pots': self.pots,
            'current_hp': self.current_hp,
            'max_hp': self.max_hp,
            'current_exp': self.current_exp
        }

    def save_to_db(self):
        try:
            with open(DBFILE, 'r') as f:
                data = f.read()
                if data:
                    data = json.loads(data)
                else:
                    data = {}
        except FileNotFoundError:
            data = {}

        data[self.user_id] = self.to_dict()

        with open(DBFILE, 'w') as f:
            json.dump(data, f, indent=4)

    def level_up(self):
        self.level += 1
        self.atk += 0.8
        self.def_ += 1
        self.eva += 0.6
        self.luk += 0.5
        self.current_exp = 0

class CharacterCreateModal(discord.ui.Modal, title="Create Your Character"):
    req1 = "Total stat points cannot exceed 25."
    
    name = discord.ui.TextInput(label="Character Name")
    atk = discord.ui.TextInput(label="Attack Points", placeholder=req1, required=True)
    def_ = discord.ui.TextInput(label="Defense Points", placeholder=req1, required=True)
    eva = discord.ui.TextInput(label="Evasion Points", placeholder=req1, required=True)
    luk = discord.ui.TextInput(label="Luck Points", placeholder=req1, required=True)
 
    async def on_submit(self, interaction: discord.Interaction):
        try:
            atk = int(self.atk.value)
            def_ = int(self.def_.value)
            eva = int(self.eva.value)
            luk = int(self.luk.value)
        except ValueError:
            await interaction.response.send_message("All stat points must be integers.", ephemeral=True)
            return

        if atk + def_ + eva + luk > 25:
            await interaction.response.send_message("Total stat points cannot exceed 25.", ephemeral=True)
            return

        char = CharCreate(
            user_id=str(interaction.user.id),
            name=self.name.value,
            atk=atk * 2,
            def_=def_ * 2,
            eva=eva * 2,
            luk=luk * 2,
            coins=0,
            pots={}
        )
        char.save_to_db()
        await interaction.response.send_message(f"Character {self.name.value} created successfully!", ephemeral=True)

class Monster:
    MONSTER_TYPES = {
        'Slime': {
            'base_hp': 20,
            'base_atk': 2,
            'base_def': 2,
            'hp_per_level': 5,
            'atk_per_level': 1.5,
            'def_per_level': 0.7,
            'weight': 0.4
        },
        'Wolf': {
            'base_hp': 15,
            'base_atk': 4,
            'base_def': 3,
            'hp_per_level': 3,
            'atk_per_level': 2.5,
            'def_per_level': 0.8,
            'weight': 0.3
        },
        'Goblin': {
            'base_hp': 25,
            'base_atk': 3,
            'base_def': 4,
            'hp_per_level': 4,
            'atk_per_level': 2,
            'def_per_level': 1.2,
            'weight': 0.2
        },
        'Orc': {
            'base_hp': 35,
            'base_atk': 5,
            'base_def': 5,
            'hp_per_level': 6,
            'atk_per_level': 2.5,
            'def_per_level': 1.5,
            'weight': 0.1
        }
    }

    def __init__(self, level):
        self.level = level
        monster_type = self._select_monster_type()
        stats = self.MONSTER_TYPES[monster_type]
        
        self.name = f"Lv.{level} {monster_type}"
        self.hp = int(stats['base_hp'] + (stats['hp_per_level'] * (level - 1)))
        self.atk = int(stats['base_atk'] + (stats['atk_per_level'] * (level - 1)))
        self.def_ = int(stats['base_def'] + (stats['def_per_level'] * (level - 1)))

    def _select_monster_type(self):
        types = list(self.MONSTER_TYPES.keys())
        weights = [self.MONSTER_TYPES[t]['weight'] for t in types]
        return random.choices(types, weights=weights)[0]

    def to_dict(self):
        return {
            'name': self.name,
            'level': self.level,
            'atk': self.atk,
            'def': self.def_,
            'hp': self.hp
        }

class Combat:
    def __init__(self, player, monster, interaction=None):
        self.player = player
        self.monster = monster
        self.message = ""
        self.interaction = interaction
        
    def attack(self):
        player_base_damage = (self.player.atk + getattr(self.player, 'temp_atk_boost', 0)) * (1 + (self.player.level * 0.1))
        variance = random.uniform(0.8, 1.2)
        monster_effective_def = self.monster.def_ * 0.5
        player_damage = max(1, int((player_base_damage - monster_effective_def) * variance))
        
        monster_base_damage = self.monster.atk * (1 + (self.monster.level * 0.1))
        variance = random.uniform(0.8, 1.2)
        player_effective_def = (self.player.def_ + getattr(self.player, 'temp_def_boost', 0)) * 0.5
        monster_damage = max(1, int((monster_base_damage - player_effective_def) * variance))

        if random.random() < (self.player.eva * 0.01):
            monster_damage = 0
            self.message = f"{self.player.name} evaded the attack!\n"
        else:
            self.message = ""

        self.monster.hp = max(0, self.monster.hp - player_damage)
        self.player.current_hp = max(0, self.player.current_hp - monster_damage)

        self.message += f"{self.player.name} dealt {player_damage} damage to {self.monster.name}.\n"
        if monster_damage > 0:
            self.message += f"{self.monster.name} dealt {monster_damage} damage to {self.player.name}."

    def is_over(self):
        return self.player.current_hp <= 0 or self.monster.hp <= 0

    def get_winner(self):
        if self.player.current_hp > 0:
            exp_gain = int(self.monster.level * 10 * (1 + (self.player.luk * 0.01)))
            self.player.current_exp += exp_gain
            
            level_up_occurred = False
            if self.player.current_exp >= 100:
                self.player.level_up()
                level_up_occurred = True
                
            loot = LootSystem.generate_loot(self.player.luk)
            self.player.coins += loot['coins']
            
            for pot, quantity in loot['pots'].items():
                if pot in self.player.pots:
                    self.player.pots[pot] += quantity
                else:
                    self.player.pots[pot] = quantity
            
            self.player.save_to_db()
            
            return {
                'winner': self.player,
                'exp_gained': exp_gain,
                'coins_gained': loot['coins'],
                'pots_gained': loot['pots'],
                'leveled_up': level_up_occurred
            }
        else:
            self.permadeath()
            return {'winner': self.monster}

    def permadeath(self):
        try:
            with open(DBFILE, 'r') as f:
                data = json.load(f)
            if self.player.user_id in data:
                HighScoreSystem.record_score(
                    self.player.user_id,
                    self.player.name,
                    self.player.level,
                    self.combat.interaction.user
                )
                del data[self.player.user_id]
            with open(DBFILE, 'w') as f:
                json.dump(data, f, indent=4)
        except FileNotFoundError:
            pass
        
    def use_pot(self, pot):
        if pot == 'heal_pot':
            self.player.current_hp += 10
            self.message = f"{self.player.name} used a Heal Potion and restored 10 HP."
        elif pot == 'atk_pot':
            self.player.atk += 3
            self.message = f"{self.player.name} used an Attack Potion and gained 3 ATK."
        elif pot == 'def_pot':
            self.player.def_ += 3
            self.message = f"{self.player.name} used a Defense Potion and gained 3 DEF."
        elif pot == 'dmg_pot':
            damage = random.randint(10, 20)
            self.monster.hp -= damage
            self.message = f"{self.player.name} used a Damage Potion and dealt {damage} damage to {self.monster.name}."

class VictoryButtons(discord.ui.View):
    def __init__(self, combat):
        super().__init__(timeout=10)
        self.combat = combat
        self.message = None

        has_potions = any(quantity > 0 for quantity in self.combat.player.pots.values())

        self.continue_button = discord.ui.Button(label="Continue", style=discord.ButtonStyle.green)
        self.continue_button.callback = self.continue_button_callback
        self.add_item(self.continue_button)

        self.use_pot_button = discord.ui.Button(label="Use Pot", style=discord.ButtonStyle.primary, disabled=not has_potions)
        self.use_pot_button.callback = self.use_pot_button_callback
        self.add_item(self.use_pot_button)

    async def continue_button_callback(self, interaction: discord.Interaction):
        monster_level = random.randint(max(1, self.combat.player.level - 2), self.combat.player.level + 3)
        self.combat.monster = Monster(monster_level)  # Create new monster
        
        embed = discord.Embed(title="Combat Session", color=discord.Color.red())
        embed.add_field(name=f"{self.combat.player.name}'s HP", value=f"{self.combat.player.current_hp}/{self.combat.player.max_hp}", inline=True)
        embed.add_field(name=f"{self.combat.monster.name}'s HP", value=self.combat.monster.hp, inline=True)
        embed.add_field(name="Message", value="Combat begins!", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)
        message = interaction.message

        while not self.combat.is_over():
            self.combat.attack()
            embed.set_field_at(0, name=f"{self.combat.player.name}'s HP", value=f"{self.combat.player.current_hp}/{self.combat.player.max_hp}", inline=True)
            embed.set_field_at(1, name=f"{self.combat.monster.name}'s HP", value=self.combat.monster.hp, inline=True)
            embed.set_field_at(2, name="Message", value=self.combat.message, inline=False)
            await message.edit(embed=embed)
            await asyncio.sleep(1)

        result = self.combat.get_winner()
        if 'exp_gained' in result:
            reward_text = (
                f"🎉 Victory! 🎉\n"
                f"EXP gained: {result['exp_gained']}\n"
                f"Coins gained: {result['coins_gained']}"
            )
            if result['pots_gained']:
                reward_text += "\nPotions gained:\n" + "\n".join(f"- {pot}: {qty}" for pot, qty in result['pots_gained'].items())
            if result['leveled_up']:
                reward_text += f"\n🔥 Level Up! Now level {self.combat.player.level}! 🔥"
            
            embed.add_field(name="Battle Rewards", value=reward_text, inline=False)
            view = VictoryButtons(self.combat)
            view.message = message
            await message.edit(embed=embed, view=view)
        else:
            embed.add_field(name="Defeat!", value="You lost the combat!", inline=False)
            await message.edit(embed=embed)

    async def use_pot_button_callback(self, interaction: discord.Interaction):
        if self.combat.player.pots:
            pot_selection = PotSelection(self.combat)
            await interaction.response.send_message("Select a pot to use:", view=pot_selection, ephemeral=True)
            self.clear_items()
            if self.message:
                await self.message.edit(view=self)
        else:
            await interaction.response.send_message("You don't have any potions!", ephemeral=True)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(content="Combat session ended due to timeout.", view=None)

class PotSelection(discord.ui.View):
    def __init__(self, combat):
        super().__init__(timeout=10)
        self.combat = combat
        self.message = None
        self.add_pot_buttons()

    def add_pot_buttons(self):
        for pot, quantity in self.combat.player.pots.items():
            if quantity > 0:
                button = discord.ui.Button(
                    label=f"{pot} ({quantity})", 
                    style=discord.ButtonStyle.primary, 
                    custom_id=pot
                )
                button.callback = self.create_pot_callback(pot)
                self.add_item(button)

    def create_pot_callback(self, pot_type):
        async def pot_callback(interaction: discord.Interaction):
            try:
                if self.combat.player.pots[pot_type] <= 0:
                    await interaction.response.send_message(
                        "You don't have this potion anymore!", 
                        ephemeral=True
                    )
                    return

                self.combat.player.pots[pot_type] -= 1
                
                if pot_type == 'heal_pot':
                    heal_amount = GameData.POTS[pot_type]['value']
                    self.combat.player.current_hp = min(
                        self.combat.player.current_hp + heal_amount,
                        self.combat.player.max_hp
                    )
                elif pot_type == 'atk_pot':
                    self.combat.player.temp_atk_boost = GameData.POTS[pot_type]['value']
                elif pot_type == 'def_pot':
                    self.combat.player.temp_def_boost = GameData.POTS[pot_type]['value']
                
                self.combat.player.save_to_db()
                
                await interaction.response.edit_message(content=f"Used {pot_type}!", view=None)
                
                monster_level = random.randint(max(1, self.combat.player.level - 2), self.combat.player.level + 3)
                self.combat.monster = Monster(monster_level)
                
                embed = discord.Embed(title="Combat Session", color=discord.Color.red())
                embed.add_field(
                    name=f"{self.combat.player.name}'s HP", 
                    value=f"{self.combat.player.current_hp}/{self.combat.player.max_hp}", 
                    inline=True
                )
                embed.add_field(
                    name=f"{self.combat.monster.name}'s HP", 
                    value=self.combat.monster.hp, 
                    inline=True
                )
                embed.add_field(
                    name="Message", 
                    value=f"Combat continues with {pot_type} effect!", 
                    inline=False
                )
                
                message = await interaction.followup.send(embed=embed)
                
                while not self.combat.is_over():
                    self.combat.attack()
                    embed.set_field_at(0, 
                        name=f"{self.combat.player.name}'s HP", 
                        value=f"{self.combat.player.current_hp}/{self.combat.player.max_hp}", 
                        inline=True
                    )
                    embed.set_field_at(1, 
                        name=f"{self.combat.monster.name}'s HP", 
                        value=self.combat.monster.hp, 
                        inline=True
                    )
                    embed.set_field_at(2, 
                        name="Message", 
                        value=self.combat.message, 
                        inline=False
                    )
                    await message.edit(embed=embed)
                    await asyncio.sleep(1)
                
                if pot_type in ['atk_pot', 'def_pot']:
                    if hasattr(self.combat.player, 'temp_atk_boost'):
                        delattr(self.combat.player, 'temp_atk_boost')
                    if hasattr(self.combat.player, 'temp_def_boost'):
                        delattr(self.combat.player, 'temp_def_boost')
                
                result = self.combat.get_winner()
                if 'exp_gained' in result:
                    reward_text = (
                        f"🎉 Victory! 🎉\n"
                        f"EXP gained: {result['exp_gained']}\n"
                        f"Coins gained: {result['coins_gained']}"
                    )
                    if result['pots_gained']:
                        reward_text += "\nPotions gained:\n" + "\n".join(
                            f"- {pot}: {qty}" for pot, qty in result['pots_gained'].items()
                        )
                    if result['leveled_up']:
                        reward_text += f"\n🔥 Level Up! Now level {self.combat.player.level}! 🔥"
                    
                    embed.add_field(name="Battle Rewards", value=reward_text, inline=False)
                    view = VictoryButtons(self.combat)
                    view.message = message
                    await message.edit(embed=embed, view=view)
                else:
                    embed.add_field(name="Defeat!", value="You lost the combat!", inline=False)
                    await message.edit(embed=embed)

            except Exception as e:
                await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

        return pot_callback

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == int(self.combat.player.user_id)

class HighScoreSystem:
    HISCORE_FILE = 'hiscore.json'

    @classmethod
    def record_score(cls, user_id, char_name, level, discord_user):
        try:
            with open(cls.HISCORE_FILE, 'r') as f:
                scores = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            scores = []

        discord_name = discord_user.display_name if hasattr(discord_user, 'display_name') else str(discord_user)

        scores.append({
            'user_id': user_id,
            'char_name': char_name,
            'level': level,
            'discord_name': discord_name,
            'date': datetime.now().strftime('%m/%d/%y')
        })

        scores.sort(key=lambda x: x['level'], reverse=True)
        scores = scores[:10]

        with open(cls.HISCORE_FILE, 'w') as f:
            json.dump(scores, f, indent=4)

    @classmethod
    def get_rankings(cls):
        try:
            with open(cls.HISCORE_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

async def start_combat(interaction, combat):
    await interaction.response.defer()

    embed = discord.Embed(title="Combat Session", color=discord.Color.red())
    embed.add_field(name=f"{combat.player.name}'s HP", value=f"{combat.player.current_hp}/{combat.player.max_hp}", inline=True)
    embed.add_field(name=f"{combat.monster.name}'s HP", value=combat.monster.hp, inline=True)
    embed.add_field(name="Message", value="Combat begins!", inline=False)

    followup_message = await interaction.followup.send(embed=embed)
    message = await followup_message.fetch()

    while not combat.is_over():
        combat.attack()
        embed.set_field_at(0, name=f"{combat.player.name}'s HP", value=f"{combat.player.current_hp}/{combat.player.max_hp}", inline=True)
        embed.set_field_at(1, name=f"{combat.monster.name}'s HP", value=combat.monster.hp, inline=True)
        embed.set_field_at(2, name="Message", value=combat.message, inline=False)
        await message.edit(embed=embed)
        await asyncio.sleep(1)

    result = combat.get_winner()
    if 'exp_gained' in result:  # Player won
        reward_text = (
            f"🎉 Victory! 🎉\n"
            f"EXP gained: {result['exp_gained']}\n"
            f"Coins gained: {result['coins_gained']}"
        )
        if result['pots_gained']:
            reward_text += "\nPotions gained:\n" + "\n".join(f"- {pot}: {qty}" for pot, qty in result['pots_gained'].items())
        if result['leveled_up']:
            reward_text += f"\n🔥 Level Up! Now level {combat.player.level}! 🔥"
        
        embed.add_field(name="Battle Rewards", value=reward_text, inline=False)
        view = VictoryButtons(combat)
        view.message = message
        await message.edit(embed=embed, view=view)
    else:
        embed.add_field(name="Defeat!", value="You lost the combat!", inline=False)
        await message.edit(embed=embed)

@bot.tree.command(name="create_character", description="Create a new character")
async def create_character(interaction: discord.Interaction):
    await interaction.response.send_modal(CharacterCreateModal())

@bot.tree.command(name="profile", description="Display your character profile")
async def profile(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if not Utils.user_has_character(user_id):
        await interaction.response.send_message("No profile found. Please create a character first.", ephemeral=True)
        return

    with open(DBFILE, 'r') as f:
        data = json.load(f)

    char_data = data.get(user_id)
    if not char_data:
        await interaction.response.send_message("Your character has died and all data is lost.", ephemeral=True)
        return

    embed = discord.Embed(title=f"{char_data['name']}'s Profile", color=discord.Color.blue())
    embed.add_field(name="Level", value=char_data['level'], inline=True)
    embed.add_field(name="HP", value=f"{char_data['current_hp']}/{char_data['max_hp']}", inline=True)
    embed.add_field(name="EXP", value=char_data['current_exp'], inline=True)
    embed.add_field(name="Attack", value=char_data['atk'], inline=True)
    embed.add_field(name="Defense", value=char_data['def'], inline=True)
    embed.add_field(name="Evasion", value=char_data['eva'], inline=True)
    embed.add_field(name="Luck", value=char_data['luk'], inline=True)
    embed.add_field(name="Coins", value=char_data['coins'], inline=True)
    
    pots = "\n".join([f"{pot}: {quantity}" for pot, quantity in char_data['pots'].items()])
    embed.add_field(name="Potions", value=pots if pots else "None", inline=False)

    embed.set_thumbnail(url=interaction.user.avatar.url)
    embed.set_footer(text="Character Profile")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="combat", description="Start a combat session")
async def combat(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if not Utils.user_has_character(user_id):
        await interaction.response.send_message("No profile found. Please create a character first.", ephemeral=True)
        return

    with open(DBFILE, 'r') as f:
        data = json.load(f)

    char_data = data[user_id]
    char_data['def_'] = char_data.pop('def')
    player = CharCreate(**char_data)
    monster_level = random.randint(max(1, player.level - 2), player.level + 3)
    monster = Monster(monster_level)

    combat = Combat(player, monster, interaction)
    await start_combat(interaction, combat)

@bot.tree.command(name="rankings", description="View the top 10 players")
async def rankings(interaction: discord.Interaction):
    scores = HighScoreSystem.get_rankings()
    
    embed = discord.Embed(
        title="🏆 Hall of Champions 🏆",
        description="The greatest warriors who have fallen in battle",
        color=discord.Color.gold()
    )
    
    separator = "═══════════════════════"
    
    if not scores:
        embed.add_field(name="No Records", value="Be the first to join the ranks!", inline=False)
    else:
        medals = ["🥇", "🥈", "🥉"]
        
        for i, score in enumerate(scores, 1):
            medal = medals[i-1] if i <= 3 else "👑"
            field_name = f"{medal} Rank #{i}"
            field_value = (
                f"**{score['discord_name']}**\n"
                f"Character: `{score['char_name']}`\n"
                f"Level: `{score['level']}`\n"
                f"Date: `{score['date']}`\n"
                f"{separator}"
            )
            embed.add_field(name=field_name, value=field_value, inline=False)

    embed.set_footer(text="May their legends live forever")
    await interaction.response.send_message(embed=embed)

webserver.keep_alive()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("Roguelike"))
    try:
        await bot.tree.sync()
        print("Slash commands synchronized successfully.")
    except Exception as e:
        print(f"Failed to synchronize commands: {e}")

async def start_bot():
    while True:
        try:
            await bot.start(TOKEN)
        except Exception as e:
            print(f"Error occurred: {e}")
            print("Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
        else:
            print("Reconnected successfully.")
            break

async def main():
    await start_bot()

if __name__ == "__main__":
    asyncio.run(main())