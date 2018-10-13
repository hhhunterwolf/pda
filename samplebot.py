# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py
import textwrap
import discord
import random
import math
import asyncio
import datetime
import traceback
import humanfriendly
import time
import os
import copy

from pserver import PokeServer
from player import Player
from pokemon import Pokemon
from battle import Battle
from mysql import MySQL
from datetime import timedelta
from pitem import PokeItem
from discord.ext import commands
from logging.handlers import TimedRotatingFileHandler

TOKEN = os.environ['PDA_TOKEN']

client = discord.Client()
trainerURL = 'https://yfrit.com/pokemon/Trainer_{}.png'
oakUrl = 'https://i.imgur.com/VbSBVi7.png'
grassUrl = 'https://i.imgur.com/zdeDVpY.png'
joyUrl = 'https://i.imgur.com/OIr3D6x.png'
pokeballUrl = 'https://i.imgur.com/2jQoEjs.png'
pokeMartUrl = 'https://i.imgur.com/RkJQOOh.png'

# This should probably be in a utils file. Logs should be done via a log lib. Meh.

M_TYPE_INFO = 'INFO'
M_TYPE_WARNING = 'WARNING'
M_TYPE_ERROR = 'ERROR'

def handle_exit():
	client.loop.run_until_complete(client.logout())
	for t in asyncio.Task.all_tasks(loop=client.loop):
		if t.done():
			t.exception()
			continue
		t.cancel()
		try:
			client.loop.run_until_complete(asyncio.wait_for(t, 5, loop=client.loop))
			t.exception()
		except asyncio.InvalidStateError:
			pass
		except asyncio.TimeoutError:
			pass
		except asyncio.CancelledError:
			pass
		except Exception:
			pass

