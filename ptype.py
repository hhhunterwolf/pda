class PokeType:
	def __init__(self, tId, identifier):
		self.tId = tId
		self.identifier = identifier

	def __str__(self):
		return self.identifier