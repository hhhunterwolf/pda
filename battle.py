import math
import random
import datetime

from pokemon import Pokemon
from mysql import MySQL

defaultPower = 75
defaultCritModifier = 1.5
expModifier = 2.5
boostModifier = 0.5

# This should probably be in a utils file. Logs should be done via a log lib. Meh.

M_TYPE_INFO = 'INFO'
M_TYPE_WARNING = 'WARNING'
M_TYPE_ERROR = 'ERROR'

class Battle:
	PLAYER_HANDICAP = 1.5

	def getModifiers(self, playerHandicap=False):
		cursor = MySQL.getCursor()

		for pokeType1 in self.challenger1.types:
			tempMod = 0
			for pokeType2 in self.challenger2.types:
				cursor.execute("""
					SELECT damage_factor 
					FROM type_efficacy 
					WHERE damage_type_id = %s
					AND target_type_id = %s
					""", (pokeType1.tId, pokeType2.tId))
				row = cursor.fetchone()
				tempMod = row['damage_factor']
				if self.modifier1 == 200 and tempMod == 200:
					self.modifier1 = 400
				else:
					self.modifier1 = max(self.modifier1, tempMod)
		self.modifier1 = self.modifier1/100
		if playerHandicap:
			self.modifier1 *= Battle.PLAYER_HANDICAP

		for pokeType1 in self.challenger2.types:
			tempMod = 0
			for pokeType2 in self.challenger1.types:
				cursor.execute("""
					SELECT damage_factor 
					FROM type_efficacy 
					WHERE damage_type_id = %s
					AND target_type_id = %s
					""", (pokeType1.tId, pokeType2.tId))
				row = cursor.fetchone()
				tempMod = row['damage_factor']
				if self.modifier2 == 200 and tempMod == 200:
					self.modifier2 = 400
				else:
					self.modifier2 = max(tempMod, self.modifier2)
		self.modifier2 = self.modifier2/100

	def __init__(self, challenger1, challenger2, boost=None, gym=False):
		random.seed()
		self.boost = boost
		self.gym = gym
		self.damageDealt = {
			'winner' : 0,
			'loser' : 0
		}

		# Handicap is for players against wild pokemon. This code is a mess.
		playerHandicap = challenger1.wild==1.5 and challenger2.wild==1 and not gym
		
		# print(datetime.datetime.now(), M_TYPE_INFO, 'Initializing battle between {} ({}) and {} ({}).'.format(challenger1.name, challenger1.pokeStats.level, challenger2.name, challenger2.pokeStats.level))
		speed1 = challenger1.pokeStats.current['speed']
		if playerHandicap:
			speed1 *= Battle.PLAYER_HANDICAP
		speed2 = challenger2.pokeStats.current['speed']
		
		self.challenger1, self.challenger2 = challenger1, challenger2
		self.modifier1, self.modifier2 = 0, 0
		self.getModifiers(playerHandicap)
		# print(datetime.datetime.now(), M_TYPE_INFO, 'Type modifier for {} is {} and for {} is {}.'.format(challenger1.name, self.modifier1, challenger2.name, self.modifier2))
		if speed2 > speed1:
			self.challenger1, self.challenger2 = self.challenger2, self.challenger1
			self.modifier1, self.modifier2 = self.modifier2, self.modifier1
		
		#print(datetime.datetime.now(), M_TYPE_INFO, challenger1)
		#print(datetime.datetime.now(), M_TYPE_INFO, challenger2)

	def getDamage(self, challenger1, challenger2, modifier):
		return math.floor(((((0.4*challenger1.pokeStats.level + 2) * defaultPower * (challenger1.pokeStats.current['attack'] / challenger2.pokeStats.current['defense']))/50) + 2) * modifier)

	def executeTurn(self, challenger1, challenger2, modifier):
		rand = random.randint(1, 100)
		if rand>=85:
			return 0, True, False, False
		rand = random.randint(85, 100)/100
		crit = defaultCritModifier if random.random() <= 0.0625 else 1
		damage = self.getDamage(challenger1, challenger2, modifier*rand*crit)
		return damage, False, crit>1, challenger2.damage(damage)

	def executeCycle(self):
		damage1 = []
		damage2 = []

		while True:
			damage, miss, critical, ko = self.executeTurn(self.challenger1, self.challenger2, self.modifier1)
			damage1.append([damage, miss, critical])
			if ko:
				return self.challenger1, self.challenger2, damage1, damage2
			damage, miss, critical, ko = self.executeTurn(self.challenger2, self.challenger1, self.modifier2)
			damage2.append([damage, miss, critical])
			if ko:
				return self.challenger2, self.challenger1, damage2, damage1

	def getDamageInfo(self, damage):
		if len(damage)==0:
			return 0, 0, 0, 0

		totalDamage = 0
		critCount = 0
		missCount = 0
		for d in damage:
			totalDamage += d[0]
			if d[1]:
				missCount += 1
			if d[2]:
				critCount += 1
		return totalDamage, totalDamage/len(damage), missCount, critCount

	def getYieldExp(self, pokemon1, pokemon2):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT experience 
			FROM pokemon_yield_ev 
			WHERE pokemon_id = %s
			""", (pokemon2.pId, ))
		baseExp = cursor.fetchone()['experience']
		return int(expModifier * math.floor((pokemon2.wild * baseExp * pokemon2.pokeStats.level)/7))

	def execute(self):
		winner, loser, damage1, damage2 = self.executeCycle()
		totalDamage, averageDamage, missCount, critCount = self.getDamageInfo(damage1)
		self.damageDealt['winner'] = totalDamage
		msg = ('```xl\n{} hit {} times.\nTotal of {} damage.\n{} misses / {} critical hits.\n'.format(winner.name, len(damage1), totalDamage, missCount, critCount))
		msg += '\n'
		totalDamage, averageDamage, missCount, critCount = self.getDamageInfo(damage2)
		self.damageDealt['loser'] = totalDamage
		msg += ('{} hit {} times.\nTotal of {} damage.\n{} misses / {} critical hits.\n'.format(loser.name, len(damage2), totalDamage, missCount, critCount))

		msg += '\n'
		msg += ('{} (HP: {}/{}) wins.\n'.format(winner.name, winner.pokeStats.hp, winner.pokeStats.current['hp']))
		
		exp = self.getYieldExp(winner, loser)
		bonusExp = 0
		if self.boost and self.boost == winner:
			bonusExp = int(exp * boostModifier)
		
		if winner.pokeStats.level < 100 and not self.gym and not winner.isWild():
			msg += '\n'
			bonusMsg = ''
			if bonusExp > 0:
				bonusMsg = ' (+' + str(bonusExp) + ' boost)'
			msg += ('{} earned '.format(winner.name) + str(exp) + bonusMsg + ' EXP points.\n')
		#print(datetime.datetime.now(), M_TYPE_INFO, msg)
		msg += '```'

		name = winner.name
		# print(datetime.datetime.now(), M_TYPE_INFO, "{} wins.".format(name))
		if not self.gym:
			leveledUp, evolved = winner.addExperience(exp+bonusExp)
		else:
			leveledUp, evolved = False, False
		levelUpMessage = None
		if leveledUp:
			levelUpMessage = ('{} leveled up to level {}!\n\n'.format(name, str(winner.pokeStats.level)))
			if evolved:
				levelUpMessage += ('What!? {} is evolving! It evolved into a {}!'.format(name, winner.name))
				#print(datetime.datetime.now(), M_TYPE_INFO, winner)
		
		if levelUpMessage:
			#print(datetime.datetime.now(), M_TYPE_INFO, levelUpMessage)
			pass

		return winner, msg, levelUpMessage
