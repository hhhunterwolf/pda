import textwrap
import datetime
import humanfriendly
import math
import string
import random
import sys

from pokemon import Pokemon
from pmove import Move
from pmove import MoveSet
from mysql import MySQL
from pitem import PokeItem
from pitem import Bag
from datetime import timedelta

class Player:
	START_MONEY = 3000
	HALLOWEEN = False # This should not be here...
	EXP_MOD = 3.5 * 2 # Remove after Christmas
	DAY_CARE_PRICE_MOD = 1.25
	DAY_CARE_TIME_MOD = 1.25 * 1000
	GYM_MODIFIER = 1.25
	MAX_LEVEL = 1000
	MAX_MONEY = 250000

	bagSizes = ['Small', 'Medium', 'Large', 'Extra Large']

	def strip_non_ascii(string):
	    ''' Returns the string without non ASCII characters'''
	    stripped = (c for c in string if 0 < ord(c) < 127)
	    return ''.join(stripped)

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
			self.selectedPokemon = Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], caughtWith=row['caught_with'], mega=row['is_mega']==1)

	def __init__(self, pId, name='Unknown'):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player 
			WHERE id = %s
			""", (pId,))
		row = cursor.fetchone()

		name = Player.strip_non_ascii(name)

		self.lastDuel = datetime.datetime.now() - timedelta(days=1)
		self.lastGym = datetime.datetime.now() - timedelta(days=1)
		self.selectedPokemon = None
		self.pId = pId
		self.badges = []
		self.lastBattle = {
			'pokemon' : None,
			'damage' : 0
		}
		self.dayCareRequest = None, 0
		self.release = None
		self.moveLearn = None
		self.bag = Bag(self.pId, 1)
		if row is not None:
			self.level = row['level']
			self.experience = row['experience']
			self.money = row['money']
			self.candy = row['candy']
			self.pokemonCaught = row['pokemon_caught']
			self.boost = row['exp_boost']
			self.name = row['name'] if row['name'] != '' else 'Unknown'
			self.bag.size = row['bag_size']

			cursor.execute("""
				SELECT *
				FROM badge JOIN type
				WHERE badge.gym_id = type.id
				AND player_id = %s
			""", (pId,))

			rows = cursor.fetchall()
			for row in rows:
				self.badges.append([row['gym_id'], row['identifier'].upper()])
			
			self.setSelectedPokemon()

		else:
			self.level = 1
			self.experience = 0
			self.money = Player.START_MONEY
			self.candy = 0
			self.pokemonCaught = 0
			self.boost = None
			self.name = name

			cursor.execute("""
				INSERT INTO player (id, name)
				VALUES (%s, %s)
				""", (pId, name))

			for i in range(0,PokeItem.NUMBER_OF_ITEMS):
				item = self.bag.getItem(i+1)
				item.quantity = 10 if i==0 else 0
				cursor.execute("""
					INSERT INTO player_item (player_id, item_id, quantity)
					VALUES (%s, %s, %s)
					""", (pId, i+1, item.quantity))
			
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
			AND player_pokemon.player_id = %s
			""", (self.pId, self.pId))
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
			AND player_pokemon.player_id = %s
			""", (self.pId,self.pId))
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

		expBoostStr = ''
		boostTime = self.getBoostTime()
		if boostTime>0:
			expBoostStr += "**\n50\% EXP Boost:** {} remaining.".format(humanfriendly.format_timespan(boostTime))

		candyStr = ''
		if Player.HALLOWEEN:
			candyStr = '\n**Candy:** {} 🍬'.format(self.candy)

		return textwrap.dedent("""
__General Stats:__

