import math
import datetime

from mysql import MySQL
from player import Player
from pokemon import Pokemon
from battle import Battle
from datetime import timedelta

class Spawn:
	def __init__(self):
		self.spawned = False
		self.name = ''
		self.pId = 0
		self.fought = []
		self.trainer = [False, 0]
		self.isBoss = False, None
		self.lastAct = [datetime.datetime.now(), 60]
		self.restSpawn = 0

	