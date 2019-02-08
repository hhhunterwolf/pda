from mysql import MySQL

class PokeItem:
	NUMBER_OF_ITEMS = 11

	def getItem(id):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * FROM item
			WHERE id = %s
		""", (id,))
		row = cursor.fetchone()
		
		return PokeItem(row['id'], row['type'], row['name'], row['price'], row['description'], row['value'], row['limit'])

	def __init__(self, id, itemType, name, price, description, value, limit, quantity=0):
		self.id = id
		self.name = name
		self.itemType = itemType
		self.price = price
		self.description = description
		self.value = value
		self.limit = limit
		self.quantity = quantity
		
	def __str__(self):
		return self.name

	def __repr__(self):
		return self.name

class Bag:
	def __init__(self, pId, size):
		self.size = size

		cursor = MySQL.getCursor()

		cursor.execute("""
			SELECT *
			FROM player_item JOIN item
			WHERE player_item.item_id = item.id
			AND player_id = %s
		""", (pId,))

		rows = cursor.fetchall()

		self.itemList = []
		for row in rows:
			self.itemList.append(PokeItem(row['id'], row['type'], row['name'], row['price'], row['description'], row['value'], row['limit'], row['quantity']))

	def addItem(self, id, amount=1):
		item = self.itemList[id-1]

		hasSpace = self.hasSpace(id, amount)
		if hasSpace:
			item.quantity += amount
		return hasSpace

	def hasSpace(self, id, amount=1):
		item = self.itemList[id-1]
		return item.limit * self.size >= item.quantity + amount

	def removeItem(self, id, amount=1):
		if self.itemList[id-1].quantity - amount >= 0:
			self.itemList[id-1].quantity -= amount
			return True
		return False

	def getItem(self, id):
		return self.itemList[id-1]

	def getLimit(self, id):
		return int(self.itemList[id-1].limit * self.size/2)