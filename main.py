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

class SessionManager:
    active_sessions = {}

    @classmethod
    def start_session(cls, user_id: str, session_type: str) -> bool:
        if user_id in cls.active_sessions:
            return False
        cls.active_sessions[user_id] = session_type
        return True

    @classmethod
    def end_session(cls, user_id: str):
        if user_id in cls.active_sessions:
            del cls.active_sessions[user_id]

    @classmethod
    def get_session(cls, user_id: str) -> str:
        return cls.active_sessions.get(user_id)

class GameData:
    POTS = {
        'heal_pot': {
            'effect': 'heal',
            'value': 10,
            'chance': 0.5,
            'description': '💚 Heals 10 HP',
            'price': 50
        },
        'atk_pot': {
            'effect': 'attack',
            'value': 3,
            'chance': 0.6,
            'description': '⚔️ +3 ATK for next combat',
            'price': 60
        },
        'def_pot': {
            'effect': 'defense',
            'value': 3,
            'chance': 0.6,
            'description': '🛡️ +3 DEF for next combat',
            'price': 60
        },
        'dmg_pot': {
            'effect': 'damage',
            'value': [10, 20],
            'chance': 0.3,
            'description': '💥 10-20 damage to enemy',
            'price': 80
        }
    }
    
    SPECIAL_POTS = {
        'exp_pot': {
            'effect': 'exp',
            'value': 50,
            'description': '📊 Grants 50 EXP',
            'price': 250
        },
        'hp_pot_plus': {
            'effect': 'heal',
            'value': 50,
            'description': '💚 Heals 50 HP',
            'price': 100
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
            base_coins = random.randint(20, 50)
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
        self.atk = float(atk) if float(atk) % 1 != 0 else int(atk)
        self.def_ = float(def_) if float(def_) % 1 != 0 else int(def_)
        self.eva = float(eva) if float(eva) % 1 != 0 else int(eva)
        self.luk = float(luk) if float(luk) % 1 != 0 else int(luk)
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
        self.atk = round(self.atk + 0.6, 1)
        self.def_ = round(self.def_ + 0.5, 1)
        self.eva = round(self.eva + 0.7, 1)
        self.luk = round(self.luk + 0.5, 1)
        
        self.atk = int(self.atk) if self.atk % 1 == 0 else self.atk
        self.def_ = int(self.def_) if self.def_ % 1 == 0 else self.def_
        self.eva = int(self.eva) if self.eva % 1 == 0 else self.eva
        self.luk = int(self.luk) if self.luk % 1 == 0 else self.luk

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
            atk=atk,
            def_=def_,
            eva=eva,
            luk=luk,
            coins=0,
            pots={}
        )
        char.save_to_db()
        await interaction.response.send_message(f"Character {self.name.value} created successfully!", ephemeral=True)

class Monster:
    MONSTER_TYPES = {
        'Slime': {
            'base_hp': 20,
            'base_atk': 3,
            'base_def': 1,
            'atk_per_level': 0.5,
            'def_per_level': 0.3,
            'weight': 0.35
        },
        'Wolf': {
            'base_hp': 25,
            'base_atk': 4,
            'base_def': 2,
            'atk_per_level': 0.7,
            'def_per_level': 0.4,
            'weight': 0.35
        },
        'Goblin': {
            'base_hp': 30,
            'base_atk': 5,
            'base_def': 3,
            'atk_per_level': 0.8,
            'def_per_level': 0.5,
            'weight': 0.25
        },
        'Orc': {
            'base_hp': 35,
            'base_atk': 6,
            'base_def': 4,
            'atk_per_level': 1.0,
            'def_per_level': 0.6,
            'weight': 0.05
        }
    }

    def __init__(self, level):
        self.level = level
        monster_type = self._select_monster_type()
        stats = self.MONSTER_TYPES[monster_type]
        
        self.name = f"Lv.{level} {monster_type}"
        self.hp = min(100, int(stats['base_hp'] + (10 * (level - 1))))
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
    def __init__(self, player_data):
        self.player = player_data
        self.combat_log = []
        self.active_effects = {}
        self.message = None
        self.is_combat_ended = False
        self.initial_stats = {
            'level': self.player['level'],
            'atk': self.player['atk'],
            'def': self.player['def'],
            'eva': self.player['eva'],
            'luk': self.player['luk']
        }
        self.monster = None
        self.next_monster = None
        self.next_monster = self.generate_monster()

    def generate_monster(self):
        player_level = self.player['level']
        min_level = max(1, player_level - 2)
        max_level = player_level + 2
        possible_levels = list(range(min_level, max_level + 1))
        weights = []
        
        for level in possible_levels:
            if level == player_level:
                weights.append(0.4)
            elif level < player_level:
                weights.append(0.35 / len([l for l in possible_levels if l < player_level]))
            else:
                weights.append(0.25 / len([l for l in possible_levels if l > player_level]))
        
        monster_level = random.choices(possible_levels, weights=weights)[0]
        new_monster = Monster(monster_level)
        
        level_diff = monster_level - player_level
        scaling_factor = 1 + (0.1 * level_diff)
        
        if level_diff > 0:
            new_monster.atk = int(new_monster.atk * 0.9)
            new_monster.def_ = int(new_monster.def_ * 0.9)
        elif level_diff < 0:
            new_monster.atk = int(new_monster.atk * 1.1)
            new_monster.def_ = int(new_monster.def_ * 1.1)

        new_monster.hp = int(min(100, new_monster.hp * scaling_factor))
        return new_monster

    async def start_combat(self, interaction):
        self.is_combat_ended = False
        
        self.monster = self.next_monster
        self.next_monster = self.generate_monster()
        
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
        base_damage = self.total_atk - (self.monster.def_ * 0.5)
        damage_roll = random.uniform(0.8, 1.2)
        damage_to_monster = max(1, int(base_damage * damage_roll))
        
        crit_chance = min(0.25, self.player['luk'] * 0.01)
        if random.random() < crit_chance:
            damage_to_monster = int(damage_to_monster * 1.5)
            self.combat_log.append(f"💥 CRITICAL HIT! You deal {damage_to_monster} damage!")
        else:
            self.combat_log.append(f"🗡️ You deal {damage_to_monster} damage!")
        
        self.monster.hp = max(0, self.monster.hp - damage_to_monster)

    def monster_attack(self):
        base_monster_damage = self.monster.atk - (self.total_def * 0.5)
        monster_damage_roll = random.uniform(0.8, 1.2)
        damage_to_player = max(1, int(base_monster_damage * monster_damage_roll))
        
        if random.random() > (1 - min(0.75, self.player['eva'] * 0.015)):
            self.combat_log.append("✨ You evaded the attack!")
            return
        
        if random.random() < 0.10:
            damage_to_player = int(damage_to_player * 1.5)
            self.combat_log.append(f"💥 CRITICAL HIT! Monster deals {damage_to_player} damage!")
        else:
            self.combat_log.append(f"☠️ Monster deals {damage_to_player} damage!")
        
        self.player['current_hp'] = max(0, self.player['current_hp'] - damage_to_player)

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
    
    def calculate_exp_gain(self):
        level_diff = self.monster.level - self.player['level']
        base_exp = 10
        
        if level_diff > 0:
            exp_gain = base_exp * (1 + (level_diff * 0.5))
        elif level_diff < 0:
            exp_gain = max(1, base_exp * (1 + (level_diff * 0.3)))
        else:
            exp_gain = base_exp
            
        exp_gain *= (1 + (self.player['level'] * 0.1))
        
        return int(exp_gain)
    
    async def handle_victory(self):
        exp_gained = self.calculate_exp_gain()
        self.player['current_exp'] += exp_gained
        
        level_up_message = await self._process_level_up()
        loot = self._process_loot()
        await self._send_victory_message(exp_gained, loot, level_up_message)
        
    async def _process_level_up(self):
        if self.player['current_exp'] < 100:
            return ""
            
        initial_stats = {
            'atk': self.player['atk'],
            'def': self.player['def'],
            'eva': self.player['eva'],
            'luk': self.player['luk']
        }
        
        self._apply_level_up()
        return self._create_level_up_message(initial_stats)
        
    def _apply_level_up(self):
        self.player['level'] += 1
        self.player['current_exp'] = 0
        
        stat_increases = {
            'atk': 0.6,
            'def': 0.7,
            'eva': 0.4,
            'luk': 0.3
        }
        
        for stat, increase in stat_increases.items():
            self.player[stat] = round(self.player[stat] + increase, 1)
            if self.player[stat] % 1 == 0:
                self.player[stat] = int(self.player[stat])
        
        heal_amount = 40
        old_hp = self.player['current_hp']
        self.player['current_hp'] = min(self.player['max_hp'], old_hp + heal_amount)
        
    def _create_level_up_message(self, initial_stats):
        stat_changes = []
        for stat in ['atk', 'def', 'eva', 'luk']:
            if self.player[stat] != initial_stats[stat]:
                stat_changes.append(
                    f"{stat.upper()}: {initial_stats[stat]} → {self.player[stat]}"
                )
        
        return (
            "🎊 **LEVEL UP!**\n"
            f"You are now level {self.player['level']}!\n"
            f"**Stat Increases:**\n" +
            "\n".join(stat_changes) + "\n" +
            "Healed for 40 HP!"
        )
        
    def _process_loot(self):
        loot = LootSystem.generate_loot(self.player['luk'])
        self.player['coins'] += loot['coins']
        
        for pot, amount in loot['pots'].items():
            if pot not in self.player['pots']:
                self.player['pots'][pot] = 0
            self.player['pots'][pot] += amount
            
        return loot
        
    async def _send_victory_message(self, exp_gained, loot, level_up_message):
        victory_embed = discord.Embed(title="🎉 Victory!", color=discord.Color.green())
        next_monster_text = (
            f"\n**Next Monster:**\n"
            f"👾 {self.next_monster.name}\n"
            f"❤️ HP: {self.next_monster.hp} | "
            f"⚔️ ATK: {self.next_monster.atk} | "
            f"🛡️ DEF: {self.next_monster.def_}"
        )
        
        victory_embed.description = (
            f"You defeated the {self.monster.name}!\n\n"
            f"**Rewards:**\n"
            f"🔰 EXP: {exp_gained} ({self.player['current_exp']}/100)\n"
            f"💰 Coins: {loot['coins']}\n\n"
            f"{level_up_message}\n"
            f"{next_monster_text}"
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
        SessionManager.end_session(self.player['user_id'])
        
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

        pot_data = None
        if pot_name in GameData.POTS:
            pot_data = GameData.POTS[pot_name]
        elif pot_name in GameData.SPECIAL_POTS:
            pot_data = GameData.SPECIAL_POTS[pot_name]
        
        if not pot_data:
            return

        self.player['pots'][pot_name] -= 1
        
        if pot_data['effect'] == 'heal':
            heal_amount = pot_data['value']
            old_hp = self.player['current_hp']
            self.player['current_hp'] = min(self.player['max_hp'], old_hp + heal_amount)
            actual_heal = self.player['current_hp'] - old_hp
            self.combat_log = [f"💚 Healed for {actual_heal} HP!"]
        elif pot_data['effect'] in ['attack', 'defense']:
            self.active_effects[pot_data['effect']] = {
                'value': pot_data['value']
            }
            self.combat_log = [f"✨ {pot_data['effect'].title()} buff activated!"]
        elif pot_data['effect'] == 'damage':
            self.active_effects['damage'] = {
                'value': pot_data['value']
            }
            self.combat_log = ["💥 Preparing to use damage potion..."]

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

        player_stats = (
            f"**Your Stats:**\n"
            f"❤️ HP: {self.player['current_hp']}/{self.player['max_hp']}\n"
            f"⚔️ ATK: {self.player['atk']}\n"
            f"🛡️ DEF: {self.player['def']}\n"
        )
        pot_embed.add_field(
            name="Current Status",
            value=player_stats,
            inline=False
        )

        next_monster_text = (
            f"**Next Monster:**\n"
            f"👾 {self.next_monster.name}\n"
            f"❤️ HP: {self.next_monster.hp} | "
            f"⚔️ ATK: {self.next_monster.atk} | "
            f"🛡️ DEF: {self.next_monster.def_}"
        )
        pot_embed.add_field(
            name="Upcoming Enemy",
            value=next_monster_text,
            inline=False
        )

        pot_sections = []
        for pot_name, quantity in self.player['pots'].items():
            if quantity > 0:
                if pot_name in GameData.POTS:
                    desc = GameData.POTS[pot_name]['description']
                elif pot_name in GameData.SPECIAL_POTS:
                    desc = GameData.SPECIAL_POTS[pot_name]['description']
                else:
                    continue
                pot_sections.append(f"{desc} (x{quantity})")
        
        if pot_sections:
            pot_embed.add_field(
                name="Available Potions",
                value="\n".join(pot_sections),
                inline=False
            )

        view = PotionButtons(self, self.player['pots'])
        
        try:
            await interaction.response.edit_message(embed=pot_embed, view=view)
        except discord.InteractionResponded:
            await self.message.edit(embed=pot_embed, view=view)
    
    async def end_combat_session(self, interaction=None):
        self._cleanup_session()
        summary_embed = await self._create_session_summary()
        await self._send_session_summary(summary_embed, interaction)

    def _cleanup_session(self):
        self.is_combat_ended = True
        self.active_effects.clear()
        SessionManager.end_session(self.player['user_id'])

    def _get_stat_progress(self):
        stat_progress = []
        for stat in ['atk', 'def', 'eva', 'luk']:
            initial = self.initial_stats[stat]
            current = self.player[stat]
            if initial != current:
                stat_progress.append(f"➤ {stat.upper()}: {initial} → {current}")
        return stat_progress

    def _get_inventory_text(self):
        inventory_text = [
            f"💰 Coins: {self.player['coins']}",
            "",
            "**Potions:**"
        ]
        
        for pot_name, quantity in self.player['pots'].items():
            if quantity > 0:
                inventory_text.append(f"🧪 {pot_name.replace('_', ' ').title()}: {quantity}")
        return inventory_text

    async def _create_session_summary(self):
        current_level = self.player['level']
        current_exp = self.player['current_exp']
        levels_gained = current_level - self.initial_stats['level']
        
        embed = discord.Embed(
            title="⚔️ Combat Session Ended ⚔️",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Progress Report",
            value="\n".join([
                "**Session Progress:**",
                f"➤ Current Level: {current_level}",
                f"➤ EXP Progress: {current_exp}/100",
                f"➤ Levels Gained: {levels_gained}" if levels_gained > 0 else ""
            ]),
            inline=False
        )
        
        if levels_gained > 0:
            stat_progress = self._get_stat_progress()
            if stat_progress:
                embed.add_field(
                    name="📈 Stat Progress",
                    value="\n".join(stat_progress),
                    inline=False
                )
        
        inventory_text = self._get_inventory_text()
        embed.add_field(
            name="🎒 Current Inventory",
            value="\n".join(inventory_text),
            inline=False
        )
        
        embed.set_footer(text="Thanks for playing! Use /combat to start a new session.")
        return embed

    async def _send_session_summary(self, embed, interaction):
        if interaction:
            try:
                await interaction.response.defer()
            except (discord.InteractionResponded, discord.NotFound):
                pass
            except discord.HTTPException as e:
                print(f"Error deferring interaction: {e}")
        
        await self.update_message(embed, view=EndSessionButton())

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
            'dmg_pot': '💥 Damage Pot',
            'hp_pot_plus': '💚 Greater Healing Pot'
        }

        for pot_name, quantity in available_pots.items():
            if quantity > 0:
                button = discord.ui.Button(
                    label=f"{pot_labels.get(pot_name, pot_name.replace('_', ' ').title())} ({quantity})",
                    style=discord.ButtonStyle.primary,
                    custom_id=pot_name
                )
                button.callback = self.create_callback(pot_name)
                self.add_item(button)

        continue_button = discord.ui.Button(
            label="Continue Combat",
            style=discord.ButtonStyle.success
        )
        continue_button.callback = self.continue_callback
        self.add_item(continue_button)

        exit_button = discord.ui.Button(
            label="Exit Combat",
            style=discord.ButtonStyle.danger
        )
        exit_button.callback = self.exit_callback
        self.add_item(exit_button)

    def create_callback(self, pot_name: str):
        async def callback(interaction):
            await self.combat_system.use_potion(interaction, pot_name)
        return callback

    async def continue_callback(self, interaction):
        await self.combat_system.start_combat(interaction)

    async def exit_callback(self, interaction):
        await self.combat_system.end_combat_session(interaction)

class ShopSystem:
    def __init__(self, player_data):
        self.player = player_data
        self.message = None
        
    def create_shop_embed(self):
        embed = discord.Embed(
            title="🏪 Item Shop",
            description=(
                f"Your Coins: 💰 {self.player['coins']}\n"
                f"Current EXP: 📊 {self.player['current_exp']}/100"
            ),
            color=discord.Color.gold()
        )

        special_items = []
        for item_id, data in GameData.SPECIAL_POTS.items():
            special_items.append(
                f"**{data['description']}**\n"
                f"💰 Price: {data['price']} coins\n"
            )
        
        normal_items = []
        for item_id, data in GameData.POTS.items():
            normal_items.append(
                f"**{data['description']}**\n"
                f"💰 Price: {data['price']} coins\n"
            )

        if special_items:
            embed.add_field(
                name="✨ Special Items",
                value="\n".join(special_items),
                inline=False
            )
        
        if normal_items:
            embed.add_field(
                name="📦 Regular Items",
                value="\n".join(normal_items),
                inline=False
            )

        return embed

    async def show_shop(self, interaction):
        embed = self.create_shop_embed()
        view = ShopButtons(self)
        
        if not self.message:
            await interaction.response.send_message(embed=embed, view=view)
            self.message = await interaction.original_response()
        else:
            await self.message.edit(embed=embed, view=view)

    async def purchase_item(self, interaction, item_id):
        if not await self._validate_purchase(interaction, item_id):
            return

        item_price = self._get_item_price(item_id)
        self.player['coins'] -= item_price

        if item_id == 'exp_pot':
            await self._handle_exp_potion(interaction)
        else:
            await self._handle_regular_potion(interaction, item_id)
            
        self._save_player_data()

    async def _validate_purchase(self, interaction, item_id):
        item_data = GameData.SPECIAL_POTS.get(item_id) or GameData.POTS.get(item_id)
        
        if not item_data:
            await interaction.response.send_message(
                "❌ Invalid item!", 
                ephemeral=True
            )
            return False
            
        if self.player['coins'] < item_data['price']:
            await interaction.response.send_message(
                "❌ Not enough coins!", 
                ephemeral=True
            )
            return False
            
        return True

    def _get_item_price(self, item_id):
        item_data = (GameData.SPECIAL_POTS.get(item_id) or 
                    GameData.POTS.get(item_id))
        return item_data['price']

    async def _handle_exp_potion(self, interaction):
        initial_stats = self._apply_exp_potion()
        level_up_message = self._create_level_up_message(initial_stats)
        
        await self._save_and_show_exp_results(interaction, level_up_message)

    def _apply_exp_potion(self):
        initial_stats = None
        self.player['current_exp'] += GameData.SPECIAL_POTS['exp_pot']['value']
        
        while self.player['current_exp'] >= 100:
            if not initial_stats:
                initial_stats = self._capture_current_stats()
            
            self._apply_level_up()
            
        return initial_stats

    def _capture_current_stats(self):
        return {
            'atk': self.player['atk'],
            'def': self.player['def'],
            'eva': self.player['eva'],
            'luk': self.player['luk'],
            'level': self.player['level']
        }

    def _apply_level_up(self):
        self.player['level'] += 1
        self.player['current_exp'] -= 100
        
        stat_increases = {
            'atk': 0.6,
            'def': 0.7,
            'eva': 0.4,
            'luk': 0.3
        }
        
        for stat, increase in stat_increases.items():
            self.player[stat] = round(self.player[stat] + increase, 1)
            if self.player[stat] % 1 == 0:
                self.player[stat] = int(self.player[stat])

    def _create_level_up_message(self, initial_stats):
        if not initial_stats or self.player['level'] <= initial_stats['level']:
            return None
            
        stat_changes = []
        for stat in ['atk', 'def', 'eva', 'luk']:
            if self.player[stat] != initial_stats[stat]:
                stat_changes.append(
                    f"{stat.upper()}: {initial_stats[stat]} → {self.player[stat]}"
                )
        
        return (
            "🎊 **LEVEL UP!**\n"
            f"You are now level {self.player['level']}!\n"
            f"**Stat Increases:**\n" +
            "\n".join(stat_changes)
        )

    async def _handle_regular_potion(self, interaction, item_id):
        if item_id not in self.player['pots']:
            self.player['pots'][item_id] = 0
        self.player['pots'][item_id] += 1
        
        await interaction.response.defer()
        await self.show_shop(interaction)

    async def _save_and_show_exp_results(self, interaction, level_up_message):
        self._save_player_data()
        
        if level_up_message:
            embed = discord.Embed(
                title="📊 Experience Potion Used!",
                description=level_up_message,
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Shop Status",
                value=(
                    f"Your Coins: 💰 {self.player['coins']}\n"
                    f"Current EXP: 📊 {self.player['current_exp']}/100"
                ),
                inline=False
            )
            
            await interaction.response.edit_message(
                embed=embed,
                view=ShopButtons(self)
            )
            
            await asyncio.sleep(2)
            await self.show_shop(interaction)
        else:
            await interaction.response.defer()
            await self.show_shop(interaction)

    async def _save_and_refresh_shop(self, interaction):
        self._save_player_data()
        await self.show_shop(interaction)

    def _save_player_data(self):
        with open(DBFILE, 'r+') as f:
            data = json.load(f)
            data[self.player['user_id']] = self.player
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

class ShopButtons(discord.ui.View):
    def __init__(self, shop_system):
        super().__init__(timeout=None)
        self.shop = shop_system
        self.add_shop_buttons()

    def add_shop_buttons(self):
        for item_id, data in GameData.SPECIAL_POTS.items():
            button = discord.ui.Button(
                label=f"{item_id.replace('_', ' ').title()} ({data['price']}💰)",
                style=discord.ButtonStyle.primary,
                custom_id=item_id,
                disabled=self.shop.player['coins'] < data['price']
            )
            button.callback = self.create_callback(item_id)
            self.add_item(button)

        for item_id, data in GameData.POTS.items():
            button = discord.ui.Button(
                label=f"{item_id.replace('_', ' ').title()} ({data['price']}💰)",
                style=discord.ButtonStyle.secondary,
                custom_id=item_id,
                disabled=self.shop.player['coins'] < data['price']
            )
            button.callback = self.create_callback(item_id)
            self.add_item(button)

        exit_button = discord.ui.Button(
            label="Exit",
            style=discord.ButtonStyle.danger
        )
        exit_button.callback = self.exit_callback
        self.add_item(exit_button)

    def create_callback(self, item_id: str):
        async def callback(interaction):
            await self.shop.purchase_item(interaction, item_id)
        return callback

    async def exit_callback(self, interaction):
        SessionManager.end_session(self.shop.player['user_id'])
        await interaction.message.delete()

class ProfileButtons(discord.ui.View):
    def __init__(self, player_data):
        super().__init__(timeout=None)
        self.player = player_data
        self.add_healing_buttons()

    def add_healing_buttons(self):
        heal_pot_count = self.player['pots'].get('heal_pot', 0)
        greater_pot_count = self.player['pots'].get('hp_pot_plus', 0)

        heal_button = discord.ui.Button(
            label=f"Use Healing Pot ({heal_pot_count})",
            style=discord.ButtonStyle.primary,
            disabled=heal_pot_count == 0,
            custom_id='heal_pot'
        )
        heal_button.callback = self.create_heal_callback('heal_pot')
        
        greater_button = discord.ui.Button(
            label=f"Use Greater Healing ({greater_pot_count})",
            style=discord.ButtonStyle.primary,
            disabled=greater_pot_count == 0,
            custom_id='hp_pot_plus'
        )
        greater_button.callback = self.create_heal_callback('hp_pot_plus')
        
        exit_button = discord.ui.Button(
            label="Exit",
            style=discord.ButtonStyle.danger
        )
        exit_button.callback = self.exit_callback
        
        self.add_item(heal_button)
        self.add_item(greater_button)
        self.add_item(exit_button)

    def create_heal_callback(self, pot_type):
        async def callback(interaction):
            if self.player['pots'].get(pot_type, 0) > 0:
                pot_data = (GameData.POTS.get(pot_type) or 
                          GameData.SPECIAL_POTS.get(pot_type))
                
                heal_amount = pot_data['value']
                old_hp = self.player['current_hp']
                self.player['current_hp'] = min(self.player['max_hp'], 
                                              old_hp + heal_amount)
                self.player['pots'][pot_type] -= 1
                
                with open(DBFILE, 'r+') as f:
                    data = json.load(f)
                    data[self.player['user_id']] = self.player
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
                
                embed = discord.Embed(title=f"{self.player['name']}'s Profile", color=discord.Color.blue())
                embed.add_field(name="Level", value=self.player['level'], inline=True)
                embed.add_field(name="HP", value=f"{self.player['current_hp']}/{self.player['max_hp']}", inline=True)
                embed.add_field(name="EXP", value=self.player['current_exp'], inline=True)
                embed.add_field(name="Attack", value=self.player['atk'], inline=True)
                embed.add_field(name="Defense", value=self.player['def'], inline=True)
                embed.add_field(name="Evasion", value=self.player['eva'], inline=True)
                embed.add_field(name="Luck", value=self.player['luk'], inline=True)
                embed.add_field(name="Coins", value=self.player['coins'], inline=True)
                
                pots = "\n".join([f"{pot}: {quantity}" for pot, quantity in self.player['pots'].items()])
                embed.add_field(name="Potions", value=pots if pots else "None", inline=False)

                embed.set_thumbnail(url=interaction.user.avatar.url)
                embed.set_footer(text="Character Profile")

                await interaction.response.edit_message(
                    embed=embed,
                    view=ProfileButtons(self.player)
                )
            
        return callback

    async def exit_callback(self, interaction):
        await interaction.message.delete()

class EndSessionButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Okay", style=discord.ButtonStyle.primary)
    async def okay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

@bot.tree.command(name="shop", description="Browse and purchase items")
async def shop(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if not Utils.user_has_character(user_id):
        await interaction.response.send_message(
            "Create a character first!", 
            ephemeral=True
        )
        return

    current_session = SessionManager.get_session(user_id)
    if current_session:
        await interaction.response.send_message(
            f"You are currently in a {current_session} session. Complete or exit it first!", 
            ephemeral=True
        )
        return

    if not SessionManager.start_session(user_id, "shop"):
        await interaction.response.send_message(
            "You are already in a session!", 
            ephemeral=True
        )
        return

    with open(DBFILE, 'r') as f:
        data = json.load(f)
        player_data = data[user_id]

    shop_system = ShopSystem(player_data)
    await shop_system.show_shop(interaction)

@bot.tree.command(name="combat", description="Enter combat with a monster")
async def combat(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if not Utils.user_has_character(user_id):
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return

    current_session = SessionManager.get_session(user_id)
    if current_session:
        await interaction.response.send_message(
            f"You are currently in a {current_session} session. Complete or exit it first!", 
            ephemeral=True
        )
        return

    if not SessionManager.start_session(user_id, "combat"):
        await interaction.response.send_message(
            "You are already in a session!", 
            ephemeral=True
        )
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

    await interaction.response.send_message(
        embed=embed,
        view=ProfileButtons(char_data)
    )

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
            medal = medals[i-1] if i <= 3 else "🌟"
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