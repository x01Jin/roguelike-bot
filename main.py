import discord
from dotenv import load_dotenv
import os
import json
import random
import asyncio
from datetime import datetime
from discord.ext import commands

DBFILE = 'database.json'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

class GameData:
    POTS = {
        'heal_pot': {
            'effect': 'heal',
            'value': 10,
            'chance': 0.5,
            'description': '💚 Heals 10 HP'
        },
        'atk_pot': {
            'effect': 'attack',
            'value': 3,
            'chance': 0.6,
            'description': '⚔️ +3 ATK for next combat'
        },
        'def_pot': {
            'effect': 'defense',
            'value': 3,
            'chance': 0.6,
            'description': '🛡️ +3 DEF for next combat'
        },
        'dmg_pot': {
            'effect': 'damage',
            'value': [10, 20],
            'chance': 0.3,
            'description': '💥 10-20 damage to enemy'
        }
    }

class LootSystem:
    @staticmethod
    def generate_loot(player_luck=0):
        loot = {'pots': {}, 'coins': 0}
        
        pot_chance = 0.2 + (player_luck * 0.008) 
        coin_chance = 0.3 + (player_luck * 0.008)
        
        if random.random() < pot_chance:
            for pot, data in GameData.POTS.items():
                modified_chance = data['chance'] + (player_luck * 0.003)
                if random.random() < modified_chance:
                    loot['pots'][pot] = 1

        if random.random() < coin_chance:
            base_coins = random.randint(3, 8)
            luck_bonus = int(player_luck * 0.3)
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
        # Round initial stats to 1 decimal
        self.atk = round(atk * 2, 1)
        self.def_ = round(def_ * 2, 1)
        self.eva = round(eva * 2, 1)
        self.luk = round(luk * 2, 1)
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
            'base_hp': 25,
            'base_atk': 4,
            'base_def': 2,
            'hp_per_level': 6,
            'atk_per_level': 1.8,
            'def_per_level': 0.7,
            'weight': 0.4
        },
        'Wolf': {
            'base_hp': 20,
            'base_atk': 6,
            'base_def': 3,
            'hp_per_level': 4,
            'atk_per_level': 2.2,
            'def_per_level': 0.8,
            'weight': 0.3
        },
        'Goblin': {
            'base_hp': 30,
            'base_atk': 5,  
            'base_def': 4,
            'hp_per_level': 5,
            'atk_per_level': 2.0, 
            'def_per_level': 1.2,
            'weight': 0.2
        },
        'Orc': {
            'base_hp': 40,
            'base_atk': 7, 
            'base_def': 5,
            'hp_per_level': 7,
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

class CombatSystem:
    def __init__(self, player_data, level_range=None):
        self.player = player_data
        self.level_range = level_range or (max(1, self.player['level'] - 1), self.player['level'] + 1)
        self.monster = Monster(random.randint(*self.level_range))
        self.combat_log = []
        self.active_effects = {}
        self.message = None
        self.is_combat_ended = False

    async def start_combat(self, interaction):
        self.is_combat_ended = False
        self.monster = Monster(random.randint(*self.level_range))
        
        if 'damage' in self.active_effects:
            damage = random.randint(*GameData.POTS['dmg_pot']['value'])
            self.monster.hp -= damage
            self.combat_log = [f"💥 Damage potion dealt {damage} damage!"]
            del self.active_effects['damage']
        else:
            self.combat_log = ["Combat started!"]
        
        embed = self.create_combat_embed()
        
        if not self.message:
            await interaction.response.send_message(embed=embed)
            self.message = await interaction.original_response()
        else:
            try:
                await interaction.response.defer()
                await self.update_message(embed)
            except discord.InteractionResponded:
                await self.update_message(embed)
        
        await self.run_combat_loop()

    async def run_combat_loop(self):
        while not self.is_combat_ended:
            await asyncio.sleep(1)
            
            if self.player['current_hp'] <= 0 or self.monster.hp <= 0:
                break

            self.apply_effects()
            self.player_attack()
            if self.monster.hp > 0:
                self.monster_attack()
            
            if self.monster.hp <= 0:
                self.active_effects.clear()

            self.combat_log = self.combat_log[-3:]
            await self.update_message(self.create_combat_embed())

        await self.end_combat()

    def apply_effects(self):
        total_atk = self.player['atk']
        total_def = self.player['def']
        
        for effect, data in self.active_effects.items():
            if effect == 'attack':
                total_atk += data['value']
            elif effect == 'defense':
                total_def += data['value']

        self.total_atk = total_atk
        self.total_def = total_def

    def player_attack(self):
        base_damage = max(1, self.total_atk - self.monster.def_)
        damage_roll = random.uniform(0.8, 1.2)
        damage_to_monster = max(1, int(base_damage * damage_roll))
        
        self.monster.hp = max(0, self.monster.hp - damage_to_monster)
        self.combat_log.append(f"🗡️ You deal {damage_to_monster} damage!")

    def monster_attack(self):
        base_monster_damage = max(1, self.monster.atk - self.total_def)
        monster_damage_roll = random.uniform(0.8, 1.2)
        damage_to_player = max(1, int(base_monster_damage * monster_damage_roll))
        
        if random.random() > self.player['eva'] * 0.01:
            self.player['current_hp'] = max(0, self.player['current_hp'] - damage_to_player)
            self.combat_log.append(f"💥 Monster deals {damage_to_player} damage!")
        else:
            self.combat_log.append("✨ You evaded the attack!")

    async def end_combat(self):
        if self.player['current_hp'] <= 0:
            await self.handle_player_death()
        elif self.monster.hp <= 0:
            await self.handle_victory()

    async def update_message(self, embed, view=None):
        if self.message:
            try:
                await self.message.edit(embed=embed, view=view)
            except discord.NotFound:
                pass
        
    async def handle_victory(self):
        exp_gained = self.monster.level * 4
        self.player['current_exp'] += exp_gained
        level_up_message = ""
        
        if self.player['current_exp'] >= 100:
            self.player['level'] += 1
            self.player['current_exp'] = 0
            # Round stat increases to 1 decimal
            self.player['atk'] = round(self.player['atk'] + 0.6, 1)
            self.player['def'] = round(self.player['def'] + 0.7, 1)
            self.player['eva'] = round(self.player['eva'] + 0.4, 1)
            self.player['luk'] = round(self.player['luk'] + 0.3, 1)
            
            heal_amount = 40
            old_hp = self.player['current_hp']
            self.player['current_hp'] = min(self.player['max_hp'], old_hp + heal_amount)
            
            level_up_message = (
                "🎊 **LEVEL UP!**\n"
                f"You are now level {self.player['level']}!\n"
                f"Your stats have increased!\n"
                f"Healed for {heal_amount} HP!"
            )

        loot = LootSystem.generate_loot(self.player['luk'])
        self.player['coins'] += loot['coins']
        
        for pot, amount in loot['pots'].items():
            if pot not in self.player['pots']:
                self.player['pots'][pot] = 0
            self.player['pots'][pot] += amount

        victory_embed = discord.Embed(title="🎉 Victory!", color=discord.Color.green())
        victory_embed.description = (
            f"You defeated the {self.monster.name}!\n\n"
            f"**Rewards:**\n"
            f"🔰 EXP: {exp_gained} ({self.player['current_exp']}/100)\n"
            f"💰 Coins: {loot['coins']}\n\n"
            f"{level_up_message}"
        )
        
        if loot['pots']:
            pots_text = "\n".join([f"🧪 {pot}: {amt}" for pot, amt in loot['pots'].items()])
            victory_embed.add_field(name="Potions Found", value=pots_text)

        self.save_player_data()

        if self.message:
            await self.message.edit(embed=victory_embed, view=CombatButtons(self))

    def create_combat_embed(self):
        embed = discord.Embed(
            title="⚔️ Combat Arena ⚔️",
            color=discord.Color.blue()
        )
        embed.description = "═" * 30
                
        buff_text_atk = ""
        buff_text_def = ""
            
        for effect, data in self.active_effects.items():
            if effect == 'attack':
                buff_text_atk = f" (+{data['value']})"
            elif effect == 'defense':
                buff_text_def = f" (+{data['value']})"
            
        player_status = [
            "",
            f"❤️ HP: {self.player['current_hp']}/{self.player['max_hp']}",
            "",
            f"⚔️ ATK: {int(self.player['atk'])}{buff_text_atk}",
            "",
            f"🛡️ DEF: {int(self.player['def'])}{buff_text_def}",
            "",
            f"💨 EVA: {self.player['eva']}",
            "",
            f"🍀 LUK: {self.player['luk']}",
            "",
            f"📊 EXP: {self.player['current_exp']}/100",
            ""
        ]
        
        embed.add_field(
            name=f"👤 Lv.{self.player['level']} {self.player['name']}",
            value="\n".join(player_status), 
            inline=True
        )
        
        monster_status = [
            "",
            f"❤️ HP: {self.monster.hp}",
            "",
            f"⚔️ ATK: {self.monster.atk}",
            "",
            f"🛡️ DEF: {self.monster.def_}",
            ""
        ]
        embed.add_field(
            name=f"👾 {self.monster.name}", 
            value="\n".join(monster_status), 
            inline=True
        )
        
        embed.add_field(
            name="═" * 30, 
            value="\n".join(self.combat_log) if self.combat_log else "Combat starting...",
            inline=False
        )
        
        return embed

    async def handle_player_death(self):
        HighScoreSystem.record_score(
            self.player['user_id'],
            self.player['name'],
            self.player['level'],
            await bot.fetch_user(int(self.player['user_id']))
        )
        
        with open(DBFILE, 'r') as f:
            data = json.load(f)
        del data[self.player['user_id']]
        with open(DBFILE, 'w') as f:
            json.dump(data, f, indent=4)
        
        death_embed = discord.Embed(
            title="💀 You Have Fallen!",
            description=(
                f"Your level {self.player['level']} journey has ended.\n"
                f"Your legacy has been recorded in the Hall of Champions."
            ),
            color=discord.Color.red()
        )
        
        if self.message:
            await self.message.edit(embed=death_embed, view=None)

    def save_player_data(self):
        with open(DBFILE, 'r+') as f:
            data = json.load(f)
            data[self.player['user_id']] = self.player
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    async def use_potion(self, interaction, pot_name):
        if self.player['pots'].get(pot_name, 0) <= 0:
            return

        pot_data = GameData.POTS[pot_name]
        self.player['pots'][pot_name] -= 1
        
        if pot_data['effect'] == 'heal':
            heal_amount = pot_data['value']
            old_hp = self.player['current_hp']
            self.player['current_hp'] = min(self.player['max_hp'], old_hp + heal_amount)
            actual_heal = self.player['current_hp'] - old_hp
            self.combat_log = [f"💚 Healed for {actual_heal} HP!"]
        
        elif pot_data['effect'] == 'damage':
            self.active_effects['damage'] = {
                'value': pot_data['value']
            }
            self.combat_log = ["💥 Preparing to use damage potion..."]
        
        else:
            self.active_effects[pot_data['effect']] = {
                'value': pot_data['value']
            }
            self.combat_log = [f"✨ {pot_data['effect'].title()} buff activated!"]

        self.save_player_data()
        await self.start_combat(interaction)

    async def show_pot_selection(self, interaction):
        if not any(self.player['pots'].values()):
            await interaction.response.send_message("You don't have any potions!", ephemeral=True)
            return

        pot_embed = discord.Embed(
            title="🧪 Select a Potion",
            color=discord.Color.blue()
        )

        pot_sections = []
        for pot_name, quantity in self.player['pots'].items():
            if quantity > 0:
                desc = GameData.POTS[pot_name]['description']
                pot_sections.append(f"{desc} (x{quantity})")
        
        pot_embed.description = "\n".join(pot_sections)
        view = PotionButtons(self, self.player['pots'])
        
        try:
            await interaction.response.edit_message(embed=pot_embed, view=view)
        except discord.InteractionResponded:
            await self.message.edit(embed=pot_embed, view=view)
    
    async def end_combat_session(self, interaction=None):
        self.is_combat_ended = True
        self.active_effects.clear()
        
        initial_exp = self.player['current_exp']
        initial_level = self.player['level']
        current_exp = self.player['current_exp']
        current_level = self.player['level']
        
        exp_gained = current_exp - initial_exp
        if current_level > initial_level:
            exp_gained += 100
        
        summary_embed = discord.Embed(
            title="⚔️ Combat Session Ended ⚔️",
            color=discord.Color.blue()
        )
        
        progress_text = [
            "**Session Progress:**",
            f"➤ Current Level: {current_level}",
            f"➤ EXP Progress: {current_exp}/100",
            f"➤ Total EXP Gained: {exp_gained}",
            "",
            "**Current Stats:**",
            f"❤️ HP: {self.player['current_hp']}/{self.player['max_hp']}",
            f"⚔️ ATK: {int(self.player['atk'])}",
            f"🛡️ DEF: {int(self.player['def'])}",
            f"💨 EVA: {self.player['eva']}",
            f"🍀 LUK: {self.player['luk']}"
        ]
        
        if current_level > initial_level:
            progress_text.insert(3, f"➤ Levels Gained: {current_level - initial_level}")
        
        summary_embed.add_field(
            name="📊 Progress Report",
            value="\n".join(progress_text),
            inline=False
        )
        
        inventory_text = [
            f"💰 Coins: {self.player['coins']}",
            "",
            "**Potions:**"
        ]
        
        for pot_name, quantity in self.player['pots'].items():
            if quantity > 0:
                inventory_text.append(f"🧪 {pot_name.replace('_', ' ').title()}: {quantity}")
        
        summary_embed.add_field(
            name="🎒 Current Inventory",
            value="\n".join(inventory_text),
            inline=False
        )
        
        summary_embed.set_footer(text="Thanks for playing! Use /combat to start a new session.")
        
        if interaction:
            try:
                await interaction.response.defer()
            except discord.InteractionResponded:
                pass
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                print(f"Error deferring interaction: {e}")
        
        await self.update_message(summary_embed)

class CombatButtons(discord.ui.View):
    def __init__(self, combat_system):
        super().__init__(timeout=None)
        self.combat_system = combat_system

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.success)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.combat_system.start_combat(interaction)

    @discord.ui.button(label="Use Potion", style=discord.ButtonStyle.primary)
    async def use_pot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(self.combat_system.player['pots'].values()):
            await interaction.response.send_message("You don't have any potions!", ephemeral=True)
            return
        await self.combat_system.show_pot_selection(interaction)

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.danger)
    async def exit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.combat_system.end_combat_session(interaction)

