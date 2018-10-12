import math
import random
import datetime

from pokemon import Pokemon
from battle import Battle
from mysql import MySQL
from player import Player

M_TYPE_INFO = 'INFO'
M_TYPE_WARNING = 'WARNING'
M_TYPE_ERROR = 'ERROR'

def main():
	cursor = MySQL.getCursor()
	while(True):
		cursor.execute("""
			SELECT *
			FROM player
			WHERE CHAR_LENGTH(id) = 36
			""")
		rows = cursor.fetchall()

		if rows:
			for row in rows:
				print(datetime.datetime.now(), M_TYPE_INFO, 'Found player \'{}\'. Merging.'.format(row['id']))
				playerId = row['id'][:-18]

				cursor.execute("""
					SELECT *
					FROM player
					WHERE id = %s
					""", (playerId,))
				newRow = cursor.fetchone()

				player = Player(playerId, row['name'])

				cursor.execute("""
					SELECT *
					FROM player_item
					WHERE player_id = %s
					""", (row['id'],))
				itemRows = cursor.fetchall()

				print(datetime.datetime.now(), M_TYPE_INFO, 'Merging items.')
				for itemRow in itemRows:
					player.addItem(itemRow['item_id']-1, itemRow['quantity'])

				cursor.execute("""
					SELECT *
					FROM player_pokemon
					WHERE player_id = %s
					""", (row['id'],))
				pokemonRows = cursor.fetchall()

				hasPokemon = False
				counter = 1
				for pokemonRow in pokemonRows:
					print(datetime.datetime.now(), M_TYPE_INFO, 'Merging pokemon: {}/{}'.format(counter, row['pokemon_caught']))
					hasPokemon = True
					pokemon = Pokemon(
										name='', 
										level=pokemonRow['level'], 
										pokemonId=pokemonRow['pokemon_id'], 
										experience=pokemonRow['experience'],
										mega=pokemonRow['is_mega']==1,
										caughtWith=pokemonRow['caught_with'],
										iv={
											'hp': pokemonRow['iv_hp'],
											'attack': pokemonRow['iv_attack'],
											'defense': pokemonRow['iv_defense'],
											'special-attack': pokemonRow['iv_special_attack'],
											'special-defense': pokemonRow['iv_special_defense'],
											'speed': pokemonRow['iv_speed']
										}
									)
					player.addPokemonViaInstace(pokemon)

					counter += 1
					if hasPokemon:
						player.selectPokemon(1)

				print(datetime.datetime.now(), M_TYPE_INFO, 'Merging player info.')
				player.addMoney(row['money'])
				player.addExperience(row['experience'])
				player.addCandy(row['candy'])
				player.calibrateLevel()

				print(datetime.datetime.now(), M_TYPE_INFO, 'Deleting old player.')
				cursor.execute("""
					DELETE 
					FROM player
					WHERE id = %s
					""", (row['id'],))
		else:
			break
  
if __name__== "__main__":
	main()
