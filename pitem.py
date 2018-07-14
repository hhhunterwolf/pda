class PokeItem:
	NUMBER_OF_ITEMS = 11

	def __init__(self, id, itemType, name, price, description, value):
		self.id = id
		self.name = name
		self.itemType = itemType
		self.price = price
		self.description = description
		self.value = value
		
	def __str__(self):
		return self.name