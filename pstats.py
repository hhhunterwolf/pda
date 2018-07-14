import math

class PokeStats:
	def getStatValue(self, baseStat, iv):
		return math.floor((2*baseStat + iv)*self.level/100) + 5

	def getHPValue(self, baseStat, iv):
		return math.floor(((2*baseStat + iv)*self.level)/100) + self.level + 10

	def __init__(self, stats, level, iv, hp):
		self.level = level
		self.base = stats
		self.current = {}
		self.fakeCurrent = {}
		self.iv = {}

		self.iv['hp'] = iv['hp']
		self.current['hp'] = self.getHPValue(stats['hp'], iv['hp'])
		self.fakeCurrent['hp'] = self.current['hp']
		self.hp = self.current['hp'] if hp==-1 else hp

		self.iv['attack'] = iv['attack']
		self.iv['special-attack'] = iv['special-attack']
		self.fakeCurrent['attack'] = self.getStatValue(stats['attack'], iv['attack'])
		self.fakeCurrent['special-attack'] = self.getStatValue(stats['special-attack'], iv['special-attack'])
		self.current['attack'] = (stats['attack'] + stats['special-attack'])/2

		self.iv['defense'] = iv['defense']
		self.iv['special-defense'] = iv['special-defense']
		self.fakeCurrent['defense'] = self.getStatValue(stats['defense'], iv['defense'])
		self.fakeCurrent['special-defense'] = self.getStatValue(stats['special-defense'], iv['special-defense'])
		self.current['defense'] = (stats['defense'] + stats['special-defense'])/2

		self.iv['speed'] = iv['speed']
		self.current['speed'] = self.getStatValue(stats['speed'], iv['speed'])
		self.fakeCurrent['speed'] = self.current['speed']