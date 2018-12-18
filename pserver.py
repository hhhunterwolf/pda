import datetime

from pspawn import Spawn
from datetime import timedelta

class PokeServer:
	def __init__(self, id, commandPrefix, spawnChannel, role):
		self.id = id
		self.commandPrefix = commandPrefix
		self.spawnChannel = spawnChannel
		self.spawn = Spawn()
		self.serverMessageMap = datetime.datetime.now().timestamp()
		self.role = role

	def __str__(self):
		return self.identifier

	def get_prefix_spawnchannel(self):
		return self.commandPrefix, self.spawnChannel