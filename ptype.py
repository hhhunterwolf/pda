from mysql import MySQL

class PokeType:
	def __init__(self, tId, identifier=None):
		self.tId = tId
		if not identifier:
			cursor = MySQL.getCursor()
			cursor.execute("""
				SELECT * FROM type
				WHERE id = %s
			""", (tId,))
			row = cursor.fetchone()
			identifier = row['identifier']

		self.identifier = identifier

	def __str__(self):
		return self.identifier