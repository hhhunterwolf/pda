import textwrap
import datetime

from pokemon import Pokemon
from mysql import MySQL
from pitem import PokeItem
from datetime import timedelta

class Player:
	def setSelectedPokemon(self):
		cursor = MySQL.getCursor()
		self.pokemonList = []
		cursor.execute("""
			SELECT * 
			FROM player_pokemon 
			WHERE player_id = %s 
			AND selected = 1
			""", (self.pId,))
		row = cursor.fetchone()
		if row:
			self.selectedPokemon = Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], caughtWith=row['caught_with'])

	def __init__(self, pId, name=''):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player 
			WHERE id = %s
			""", (pId,))
		row = cursor.fetchone()

		self.lastDuel = datetime.datetime.now() - timedelta(days=1)
		self.lastGym = datetime.datetime.now() - timedelta(days=1)
		self.selectedPokemon = None
		self.name = name
		self.pId = pId
		self.items = []
		self.badges = []
		if row is not None:
			self.level = row['level']
			self.experience = row['experience']
			self.money = row['money']
			self.pokemonCaught = row['pokemon_caught']
			self.boost = row['exp_boost']

			cursor.execute("""
				SELECT *
				FROM player_item JOIN item
				WHERE player_item.item_id = item.id
				AND player_id = %s
			""", (pId,))

			rows = cursor.fetchall()
			for row in rows:
				self.items.append(row['quantity'])

			cursor.execute("""
				SELECT *
				FROM badge JOIN type
				WHERE badge.gym_id = type.id
				AND player_id = %s
			""", (pId,))

			rows = cursor.fetchall()
			for row in rows:
				self.badges.append([row['gym_id'], row['identifier']])
			
			self.setSelectedPokemon()

		else:
			self.level = 1
			self.experience = 0
			self.money = 0
			self.pokemonCaught = 0
			self.boost = None

			cursor.execute("""
				INSERT INTO player (id, name)
				VALUES (%s, %s)
				""", (pId, name))

			for i in range(0,PokeItem.NUMBER_OF_ITEMS):
				self.items.append(10 if i==0 else 0)
				cursor.execute("""
					INSERT INTO player_item (player_id, item_id, quantity)
					VALUES (%s, %s, %s)
					""", (pId, i+1, self.items[i]))
			
			MySQL.commit()

	def __str__(self):
		averageLevel = 0

		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT AVG(level) AS average_level
			FROM player_pokemon
			WHERE player_id = %s
			""", (self.pId,))
		row = cursor.fetchone()
		if row:
			averageLevel = row['average_level'] if row['average_level'] else 0

		highLevelStr = '-'
		cursor.execute("""
			SELECT *
			FROM player_pokemon
			JOIN pokemon
			WHERE level = (
				SELECT MAX(level)
				FROM player_pokemon
				WHERE player_pokemon.player_id = %s
			)
			AND player_pokemon.pokemon_id = pokemon.id
			""", (self.pId,))
		row = cursor.fetchone()
		if row:
			highLevelStr = '{} (**ID:** {} / **Lv.:** {})'.format(row['identifier'].upper(), row['id'], row['level'])

		highIvStr = '-'
		cursor.execute("""
			SELECT player_pokemon.id, pokemon.identifier, (iv_hp + iv_attack + iv_defense + iv_special_attack + iv_special_defense + iv_speed) as iv
			FROM player_pokemon
			JOIN pokemon
			WHERE iv_hp + iv_attack + iv_defense + iv_special_attack + iv_special_defense + iv_speed = (
				SELECT MAX(iv_hp + iv_attack + iv_defense + iv_special_attack + iv_special_defense + iv_speed)
				FROM player_pokemon
				WHERE player_pokemon.player_id = %s
			)
			AND player_pokemon.pokemon_id = pokemon.id
			""", (self.pId,))
		row = cursor.fetchone()
		if row:
			highIvStr = '{} (**ID:** {} / **Average IV**: {})'.format(row['identifier'].upper(), row['id'], row['iv']//6)

		badgesStr = 'None, '
		badgesLength = ''
		if self.badges:
			badgesLength = ' ({})'.format(len(self.badges))
			badgesStr = ''
			for badge in self.badges:
				bId, bType = badge
				badgesStr += bType.upper() + ', '
		badgesStr = badgesStr[:-2]

		return textwrap.dedent("""
__General Stats:__

**Name:** %s
**Level:** %s
**Experience:** %d / %d
**Money:** %d₽

__Pokemon Stats:__

**Pokemons Caught:** %d
**Avg. Pokemon Lv.:** %d
**Highest Lv. Pokemon:**: %s
**Highest IV Pokemon:** %s

__Badges%s:__

%s.

__Pokeball Stats:__

""") % (
			self.name, 
			self.level,
			self.experience,
			self.calculateExp(self.level + 1),
			self.money,
			self.pokemonCaught,
			averageLevel,
			highLevelStr,
			highIvStr,
			badgesLength,
			badgesStr)

	def getSelectedPokemon(self):
		return self.selectedPokemon

	def hasStarted(self):
		return self.selectedPokemon is not None

	pokemonPerPage = 20
	def getPokemonList(self, page):
		pokemonPerPage = Player.pokemonPerPage

		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player_pokemon
			WHERE player_id = %s
			LIMIT %s
			OFFSET %s
			""", (self.pId, pokemonPerPage, (pokemonPerPage*(page-1))))
		rows = cursor.fetchall()
		
		pokemonList = []
		if rows:
			for row in rows:
				pokemonList.append([Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing']), row['selected'], row['in_gym']])

		cursor.execute("""
			SELECT COUNT(*) 
			FROM player_pokemon
			WHERE player_id = %s
			""", (self.pId,))
		row = cursor.fetchone()

		pages = 1
		if row:
			pages = int(row['COUNT(*)'] / (pokemonPerPage)) + 1
		
		return pokemonList, pages

	def getPokemon(self, pId):
		if pId == self.getSelectedPokemon().ownId:
			return self.getSelectedPokemon()

		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player_pokemon
			WHERE player_id = %s
			AND id = %s
			""", (self.pId, pId))
		row = cursor.fetchone()
		if row:
			if row['in_gym'] > 0:
				return False
				
			return Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], caughtWith=row['caught_with'])
		else:
			return self.getSelectedPokemon()
		
	def selectPokemon(self, ownId):
		cursor = MySQL.getCursor()
		cursor.execute("""
			UPDATE player_pokemon
			SET selected = 0
			WHERE player_id = %s
			AND selected = 1
			""", (self.pId,))

		cursor.execute("""
			UPDATE player_pokemon
			SET selected = 1
			WHERE id = %s
			AND player_id = %s
			""", (ownId,self.pId))
		MySQL.commit()

		self.setSelectedPokemon()

	def commitPokemonToDB(self, pokemon=None):
		cursor = MySQL.getCursor()
		
		if not pokemon:
			pokemon = self.getSelectedPokemon()

		cursor.execute("""
			UPDATE player_pokemon
			SET pokemon_id = %s,
				level = %s,
				experience = %s,
				current_hp = %s,
				healing = %s
			WHERE id = %s
			AND player_id = %s
			""", (pokemon.pId, pokemon.pokeStats.level, pokemon.experience, pokemon.pokeStats.hp, pokemon.healing, pokemon.ownId, self.pId))
		MySQL.commit()

	def update(self):
		cursor = MySQL.getCursor()
		cursor.execute("""
				UPDATE player
				SET level = %s,
					experience = %s,
					money = %s,
					pokemon_caught = %s,
					exp_boost = %s
				WHERE id = %s
			""", (self.level, self.experience, self.money, self.pokemonCaught, self.boost, self.pId))

		for i in range(0,PokeItem.NUMBER_OF_ITEMS):
			cursor.execute("""
				UPDATE player_item
				SET	quantity = %s
				WHERE player_id = %s
				AND item_id = %s 
				""", (self.items[i], self.pId, i+1))

		MySQL.commit()

	def addPokemonViaInstace(self, pokemon, selected=False):
		self.pokemonCaught += 1
		cursor = MySQL.getCursor()
		cursor.execute("""
			INSERT INTO player_pokemon (id, player_id, pokemon_id, level, experience, current_hp, iv_hp, iv_attack, iv_defense, iv_special_attack, iv_special_defense, iv_speed, selected, caught_with)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""", (self.pokemonCaught, self.pId, pokemon.pId, pokemon.pokeStats.level, pokemon.experience, pokemon.pokeStats.hp, pokemon.pokeStats.iv['hp'], pokemon.pokeStats.iv['attack'], pokemon.pokeStats.iv['defense'], pokemon.pokeStats.iv['special-attack'], pokemon.pokeStats.iv['special-defense'], pokemon.pokeStats.iv['speed'], 1 if selected else 0, pokemon.caughtWith))
		MySQL.commit()

		self.update()

		pokemon.ownId = cursor.lastrowid
		if selected:
			self.selectPokemon(pokemon.ownId)

	def addPokemon(self, level, name='', pokemonId=0, selected=False):
		pokemon = None
		if pokemonId == 0:
			pokemon = Pokemon(name, level, 1.5)
		else:
			pokemon = Pokemon(name='', pokemonId=pokemonId, level=level, wild=1.5)
		
		self.pokemonCaught += 1

		cursor = MySQL.getCursor()
		cursor.execute("""
			INSERT INTO player_pokemon (id, player_id, pokemon_id, level, experience, current_hp, iv_hp, iv_attack, iv_defense, iv_special_attack, iv_special_defense, iv_speed, selected, caught_with)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""", (self.pokemonCaught, self.pId, pokemon.pId, pokemon.pokeStats.level, pokemon.experience, pokemon.pokeStats.hp, pokemon.pokeStats.iv['hp'], pokemon.pokeStats.iv['attack'], pokemon.pokeStats.iv['defense'], pokemon.pokeStats.iv['special-attack'], pokemon.pokeStats.iv['special-defense'], pokemon.pokeStats.iv['speed'], 1 if selected else 0, pokemon.caughtWith))
		MySQL.commit()

		self.update()

		pokemon.ownId = self.pokemonCaught
		if selected:
			self.selectPokemon(pokemon.ownId)

	def getNextLevelExp(self):
		return self.calculateExp(self.level + 1)

	def calculateExp(self, level):
		exp = (233) * (level**3) - 15*(level**2) + 100*level - 140
		return exp if exp>0 else 0

	def addExperience(self, experience):
		if self.level == 50:
			return False

		self.experience += experience
		if self.experience >= self.getNextLevelExp():
			self.level += 1
			return True
		
		return False

	def addMoney(self, money):
		self.money += money

	def removeMoney(self, money):
		if(self.money >= money):
			self.money -= money
			return True
		return False

	def addItem(self, id):
		self.items[id] += 1
		self.update()
				
	def getUsableItems(self):
		usable = []
		for i in range(4, len(self.items)): # pokeballs are not usable
			quantity = self.items[i]
			if quantity > 0:
				usable.append(i)
		return usable

	def useItem(self, item):
		self.items[item.id-1] -= 1
		if item.itemType == 1:
			pokemon = self.getSelectedPokemon()
			pokemon.pokeStats.hp += item.value
			pokemon.pokeStats.hp = pokemon.pokeStats.hp if pokemon.pokeStats.hp <= pokemon.pokeStats.current['hp'] else pokemon.pokeStats.current['hp']
			self.commitPokemonToDB()
		elif item.itemType == 2:
			self.boost = datetime.datetime.now() + timedelta(seconds=item.value)
			self.update()

		return item.itemType

	def isBoosted(self):
		if self.boost:
			isBoosted = (datetime.datetime.now().timestamp()-self.boost.timestamp())>0
			if isBoosted:
				return True
			else:
				self.boost = None
				return False
		else:
			return False

	def addBadge(self, badge):
		if badge not in self.badges:
			self.badges.append(badge)
			cursor = MySQL.getCursor()
			cursor.execute("""
				INSERT INTO badge (player_id, gym_id)
				VALUES (%s, %s)
				""", (self.pId, badge[0]))
			MySQL.commit()
			return True
		return False