import MySQLdb

class MySQL:
	cnx = MySQLdb.connect(user='root', passwd='', host='127.0.0.1', db='pda')

	@staticmethod	
	def getCursor():
		return MySQL.cnx.cursor(MySQLdb.cursors.DictCursor)

	@staticmethod
	def commit():
		MySQL.cnx.commit()

	@staticmethod
	def close():
		MySQL.cnx.close()

