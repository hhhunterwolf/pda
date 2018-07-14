import math
import random

from pokemon import Pokemon
from battle import Battle
from mysql import MySQL
from player import Player

def main():
	#pokemon1 = Pokemon('eevee', 50, 1.5)
	#print(pokemon1)
	#pokemon2 = Pokemon('moltres', 30, 1)
	#print(pokemon2)
	#battle = Battle(pokemon1, pokemon2)
	#for i in range(1,2):
	#	battle.start()
	#player = Player(1)
	#print(player.getSelectedPokemon())

	cursor = MySQL.getCursor()
	cursor.execute("""
		SELECT * FROM type
		WHERE id <= 18
		""")

	lastPokemon = 1
	rows = cursor.fetchall()
	for row in rows:
		cursor.execute("""
			SELECT * 
			FROM type JOIN pokemon_type JOIN pokemon
			WHERE pokemon_type.type_id = type.id
			AND pokemon_type.pokemon_id = pokemon.id
			AND type.id = %s
			AND slot = 1
			AND pokemon_type.pokemon_id < 722
			AND pokemon.evolved_at_level > 30
			ORDER BY RAND()
			LIMIT 1
			""", (row['id'],))
		rowPokemon = cursor.fetchone()

		pokemon = Pokemon(name='', pokemonId=rowPokemon['pokemon_id'], level=100)
		
		cursor.execute("""
			INSERT INTO player_pokemon (id, player_id, pokemon_id, level, experience, current_hp, iv_hp, iv_attack, iv_defense, iv_special_attack, iv_special_defense, iv_speed, selected, caught_with)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""", (lastPokemon, "PDA", pokemon.pId, pokemon.pokeStats.level, pokemon.experience, pokemon.pokeStats.hp, pokemon.pokeStats.iv['hp'], pokemon.pokeStats.iv['attack'], pokemon.pokeStats.iv['defense'], pokemon.pokeStats.iv['special-attack'], pokemon.pokeStats.iv['special-defense'], pokemon.pokeStats.iv['speed'], 0, pokemon.caughtWith))		

		cursor.execute("""
			INSERT INTO gym (type, holder_id, pokemon_id)
			VALUES (%s, 'PDA', %s)
			""", (row['id'], lastPokemon))

		MySQL.commit()

		lastPokemon += 1

	MySQL.close()
  
if __name__== "__main__":
	main()