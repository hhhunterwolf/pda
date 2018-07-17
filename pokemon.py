import textwrap
import random
import time
import datetime

from ptype import PokeType
from pstats import PokeStats
from mysql import MySQL
from datetime import timedelta

class Pokemon:
	def __init__(self, name, level, wild=1, iv=None, experience=0, pokemonId=0, ownId=0, currentHp=-1, healing=None, caughtWith=0):
		cursor = MySQL.getCursor()

		self.wild = wild
		self.ownId = ownId
		self.healing = healing
		self.caughtWith = caughtWith

		if pokemonId == 0:
			cursor.execute("""SELECT * FROM pokemon WHERE pokemon.identifier = %s""", (name,))		
			row = cursor.fetchone()
			pId = row['id']
		else:
			cursor.execute("""SELECT * FROM pokemon WHERE pokemon.id = %s""", (pokemonId,))		
			row = cursor.fetchone()
			name = row['identifier']
			pId = pokemonId

		self.name = name.upper()
		self.captureRate = row['capture_rate']

		cursor.execute("""
			SELECT * FROM `type` JOIN pokemon_type 
			WHERE pokemon_type.pokemon_id = %s 
			AND `type`.id = pokemon_type.type_id
			""", (pId,))		
		rows = cursor.fetchall()
		
		self.types = []
		for row in rows:
			t = PokeType(row['type_id'], row['identifier'])
			self.types.append(t)

		cursor.execute("""
			SELECT * FROM pokemon_stat  JOIN stat
			WHERE pokemon_stat.pokemon_id = %s 
			AND stat.id = pokemon_stat.stat_id
			""", (pId,))		
		rows = cursor.fetchall()
		
		stats = {}
		if not iv:
			iv = {}

		for row in rows:
			stats[row['identifier']] = row['base_stat']
			if row['identifier'] not in iv:
				iv[row['identifier']] = random.randint(1, 31)
		self.pokeStats = PokeStats(stats, level, iv, currentHp)

		self.pId = pId
		self.experience = experience if experience!=0 else self.calculateExp(level)

	def __str__(self):
		t = self.types[0].identifier
		ballList = ['Poke Ball', 'Great Ball', 'Ultra Ball', 'Master Ball']
		try: 
			t = t + ', ' + self.types[1].identifier
		except IndexError:
			pass

		ivAverage = 0
		for key, value in self.pokeStats.iv.items():
			ivAverage += value
		ivAverage = ivAverage // len(self.pokeStats.iv)

		isHealing, delta = self.isHealing()
		deltaStr = Pokemon.convertDeltaToHuman(delta)
		healingStr = '- **__Heals in *{}*__**'.format(deltaStr) if isHealing else ''

		return textwrap.dedent("""
__Information:__

**Pokedex:** %d
**Name:** %s
**Level:** %s
**Types:** %s
**Ball Used:** %s

__Stats and IV:__

**HP:** %d/%d (%d/31) %s
**Attack:** %d (%d/31)
**Defense:** %d (%d/31)
**Sp. Attack:** %d (%d/31)
**Sp. Defense:** %d (%d/31)
**Speed:** %d (%d/31)
**Average IV:** %d/31

__Experience:__

**Next level:** %d EXP""") % (
			self.pId, 
			self.name, 
			self.pokeStats.level,
			t,
			ballList[self.caughtWith-1] if self.caughtWith > 0 else 'Starter',
			self.pokeStats.hp,
			self.pokeStats.current['hp'], 
			self.pokeStats.iv['hp'],
			healingStr,
			self.pokeStats.fakeCurrent['attack'], 
			self.pokeStats.iv['attack'],
			self.pokeStats.fakeCurrent['defense'], 
			self.pokeStats.iv['defense'],
			self.pokeStats.fakeCurrent['special-attack'], 
			self.pokeStats.iv['special-attack'],
			self.pokeStats.fakeCurrent['special-defense'], 
			self.pokeStats.iv['special-defense'],
			self.pokeStats.current['speed'],
			self.pokeStats.iv['speed'],
			ivAverage,
			max(self.getNextLevelExp() - self.experience, 0) if self.pokeStats.level < 100 else 0)

	def damage(self, damage):
		if self.pokeStats.hp>damage:
			self.pokeStats.hp -= damage
			return False
		else:
			self.pokeStats.hp = 0
			return True

	def getNextLevelExp(self):
		return self.calculateExp(self.pokeStats.level + 1)

	def calculateExp(self, level):
		exp = (6/5) * (level**3) - 15*(level**2) + 100*level - 140
		return exp if exp>0 else 0

	def evolve(self, evolution):
		self.pId = evolution.pId
		self.name = evolution.name
		self.pokeStats = evolution.pokeStats
		self.types = evolution.types

	def hasEvolved(self):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * FROM pokemon
			WHERE pokemon.evolves_from_species_id = %s
			ORDER BY RAND()
			""", (self.pId,))		
		row = cursor.fetchone()

		if row:
			evolveLevel = row['evolved_at_level']
			if self.pokeStats.level >= evolveLevel:
				self.evolve(Pokemon(row['identifier'], self.pokeStats.level, self.wild, self.pokeStats.iv))
				return True

		return False

	def isWild(self):
		return self.wild==1

	ballRatios = [3, 3.5, 4, 255]
	def attemptCapture(self, ball):
		chance = ((2*self.pokeStats.current['hp']) * self.captureRate * Pokemon.ballRatios[ball]) / (3*self.pokeStats.current['hp'])
		random.seed()
		dice = random.randint(0, 225)
		print('Capture chance is: {}/{}'.format(dice, chance))
		return chance >= dice

	def addExperience(self, experience):
		if self.pokeStats.level == 100 or self.isWild():
			return [False, False]

		self.experience += experience
		if self.experience >= self.getNextLevelExp():
			self.pokeStats.level += 1
			self.evolve(Pokemon(self.name, self.pokeStats.level, self.wild, self.pokeStats.iv))
			return [True, self.hasEvolved()]
		else:
			return [False, False]

	healingTimeMultiplier = 3 # k*level seconds
	def isHealing(self):
		healing = self.healing
		deltaHp = 1 - (self.pokeStats.hp/self.pokeStats.current['hp'])
		healTime = Pokemon.healingTimeMultiplier*self.pokeStats.level*deltaHp
		if healing:
			deltaTime = datetime.datetime.now().timestamp() - healing.timestamp()
			healed = deltaTime <= healTime
			if healed == False:
				self.pokeStats.hp = self.pokeStats.current['hp']
			return healed, healTime - deltaTime
				
		return None, 0

	def convertDeltaToHuman(deltaTime):
		minutes = int(deltaTime/60)
		if minutes == 0:
			return '{} second(s)'.format(int(deltaTime))
		if minutes > 0:
			return '{} minute(s) and {} second(s)'.format(minutes, int(deltaTime - minutes*60))

	def isType(self, tId):
		if len(self.types)>1:
			return self.types[0].tId == tId
		else:
			return self.types[0].tId == tId or self.types[1].tId
