import MySQLdb
import os

class Cursor:
    def execute(self, query, tuple=None):
        cnx = MySQLdb.connect(user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PASS'], host=os.environ['MYSQL_HOST'], db='pda')
        try:
            self.cursor = cnx.cursor(MySQLdb.cursors.DictCursor)
            self.cursor.execute(query, tuple)

        finally:
            cnx.commit()
            cnx.close()

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class MySQL:
    cnx = None

    @staticmethod
    def getCursor():
        return Cursor()

    # TODO remove these
    @staticmethod
    def commit():
        return

    @staticmethod
    def close():
        return
