# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py
import textwrap
import discord
import random
import math
import asyncio
import datetime
import traceback
import humanfriendly
import os

from player import Player
from pokemon import Pokemon
from battle import Battle
from mysql import MySQL
from datetime import timedelta
from pitem import PokeItem

# TODO:
# Make shop for multiple items
# Fix pages for exactly %20 pokemon

TOKEN = os.environ['PDA_TOKEN']

client = discord.Client()

playerMessageMap = {}
messageThreshold = 1.5

playerMap = {}

async def send_maintenance(message):
	msg = 'Hello {0.author.mention}, PDA is currently under maintenance. It will be back on shortly with new updates! Sorry for the inconvenience, and thank you for your patience.'.format(message)
	em = discord.Embed(title='Ops!', description=msg, colour=0xDEADBF)
	em.set_footer(text='If you have any doubts, suggestions, or just wanna chat about the bot, send me a DM at Fairfruit#8973.')
	await client.send_message(message.channel, embed=em)

@client.event
async def on_message(message):
	await client.wait_until_ready()

	# we do not want the bot to reply to itself
	if message.author == client.user:
		return

	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	content = message.content.lower()
	if content.startswith(commandPrefix):
		key = message.author.id + message.server.id
		if not key in playerMap:
			playerMap[key] = Player(key, message.author.name)
			playerMessageMap[key] = 0

		lastMessage = playerMessageMap[key]
		deltaTime = datetime.datetime.now().timestamp() - lastMessage
		if deltaTime>messageThreshold:
			playerMessageMap[key] = datetime.datetime.now().timestamp()
			await send_maintenance(message)
			
serverMap = {}

@client.event
async def on_server_join(server):
	evaluate_server(server)

def evaluate_server(server):
	cursor = MySQL.getCursor()
	cursor.execute("""SELECT * FROM server WHERE id = %s""", (server.id,))
	row = cursor.fetchone()

	commandPrefix = 'p!'
	spawnChannel = None
	if row:
		print('Found server {} in database. Fetching configs.'.format(server.id))
		commandPrefix = row['prefix']
		spawnChannel = row['spawn_channel']
	else:
		print('Server was not {} found in database. Adding.'.format(server.id))
		cursor.execute("""
			INSERT INTO server (id)
			VALUES (%s)"""
			, (server.id,))

		cursor.execute("""
		SELECT * FROM type
		WHERE id <= 18
		""")

		rows = cursor.fetchall()
		for row in rows:
			random.seed()
			lastPokemon = random.getrandbits(24)

			cursor.execute("""
				SELECT *
				FROM (
					SELECT pokemon.id as pokemon_id, SUM(base_stat) as sum_var
				  FROM type JOIN pokemon_type JOIN pokemon JOIN pokemon_stat
				  WHERE pokemon_type.type_id = type.id
				  AND pokemon_type.pokemon_id = pokemon.id
				  AND pokemon_stat.pokemon_id = pokemon.id
				  AND type.id = %s
				  AND pokemon_type.pokemon_id < 722
				  GROUP BY pokemon.id
				) as temp
				WHERE sum_var > 450
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
				INSERT INTO gym (server_id, type_id, holder_id, pokemon_id)
				VALUES (%s, %s, 'PDA', %s)
				""", (server.id, row['id'], lastPokemon))

		MySQL.commit()

	serverMap[server.id] = [commandPrefix, spawnChannel]
	print('Done.')
	
@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

	for server in client.servers:
		evaluate_server(server)

	print('------')

client.run(TOKEN)
