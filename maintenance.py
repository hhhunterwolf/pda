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
from pserver import PokeServer

TOKEN = os.environ['PDA_TOKEN']

client = discord.Client()

playerMessageMap = {}
messageThreshold = 1.5

playerMap = {}

M_TYPE_INFO = 'INFO'
M_TYPE_WARNING = 'WARNING'
M_TYPE_ERROR = 'ERROR'

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
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()
	except KeyError as err:
		return

	content = message.content.lower()
	if content.startswith(commandPrefix):
		key = message.author.id
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
		print('Found server \'{}\' in database. Fetching configs.'.format(server.id))
		commandPrefix = row['prefix']
		spawnChannel = row['spawn_channel']
	else:
		print('Server \'{}\' was not found in database. Adding.'.format(server.id))
		cursor.execute("""
		INSERT INTO server (id)
		VALUES (%s)"""
		, (server.id,))
		
	serverMap[server.id] = PokeServer(id=server.id, commandPrefix=commandPrefix.lower(), spawnChannel=spawnChannel)
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
