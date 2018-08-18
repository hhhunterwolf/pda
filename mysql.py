import MySQLdb
import os

class MySQL:
    cnx = None

    @staticmethod
    def getCursor():
        if not MySQL.cnx:
            MySQL.cnx = MySQLdb.connect(user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PASS'], host=os.environ['MYSQL_HOST'], db='pda')

        return MySQL.cnx.cursor(MySQLdb.cursors.DictCursor)


    @staticmethod
    def commit():
        MySQL.cnx.commit()

    @staticmethod
    def close():
        MySQL.cnx.close()

