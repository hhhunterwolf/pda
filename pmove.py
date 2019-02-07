import math
import sys
import operator

from ptype import PokeType

class Move:
	def calculateCost(self):
		powerMod = 100 * self.basePower if self.basePower else 0
		accuracyMod = 50 * self.accuracy if self.accuracy else 0
		damClasses = {
			'physical' : 2,
			'special' : 2,
			'status' : 7
		}
		damMod = 1000 * damClasses[self.damageClass]

		return powerMod + accuracyMod + damMod

	def __init__(self, mId, name, description, typeId, basePower, accuracy, priority, damageClass, enabled, learnedAtLevel=None, learned=False):
		self.mId = mId
		self.name = name
		self.description = description
		self.type = PokeType(typeId)
		self.basePower = basePower
		self.accuracy = accuracy
		self.priority = priority
		self.damageClass = damageClass
		self.enabled = enabled
		self.learnedAtLevel = learnedAtLevel
		self.learned = learned
		self.cost = self.calculateCost()

	def __str__(self):
		accStr = ''
		if self.accuracy:
			accStr = '\n**Accuracy:** {}'.format(self.accuracy)

		pwrStr = ''
		if self.basePower:
			pwrStr = '\n**Base Power:** {}'.format(self.basePower)

		return """**Id**: {}
				**Name:** {}
				**Description:** {}
				**Type:** {}
				**Damage Class:** {}{}{}
		""".replace('\t', '').format(self.mId, self.name.capitalize(), self.description, self.type.identifier.capitalize(), self.damageClass.capitalize(), pwrStr, accStr)

	def __repr__(self):
		return '{}-{} ({})'.format(self.mId, self.name, self.learned)

class MoveSet:
	def __init__(self):
		self.moveList = {}

	def addMove(self, move):
		self.moveList[move.mId] = move

	def removeMove(self, move):
		del self.moveList[move.mId]

	def getMove(self, mId):
		return self.moveList[mId]

	def getMoves(self):
		return [key for key, value in self.moveList.items()]

	def contains(self, mId):
		return mId in self.moveList

	def setLearned(self, mId):
		self.moveList[mId].learned = True

	MOVES_PER_PAGE = 20
	def getMoveSetString(self, default, level, page):
		#print(default)
		mag = ''
		if default:
			msg = '__Default Move Set__\n\n'
			for move in default:
				msg += '**{}.** {}\n'.format(move, self.moveList[move].name.capitalize())
			msg += '\n'

		sortedValues = sorted(self.moveList.values(), key=lambda move: (move.learnedAtLevel, -move.learned, move.mId))

		msg += '__List of Moves__\n\n'
		counter = 0
		for move in sortedValues:
			counter += 1
			if counter >= MoveSet.MOVES_PER_PAGE*(page-1) and counter < MoveSet.MOVES_PER_PAGE*(page):
				learned = '*not learned*'
				if move.learned and level < move.learnedAtLevel:
					learned = '*learned*'
				elif move.learnedAtLevel < sys.maxsize:
					learned = '*learned* at level {}'.format(move.learnedAtLevel) if move.learnedAtLevel <= level else '*learns at level {}*'.format(move.learnedAtLevel)
				elif move.learnedAtLevel == sys.maxsize:
					learned = '*learned*' if move.learned else '*not learned*'
				msg += '**{0}.** {3}{1}{3} ({2})\n'.format(move.mId, move.name.capitalize(), learned, '__' if move.learned else '')	

		#print(len(msg))
		return msg, 1 + ((len(self.moveList)-1)//MoveSet.MOVES_PER_PAGE)

	def __str__(self):
		return str([move for id, move in self.moveList.items()])

	def __repr__(self):
		return str([move for id, move in self.moveList.items()])