**Name:** %s
**Level:** %s
**Experience:** %d / %d%s
**Money:** %d₽ / %s₽%s
**Bag Size: **%s

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
			expBoostStr,
			self.money,
			self.getMoneyLimit(),
			candyStr,
			Player.bagSizes[self.bag.size-1],
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
				pokemon = Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], mega=row['is_mega']==1, inDayCare=row['in_day_care'], dayCareLevel=row['day_care_level'])
				self.removeFromDayCare(pokemon)
				pokemonList.append([pokemon, row['selected'], row['in_gym']])

		cursor.execute("""
			SELECT COUNT(*) 
			FROM player_pokemon
			WHERE player_id = %s
			""", (self.pId,))
		row = cursor.fetchone()

		pages = 1
		if row:
			pages = 1 + ((row['COUNT(*)']-1) // (pokemonPerPage))
		
		return pokemonList, pages

	def getDayCarePokemonList(self):
		pokemonPerPage = Player.pokemonPerPage

		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player_pokemon
			WHERE player_id = %s
			AND in_day_care IS NOT NULL
			ORDER BY in_day_care ASC
			""", (self.pId,))
		rows = cursor.fetchall()
		
		pokemonList = []
		if rows:
			for row in rows:
				pokemon = Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], mega=row['is_mega']==1, inDayCare=row['in_day_care'], dayCareLevel=row['day_care_level'])
				isDone, delta = self.removeFromDayCare(pokemon)
				if isDone:
					continue
				pokemonList.append([pokemon, delta, row['day_care_level']])

		return pokemonList

	def removeFromDayCare(self, pokemon):
		level = pokemon.dayCareLevel
		if not level:
			return True, 0
		timeAdded = pokemon.inDayCare
		cost, time = self.getDayCareCost(pokemon=pokemon, level=level)
		delta = datetime.datetime.now().timestamp() - timeAdded.timestamp()
		isDone = delta >= time
		remaining = round(time + timeAdded.timestamp() - datetime.datetime.now().timestamp())
		if isDone:
			pokemon.setLevel(level)
			self.commitPokemonToDB(pokemon)
			cursor = MySQL.getCursor()
			cursor.execute("""
				UPDATE player_pokemon
				SET in_day_care = NULL,
					day_care_level = NULL
				WHERE player_id = %s
				AND id = %s
				""", (self.pId, pokemon.ownId))
			MySQL.commit()

			pokemon.inDayCare = None
			pokemon.dayCareLevel = None

			return True, remaining

		return False, remaining

	def getFavoritePokemonList(self, page):
		pokemonPerPage = Player.pokemonPerPage

		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player_pokemon
			WHERE player_id = %s
			AND favorite IS NOT NULL
			ORDER BY favorite ASC
			LIMIT %s
			OFFSET %s
			""", (self.pId, pokemonPerPage, (pokemonPerPage*(page-1))))
		rows = cursor.fetchall()
		
		pokemonList = []
		if rows:
			for row in rows:
				pokemon = Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], mega=row['is_mega']==1, inDayCare=row['in_day_care'], dayCareLevel=row['day_care_level'])
				self.removeFromDayCare(pokemon)
				pokemonList.append([pokemon, row['selected'], row['in_gym']])

		cursor.execute("""
			SELECT COUNT(*) 
			FROM player_pokemon
			WHERE player_id = %s
			AND favorite IS NOT NULL
			""", (self.pId,))
		row = cursor.fetchone()

		pages = 1
		if row:
			pages = 1 + ((row['COUNT(*)']-1) // (pokemonPerPage))
		
		return pokemonList, pages

	# isFav and isDayCare cannot both be true. This sucks, yes, but XGH.
	def getPokemon(self, pId, isFav=False, returnSelected=True, isDayCare=False):
		cursor = MySQL.getCursor()
		if isFav:
			cursor.execute("""
				SELECT * 
				FROM player_pokemon
				WHERE player_id = %s
				AND favorite IS NOT NULL
				ORDER BY favorite ASC
				""", (self.pId,))
			rows = cursor.fetchall()

			row = None
			if rows:
				if pId <= len(rows):
					row = rows[pId-1]
			
		elif isDayCare:
			cursor.execute("""
				SELECT * 
				FROM player_pokemon
				WHERE player_id = %s
				AND in_day_care IS NOT NULL
				ORDER BY in_day_care ASC
				""", (self.pId,))
			rows = cursor.fetchall()

			row = None
			if rows:
				if pId <= len(rows):
					row = rows[pId-1]
		
		else:
			cursor.execute("""
				SELECT * 
				FROM player_pokemon
				WHERE player_id = %s
				AND id = %s
				""", (self.pId, pId))
			row = cursor.fetchone()

		if row:
			if row['id'] == self.getSelectedPokemon().ownId:
				return self.getSelectedPokemon(), False

			return Pokemon(name='', level=row['level'], wild=1.5, iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']}, experience=row['experience'], pokemonId=row['pokemon_id'], ownId=row['id'], currentHp=row['current_hp'], healing=row['healing'], caughtWith=row['caught_with'], mega=row['is_mega']==1, inDayCare=row['in_day_care'], dayCareLevel=row['day_care_level']), row['in_gym'] > 0 # You should fucking change this inGym trash, it SUCKS
		elif returnSelected:
			return self.getSelectedPokemon(), False
		else:
			return None, False
		
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
				healing = %s,
				is_mega = %s,
				in_day_care = %s,
				day_care_level = %s
			WHERE id = %s
			AND player_id = %s
			""", (pokemon.pId, pokemon.pokeStats.level, pokemon.experience, pokemon.pokeStats.hp, pokemon.healing, pokemon.mega, pokemon.inDayCare, pokemon.dayCareLevel, pokemon.ownId, self.pId))
		MySQL.commit()

	def update(self):
		cursor = MySQL.getCursor()
		cursor.execute("""
				UPDATE player
				SET name = %s,
					level = %s,
					experience = %s,
					money = %s,
					candy = %s,
					pokemon_caught = %s,
					exp_boost = %s,
					bag_size = %s
				WHERE id = %s
			""", (self.name, self.level, self.experience, self.money, self.candy, self.pokemonCaught, self.boost, self.bag.size, self.pId))

		for i in range(0,PokeItem.NUMBER_OF_ITEMS):
			item = self.bag.getItem(i+1)
			cursor.execute("""
				UPDATE player_item
				SET	quantity = %s
				WHERE player_id = %s
				AND item_id = %s 
				""", (item.quantity, self.pId, i+1))

		MySQL.commit()

	def addPokemonViaInstance(self, pokemon, selected=False):
		self.pokemonCaught += 1
		cursor = MySQL.getCursor()
		cursor.execute("""
			INSERT INTO player_pokemon (id, player_id, pokemon_id, level, experience, current_hp, iv_hp, iv_attack, iv_defense, iv_special_attack, iv_special_defense, iv_speed, selected, caught_with, is_mega, in_day_care, day_care_level)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""", (self.pokemonCaught, self.pId, pokemon.pId, pokemon.pokeStats.level, pokemon.experience, pokemon.pokeStats.hp, pokemon.pokeStats.iv['hp'], pokemon.pokeStats.iv['attack'], pokemon.pokeStats.iv['defense'], pokemon.pokeStats.iv['special-attack'], pokemon.pokeStats.iv['special-defense'], pokemon.pokeStats.iv['speed'], 1 if selected else 0, pokemon.caughtWith, 1 if pokemon.mega else 0, pokemon.inDayCare, pokemon.dayCareLevel))
		MySQL.commit()

		self.update()

		pokemon.ownId = cursor.lastrowid
		if selected:
			self.selectPokemon(pokemon.ownId)

	def addPokemon(self, level, name='', pokemonId=0, selected=False, mega=False, caughtWith=0):
		pokemon = None
		if pokemonId == 0:
			pokemon = Pokemon(name, level, 1.5)
		else:
			pokemon = Pokemon(name='', pokemonId=pokemonId, level=level, wild=1.5, mega=mega, caughtWith=caughtWith)
		
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

		return pokemon

	def getNextLevelExp(self):
		return self.calculateExp(self.level + 1)

	def calculateExp(self, level):
		exp = (88) * (level**3) - 15*(level**2) + 100*level - 140
		return exp if exp>0 else 0

	def calibrateLevel(self):
		while(True):
			nextLevel = self.level + 1
			if self.experience < self.calculateExp(nextLevel):
				break
			else:
				self.level += 1
		self.update()


	def addExperience(self, experience):
		if self.level == Player.MAX_LEVEL:
			return False

		self.experience += experience
		if self.experience >= self.getNextLevelExp():
			self.level += 1
			return True
		
		return False

	def getMoneyLimit(self):
		return Player.MAX_MONEY * self.bag.size

	def addMoney(self, money):
		if self.money + money <= self.getMoneyLimit():
			self.money += money

	def removeMoney(self, money):
		if(self.money >= money):
			self.money -= money
			self.update()
			return True
		return False

	def addCandy(self, candy):
		self.candy += candy

	def removeCandy(self, candy):
		if(self.candy >= candy):
			self.candy -= candy
			return True
		return False

	def addItem(self, id, amount=1):
		ret = self.bag.addItem(id, amount)
		self.update()
		return ret

	def hasSpace(self, id, amount=1):
		return self.bag.hasSpace(id, amount)

	def useItem(self, item):
		if self.bag.removeItem(item.id):
			if item.itemType == 1:
				pokemon = self.getSelectedPokemon()
				pokemon.pokeStats.hp += item.value
				pokemon.pokeStats.hp = pokemon.pokeStats.hp if pokemon.pokeStats.hp <= pokemon.pokeStats.current['hp'] else pokemon.pokeStats.current['hp']
				self.commitPokemonToDB()
			elif item.itemType == 2:
				self.boost = datetime.datetime.now() + timedelta(seconds=item.value)
			
			self.update()
			return item.itemType
		
		return None		

	def getBagLimit(self, id):
		return self.bag.getLimit(id)

	def getBoostTime(self):
		if self.boost:
			return (self.boost.timestamp() - datetime.datetime.now().timestamp())
		return 0

	def isBoosted(self):
		if self.getBoostTime()>0:
			return True
		else:
			self.boost = None
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

	def reselectPokemon(self):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player_pokemon
			WHERE player_id = %s
			AND in_gym = 0
			AND in_day_care is NULL
			""", (self.pId,))

		row = cursor.fetchone()
		self.selectPokemon(row['id'])

	def releasePokemon(self, pId):
		pokemon, inGym = self.getPokemon(pId)

		if inGym:
			return False

		cursor = MySQL.getCursor()
		cursor.execute("""
			DELETE 
			FROM player_pokemon
			WHERE player_id = %s
			AND id = %s
			""", (self.pId, pId))

		cursor.execute("""
			UPDATE player_pokemon
			SET id = id - 1
			WHERE player_id = %s
			AND id > %s
			""", (self.pId, pId))

		MySQL.commit()

		self.pokemonCaught -= 1
		self.update()

		if pId == self.getSelectedPokemon().ownId:
			self.reselectPokemon()
		else:
			cursor.execute("""
				SELECT * 
				FROM player_pokemon
				WHERE player_id = %s
				AND selected = 1
				""", (self.pId,))

			row = cursor.fetchone()
			self.getSelectedPokemon().ownId = row['id']
			
		return pokemon		

	def isGymLeader(self):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT COUNT(*) AS gyms
			FROM player_pokemon
			WHERE player_id = %s
			AND in_gym > 0
			""", (self.pId,))

		row = cursor.fetchone()
		return row and row['gyms']>0

	def getCaptureMod(self):
		mod = (math.log10(3*self.level+1)/3)
		isGymLeader = self.isGymLeader()
		return mod * Player.GYM_MODIFIER if isGymLeader else mod

	def addFavorite(self, pId):
		cursor = MySQL.getCursor()
		
		cursor.execute("""
			SELECT count(*) as favs 
			FROM player_pokemon 
			WHERE favorite IS NOT NULL
			AND player_id = %s
			""", (self.pId,))
		row = cursor.fetchone()

		cursor.execute("""
			UPDATE player_pokemon 
			SET favorite = %s
			WHERE player_id = %s
			AND id = %s
			""", (datetime.datetime.now(), self.pId, pId))
		MySQL.commit()

		favs = row['favs']
		pokemon, inGym = self.getPokemon(pId, returnSelected=False)
		if pokemon:
			return 'success', pokemon, favs+1
		else:
			return 'error', None, 0

	def removeFavorite(self, pId):
		pokemon, inGym = self.getPokemon(pId, True, False)

		if not pokemon:
			return False, None

		cursor = MySQL.getCursor()
		cursor.execute("""
			UPDATE player_pokemon 
			SET favorite = NULL
			WHERE player_id = %s
			AND id = %s
			""", (self.pId, pokemon.ownId))
		MySQL.commit()

		return True, pokemon

	def hasAllBadges(self):
		return len(self.badges) == 18

	def hasBadge(self, badgeId, badgeName):
		return [badgeId, badgeName.upper()] in self.badges

	def canMegaEvolvePokemon(self, pokemon=None):
		if not pokemon:
			pokemon = self.getSelectedPokemon()

		hasMega = False
		hasBadges = True
		hasLevel = False
		isMega = False

		hasMega = pokemon.canMegaEvolve()

		for t in pokemon.types:
			if not self.hasBadge(t.tId, t.identifier):
				hasBadges = False
				break
		
		isMega = pokemon.mega

		hasLevel = pokemon.pokeStats.level == 100

		return hasMega, hasBadges, isMega, hasLevel

	def megaEvolvePokemon(self, pokemon, evolution):
		self.preserveEvolutionMoves(pokemon, evolution)
		pokemon.megaEvolve(evolution)
		self.commitPokemonToDB(pokemon)

	def isPokemonOnDayCare(self, pId):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player_pokemon
			WHERE player_id = %s
			AND id = %s
			""", (self.pId, pId))
		row = cursor.fetchone()

		return row and row['in_day_care'] is not None

	# Returns [cost, time]
	def getDayCareCost(self, pId=0, level=0, pokemon=None):
		if not pokemon:
			pokemon, inGym = self.getPokemon(pId)

		deltaExp = int(pokemon.calculateExp(level) - pokemon.experience)

		cost = (500 + int(math.log10(1 + deltaExp)*level**2 + (deltaExp//100) ** 1.3))
	
		time = (500 + int(math.log10(1 + deltaExp)*level**2 + (deltaExp//100) ** 1.25))
		
		return cost, time

	def requestAddPokemonToDayCare(self, pId, level):
		alreadyIn = self.isPokemonOnDayCare(pId)
		pokemon, inGym = self.getPokemon(pId, returnSelected=False)
		if alreadyIn:
			return 'already_in', pokemon, None, 0

		if inGym:
			return 'in_gym', pokemon, None, 0

		if not pokemon:
			return 'invalid_id', None, None, 0

		if pokemon.pokeStats.level >= level:
			return 'higher_level', pokemon, None, 0

		cost, time = self.getDayCareCost(pId, level)
		self.dayCareRequest = pokemon, level
		return 'success', pokemon, cost, time

	def confirmAddPokemonToDayCare(self):
		pokemon, level = self.dayCareRequest
		if pokemon:
			cost, time = self.getDayCareCost(pokemon.ownId, level)
			if self.removeMoney(cost):
				cursor = MySQL.getCursor()
				cursor.execute("""
					UPDATE player_pokemon
					SET in_day_care = %s,
						day_care_level = %s,
						selected = 0
					WHERE player_id = %s
					AND id = %s
					""", (datetime.datetime.now(), level, self.pId, pokemon.ownId))
				MySQL.commit()

				if pokemon.ownId == self.getSelectedPokemon().ownId:
					self.reselectPokemon()
				
				self.dayCareRequest = None, 0
				return 'added', pokemon, level, cost, time
			else:
				return 'no_money', pokemon, level, cost, time
		return None, None, 0, 0, 0

	REWARD_STREAK_TIME = 12*60*60
	def giveUpvoteReward(self):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM player JOIN botlist_upvotes ON (player.id = botlist_upvotes.player_id)
			WHERE id = %s
		""", (self.pId,))

		row = cursor.fetchone()
		reward = None
		if row:
			reward = Reward()
			lastReward = row['last_reward']==0
			reward.streak = row['streak']
			item = None
			if lastReward:
				cursor.execute("""
					UPDATE botlist_upvotes
					SET last_reward = 1
					WHERE player_id = %s
					""", (self.pId,))
				MySQL.commit()

				reward.money = int(1000 + (math.log(self.level*500)) * (self.level*10) ** 1.35)
				self.addMoney(reward.money)

				if reward.streak%2 == 0:
					reward.item = PokeItem.getItem(11)
					if not self.addItem(10, 1):
						reward.full = True
				if reward.streak%3 == 0:
					reward.item = PokeItem.getItem(3)
					if not self.addItem(2, 5):
						reward.full = True
				if reward.streak%7 == 0:
					pokemonId = random.randint(1,Pokemon.NUMBER_OF_POKEMON+1)
					reward.pokemon = self.addPokemon(pokemonId=pokemonId, level=random.randint(5,100))
				if reward.streak%11 == 0:
					reward.item = PokeItem.getItem(8)
					if not self.self.addItem(7, 5):
						reward.full = True
				if reward.streak%23 == 0:
					reward.item = PokeItem.getItem(4)
					if not self.addItem(3):
						reward.full = True

		return reward

	def checkMove(self, move, pokemon=None):
		cursor = MySQL.getCursor()

		if not pokemon:
			pokemon = self.getSelectedPokemon()

		cursor.execute("""
			(SELECT pokemon_move.move_id FROM pokemon_move 
			JOIN move ON (pokemon_move.move_id = move.id)
			WHERE pokemon_id = %s
			AND move_id = %s
			AND enabled = 1
			AND learned_at_level <= %s)
			UNION
			(SELECT player_pokemon_move.move_id FROM player_pokemon_move 
			JOIN player_pokemon 
			ON (player_pokemon_move.player_id = player_pokemon.player_id 
			AND player_pokemon_move.pokemon_id = player_pokemon.id)
			WHERE player_pokemon_move.pokemon_id = %s
			AND player_pokemon_move.player_id = %s
			AND player_pokemon_move.move_id = %s
			)
		""", (pokemon.pId, move, pokemon.pokeStats.level, pokemon.ownId, self.pId, move))

		return cursor.fetchone() is not None

	def canLearnMove(self, move, pokemon=None):
		if not pokemon:
			pokemon = self.getSelectedPokemon()
		return move in pokemon.getMoves()

	def learnMove(self, move, pokemon=None, force=False):
		cursor = MySQL.getCursor()

		if not pokemon:
			pokemon = self.getSelectedPokemon()

		if not force and not self.canLearnMove(move, pokemon):
			return 'cannot_learn'

		if not force and self.checkMove(move, pokemon):
			return 'already_knows'

		cursor.execute("""
			INSERT INTO player_pokemon_move (player_id, pokemon_id, move_id)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE move_id = move_id
		""", (self.pId, pokemon.ownId, move))

		return 'learned'

	def getMoves(self, pokemon=None, levelLimit=False):
		cursor = MySQL.getCursor()

		if not pokemon:
			pokemon = self.getSelectedPokemon()

		moveSet = MoveSet()

		cursor.execute("""
			SELECT * FROM move 
			JOIN pokemon_move ON (move.id = pokemon_move.move_id)
			WHERE pokemon_id = %s
			AND enabled = True
			ORDER BY learned_at_level ASC
		""", (pokemon.pId,))
		rows = cursor.fetchall()

		for row in rows:
			learnedAtLevel = row['learned_at_level'] if row['learned_at_level'] else sys.maxsize
			moveSet.addMove(Move(row['id'], row['name'], row['description'], row['type_id'], row['base_power'], row['accuracy'], row['priority'], row['damage_class'], row['enabled'], learnedAtLevel, learnedAtLevel<=pokemon.pokeStats.level))
		
		cursor.execute("""
			SELECT move.id, move.name, move.description, move.type_id, move.accuracy, move.base_power, move.accuracy, move.priority, move.damage_class, move.enabled
			FROM player_pokemon_move 
			JOIN player_pokemon
			ON (player_pokemon_move.player_id = player_pokemon.player_id 
			AND player_pokemon_move.pokemon_id = player_pokemon.id)
			JOIN move
			ON (move.id = player_pokemon_move.move_id)
			WHERE player_pokemon_move.pokemon_id = %s
			AND player_pokemon_move.player_id = %s
			AND enabled = True
		""", (pokemon.ownId, self.pId))
		rows = cursor.fetchall()

		for row in rows:
			if moveSet.contains(row['id']):
				moveSet.setLearned(row['id'])
			else:
				moveSet.addMove(Move(row['id'], row['name'], row['description'], row['type_id'], row['base_power'], row['accuracy'], row['priority'], row['damage_class'], row['enabled'], sys.maxsize, True))

		return moveSet

	def setDefaultMoves(self, moves, pokemon=None):
		cursor = MySQL.getCursor()

		if not pokemon:
			pokemon = self.getSelectedPokemon()

		cursor.execute("""
			DELETE FROM player_pokemon_default_move
			WHERE player_id = %s
			AND pokemon_id = %s
		""", (self.pId, pokemon.ownId))

		for move in moves:
			cursor.execute("""
				INSERT INTO player_pokemon_default_move (pokemon_id, player_id, move_id)
				VALUES (%s, %s, %s)
			""", (pokemon.ownId, self.pId, move))

	def getDefaultMoves(self, pokemon=None):
		cursor = MySQL.getCursor()

		moves = []

		if not pokemon:
			pokemon = self.getSelectedPokemon()

		cursor.execute("""
			SELECT * FROM player_pokemon_default_move
			WHERE player_id = %s
			AND pokemon_id = %s
		""", (self.pId, pokemon.ownId))
		rows = cursor.fetchall()

		for row in rows:
			moves.append(row['move_id'])

		if not moves:
			moves = pokemon.getLatestNaturalMoves()

		return moves

	def getMove(self, moveId, pokemon=None):
		cursor = MySQL.getCursor()

		if not pokemon:
			pokemon = self.getSelectedPokemon()

		cursor.execute("""
			SELECT * FROM move 
			JOIN pokemon_move ON (move.id = pokemon_move.move_id)
			WHERE pokemon_id = %s
			AND move_id = %s
			AND enabled = True
		""", (pokemon.pId, moveId))
		row = cursor.fetchone()

		move = None
		canLearn = False
		if row:
			canLearn = True
		else:
			cursor.execute("""
				SELECT * FROM move 
				JOIN pokemon_move ON (move.id = pokemon_move.move_id)
				AND move_id = %s
				AND enabled = True
			""", (moveId,))
			row = cursor.fetchone()

		if row:
			learnedAtLevel = row['learned_at_level'] if row['learned_at_level'] else sys.maxsize
			move = Move(row['id'], row['name'], row['description'], row['type_id'], row['base_power'], row['accuracy'], row['priority'], row['damage_class'], row['enabled'], learnedAtLevel, learnedAtLevel<=pokemon.pokeStats.level and canLearn)
				
		cursor.execute("""
			SELECT move.id, move.name, move.description, move.type_id, move.accuracy, move.priority, move.damage_class, move.enabled
			FROM player_pokemon_move 
			JOIN player_pokemon
			ON (player_pokemon_move.player_id = player_pokemon.player_id 
			AND player_pokemon_move.pokemon_id = player_pokemon.id)
			AND move_id = %s
			JOIN move
			ON (move.id = player_pokemon_move.move_id)
			WHERE player_pokemon_move.pokemon_id = %s
			AND player_pokemon_move.player_id = %s
			AND enabled = True
			AND move_id = %s
		""", (moveId, pokemon.ownId, self.pId, moveId))
		row = cursor.fetchone()

		if move:
			if row:
				move.learned = True
			move.canLearn = canLearn

		return move

	def preserveEvolutionMoves(self, pokemon, evolution):
		cursor = MySQL.getCursor()

		cursor.execute("""
			SELECT * FROM pokemon_move
			WHERE pokemon_id = %s
			AND learned_at_level IS NOT NULL
			AND move_id NOT IN (
				SELECT move_id FROM pokemon_move
				WHERE pokemon_id = %s
				AND learned_at_level IS NOT NULL
			)
		""", (pokemon.pId, evolution.pId))
		rows = cursor.fetchall()

		moves = []
		for row in rows:
			self.learnMove(row['move_id'], pokemon, True)

		cursor.execute("""
			SELECT * FROM pokemon_move
			WHERE pokemon_id = %s
			AND learned_at_level <= %s
			AND move_id IN (
				SELECT move_id FROM pokemon_move
				WHERE pokemon_id = %s
				AND learned_at_level > %s
			)
		""", (pokemon.pId, pokemon.pokeStats.level, evolution.pId, pokemon.pokeStats.level))
		rows = cursor.fetchall()

		for row in rows:
			self.learnMove(row['move_id'], pokemon, True)

	def getBagQuest(self):
		cursor = MySQL.getCursor()

		quest = self.getQuest(1)
		if quest:
			quest.value = Pokemon(name='', pokemonId=quest.value, level=1)
		else:
			cursor.execute("""
				SELECT * FROM pokemon
				WHERE capture_rate = 255
				AND enabled = 1
				ORDER BY RAND()
				LIMIT 1
			""")
			row = cursor.fetchone()

			quest = self.addQuest(1, row['id'])
			quest.value = Pokemon(name='', pokemonId=row['id'], level=1)

		return quest

	def completeBagQuest(self, quest=None, qId=None):
		cursor = MySQL.getCursor()

		if not quest:
			quest = self.getBagQuest()

		if not qId:
			qId = quest.qId

		rates = [255, 190, 45, 3]
		if quest.status == 3:
			quest.completed = True
			quest.value = 1
		else:
			quest.status += 1
			cursor.execute("""
				SELECT * FROM pokemon
				WHERE capture_rate = %s
				AND enabled = 1
				ORDER BY RAND()
				LIMIT 1
			""", (rates[quest.status],))
			row = cursor.fetchone()
			quest.value = row['id']
		
		self.bag.size += 1
		self.update()
		self.updateQuest(qId, quest.status, quest.value, quest.completed)

	def addQuest(self, qId, value):
		cursor = MySQL.getCursor()
		cursor.execute("""
			INSERT INTO player_quest (quest_id, player_id, value)
			VALUES (%s, %s, %s)
		""", (qId, self.pId, value))

		return Quest(qId, row['status'], row['value'], row['completed'])

	def updateQuest(self, qId, status, value=None, completed=False):
		cursor = MySQL.getCursor()
		
		cursor.execute("""
			UPDATE player_quest 
			SET status = %s,
				value = %s,
				completed = %s
			WHERE player_id = %s
			AND quest_id = %s
		""", (status, value, completed, self.pId, qId))

	def getQuest(self, qId):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * FROM player_quest
			WHERE player_id = %s
			AND quest_id = 1
		""", (self.pId,))
		row = cursor.fetchone()

		quest = None
		if row:
			quest = Quest(qId, row['status'], row['value'], row['completed'])

		return quest

class Reward:
	def __init__(self):
		self.deltaTime = 0
		self.streak = 0
		self.money = 0
		self.pokemon = None
		self.rewarded = False
		self.alreadyCollected = False
		self.full = True

class Quest:
	def __init__(self, qId, status, value, completed):
		self.qId = qId
		self.status = status
		self.value = value
		self.completed = completed