class PotionButtons(discord.ui.View):
    def __init__(self, combat_system, available_pots):
        super().__init__(timeout=None)
        self.combat_system = combat_system
        self.add_pot_buttons(available_pots)

    def add_pot_buttons(self, available_pots):
        pot_labels = {
            'heal_pot': '💚 Healing Pot',
            'atk_pot': '⚔️ Attack Pot',
            'def_pot': '🛡️ Defense Pot',
            'dmg_pot': '💥 Damage Pot'
        }

        for pot_name, quantity in available_pots.items():
            if quantity > 0:
                button = discord.ui.Button(
                    label=f"{pot_labels[pot_name]} ({quantity})",
                    style=discord.ButtonStyle.primary,
                    custom_id=pot_name
                )
                button.callback = self.create_callback(pot_name)
                self.add_item(button)

        exit_button = discord.ui.Button(
            label="Exit",
            style=discord.ButtonStyle.danger
        )
        exit_button.callback = self.exit_callback
        self.add_item(exit_button)

    def create_callback(self, pot_name: str):
        async def callback(interaction):
            await self.combat_system.use_potion(interaction, pot_name)
        return callback

    async def exit_callback(self, interaction):
        await self.combat_system.end_combat_session(interaction)

@bot.tree.command(name="combat", description="Enter combat with a monster")
async def combat(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if not Utils.user_has_character(user_id):
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return

    with open(DBFILE, 'r') as f:
        data = json.load(f)
        player_data = data[user_id]

    combat_system = CombatSystem(player_data)
    await combat_system.start_combat(interaction)

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

def run_bot():
    load_dotenv()
    token = os.getenv('DISCORD_BOT_TOKEN')
    bot.run(token)

run_bot()