while True: # Why do I do this to myself
	playerMap = {}
	
	def getImageUrl(pId, mega=False):
		if not mega:
			return 'https://yfrit.com/pokemon/{}.png'.format(pId)
		else:
			return 'https://yfrit.com/pokemon/{}-mega.png'.format(pId)

	async def send_greeting(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		msg = 'Hello {0.author.mention}, and welcome to Pokemon Discord Adventure! To start your wonderful journey, type {1}start to see the info about starter Pokemons!'.format(message, commandPrefix)
		em = discord.Embed(title='Welcome!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: ``Use {}start #`` to select a starter pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, msg)

	startersId = [1, 4, 7, 25, 152, 155, 158, 252, 255, 258, 387, 390, 393, 495, 498, 501, 650, 653, 656]
	def getStartersString():
		format_strings = ','.join(['%s'] * len(startersId))
		
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT *
			FROM pokemon
			WHERE id in (%s)
			""" % format_strings, tuple(startersId))

		rows = cursor.fetchall()

		msg = ''
		counter = 1
		for row in rows:
			msg += '**{}.** {}\n'.format(counter, row['identifier'].upper())
			counter += 1
		return msg

	async def select_starter(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
		
		msg = 'Hello {0.author.mention}, and welcome to Pokemon Discord Adventure! To begin your journey, you will have to choose a starter. That is easy! Type ``{1}start #``, where # is the number of one of the starter pokemon listed below: \n\n'.format(message, commandPrefix)
		msg += getStartersString()

		if player.hasStarted():
			msg = '{0.author.mention}, you have already selected a starter pokemon!'.format(message)
		else:
			temp = message.content.split(' ')
			
			option = None
			if len(temp)>1:
				option = int(temp[1])

			if option and option > 0 and option <= len(startersId):
				try:
					pId = startersId[option-1]
					msg = '{0.author.mention}, here\'s your level 5 starter Pokemon!'.format(message)
					player.addPokemon(pokemonId=pId, level=5, selected=True)
					await display_pokemon_info(message)
				except IndexError:
					pass

		em = discord.Embed(title='Choose your starter!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: Use {}start # to select a starter pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_pokemon_info(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		if player.hasStarted():
			temp = message.content.split(' ')
			
			option = None
			if len(temp)>1:
				option = int(temp[1])

			if option:
				pokemon, inGym = player.getPokemon(option)
			else:
				pokemon = player.getSelectedPokemon()
			
			em = discord.Embed(title='{}\'s Pokemon'.format(message.author.name), description=str(pokemon), colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
			em.set_footer(text='HINT: Use {0}pokemon to see your full list of Pokemon. Use {0}info # to see info of an unselected pokemon.'.format(commandPrefix))
			await client.send_message(message.channel, embed=em)
		else:
			await display_not_started(message, commandPrefix)

	async def display_success_add_favorite(message, pokemon, favId, commandPrefix):
		msg = '{0.author.mention}, your  *{1}* was added to your favorites with Fav. ID: **{2}**. Use ``{3}favorite {2}`` to select it, or just ``{3}favorite`` to list all favorite pokemon.'.format(message, pokemon.name, favId, commandPrefix)
		em = discord.Embed(title='Favorite added!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		await client.send_message(message.channel, embed=em)

	async def display_fail_add_favorite(message, pokemon, favId, commandPrefix):
		msg = '{0.author.mention}, your *{1}* is already in your favorite list with Fav ID: **{2}**. Use ``{3}favorite {2}`` to select it, or just ``{3}favorite`` to list all favorite pokemon.'.format(message, pokemon.name, favId, commandPrefix)
		em = discord.Embed(title='Could not add favorite...', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		await client.send_message(message.channel, embed=em)

	async def display_success_rem_favorite(message, pokemon, commandPrefix):
		msg = '{0.author.mention}, your  *{1}* was removed from your favorite list. Type ``{2}favorite`` to list all favorite pokemon.'.format(message, pokemon.name, commandPrefix)
		em = discord.Embed(title='Favorite removed!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		await client.send_message(message.channel, embed=em)

	async def display_fail_rem_favorite(message, favId, commandPrefix):
		msg = '{0.author.mention}, no favorite with Fav. ID: *{1}* was found. Type ``{2}favorite`` to list all favorite pokemon.'.format(message, favId, commandPrefix)
		em = discord.Embed(title='Could not remove favorite...', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=message.author.avatar_url)
		await client.send_message(message.channel, embed=em)

	async def display_fail_full_favorite(message, commandPrefix):
		msg = '{0.author.mention}, you already have the maximum amount of 20 favorites. Please remove a favorite before adding more.'.format(message)
		em = discord.Embed(title='Could not add favorite...', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=message.author.avatar_url)
		await client.send_message(message.channel, embed=em)

	async def display_favorite_pokemons(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
		if player.hasStarted():
			temp = message.content.split(' ')
			
			option = 1
			if len(temp)>2:
				option = temp[1]
				param = temp[2]
				if option.lower() == 'add':
					addResult, pokemon, favId = player.addFavorite(param)
					if addResult == 'success':
						await display_success_add_favorite(message, pokemon, favId, commandPrefix)
						return
					elif addResult == 'duplicate':
						await display_fail_add_favorite(message, pokemon, favId, commandPrefix)
						return
					elif addResult == 'full':
						await display_fail_full_favorite(message, commandPrefix)
						return
				elif option.lower() == 'remove':
					removeResult, pokemon = player.removeFavorite(param)
					if removeResult:
						await display_success_rem_favorite(message, pokemon, commandPrefix)
						return
					else:
						await display_fail_rem_favorite(message, param, commandPrefix)
						return
			elif len(temp)==2:
				option = int(temp[1])
				pokemon, inGym = player.getPokemon(option, True)
				if not inGym:
					player.selectPokemon(pokemon.ownId)
					message.content = ''
					await display_pokemon_info(message)
					return
				else:
					await display_pokemon_in_gym(message)
					return
				
			pokemonList = player.getFavoritePokemonList()

			string = ''
			counter = 1
			if len(pokemonList)>0:
				for pokemon, selected, inGym in pokemonList:
					avg = sum(pokemon.pokeStats.iv.values()) // 6
					string += ('**' if selected else '') + str(counter) + ': ' + pokemon.name + ' ID. {} Lv. {} IV. {}'.format(pokemon.ownId, pokemon.pokeStats.level, avg) + (' (selected)**' if selected else '') + (' *(holding gym {})*'.format(inGym) if inGym > 0 else '') + '\n'
					counter += 1
			else:
				string = 'No favorite pokemon.'

			msg = '{0.author.mention}, this is your favorite pokemon list. You can quickly select your favorite pokemon by typing ``{1}favorite #``, where # is one of the favorite pokemon listed below, if any. To add pokemon to your favorites, type ``{1}favorite add #``, where # is the pokemon id found in ``{1}pokemon``. Finally, to remove a pokemon from your favorites, type ``{1}favorite rem #``.\n\n'.format(message, commandPrefix)
			em = discord.Embed(title='{}\'s Favorite Pokemon List'.format(message.author.name), description=msg+string, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_footer(text='HINT: Favoriting pokemon is an easy way of organizing them.'.format(commandPrefix))
			await client.send_message(message.channel, embed=em)

	async def display_pokemons(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
		if player.hasStarted():
			temp = message.content.split(' ')
			
			option = None
			if len(temp)>1:
				option = int(temp[1])

			pokemonList = None
			curPage = 1
			pages = 1
			if not option:
				option = 1 + (player.getSelectedPokemon().ownId-1) // Player.pokemonPerPage

			curPage = option
			pokemonList, pages = player.getPokemonList(option)

			string = ''
			if len(pokemonList)>0:
				counter = ((curPage-1) * Player.pokemonPerPage) + 1
				for pokemon, selected, inGym in pokemonList:
					avg = sum(pokemon.pokeStats.iv.values()) // 6
					string += ('**' if selected else '') + str(counter) + ': ' + pokemon.name + ' Lv. {} IV. {}'.format(pokemon.pokeStats.level, avg) + (' (selected)**' if selected else '') + (' *(holding gym {})*'.format(inGym) if inGym > 0 else '') + '\n'
					counter += 1
			else:
				string = 'Invalid page.'

			em = discord.Embed(title='{}\'s Pokemon List'.format(message.author.name), description=string, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_thumbnail(url=message.author.avatar_url)
			em.set_footer(text='HINT: Page {}/{}. Use {}pokemon # to select a different page.'.format(curPage, pages, commandPrefix))
			await client.send_message(message.channel, embed=em)

	async def display_pokemon_in_gym(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		msg = '{0.author.mention}, that pokemon is currently holding a gym, it cannot be selected.'.format(message)
		em = discord.Embed(title='Cannot select!', description=str(msg), colour=0xDEADBF)
		em.set_thumbnail(url=message.author.avatar_url)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def display_release_success(message, pokemon):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		msg = '{0.author.mention}, your {1} was released back to the wild. It will probably die. Alone.'.format(message, pokemon.name)
		em = discord.Embed(title='Good bye!', description=str(msg), colour=0xDEADBF)
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def release_pokemon(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
		
		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			
			option = None
			if len(temp)>1:
				try:
					option = int(temp[1])
					if option and option > 0 and option <= player.pokemonCaught:
						try:
							em = check_hold_availability(message.author.mention, player, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							pokemon = player.releasePokemon(option)
							await display_release_success(message, pokemon)
						except IndexError as error:
							print(datetime.datetime.now(), M_TYPE_ERROR, error)
							traceback.print_exc()
				except ValueError as err:
					print(datetime.datetime.now(), M_TYPE_ERROR, err)

	async def select_pokemon(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
		
		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			
			option = None
			if len(temp)>1:
				try:
					option = int(temp[1])
					if option:
						try:
							pokemon, inGym = player.getPokemon(option)
							if not inGym:
								player.selectPokemon(pokemon.ownId)
								await display_pokemon_info(message)
							else:
								await display_pokemon_in_gym(message)
						except IndexError as error:
							print(datetime.datetime.now(), M_TYPE_ERROR, error)
							traceback.print_exc()
				except ValueError as err:
					print(datetime.datetime.now(), M_TYPE_ERROR, err)

	async def display_invite(message):
		try:
			commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()
		except KeyError as err:
			return

		msg = 'If you like this bot and wish to add it to your server, feel free to do it, but please keep in mind it is still in alpha state, so bugs, crashes and restarts will happen now and then. You can add the bot to your server with this link: https://discordapp.com/oauth2/authorize?client_id=463744693910372362&scope=bot.'

		em = discord.Embed(title='Invite the bot to your server!', description=msg, colour=0xDEADBF)
		footerMsg = 'HINT: Don\'t forget to set the spawn channel with the spawn command, otherwise wild pokemon will not spawn until you do. The bot also has an "anti-afk" system, in which spawn channels that don\'t receive messages for a while will stop having pokemon spawned.'
		em.set_footer(text=footerMsg)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def display_help(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		msg = 'Welcome to Pokemon Discord Adventure! This bot is in a very alpha state, and most things are still being worked on. Please expect it to crash, bug out and suddenly restart. If you have any questions, suggestions, or just want to have a chat, contact me at Discord Fairfruit#8973, or send me an email at contact@yfrit.com.\n\n' \
			'__Player Commands:__ \n' \
			'**{0}info or {0}i :** Shows stats of a specific pokemon (selected pokemon if none is specified) \n' \
			'**{0}start:** Shows information on how to select a starter and start the adventure. \n' \
			'**{0}pokemon or {0}p:** Shows a list of all your pokemon. \n' \
			'**{0}select or {0}s:** Selects a pokemon in your list to use on your journey.\n' \
			'**{0}favorite or {0}v:** Shows information on how to add pokemon to your favorite list.\n' \
			'**{0}release or {0}r:** Releases a pokemon in your list pokemon. It will never come back.\n' \
			'**{0}fight or {0}f:** Fights the currently spawned pokemon or poketrainer if available.\n' \
			'**{0}catch or {0}c:** Fights and tries to catch the currently spawned pokemon if available.\n' \
			'**{0}center or {0}h:** Heals wounded pokemon.\n' \
			'**{0}me:** Shows information on the player.\n' \
			'**{0}shop or {0}b:** Displays the shop. \n' \
			'**{0}item or {0}u:** Displays the player inventory. \n' \
			'**{0}duel or {0}d:** Challenges another player to a duel. \n' \
			'**{0}accept or {0}a:** Accepts a duel challenge. \n' \
			'**{0}gym or {0}g:** Shows information on the gyms. \n' \
			'**{0}mega:** Shows info on how to mega evolve pokemon. \n' \
			'**{0}rank:** Shows the top 10 players in the server. \n' \
			'**{0}ping:** Standard ping command. \n' \
			'**{0}trade:** Displays the Halloween Event Poke Mart. \n' \
			'**{0}donate:** Displays information on donations. \n\n' \
			'__Admin Commands:__ \n' \
			'**{0}prefix:** Changes the prefix used to trigger bot commands (default is p). \n' \
			'**{0}spawn:** Sets the channel where wild pokemon and poketrainers will spawn. \n'

		msg = msg.format(commandPrefix)
		em = discord.Embed(title='Help!', description=msg, colour=0xDEADBF)
		footerMsg = 'HINT: Don\'t forget to set the spawn channel with the spawn command, otherwise wild pokemon will not spawn until you do. The bot also has an "anti-afk" system, in which spawn channels that don\'t receive messages for a while will stop having pokemon spawned.'
		em.set_footer(text=footerMsg)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def display_server(message):
		try:
			commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()
		except KeyError as err:
			return

		msg = 'Want to play the game? PDA now has an official Discord server! You can join it [here](https://discord.gg/rEkQWUa).'

		em = discord.Embed(title='Server!', description=msg, colour=0xDEADBF)
		footerMsg = 'HINT: Don\'t forget to set the spawn channel with the spawn command, otherwise wild pokemon will not spawn until you do. The bot also has an "anti-afk" system, in which spawn channels that don\'t receive messages for a while will stop having pokemon spawned.'
		em.set_footer(text=footerMsg)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	def get_random_boss_pokemon():
		cursor = MySQL.getCursor()
		if Player.HALLOWEEN and random.randint(0, 255) >= GHOST_SPAWN_CHANCE:
			cursor.execute("""
				SELECT * 
				FROM pokemon
				JOIN pokemon_type
				WHERE enabled = 1 
				AND capture_rate <= 3
				ORDER BY RAND()
				LIMIT 1
				""")
		else:
			cursor.execute("""
				SELECT * 
				FROM pokemon
				JOIN pokemon_type
				WHERE enabled = 1
				AND pokemon_type.type_id = 8
				AND  pokemon_type.pokemon_id = pokemon.id 
				AND capture_rate <= 3
				ORDER BY RAND()
				LIMIT 1
				""")
		row = cursor.fetchone()

		return row['id'], row['identifier'].upper()

	GHOST_SPAWN_CHANCE = 135
	def get_random_pokemon_spawn():
		rates = [[3,8], [15,45], [46,255]]
		rateList = []
		for i in range(0,len(rates)):
			rate = int(rates[i][1]**1.4)
			rateList += rate * [rates[i]]
		
		row = None
		while not row:
			captureRate = random.choice(rateList)
			minR, maxR = captureRate
			cursor = MySQL.getCursor()
			if Player.HALLOWEEN and random.randint(0, 255) >= GHOST_SPAWN_CHANCE:
				cursor.execute("""
					SELECT * 
					FROM pokemon
					JOIN pokemon_type
					WHERE enabled = 1
					AND pokemon_type.type_id = 8
					AND  pokemon_type.pokemon_id = pokemon.id
					AND capture_rate >= %s
					AND capture_rate <= %s
					ORDER BY RAND()
					LIMIT 1
					""", (minR, maxR))
			else:
				cursor.execute("""
					SELECT * 
					FROM pokemon
					WHERE enabled = 1 
					AND capture_rate >= %s
					AND capture_rate <= %s
					ORDER BY RAND()
					LIMIT 1
					""", (minR, maxR))

			row = cursor.fetchone()

		print(datetime.datetime.now(), M_TYPE_INFO, textwrap.dedent("""Spawning: Capture Rate: %d, Chance: %f""") % (
			maxR,
			int(maxR**1.4) / len(rateList),
		))
		
		return row['id'], row['identifier'].upper()

	def convertDeltaToHuman(deltaTime):
		return humanfriendly.format_timespan(deltaTime)

	async def give_players_boss_prize(message, commandPrefix, spawn, candy):
		serverId = message.server.id
		rand = random.randint(0, 255)
		item = None
		numerous = True
		if rand <= 16:
			item = items[3]
			numerous = False
		elif rand <= 32:
			item = items[7]
		else:
			item = items[2]

		msg = '{0.author.mention}, there are no wild pokemon or trainers willing to fight near you at this time.'.format(message)
		
		for pId in spawn.fought:
			player = playerMap[pId]
			pokemon = player.lastBattle['pokemon']
			damage = player.lastBattle['damage']

			# player exp and money
			baseValue = int(valueMod*(damage/math.log10(3)))//3 + random.randint(20, 75)
			exp = int(random.uniform(0.7, 1)*baseValue)
			player.addExperience(exp)
			print(datetime.datetime.now(), M_TYPE_INFO, 'Earned Boss EXP: {}'.format(baseValue))
			money = int(random.uniform(13.5,15.6)*baseValue)
			player.addMoney(money)
			print(datetime.datetime.now(), M_TYPE_INFO, 'Earned Boss Money: {}'.format(money))

			# pokemon exp
			basePValue = int(random.randint(40, 43)*damage)
			leveledUp, evolved = pokemon.addExperience(basePValue)
			levelUpMessage = None
			if leveledUp:
				levelUpMessage = ('{} leveled up to level {}!\n\n'.format(pokemon.name, str(pokemon.pokeStats.level)))
				if evolved:
					levelUpMessage += ('What!? {} is evolving! It evolved into a {}!'.format(name, winner.name))
				lem = discord.Embed(title='Level up!', description='<@{0}>, your '.format(player.pId.replace(serverId, '')) + levelUpMessage, colour=0xDEADBF)
				lem.set_author(name='Professor Oak', icon_url=oakUrl)
				lem.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
				lem.set_footer(text='HINT: Two pokemons of the same species and level can have different stats. That happens because pokemon with higher IV are stronger. Check your pokemon\'s IV by typing {}info!'.format(commandPrefix))

			# item gift
			baseAmount = int(math.log10(damage/10) + 1) + 1
			amount = 1 if not numerous else int(random.uniform(baseAmount*3, baseAmount*5))
			player.addItem(item.id-1, amount)
			halloweenStr = ''
			if Player.HALLOWEEN and candy>0:
				player.addCandy(candy)
				halloweenStr = 'You also got **{}** 🍬!'.format(candy)

			# update
			player.update()

			msg = '<@{}>, you participated in the boss fight, your reward is {} EXP for you, {} EXP for your {}, {}P and {} unit(s) of {}! {}'.format(player.pId.replace(serverId, ''), exp, basePValue, pokemon.name, money, amount, item.name, halloweenStr)
			em = discord.Embed(title='Well done!', description=msg, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
			em.set_footer(text='HINT: No wild pokemon? Challenge a friend to a duel by typing {}duel @nickname!'.format(commandPrefix))
			await client.send_message(message.channel, embed=em)

			if leveledUp:
				await client.send_message(message.channel, embed=lem)

	bossChance = 4
	afkTime = 150
	valueMod = 8.75*0.45
	ballList = ['Poke Ball', 'Great Ball', 'Ultra Ball', 'Master Ball']
	class SpawnManager:
		name = {}
		pId = {}
		spawned = {}
		fought = {}
		trainer = {}
		isBoss = {}
		bossFighters = {}
		restSpawn = 0
		lastAct = {}

		@staticmethod
		async def fight(message, capture=0):
			pokeServer = serverMap[message.server.id]
			commandPrefix, spawnChannel = pokeServer.get_prefix_spawnchannel()
			spawn = pokeServer.spawn

			if spawnChannel != message.channel.id:
				return

			player = playerMap[message.author.id]

			if not spawn:
				msg = '{0.author.mention}, there are no wild pokemon or trainers willing to fight near you at this time.'.format(message)
				em = discord.Embed(title='Ops!', description=msg, colour=0xDEADBF)
				em.set_author(name='Tall Grass', icon_url=grassUrl)
				em.set_footer(text='HINT: No wild pokemon? Challenge a friend to a duel by typing {}duel @nickname!'.format(commandPrefix))
				await client.send_message(message.channel, embed=em)
				return
			
			if spawn.spawned and not player.pId in spawn.fought:
				playerPokemon = player.getSelectedPokemon()

				if not playerPokemon:
					await display_not_started(message, commandPrefix)
					return

				isHealing, deltaTime = playerPokemon.isHealing()
				if isHealing == True:
					msg = '{0.author.mention}, your {1} is currently healing at the pokemon center, and won\'t be able to fight for {2}.'.format(message, playerPokemon.name, convertDeltaToHuman(deltaTime+1))
					em = discord.Embed(title='There is no way!', description=msg, colour=0xDEADBF)
					em.set_author(name='Nurse Joy', icon_url=joyUrl)
					em.set_thumbnail(url=getImageUrl(playerPokemon.pId, playerPokemon.mega))
					em.set_footer(text='HINT:  Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
					await client.send_message(message.channel, embed=em)
					return
				elif isHealing == False:
					cursor = MySQL.getCursor()
					cursor.execute("""
						UPDATE player_pokemon
						SET healing = NULL
						WHERE id = %s
						AND player_id = %s
						""", (playerPokemon.ownId, player.pId))
					MySQL.commit()
					playerPokemon.healing = None
					playerPokemon.pokeStats.hp = playerPokemon.pokeStats.current['hp']				

				isTrainer = False
				if playerPokemon.pokeStats.hp > 0:
					isBossBool, wildPokemon = spawn.isBoss
					if isBossBool:
						gym = True
						if not wildPokemon:
							wildPokemon = Pokemon(name=spawn.name, pokemonId=spawn.pId, level=100, wild=1, customHp=5)
							spawn.isBoss = True, wildPokemon
					else:
						gym = False
						level = playerPokemon.pokeStats.level
						levelDeviation = 1/(math.log10(2*level)+1)
						isTrainer, gender = spawn.trainer
						uniform = random.uniform(levelDeviation, 0.85 + (0.45 if isTrainer else 0.1))
						newLevel =  int(uniform * level)
						newLevel = min(newLevel, 100)
						newLevel = max(newLevel, 1)
						wildPokemon = Pokemon(name=spawn.name, pokemonId=spawn.pId, level=newLevel, wild=1 if not isTrainer else 1.5)
						
					boost = None
					isBoosted = player.isBoosted()
					if isBoosted:
						boost = playerPokemon

					battle = Battle(challenger1=playerPokemon, challenger2=wildPokemon, boost=boost, gym=gym)
					winner, battleLog, levelUpMessage = battle.execute()
					player.commitPokemonToDB()

					captureMessage = ''
					victory = winner == playerPokemon
					
					if not isBossBool:
						if victory:
							spawn.fought.append(player.pId)

							baseValue = int(valueMod*(wildPokemon.pokeStats.level*3/math.log10(wildPokemon.captureRate)))//3 + random.randint(20, 75)
							print(datetime.datetime.now(), M_TYPE_INFO, 'Earned Player EXP: {}'.format(baseValue))
							money = int(random.uniform(2.5,3.6)*baseValue)
							player.addMoney(money)

							if capture>0:
								player.items[capture-1] -= 1
								captureMessage += '\nYou threw a {} into {} and...\n'.format(ballList[capture-1], wildPokemon.name)
								if wildPokemon.attemptCapture(capture-1, player.getCaptureMod()):
									captureMessage += '```fix\nGotcha! {} was added to your pokemon list!\n```'.format(wildPokemon.name)
									wildPokemon.caughtWith = capture
									baseValue *= math.log10(wildPokemon.pokeStats.level)
									player.addPokemonViaInstace(wildPokemon)
								else:
									captureMessage += '```css\nIt escaped...\n```'

							player.addExperience(baseValue)
							player.addCandy(wildPokemon.candyDrop)
							captureMessage += getPlayerEarnedMoneyEXP(message.author.mention, baseValue, money, wildPokemon.candyDrop)

							if levelUpMessage:
								lem = discord.Embed(title='Level up!', description='{0.author.mention}, your '.format(message) + levelUpMessage, colour=0xDEADBF)
								lem.set_author(name='Professor Oak', icon_url=oakUrl)
								lem.set_thumbnail(url=getImageUrl(winner.pId, winner.mega))
								lem.set_footer(text='HINT: Two pokemons of the same species and level can have different stats. That happens because pokemon with higher IV are stronger. Check your pokemon\'s IV by typing {}info!'.format(commandPrefix))
					else:
						spawn.fought.append(player.pId)
						if victory:
							player.lastBattle = {
								'pokemon' : playerPokemon, 
								'damage' : battle.damageDealt['winner']
							}
							spawn.isBoss = False, None
							spawn.spawned = False
							await give_players_boss_prize(message, commandPrefix, spawn, wildPokemon.candyDrop)
							bossMsg = '{} was defeated! All the participant were rewarded according to the damage dealt! '.format(spawn.name)
							bem = discord.Embed(title='The boss is down!', description=bossMsg, colour=0xDEADBF)
							bem.set_author(name='Professor Oak', icon_url=oakUrl)
							bem.set_thumbnail(url=getImageUrl(spawn.pId))
						else:
							player.lastBattle = {
								'pokemon' : playerPokemon, 
								'damage' : battle.damageDealt['loser']
							}
							

					if isTrainer:
						if victory:
							money = int(random.uniform(3.1,3.8)*money)
							player.addMoney(money)
							trainerMessage = 'Damn, {}! Your *{}* completely destroyed my *{}*! Here\'s **{}₽** for your deserved win!'.format(message.author.mention, playerPokemon.name, wildPokemon.name, money)
						else:
							trainerMessage = 'Wow, {}! My *{}* destroyed your *{}*! Better luck next time!'.format(message.author.mention, wildPokemon.name, playerPokemon.name)

						tem = discord.Embed(title='Well fought!', description=trainerMessage, colour=0xDEADBF)
						tem.set_author(name='Poketrainer', icon_url=pokeballUrl)
						tem.set_thumbnail(url=trainerURL.format(gender))

					player.update()
					
					if not isBossBool:		
						msg = '{0.author.mention}, your {1} fought a beautiful battle against {2}! Here are the details: \n\n'.format(message, playerPokemon.name, wildPokemon.name)
						em = discord.Embed(title='Battle: {} (Lv. {}) vs. {}{} (Lv. {})!'.format(playerPokemon.name, playerPokemon.pokeStats.level, 'Trainer\'s ' if isTrainer else '', wildPokemon.name, newLevel), description=msg+battleLog+captureMessage, colour=0xDEADBF)
					else:
						msg = '{0.author.mention}, your {1} gave it all against the boss {2}! Here are the details: \n\n'.format(message, playerPokemon.name, wildPokemon.name)
						em = discord.Embed(title='Boss Battle: {} (Lv. {}) against ({} Lv. 100)!'.format(playerPokemon.name, playerPokemon.pokeStats.level, wildPokemon.name), description=msg+battleLog, colour=0xDEADBF)
					em.set_author(name='Professor Oak', icon_url=oakUrl)
					em.set_thumbnail(url=getImageUrl(spawn.pId))
					em.set_footer(text='HINT: You can check your pokeball supply by typing {}me.'.format(commandPrefix))
					await client.send_message(message.channel, embed=em)
					
					if victory and levelUpMessage:
						await client.send_message(message.channel, embed=lem)

					if isTrainer:
						await client.send_message(message.channel, embed=tem)	

					if victory and isBossBool:
						await client.send_message(message.channel, embed=bem)									

				else:
					msg = '{0.author.mention}, your pokemon has 0 HP, it is in no condition to fight! Take it to the pokemon center by typing ``{1}center.``'.format(message, commandPrefix)
					em = discord.Embed(title='Your {} is fainted!'.format(playerPokemon.name), description=msg, colour=0xDEADBF)
					em.set_thumbnail(url=getImageUrl(playerPokemon.pId, playerPokemon.mega))
					em.set_author(name='Professor Oak', icon_url=oakUrl)
					await client.send_message(message.channel, embed=em)
			elif spawn.spawned:
				msg = '{0.author.mention}, you you already fought {1}! You can\'t fight it twice.'.format(message, spawn.name)
				em = discord.Embed(title='Ops!', description=msg, colour=0xDEADBF)
				em.set_author(name='Tall Grass', icon_url=grassUrl)
				em.set_thumbnail(url=getImageUrl(spawn.pId))
				em.set_footer(text='HINT: No wild pokemon? Challenge a friend to a duel by typing {}duel @nickname!'.format(commandPrefix))
				await client.send_message(message.channel, embed=em)
			else:
				msg = '{0.author.mention}, there are no wild pokemon or trainers willing to fight near you at this time.'.format(message)
				em = discord.Embed(title='Ops!', description=msg, colour=0xDEADBF)
				em.set_author(name='Tall Grass', icon_url=grassUrl)
				em.set_footer(text='HINT: No wild pokemon? Challenge a friend to a duel by typing {}duel @nickname!'.format(commandPrefix))
				await client.send_message(message.channel, embed=em)

		@staticmethod	
		async def spawn():
			for server in client.servers:
				pokeServer = serverMap[server.id]
				
				commandPrefix, spawnChannel = pokeServer.get_prefix_spawnchannel()

				if not pokeServer.spawn:
					pokeServer.spawn = Spawn()
				spawn = pokeServer.spawn

				for channel in server.channels:
					if channel.id == spawnChannel:
						lastAct, actDelay = spawn.lastAct
						canAct = datetime.datetime.now().timestamp() - lastAct.timestamp()
						if canAct > actDelay:
							print(datetime.datetime.now(), M_TYPE_INFO, "Server '" + server.id + "' ready to act. Acting and updating delay.")
							if not spawn.spawned:
								spawn.lastAct = [datetime.datetime.now(), random.randint(45, 55)]
								isAfk = True
								localAfkTime = (datetime.datetime.now().timestamp() - pokeServer.serverMessageMap)
								isAfk = localAfkTime > afkTime + spawn.restSpawn

								print(datetime.datetime.now(), M_TYPE_INFO, 'Server AFK Status: {2}/{1} ({0})'.format(isAfk, afkTime, localAfkTime)) # Why am I so lazy
								if isAfk:
									break

								spawn.spawned = True
								spawn.fought = []
								spawn.isBoss = False, None
								spawn.trainer = [False, 0]
								if random.randint(0,255) <= bossChance:
									spawn.pId, spawn.name = get_random_boss_pokemon()
									spawn.isBoss = True, None
									msg = 'A boss {0} has appeared! Type ``{1}fight`` to fight it!'.format(spawn.name, commandPrefix)
									em = discord.Embed(title='A wild Boss Pokemon appears!', description=msg, colour=0xDEADBF)
									em.set_author(name='Tall Grass', icon_url=grassUrl)
									em.set_image(url=getImageUrl(spawn.pId))
									em.set_footer(text='HINT: The more people fight the boss, the easier it is to defeat it!'.format(commandPrefix))
								else:
									spawn.pId, spawn.name = get_random_pokemon_spawn()
									spawn.trainer[0] = random.randint(0, 255)<=30
									spawn.trainer[1] = random.randint(0, 1)
									isTrainer, gender = spawn.trainer
									if isTrainer:
										article = 'him' if gender==0 else 'her'
										msg = 'A poketrainer is looking for a challenger! Type ``{0}fight`` to fight {1}!'.format(commandPrefix, article)
										em = discord.Embed(title='Here comes a new challenger!', description=msg, colour=0xDEADBF)
										em.set_author(name='Tall Grass', icon_url=grassUrl)
										em.set_thumbnail(url=trainerURL.format(gender))
										em.set_footer(text='HINT: You cannot catch other trainer\'s pokemon, but you will earn money if you win the fight.'.format(commandPrefix))
									else:
										msg = 'A wild {0} wants to fight! Type ``{1}fight`` to fight it, or ``{1}catch #`` to try and catch it as well!'.format(spawn.name, commandPrefix)
										em = discord.Embed(title='A wild {} appeared!'.format(spawn.name), description=msg, colour=0xDEADBF)
										em.set_author(name='Tall Grass', icon_url=grassUrl)
										em.set_thumbnail(url=getImageUrl(spawn.pId))
										em.set_footer(text='HINT: You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
								await client.send_message(channel, embed=em)
								#await asyncio.sleep(50)
							else:
								isTrainer, gender = spawn.trainer
								spawn.lastAct = [datetime.datetime.now(), random.randint(25, 80)]
								if isTrainer:
									msg = 'The poketrainer is gone! Don\'t worry if you didn\'t have a chance to fight {}, though. Pokemon trainers eager to fight always come back.'.format('him' if gender==0 else 'her')
									em = discord.Embed(title='Bye!', description=msg, colour=0xDEADBF)
									em.set_thumbnail(url=trainerURL.format(gender))
									em.set_author(name='Tall Grass', icon_url=grassUrl)
									em.set_footer(text='HINT: Your selected pokemon must be in fighting conditions for you to enter a fight! If you need to heal it, type {}center.'.format(commandPrefix))
								else:
									msg = 'Darn it, {} has fled the scene! Don\'t worry if you didn\'t have a chance to fight it, though. Wild pokemon appear a lot around these parts.'.format(spawn.name, commandPrefix)
									em = discord.Embed(title='{} fled!'.format(spawn.name), description=msg, colour=0xDEADBF)
									em.set_thumbnail(url=getImageUrl(spawn.pId))
									em.set_author(name='Tall Grass', icon_url=grassUrl)
									em.set_footer(text='HINT: Your selected pokemon must be in fighting conditions for you to enter a fight! If you need to heal it, type {}center.'.format(commandPrefix))
								
								spawn.spawned = False
								spawn.isBoss = False, None
								try:
									await client.send_message(channel, embed=em)
								except Exception as e: # I am very disappointed in you, past self
									traceback.print_exc()

			await asyncio.sleep(10)

	@asyncio.coroutine
	async def spawn_wild_pokemon():
		await client.wait_until_ready()

		while True:
			try:
				await SpawnManager.spawn()
			except Exception as e: # Still disgusting
				traceback.print_exc()
			
	async def add_random_pokemon(message):
		player = playerMap[message.author.id]
		for i in range(1,100):
			player.addPokemon(pokemonId=random.randint(1,500), level=random.randint(1,100))

	async def give_pokemon(message):
		temp = message.content.split(' ')
			
		option = None
		if len(temp)>1:
			playerId = temp[1].replace('#', '').replace('@', '').replace('!', '').replace('<', '').replace('>', '')
			pokemonId = int(temp[2])
			print(datetime.datetime.now(), M_TYPE_INFO, 'Giving player {} a level 5 Pokemon (ID: {}).'.format(playerId, pokemonId))
			
			cursor = MySQL.getCursor()
			cursor.execute("""
				SELECT *
				FROM player
				WHERE id LIKE %s
			""", ('%%%s%%' % playerId,))
			rows = cursor.fetchall()
		
		for row in rows:
			player = None
			if not player in playerMap:
				player = Player(row['id'], row['name'])
				key = message.author.id
				playerMap[key] = player
			else:
				player = playerMap[row['id']]
			player.addPokemon(pokemonId=pokemonId, level=5)

	async def stop_server(message):
		await client.logout()

	async def change_prefix(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		temp = message.content.split(' ')
			
		option = None
		if len(temp)<=1:
			msg = 'Invalid prefix. Type ``{}prefix your_prefix`` to change the command prefix. In this example, commands would be called as your_prefix!command.'.format(commandPrefix)
		else:
			option = temp[1]
			if len(option)>10:
				msg = 'Invalid prefix. Prefix is too long. Maximum of 10 characters.'.format(commandPrefix)
			else:
				option = option.lower()
				cursor = MySQL.getCursor()
				cursor.execute("""
					UPDATE server
					SET prefix = %s
					WHERE id = %s
					""", (option, message.server.id))
				msg = 'Prefix set to {0}. Commands now must be called as {0}command.'.format(option)
				MySQL.commit()

				serverMap[message.server.id].commandPrefix = option

		em = discord.Embed(title='Change Prefix', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def set_spawn_channel(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		temp = message.content.split(' ')
			
		option = None
		if len(temp)<=1:
			msg = 'Type ``{}spawn #channel_name`` to set the channel where wild pokemon will appear.'.format(commandPrefix)
		else:
			option = temp[1].replace('#', '').replace('!', '').replace('<', '').replace('>', '')
			selectedChannel = None
			for channel in message.server.channels:
				if int(channel.id) == int(option):
					selectedChannel = channel
					break
			if not selectedChannel:
				msg = 'Invalid channel. Type ``{}spawn #channel_name`` to set the channel where wild pokemon will appear.'.format(commandPrefix)
			else:
				cursor = MySQL.getCursor()
				cursor.execute("""
					UPDATE server
					SET spawn_channel = %s
					WHERE id = %s
					""", (selectedChannel.id, message.server.id))
				msg = 'Spawn channel set to #{0}.'.format(selectedChannel)
				MySQL.commit()

				serverMap[message.server.id].spawnChannel = selectedChannel.id

		em = discord.Embed(title='Set Spawn Channel', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def display_fight(message):
		await SpawnManager.fight(message)

	def getBallsString(player):
		msg = ''
		counter = 1
		for ball in ballList:
			msg += '{}. {} ({} available)\n'.format(counter, ball, player.items[counter-1])
			counter += 1
		return msg

	async def display_balls_message(message, player, commandPrefix):
		msg = '{0.author.mention}, type ``{1}catch #`` to try to catch the wild pokemon. These are the possible pokeballs: \n\n'.format(message, commandPrefix)

		msg += getBallsString(player)

		em = discord.Embed(title='Select your pokeball!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: Low on pokeballs? You can buy more by typing {}shop. Or if you\'re low on cash, you get pokeballs by just staying online!'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_catch(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		temp = message.content.split(' ')
		option = None
		if len(temp)<=1:
			await display_balls_message(message, player, commandPrefix)
		else:
			try:
				option = int(temp[1])
				if option and option > len(ballList) or option < 1:
					await display_balls_message(message, player, commandPrefix)
				else:
					if player.items[option-1]>0:
						if option-1 == 3 and not player.hasAllBadges():
							msg = '{0.author.mention}, only players with all the 18 gym badges can use Master Balls!'.format(message)
							em = discord.Embed(title='You wish!', description=msg, colour=0xDEADBF)
							em.set_author(name='Professor Oak', icon_url=oakUrl)
							await client.send_message(message.channel, embed=em)
						else:
							pokeServer = serverMap[message.server.id]
							spawn = pokeServer.spawn

							isTrainer, gender = spawn.trainer
							isBossBool, pokemon = spawn.isBoss
							if isTrainer:
								msg = '{0.author.mention}, you cannot catch a pokemon that belongs to a trainer!'.format(message)
								em = discord.Embed(title='That is not how this works!', description=msg, colour=0xDEADBF)
								em.set_author(name='Professor Oak', icon_url=oakUrl)
								await client.send_message(message.channel, embed=em)
							elif isBossBool:
								msg = '{0.author.mention}, you cannot catch a boss pokemon!'.format(message)
								em = discord.Embed(title='That is not how this works!', description=msg, colour=0xDEADBF)
								em.set_author(name='Professor Oak', icon_url=oakUrl)
								await client.send_message(message.channel, embed=em)
							else:
								await SpawnManager.fight(message, option)
					else:
						msg = '{0.author.mention}, you don\'t have any {1}s left! Here\'s your list of pokeballs: \n\n'.format(message, ballList[option-1])

						counter = 1
						for ball in ballList:
							msg += '{}. {} ({} available)\n'.format(counter, ball, player.items[counter-1])
							counter += 1

						em = discord.Embed(title='Select your pokeball!', description=msg, colour=0xDEADBF)
						em.set_author(name='Professor Oak', icon_url=oakUrl)
						em.set_footer(text='HINT: Low on pokeballs? You can buy more by typing {}shop. Or if you\'re low on cash, you get pokeballs by just staying online!'.format(commandPrefix))
						await client.send_message(message.channel, embed=em)
			except ValueError as err:
				await display_balls_message(message, player, commandPrefix)

	async def display_success_pokecenter(message, commandPrefix):
		msg = '{0.author.mention}, we will take good care of your pokemon!'.format(message)
		em = discord.Embed(title='Thanks for using the pokemon center!', description=msg, colour=0xDEADBF)
		em.set_author(name='Nurse Joy', icon_url=joyUrl)
		em.set_thumbnail(url=getImageUrl(113))
		em.set_footer(text='HINT: Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_fail_pokecenter(message, commandPrefix):
		msg = '{0.author.mention}, welcome to the Pokemon Center! You can heal a single pokemon by typing ``{1}center #``, or you can heal all your pokemon by typing ``{1}center all``.'.format(message, commandPrefix)
		em = discord.Embed(title='Hello there!', description=msg, colour=0xDEADBF)
		em.set_author(name='Nurse Joy', icon_url=joyUrl)
		em.set_thumbnail(url=getImageUrl(113))
		em.set_footer(text='HINT: Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_healing_pokecenter(message, commandPrefix, pokemon, deltaTime):
		msg = '{0.author.mention}, your {1} is already being healed. It will be ready for battle in {2}.'.format(message, pokemon.name, convertDeltaToHuman(deltaTime+1))
		em = discord.Embed(title='Already healing!', description=msg, colour=0xDEADBF)
		em.set_author(name='Nurse Joy', icon_url=joyUrl)
		em.set_thumbnail(url=getImageUrl(113))
		em.set_footer(text='HINT: Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_healed_pokecenter(message, commandPrefix, pokemon):
		msg = '{0.author.mention}, your {1} is fully healed! It is ready for combat.'.format(message, pokemon.name)
		em = discord.Embed(title='All done!', description=msg, colour=0xDEADBF)
		em.set_author(name='Nurse Joy', icon_url=joyUrl)
		em.set_thumbnail(url=getImageUrl(113))
		em.set_footer(text='HINT: Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_center(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			option = None
			if len(temp)>1:
				try:
					option = int(temp[1])
					if option:
						try:
							pokemon, inGym = player.getPokemon(option)
							isHealing, deltaTime = pokemon.isHealing()
							isFull = (pokemon.pokeStats.current['hp'] - pokemon.pokeStats.hp)<=0
							if not isFull and isHealing == None:
								# start healing process
								pokemon.healing = datetime.datetime.now()
								player.commitPokemonToDB(pokemon)
								await display_success_pokecenter(message, commandPrefix)
							elif not isFull and isHealing == True:
								# show healing time
								await display_healing_pokecenter(message, commandPrefix, pokemon, deltaTime)
							else:
								# return healed pokemon
								pokemon.healing = None
								pokemon.pokeStats.hp = pokemon.pokeStats.current['hp']
								player.commitPokemonToDB(pokemon)
								await display_healed_pokecenter(message, commandPrefix, pokemon)

						except IndexError:
							await display_fail_pokecenter(message, commandPrefix)
				except ValueError as err:
					if temp[1] == 'all':
						now = datetime.datetime.now()
						cursor = MySQL.getCursor()
						cursor.execute("""
							UPDATE player_pokemon
							SET healing = %s
							WHERE player_id = %s
							AND healing IS NULL
							""", (now, player.pId))
						MySQL.commit()
						player.getSelectedPokemon().healing = now
						await display_success_pokecenter(message, commandPrefix)
					else:
						await display_fail_pokecenter(message, commandPrefix)
			else:
				await display_fail_pokecenter(message, commandPrefix)

	async def display_not_started(message, commandPrefix):
		msg = '{0.author.mention}, you don\'t have a Pokemon yet! Type ``{1}start`` to start your adventure!'.format(message, commandPrefix)
		em = discord.Embed(title='Choose your starter!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: Use {}start # to select a starter pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_success_shop(message, item, amount, commandPrefix):
		msg = '{0.author.mention}, you purchased **{1}** units of **{2}** for **{3}₽**. Thank you for your purchase!'.format(message, amount, item.name, amount*item.price)
		em = discord.Embed(title='Thanks!', description=msg, colour=0xDEADBF)
		em.set_author(name='Poke Mart', icon_url=pokeballUrl)
		em.set_thumbnail(url=pokeMartUrl)
		await client.send_message(message.channel, embed=em)

	async def display_fail_shop(message, commandPrefix):
		msg = '{0.author.mention}, you don\'t have enough money for that!'.format(message)
		em = discord.Embed(title='Erm...', description=msg, colour=0xDEADBF)
		em.set_author(name='Poke Mart', icon_url=pokeballUrl)
		em.set_thumbnail(url=pokeMartUrl)
		await client.send_message(message.channel, embed=em)

	itemTypes = ['__PokeBalls__', '__Potions__', '__EXP Boosts__']
	def getItemsString():
		msg = {}
		counter = 1
		oldType = -1

		# This is a trash piece of code that is only here because I am a XGH lazy piece of crap
		for item in shopItems:
			if oldType < item.itemType:
				msg[itemTypes[item.itemType]] = ''
				oldType = item.itemType

			msg[itemTypes[item.itemType]] += '**{}.** {} ({}₽)\n'.format(counter, item.name, item.price)
			msg[itemTypes[item.itemType]] += '**Description:** {}\n'.format(item.description)
			counter += 1
		return msg

	async def display_info_shop(message, player, commandPrefix):
		msg = '{0.author.mention}, welcome to the Poke Mart! To buy an item type ``{1}shop item amount``. Here these are the available items:'.format(message, commandPrefix)
		em = discord.Embed(title='Hello there, {0}. You have {1}₽.'.format(message.author.name, player.money), description=msg, colour=0xDEADBF)
		em.set_author(name='Poke Mart', icon_url=pokeballUrl)
		em.set_thumbnail(url=pokeMartUrl)
		em.set_footer(text='HINT: To use an item, type {0}item #. You can see your items by typing {0}item.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

		shopMessages = getItemsString()
		for itemType, itemMessage in shopMessages.items():
			em = discord.Embed(title='{0}'.format(itemType.replace("_", "")), description=itemMessage, colour=0xDEADBF) # and with trash code, comes trashier code
			em.set_author(name='Poke Mart', icon_url=pokeballUrl)
			em.set_thumbnail(url=pokeMartUrl)
			em.set_footer(text='HINT: To use an item, type {0}item #. You can see your items by typing {0}item.'.format(commandPrefix))
			await client.send_message(message.channel, embed=em)

	shopItems = []
	items = []

	async def display_shop(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			option = None
			if len(temp)>1:
				try:
					option = int(temp[1]) - 1
					if option >=0 and option < len(shopItems):
						item = shopItems[option]
						
						amount = 1
						if len(temp)>2:
							amount = int(temp[2])
						
						if player.removeMoney(item.price*amount):
							item = shopItems[option]
							await display_success_shop(message, item, amount, commandPrefix)
							player.addItem(item.id-1, amount)
						else:
							await display_fail_shop(message, commandPrefix)

				except ValueError as err:
					traceback.print_exc()
			else:
				await display_info_shop(message, player, commandPrefix)

	def get_candy_shop_pokemon_list():
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT *
			FROM pokemon
			WHERE candy_cost > 0
		""")
		return cursor.fetchall()

	async def display_fail_candy_shop(message, commandPrefix):
		msg = '{0.author.mention}, you don\'t have enough candy 🍬 for that!'.format(message)
		em = discord.Embed(title='Erm...', description=msg, colour=0xFFA500)
		em.set_author(name='Spooky Poke Mart', icon_url=pokeballUrl)
		em.set_thumbnail(url=pokeMartUrl)
		await client.send_message(message.channel, embed=em)

	async def display_info_candy_shop(message, player, commandPrefix):
		msg = '{0.author.mention}, welcome to the Spooky Poke Mart! Here you can trade your candy for spooky Pokemon! Just type ``{1}trade pokemon_number``. These are the available pokemon:\n\n'.format(message, commandPrefix)
		
		pokemonList = get_candy_shop_pokemon_list()
		counter = 1
		for row in pokemonList:
			msg += '**{0}.** {1}: {2} 🍬\n'.format(counter, row['identifier'].upper(), row['candy_cost'])
			counter += 1

		em = discord.Embed(title='Hello there, {0}. You have {1} 🍬.'.format(message.author.name, player.candy), description=msg, colour=0xFFA500)
		em.set_author(name='Spooky Poke Mart', icon_url=pokeballUrl)
		em.set_thumbnail(url=pokeMartUrl)
		em.set_footer(text='HINT: To use an item, type {0}item #. You can see your items by typing {0}item.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_success_candy_shop(message, pokemon, commandPrefix):
		msg = '{0.author.mention}, here is your {1}! And it only costed you {2} 🍬!'.format(message, pokemon['identifier'].upper(), pokemon['candy_cost'])
		em = discord.Embed(title='Thanks!', description=msg, colour=0xFFA500)
		em.set_author(name='Spooky Poke Mart', icon_url=pokeballUrl)
		em.set_thumbnail(url=getImageUrl(pokemon['id']))
		em.set_footer(text='HINT: Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)

	async def display_candy_shop(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		pokemonList = get_candy_shop_pokemon_list()

		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			option = None
			if len(temp)>1:
				try:
					option = int(temp[1]) - 1
					if option >=0 and option < len(pokemonList):
						pokemon = pokemonList[option]
						if player.removeCandy(pokemon['candy_cost']):
							player.addPokemon(pokemonId=pokemon['id'], level=5)
							await display_success_candy_shop(message, pokemon, commandPrefix)
						else:
							await display_fail_candy_shop(message, commandPrefix)

				except ValueError as err:
					traceback.print_exc()
			else:
				await display_info_candy_shop(message, player, commandPrefix)

	async def display_me(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
		finalStr = str(player) + getBallsString(player)

		em = discord.Embed(title='{}\'s player information!'.format(message.author.name), description=str(finalStr), colour=0xDEADBF)
		em.set_thumbnail(url=message.author.avatar_url)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: Higher level players have a bigger chance of catching wild pokemon.')
		await client.send_message(message.channel, embed=em)

	def getUsableItemsString(player):
		usable = player.getUsableItems()
		msg = ''
		counter = 1
		for i in range(0,len(usable)):
			itemId = usable[i]
			item = items[itemId]
			msg += '**{}.** {} ({} units)\n'.format(counter, item.name, player.items[itemId])
			msg += '**Description:** {}\n'.format(item.description)
			counter += 1
		
		return msg

	async def display_info_item(message, player, commandPrefix):
		itemStr = getUsableItemsString(player)
		if itemStr != '':
			msg = '{0.author.mention}, use ``{1}item #`` to use an item. Here\'s your usable item list:\n\n'.format(message, commandPrefix)
			em = discord.Embed(title='{}\'s Inventory.'.format(message.author.name), description=msg+itemStr, colour=0xDEADBF)
		else:
			msg = '{0.author.mention}, you don\'t have any items at the moment. You can buy items by typing ``{1}shop``.'.format(message, commandPrefix)
			em = discord.Embed(title='{}\'s Inventory.'.format(message.author.name), description=msg, colour=0xDEADBF)
		em.set_thumbnail(url=message.author.avatar_url)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def display_used_potion(message, player, item, commandPrefix):
		if item.value < 300:
			msg = '{0.author.mention} healed {1} by {2} HP.'.format(message, player.getSelectedPokemon().name, item.value)
		else:
			msg = '{0.author.mention} fully healed {1}.'.format(message, player.getSelectedPokemon().name)

		em = discord.Embed(title='Used {}!'.format(item.name), description=msg, colour=0xDEADBF)
		em.set_thumbnail(url=message.author.avatar_url)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	def secondsToMinutesOrHours(timeInSec):
		if timeInSec//3600 == 0:
			return '{} minute(s)'.format(timeInSec//60)
		else:
			return '{} hour(s)'.format(timeInSec//3600)

	async def display_used_boost(message, player, item, commandPrefix):
		msg = '{0.author.mention} will receive 50\% extra experience for the next {1}.'.format(message, secondsToMinutesOrHours(item.value))
		em = discord.Embed(title='Used {}!'.format(item.name), description=msg, colour=0xDEADBF)
		em.set_thumbnail(url=message.author.avatar_url)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	async def display_item(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			option = None
			if len(temp)>1:
				try:
					option = int(temp[1]) - 1
					usable = player.getUsableItems()
					if option >=0 and option < len(usable):
						itemId = usable[option]
						item = items[itemId]
						used = player.useItem(item)
						if used == 1:
							await display_used_potion(message, player, item, commandPrefix)
						elif used == 2:
							await display_used_boost(message, player, item, commandPrefix)
					else:
						await display_info_item(message, player, commandPrefix)

				except ValueError as err:
					traceback.print_exc()
			else:
				await display_info_item(message, player, commandPrefix)

	async def challenge_player(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		temp = message.content.split(' ')
			
		option = None
		if len(temp)<=1:
			msg = 'Type ``{}duel @player`` to challenge a player for a duel.'.format(commandPrefix)
		else:
			player = playerMap[message.author.id]
			
			option = temp[1].replace('@', '').replace('!', '').replace('<', '').replace('>', '')
			if str(message.author.id) == option:
				msg = 'You cannot battle yourself.'
			else:
				lastDuel = datetime.datetime.now().timestamp() - player.lastDuel.timestamp()
				if lastDuel < duelCooldown:
					msg = '{0}, you have just battled someone! You will be able to duel again in {1}.'.format(message.author.mention, convertDeltaToHuman(duelCooldown - lastDuel))
				else:
					member = message.server.get_member(option)
					if member:
						msg = '{0}, {1} is challenging you to a duel! Type ``{2}accept`` to accept!'.format(temp[1], message.author.mention, commandPrefix)
						duelMap[option] = [message.author.id, message.author.mention]
					else:
						msg = 'No member with that name could be found!'

		em = discord.Embed(title='Duel time!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	def check_player_pokemon_healing(callout, pokemon, commandPrefix):
		isHealing, deltaTime = pokemon.isHealing()
		em = None
		if isHealing == True:
			msg = '{0}, your {1} is currently healing at the pokemon center, and won\'t be able to fight for {2}.'.format(callout, pokemon.name, convertDeltaToHuman(deltaTime))
			em = discord.Embed(title='There is no way!', description=msg, colour=0xDEADBF)
			em.set_author(name='Nurse Joy', icon_url=joyUrl)
			em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
			em.set_footer(text='HINT: Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
		
		elif isHealing == False:
			cursor = MySQL.getCursor()
			cursor.execute("""
				UPDATE player_pokemon
				SET healing = NULL
				WHERE id = %s
				""", (pokemon.ownId,))
			MySQL.commit()
			pokemon.healing = None
			pokemon.pokeStats.hp = pokemon.pokeStats.current['hp']
		
		return em

	def check_player_pokemon_hp(callout, pokemon, commandPrefix):
		em = None
		if pokemon.pokeStats.hp <= 0:
			msg = '{0}, your pokemon has 0 HP, it is in no condition to fight! Take it to the pokemon center by typing ``{1}center``.'.format(callout, commandPrefix)
			em = discord.Embed(title='Your {} is fainted!'.format(pokemon.name), description=msg, colour=0xDEADBF)
			em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
			em.set_author(name='Professor Oak', icon_url=oakUrl)
		
		return em

	def check_not_started(callout, player, commandPrefix):
		em = None
		if not player.hasStarted():
			msg = '{0}, you don\'t have a Pokemon yet! Type ``{1}start`` to start your adventure!'.format(callout, commandPrefix)
			em = discord.Embed(title='Choose your starter!', description=msg, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_footer(text='HINT: Use {}start # to select a starter pokemon.'.format(commandPrefix))
		return em

	def getPlayerEarnedMoneyEXP(callout, exp, money, candy):
		halloweenStr = ''
		if Player.HALLOWEEN and candy>0:
			halloweenStr = ' You also got **{}** 🍬!'.format(candy)
		return '\n{} earned **{} EXP** and **{}₽** for this battle.{}'.format(callout, int(exp), money, halloweenStr)

	duelCooldown = 300
	async def accept_challenge(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		challengedKey = message.author.id
		if challengedKey in duelMap:
			challengerKey, challlengerCallout = duelMap[challengedKey]
			
			challenger = playerMap[challengerKey]
			challenged = playerMap[challengedKey]

			lastDuel = datetime.datetime.now().timestamp() - challenged.lastDuel.timestamp()
			if lastDuel < duelCooldown:
				msg = '{0}, you have just battled someone! You will be able to duel again in {1}.'.format(message.author.mention, convertDeltaToHuman(duelCooldown - lastDuel))
				em = discord.Embed(title='On cooldwn!', description=msg, colour=0xDEADBF)
				em.set_author(name='Professor Oak', icon_url=oakUrl)
				await client.send_message(message.channel, embed=em)
				return

			em = check_not_started(message.author.mention, challenged, commandPrefix)
			if em:
				await client.send_message(message.channel, embed=em)
				return

			em = check_not_started(challlengerCallout, challenger, commandPrefix)
			if em:
				await client.send_message(message.channel, embed=em)
				return

			challengerPokemon = challenger.getSelectedPokemon()
			challengedPokemon = challenged.getSelectedPokemon()

			em = check_player_pokemon_healing(message.author.mention, challengedPokemon, commandPrefix)
			if em:
				await client.send_message(message.channel, embed=em)
				return
			
			em = check_player_pokemon_healing(challlengerCallout, challengerPokemon, commandPrefix)
			if em:
				await client.send_message(message.channel, embed=em)
				return

			em = check_player_pokemon_hp(message.author.mention, challengedPokemon, commandPrefix)
			if em:
				await client.send_message(message.channel, embed=em)
				return

			em = check_player_pokemon_hp(challlengerCallout, challengerPokemon, commandPrefix)
			if em:
				await client.send_message(message.channel, embed=em)
				return

			del duelMap[challengedKey]
			challenger.lastDuel = datetime.datetime.now()
			challenged.lastDuel = datetime.datetime.now()

			battle = Battle(challenger1=challengerPokemon, challenger2=challengedPokemon, gym=True)

			winner, battleLog, levelUpMessage = battle.execute()
			challenger.commitPokemonToDB()
			challenged.commitPokemonToDB()

			if winner == challengerPokemon:
				callout = challlengerCallout
				winnerPlayer = challenger
				loser = challengedPokemon
			else:
				callout = message.author.mention
				winnerPlayer = challenged
				loser = challengerPokemon

			if levelUpMessage:
				lem = discord.Embed(title='Level up!', description='{0}, your '.format(callout) + levelUpMessage, colour=0xDEADBF)
				lem.set_author(name='Professor Oak', icon_url=oakUrl)
				lem.set_thumbnail(url=getImageUrl(winner.pId, winner.mega))
				lem.set_footer(text='HINT: Two pokemons of the same species and level can have different stats. That happens because pokemon with higher IV are stronger. Check your pokemon\'s IV by typing {}info!'.format(commandPrefix))
			
			msg = '{0} and {1}, your {2} and {3} fought a beautiful battle against each other! Here are the details: \n\n'.format(challlengerCallout, message.author.mention, challengerPokemon.name, challengedPokemon.name)
			em = discord.Embed(title='{} Lv. {} vs {} Lv. {}!'.format(challengerPokemon.name, challengerPokemon.pokeStats.level, challengedPokemon.name, challengedPokemon.pokeStats.level), description=msg+battleLog, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_thumbnail(url=getImageUrl(winner.pId, winner.mega))
			await client.send_message(message.channel, embed=em)
			
			if levelUpMessage:
				await client.send_message(message.channel, embed=lem)

	duelMap = {}

	def check_poketype(callout, pokemon, tId, tAlias, commandPrefix):
		em = None
		if not pokemon.isType(tId):
			msg = '{0}, to claim the {1} gym your pokemon must be a {1} type.'.format(callout, tAlias.upper())
			em = discord.Embed(title='Wrong type!', description=msg, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_footer(text='HINT: Use {}start # to select a starter pokemon.'.format(commandPrefix))
		return em

	def getGymInfo(gymId):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT type.id, gym.type_id, gym.pokemon_id as gym_pokemon_id, player_pokemon.id, gym.holder_id, player_pokemon.player_id, player_pokemon.id, pokemon.id as pokemon_p_id, gym.holder_id, player.id, type.identifier as type_identifier, player.name as player_name, pokemon.identifier as pokemon_identifier, player_pokemon.level as pokemon_level, gym.date as gym_date, iv_hp, iv_attack, iv_defense, iv_special_attack, iv_special_defense, iv_speed, player_pokemon.is_mega as is_mega
			FROM gym JOIN type JOIN player_pokemon JOIN pokemon JOIN player
			WHERE type.id = gym.type_id
			AND gym.pokemon_id = player_pokemon.id
			AND gym.holder_id = player_pokemon.player_id
			AND player_pokemon.pokemon_id = pokemon.id
			AND gym.holder_id = player.id
			AND gym.type_id = %s
			""", (gymId,))
		return cursor.fetchone()

	async def display_info_gym(message, gymId, commandPrefix):
		row = getGymInfo(gymId)

		holdTime = convertDeltaToHuman(datetime.datetime.now().timestamp() - row['gym_date'].timestamp())
		msg = 'Here\'s the information about the {} type gym:\n\n'.format(row['type_identifier'].upper())
		msg += '**Pokemon:** {} Lv. {}.\n'.format(row['pokemon_identifier'].upper(), row['pokemon_level'])
		msg += '**Holder:** {}.\n'.format(row['player_name'])
		msg += '**Holding time:** {}.\n'.format(holdTime)

		em = discord.Embed(title='Gyms.', description=msg, colour=0xDEADBF)
		em.set_thumbnail(url=getImageUrl(row['pokemon_p_id'], row['is_mega']))
		em.set_footer(text='HINT: Use {0}gym to get a the full list of gyms'.format(commandPrefix))
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	numberOfGyms = 18
	async def display_info_gyms(message, commandPrefix):
		cursor = MySQL.getCursor()
		# MASSIVE GAMBIARRA
		cursor.execute("""
			SELECT *
			FROM type
			WHERE type.id <= 18
			""")
		rows = cursor.fetchall()

		msg = 'If you want to become a Pokemon master, you need to beat all the gyms and get all the badges! There are 18 gyms in total, each one with a different pokemon type. Gyms can be held by players if they\'re able to win a fight against the current owner.\n\nFor more information on a gym\'s current owner, type `{0}gym # info`, where *#* is the gym number. To fight a gym and try to earn its badges, type `{0}gym # fight`. To challenge the current holder of a gym, type `{0}gym # claim`. Only pokemon with the correct type can hold a gym. This means the *FLYING* gym, for instance, can only be held by a *FLYING* pokemon.\n\nThese are the currently available gyms:\n\n'.format(commandPrefix)
		
		counter = 1
		for row in rows:
			msg += '**{}**. {} Gym.\n'.format(counter, row['identifier'].upper())
			counter += 1

		em = discord.Embed(title='Gyms.', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		await client.send_message(message.channel, embed=em)

	def check_hold_availability(callout, player, commandPrefix):
		em = None

		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT COUNT(*) as count
			FROM player_pokemon
			WHERE selected <> 1
			AND in_gym = 0
			AND player_id = %s
		""", (player.pId,))
		row = cursor.fetchone()

		if row['count'] == 0:
			msg = '{0}, your {1} is your only available pokemon. You cannot release or leave your only pokemon to hold the gym.'.format(callout, player.getSelectedPokemon().name)
			em = discord.Embed(title='No pokemon!', description=msg, colour=0xDEADBF)
			em.set_author(name='Professor Oak', icon_url=oakUrl)
			em.set_footer(text='HINT: Once a pokemon becomes the holder of a gym, it stays there until another claims it\'s place. Type {}gym for more information.'.format(commandPrefix))
		return em

	gymCooldown = 1800	
	async def display_gym(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]

		msg = ''
		if not player.hasStarted():
			await display_not_started(message, commandPrefix)
		else:
			temp = message.content.split(' ')
			if len(temp)>2:
				gymId = int(temp[1])
				option = temp[2].lower()

				if gymId >=1 and gymId <= numberOfGyms:
					if option == 'info':
						await display_info_gym(message, gymId, commandPrefix)
					elif option == 'fight':
						lastDuel = datetime.datetime.now().timestamp() - player.lastGym.timestamp()
						if lastDuel < duelCooldown:
							msg = '{0}, you have just battled a gym! You will be able to challenge a gym again in {1}.'.format(message.author.mention, convertDeltaToHuman(gymCooldown - lastDuel))
							em = discord.Embed(title='On cooldwn!', description=msg, colour=0xDEADBF)
							em.set_author(name='Professor Oak', icon_url=oakUrl)
							await client.send_message(message.channel, embed=em)
						else:
							row = getGymInfo(gymId)

							gymPokemon = Pokemon(name='', pokemonId=row['pokemon_p_id'], level=row['pokemon_level'], iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']})

							playerPokemon = player.getSelectedPokemon()

							em = check_not_started(message.author.mention, player, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							em = check_player_pokemon_healing(message.author.mention, playerPokemon, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							em = check_player_pokemon_hp(message.author.mention, playerPokemon, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							player.lastGym = datetime.datetime.now()
							battle = Battle(challenger1=playerPokemon, challenger2=gymPokemon, gym=True)
							
							winner, battleLog, levelUpMessage = battle.execute()

							msg = '{0.author.mention}, your {1} fought a beautiful battle against gym leader {2}\'s {3}! Here are the details: \n\n'.format(message, playerPokemon.name, row['player_name'], gymPokemon.name)
							em = discord.Embed(title='{} Gym Battle: {} Lv. {} vs {} Lv. {}!'.format(row['type_identifier'], playerPokemon.name, playerPokemon.pokeStats.level, gymPokemon.name, gymPokemon.pokeStats.level), description=msg+battleLog, colour=0xDEADBF)
							em.set_author(name='Professor Oak', icon_url=oakUrl)
							em.set_thumbnail(url=getImageUrl(gymPokemon.pId, gymPokemon.mega))
							em.set_footer(text='HINT: You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
							await client.send_message(message.channel, embed=em)

							if winner == playerPokemon:
								if player.addBadge([gymId, row['type_identifier'].upper()]):
									em = discord.Embed(title='You got a new badge!', description='{0.author.mention}, you won against {1}\'s {2} and earned the {3} gym badge!'.format(message, row['player_name'], gymPokemon.name, row['type_identifier'].upper()), colour=0xDEADBF)
									em.set_author(name='Professor Oak', icon_url=oakUrl)
									em.set_thumbnail(url=message.author.avatar_url)
									em.set_footer(text='HINT: Think you have what it takes to hold a gym? You can fight for the claim of a gym by typing {}gym # claim.'.format(commandPrefix))
									await client.send_message(message.channel, embed=em)

					elif option == 'claim': 
						lastDuel = datetime.datetime.now().timestamp() - player.lastGym.timestamp()
						if lastDuel < duelCooldown:
							msg = '{0}, you have just battled a gym! You will be able to challenge a gym again in {1}.'.format(message.author.mention, convertDeltaToHuman(gymCooldown - lastDuel))
							em = discord.Embed(title='On cooldwn!', description=msg, colour=0xDEADBF)
							em.set_author(name='Professor Oak', icon_url=oakUrl)
							await client.send_message(message.channel, embed=em)
						else:
							row = getGymInfo(gymId)

							gymPokemon = Pokemon(name='', pokemonId=row['pokemon_p_id'], level=row['pokemon_level'], iv={'hp' : row['iv_hp'], 'attack' : row['iv_attack'], 'defense' : row['iv_defense'], 'special-attack' : row['iv_special_attack'], 'special-defense' : row['iv_special_defense'], 'speed' : row['iv_speed']})

							playerPokemon = player.getSelectedPokemon()

							em = check_not_started(message.author.mention, player, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							em = check_poketype(message.author.mention, playerPokemon, gymId, row['type_identifier'], commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							em = check_hold_availability(message.author.mention, player, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							em = check_player_pokemon_healing(message.author.mention, playerPokemon, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							em = check_player_pokemon_hp(message.author.mention, playerPokemon, commandPrefix)
							if em:
								await client.send_message(message.channel, embed=em)
								return

							player.lastGym = datetime.datetime.now()
							battle = Battle(challenger1=playerPokemon, challenger2=gymPokemon, gym=True)
							
							winner, battleLog, levelUpMessage = battle.execute()

							msg = '{0.author.mention}, your {1} fought a beautiful battle against gym leader {2}\'s {3}! Here are the details: \n\n'.format(message, playerPokemon.name, row['player_name'], gymPokemon.name)
							em = discord.Embed(title='Gym Battle: {} Lv. {} vs {} Lv. {}!'.format(playerPokemon.name, playerPokemon.pokeStats.level, gymPokemon.name, gymPokemon.pokeStats.level), description=msg+battleLog, colour=0xDEADBF)
							em.set_author(name='Professor Oak', icon_url=oakUrl)
							em.set_thumbnail(url=getImageUrl(gymPokemon.pId, gymPokemon.mega))
							em.set_footer(text='HINT: You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
							await client.send_message(message.channel, embed=em)

							if winner == playerPokemon:
								if player.addBadge([gymId, row['type_identifier'].upper()]):
									em = discord.Embed(title='You got a new badge!', description='{0.author.mention}, you won against {1}\'s {2} and earned the {3} gym badge!'.format(message, row['player_name'], gymPokemon.name, row['type_identifier'].upper()), colour=0xDEADBF)
									em.set_author(name='Professor Oak', icon_url=oakUrl)
									em.set_thumbnail(url=message.author.avatar_url)
									em.set_footer(text='HINT: Think you have what it takes to hold a gym? You can fight for the claim of a gym by typing {}gym # claim.'.format(commandPrefix))
									await client.send_message(message.channel, embed=em)

								em = discord.Embed(title='{} is now the leader of the {} gym!'.format(message.author.name, row['type_identifier'].upper()), description='{0.author.mention}, you won against {1}\'s {2} and are now the leader of the {3} gym!'.format(message, row['player_name'], gymPokemon.name, row['type_identifier'].upper()), colour=0xDEADBF)
								em.set_author(name='Professor Oak', icon_url=oakUrl)
								em.set_thumbnail(url=getImageUrl(winner.pId, winner.mega))
								em.set_footer(text='HINT: Taking too long to level up? Buy an EXP boost at the shop! Type {}shop for more information.'.format(commandPrefix))

								cursor = MySQL.getCursor()
								cursor.execute("""
									UPDATE gym
									SET holder_id = %s,
										pokemon_id = %s
									AND type_id = %s
									""", (player.pId, playerPokemon.ownId, gymId))
								
								cursor.execute("""
									UPDATE player_pokemon
									SET selected = 0,
										in_gym = %s
									WHERE player_id = %s
									AND id = %s
									""", (gymId, player.pId, playerPokemon.ownId))

								cursor.execute("""
									UPDATE player_pokemon
									SET selected = 0,
										in_gym = 0
									WHERE player_id = %s
									AND id = %s
									""", (row['holder_id'], row['gym_pokemon_id']))
								MySQL.commit()

								cursor.execute("""
									SELECT * 
									FROM player_pokemon
									WHERE player_id = %s
									AND in_gym = 0
									""", (player.pId,))
								row = cursor.fetchone()

								player.selectPokemon(row['id'])

								await client.send_message(message.channel, embed=em)
				else:
					await display_info_gyms(message, commandPrefix)
			else:
				await display_info_gyms(message, commandPrefix)

	async def display_donation(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		msg = "PDA is a for fun project that I work on as a hobby, and I'm really happy with how it's turning out! If you want to support me, help me pay for the server, or even request a feature, you can send a donation directly to me via PayPal to __matheus.pinheiro@usp.br__. If you want to request a feature, send an email to contact@yfrit.com, and I'll be happy to talk to you!"
		await client.send_message(message.channel, msg)

	async def ping(message):
		time
		channel = message.channel
		t1 = time.perf_counter()
		await client.send_typing(channel)
		t2 = time.perf_counter()
		return await client.send_message(message.channel, 'Pong! {}ms.'.format(round((t2-t1)*1000)).format(round((t2-t1)*1000)))

	megaEvolutionPrice = 250000
	async def display_mega_info_message(message, commandPrefix, pokemon, player):
		msg = '{0.author.mention}, here\'s what you need for your Mega Evolution: \n\n'.format(message, megaEvolutionPrice)
		msg += "**Level:** {0}/100.\n".format(pokemon.pokeStats.level)
		msg += "**Badges:** \n"

		for t in pokemon.types:
			msg += "    {0}: {1}\n ".format(t.identifier.upper(), ("✓" if player.hasBadge(t.tId, t.identifier) else "򪪪"))

		msg += "**Money:** {0}₽/{1}₽. \n".format(player.money, megaEvolutionPrice)

		em = discord.Embed(title='Sorry, but you can\'t mega evolve yet!', description=msg, colour=0xDEADBF)
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: You can buy an EXP Boost on the PokeMart to level up your pokemon faster!')
		await client.send_message(message.channel, embed=em)

	async def display_mega_evolved_message(message, commandPrefix, pokemon):
		msg = '{0.author.mention}, congratulations, you now have a {1}!'.format(message, pokemon.name)
		em = discord.Embed(title='What!? It\'s mega evolving!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: You can buy an EXP Boost on the PokeMart to level up your pokemon faster!')
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		await client.send_message(message.channel, embed=em)

	async def display_mega_nomega_message(message, commandPrefix, pokemon):
		msg = '{0.author.mention}, that is a {1}! It cannot Mega Evolve.'.format(message, pokemon.name)
		em = discord.Embed(title='That is not how this works!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: You can buy an EXP Boost on the PokeMart to level up your pokemon faster!')
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		await client.send_message(message.channel, embed=em)

	async def display_mega_ismega_message(message, commandPrefix, pokemon):
		msg = '{0.author.mention}, that is a {1}! It is already Mega Evolved!'.format(message, pokemon.name)
		em = discord.Embed(title='That is not how this works!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: You can buy an EXP Boost on the PokeMart to level up your pokemon faster!')
		em.set_thumbnail(url=getImageUrl(pokemon.pId, pokemon.mega))
		await client.send_message(message.channel, embed=em)

	async def display_mega_no_money_message(message, commandPrefix, player):
		msg = '{0.author.mention}, you need {1}₽ to do that!'.format(message, megaEvolutionPrice)
		em = discord.Embed(title='Out of cash... You only have {}₽.'.format(player.money), description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: Winning against trainers is a very good way of getting cash!')
		await client.send_message(message.channel, embed=em)

	async def display_mega(message):
		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()

		player = playerMap[message.author.id]
			
		hasMega, hasBadges, isMega, hasLevel = player.megaEvolveSelectedPokemon()
		pokemon = player.getSelectedPokemon()

		if not hasMega:
			await display_mega_nomega_message(message, commandPrefix, pokemon)
		elif isMega:
			await display_mega_ismega_message(message, commandPrefix, pokemon)
		elif not hasBadges or not hasLevel:
			await display_mega_info_message(message, commandPrefix, pokemon, player)
		else:
			if player.removeMoney(megaEvolutionPrice):
				await display_mega_evolved_message(message, commandPrefix, pokemon)
			else:
				await display_mega_info_message(message, commandPrefix, pokemon, player)


	async def display_rank(message):
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT *
			FROM player
			ORDER BY level DESC
			LIMIT 10
		""")
		rows = cursor.fetchall()

		counter = 1
		msg = ''
		for row in rows:
			msg += '**{0}.** {1}: Level {2} | {3} Pokemons owned | {4}₽\n'.format(counter, row['name'], row['level'], row['pokemon_caught'], row['money'])
			counter += 1

		em = discord.Embed(title='Top 10 PokeTrainers', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='HINT: Winning against trainers is a very good way of getting cash!')
		await client.send_message(message.channel, embed=em)

	#'welcome' : send_greeting,
	commandList = {
		'start' : select_starter,
		'i' : display_pokemon_info,
		'info' : display_pokemon_info,
		'p' : display_pokemons,
		'pokemon' : display_pokemons,
		'a' : display_favorite_pokemons,
	#	'v' : display_favorite_pokemons,
	#	'favorite' : display_favorite_pokemons,
		's' : select_pokemon,
		'select' : select_pokemon,
		'r' : release_pokemon,
		'release' : release_pokemon,
		'help' : display_help,
		'invite' : display_invite,
		'server' : display_server,
		'f' : display_fight,
		'fight' : display_fight,
		'c' : display_catch,
		'catch' : display_catch,
		'h' : display_center,
		'center' : display_center,
		'hospitalize' : display_center,
		'heal' : display_center,
		'me' : display_me,
		'b' : display_shop,
		'shop' : display_shop,
		'buy' : display_shop,
		'u' : display_item,
		'item' : display_item,
		'use' : display_item,
		'd' : challenge_player,
		'duel' : challenge_player,
		'a' : accept_challenge,
		'accept' : accept_challenge,
		'g' : display_gym,
		'gym' : display_gym,
		'donate' : display_donation,
		'ping' : ping,
		'mega' : display_mega,
		'rank' : display_rank,
		'trade' : display_candy_shop
	}

	admin = 229680411079475201
	adminCommandList = {
		#'stop' : stop_server,
		'add' : add_random_pokemon,
		'give' : give_pokemon,
	}

	serverAdminCommandList = {
		'prefix' : change_prefix,
		'spawn' : set_spawn_channel
	}

	playerMessageMap = {}
	messageThreshold = 1.5
	async def executeCommand(commandList, command, key, message):
		lastMessage = playerMessageMap[key]
		deltaTime = datetime.datetime.now().timestamp() - lastMessage
		if deltaTime>messageThreshold:
			playerMessageMap[key] = datetime.datetime.now().timestamp()
			await commandList[command](message)

	@client.event
	async def on_message(message):
		await client.wait_until_ready()

		# we do not want the bot to reply to itself
		if message.author == client.user:
			return 

		commandPrefix, spawnChannel = serverMap[message.server.id].get_prefix_spawnchannel()
		serverMap[message.server.id].serverMessageMap = datetime.datetime.now().timestamp()

		content = message.content.lower()
		if content.startswith(commandPrefix):
			key = message.author.id
			if not key in playerMap:
				playerMap[key] = Player(key, message.author.name if (message.author.name is not '') else 'Unknown')
				playerMessageMap[key] = 0

			random.seed()
			
			# get command
			command = content.split(' ')[0].replace(commandPrefix, '')

			# try executing command as player
			if command in commandList:
				await executeCommand(commandList, command, key, message)
				return

			# try executing command as server admin		
			if command in adminCommandList and int(message.author.id) == int(admin):
				await executeCommand(adminCommandList, command, key, message)
				return

			# try execyting command as game admin
			if command in serverAdminCommandList and message.author.server_permissions.administrator:
				await executeCommand(serverAdminCommandList, command, key, message)
				return

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
			print(datetime.datetime.now(), M_TYPE_INFO, 'Found server \'{}\' in database. Fetching configs.'.format(server.id))
			commandPrefix = row['prefix']
			spawnChannel = row['spawn_channel']
		else:
			print(datetime.datetime.now(), M_TYPE_INFO, 'Server \'{}\' was not found in database. Adding.'.format(server.id))
			cursor.execute("""
			INSERT INTO server (id)
			VALUES (%s)"""
			, (server.id,))
			
		serverMap[server.id] = PokeServer(id=server.id, commandPrefix=commandPrefix.lower(), spawnChannel=spawnChannel)
		print(datetime.datetime.now(), M_TYPE_INFO, 'Done.')

	def isGymFirstPokemonExist():
		return getGymInfo(1) is not None

	def createFirstGymPokemon():
		if isGymFirstPokemonExist():
			return

		print(datetime.datetime.now(), M_TYPE_INFO, 'No Gym pokemon found. Creating.')
		cursor = MySQL.getCursor()
		
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
				INSERT INTO gym (type_id, holder_id, pokemon_id)
				VALUES (%s, 'PDA', %s)
				""", (row['id'], lastPokemon))

		MySQL.commit()
		print(datetime.datetime.now(), M_TYPE_INFO, 'Gym pokemon added.')

	filePath = os.path.abspath('motd.txt')
	with open(filePath, "r") as file:
		messageFile = file.read()

	async def send_online_message(channel):
		em = discord.Embed(title='PDA admin.', description=messageFile, colour=0xDEADBF)
		try:
			pass
			#await client.send_message(channel, embed=em)
		except Exception as e:
			print(datetime.datetime.now(), M_TYPE_WARNING, "Can't send message to channel {}. Missing permissions. Skipping.".format(str(channel)))

	@client.event
	async def on_ready():
		print(datetime.datetime.now(), M_TYPE_INFO, 'Logged in as')
		print(datetime.datetime.now(), M_TYPE_INFO, client.user.name)
		print(datetime.datetime.now(), M_TYPE_INFO, client.user.id)
		print(datetime.datetime.now(), M_TYPE_INFO, '------')

		createFirstGymPokemon()

		for server in client.servers:
			evaluate_server(server)
			spawnChannel = serverMap[server.id].spawnChannel
			if spawnChannel:
				for channel in server.channels:
					if channel.id == spawnChannel:
						await send_online_message(channel)

		client.loop.create_task(spawn_wild_pokemon())

		print(datetime.datetime.now(), M_TYPE_INFO, '------')
		
		print(datetime.datetime.now(), M_TYPE_INFO, 'Load item list')
		cursor = MySQL.getCursor()
		cursor.execute("""SELECT * FROM item""")

		rows = cursor.fetchall() 
		for row in rows:
			item = PokeItem(id=row['id'], itemType=row['type'], name=row['name'], price=row['price'], description=row['description'], value=row['value'])
			items.append(item)
			if row['price']>0:
				shopItems.append(item)
		print(datetime.datetime.now(), M_TYPE_INFO, '------')

	try:
		print(datetime.datetime.now(), M_TYPE_INFO, "Starting PDA Bot.")
		client.loop.run_until_complete(client.start(TOKEN))
	except SystemExit:
		handle_exit()
	except KeyboardInterrupt:
		handle_exit()
		client.loop.close()
		print(datetime.datetime.now(), M_TYPE_ERROR, "PDA was interrupted.")
		break

	print(datetime.datetime.now(), M_TYPE_ERROR, "A problem occurred, PDA is restarting.")
	client = discord.Client(loop=client.loop)
