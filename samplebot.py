# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py
import textwrap
import discord
import random
import math
import asyncio
import datetime
import traceback
import humanfriendly

from player import Player
from pokemon import Pokemon
from battle import Battle
from mysql import MySQL
from datetime import timedelta
from pitem import PokeItem

# TODO:
# Implement dudududuel time
# Implement gyms

TOKEN = 'NDYzNzQ0NjkzOTEwMzcyMzYy.Dh03cA.jaXIvI0zQdOieINXT46_Y9X-L2k'

client = discord.Client()
playerMap = {}
imageURL = 'https://microcubo.com.br/pokemon/{}.png'
trainerURL = 'https://microcubo.com.br/pokemon/Trainer_{}.png'
oakUrl = 'https://i.imgur.com/VbSBVi7.png'
grassUrl = 'https://i.imgur.com/zdeDVpY.png'
joyUrl = 'https://i.imgur.com/OIr3D6x.png'
pokeballUrl = 'https://i.imgur.com/2jQoEjs.png'
pokeMartUrl = 'https://i.imgur.com/RkJQOOh.png'

# lastPokemonEnabled = 649

async def send_greeting(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	msg = 'Hello {0.author.mention}, and welcome to Pokemon Discord Adventure! To start your wonderful journey, type {1}start to see the info about starter Pokemons!'.format(message, commandPrefix)
	em = discord.Embed(title='Welcome!', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	em.set_footer(text='Use {}start # to select a starter pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, msg)

starters = 'Bulbasaur (1), Charmander (2) or Squirtle (3)'
startersId = [1, 4, 7]
async def select_starter(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]
	
	msg = '{0.author.mention}, the possible starters are {1}. Type {2}start followed by a number to select a starter. For instance, {2}start 2 will give you Charmander!'.format(message, starters, commandPrefix)

	if player.hasStarted():
		msg = '{0.author.mention}, you have already selected a starter pokemon!'.format(message)
	else:
		temp = message.content.split(' ')
		
		option = None
		if len(temp)>1:
			option = int(temp[1])

		if option:
			try:
				pId = startersId[option-1]
				msg = '{0.author.mention}, here\'s your level 5 starter Pokemon!'.format(message)
				player.addPokemon(pokemonId=pId, level=5, selected=True)
				await display_pokemon_info(message)
			except IndexError:
				pass

	em = discord.Embed(title='Choose your starter!', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	em.set_footer(text='Use {}start # to select a starter pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_pokemon_info(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]

	if player.hasStarted():
		temp = message.content.split(' ')
		
		option = None
		if len(temp)>1:
			option = int(temp[1])

		if option:
			pokemon = player.getPokemon(option)
		else:
			pokemon = player.getSelectedPokemon()
		
		em = discord.Embed(title='{}\'s Pokemon'.format(message.author.name), description=str(pokemon), colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=imageURL.format(pokemon.pId))
		em.set_footer(text='Use {0}pokemon to see your full list of Pokemon. Use {0}info # to see info of an unselected pokemon.'.format(commandPrefix))
		await client.send_message(message.channel, embed=em)
	else:
		await display_not_started(message, commandPrefix)

async def display_pokemons(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]
	if player.hasStarted():
		temp = message.content.split(' ')
		
		option = None
		if len(temp)>1:
			option = int(temp[1])

		pokemonList = None
		curPage = 1
		pages = 1
		if not option:
			option = 1 + player.getSelectedPokemon().ownId // Player.pokemonPerPage

		curPage = option
		pokemonList, pages = player.getPokemonList(option)

		string = ''
		if len(pokemonList)>0:
			counter = ((curPage-1) * Player.pokemonPerPage) + 1
			for pokemon, selected, inGym in pokemonList:
				string += ('**' if selected else '') + str(counter) + ': ' + pokemon.name + ' Lv. {}'.format(pokemon.pokeStats.level) + (' (selected)**' if selected else '') + (' *(holding gym {})*'.format(inGym) if inGym > 0 else '') + '\n'
				counter += 1
		else:
			string = 'Invalid page.'

		em = discord.Embed(title='Pokemon List', description=string, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='Page {}/{}. Use {}pokemon # to select a different page.'.format(curPage, pages, commandPrefix))
		await client.send_message(message.channel, embed=em)

async def display_pokemon_in_gym(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	msg = '{0.author.mention}, that pokemon is currently holding a gym, it cannot be selected.'.format(message)
	em = discord.Embed(title='Cannot select!', description=str(msg), colour=0xDEADBF)
	em.set_thumbnail(url=message.author.avatar_url)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	await client.send_message(message.channel, embed=em)

async def select_pokemon(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]
	
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
						pokemon = player.getPokemon(option)
						if pokemon:
							player.selectPokemon(pokemon.ownId)
							await display_pokemon_info(message)
						else:
							await display_pokemon_in_gym(message)
					except IndexError as error:
						print(error)
						traceback.print_exc()
			except ValueError as err:
				print(err)

async def display_help(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	msg = 'These are the possible commands: \n\n' \
		'__Player Commands:__ \n\n' \
		'**{0}info:** Shows stats of a specific pokemon (selected pokemon if none is specified) \n' \
		'**{0}start:** Shows information on how to select a starter and start the adventure. \n' \
		'**{0}pokemon:** Shows a list of all your pokemon. \n' \
		'**{0}select:** Selects a pokemon in your list to use on your journey.\n' \
		'**{0}help:** Shows this help message. \n' \
		'**{0}fight:** Fights the currently spawned pokemon or poketrainer if available.\n' \
		'**{0}catch:** Fights and tries to catch the currently spawned pokemon if available.\n' \
		'**{0}center:** Heals wounded pokemon.\n' \
		'**{0}me:** Shows information on the player.\n' \
		'**{0}shop:** Displays the shop.. \n' \
		'**{0}item:** Displays the player inventory. \n' \
		'**{0}duel:** Challenges another player to a duel. \n' \
		'**{0}accept:** Accepts a duel challenge. \n' \
		'**{0}gym:** Shows information on the gyms. \n\n' \
		'__Admin Commands:__ \n\n' \
		'**{0}prefix:** Changes the prefix used to trigger bot commands (default is p). \n' \
		'**{0}spawn:** Sets the channel where wild pokemon and poketrainers will spawn. \n'
	msg = msg.format(commandPrefix)
	em = discord.Embed(title='Help!', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	await client.send_message(message.channel, embed=em)

def get_random_pokemon_spawn():
	rates = [3,15,25,30,35,45,50,55,60,65,70,75,80,90,100,120,125,127,130,140,145,150,155,160,170,180,190,200,205,220,225,235,255]
	rateList = []
	for i in range(0,len(rates)):
		rateList += int(rates[i] ** 1.5) * [rates[i]]
	
	generationList = []
	for i in range(1, 7):
		generationList += 20//i * [i]
	
	row = None
	while not row:
		captureRate = random.choice(rateList)
		generation = random.choice(generationList)
		cursor = MySQL.getCursor()
		cursor.execute("""
			SELECT * 
			FROM pokemon
			WHERE enabled = 1 
			AND capture_rate = %s
			AND generation_id = %s
			ORDER BY RAND()
			LIMIT 1
			""", (captureRate, generation))
		row = cursor.fetchone()

	print(textwrap.dedent("""SPAWN INFO
Capture Rate: %d
Chance: %f
Generation: %d
Chance: %f
""") % (
		captureRate,
		int(captureRate ** 1.5) / len(rateList),
		generation,
		(20 // generation) / len(generationList)
	))
	
	return row['id'], row['identifier'].upper()

def convertDeltaToHuman(deltaTime):
	return humanfriendly.format_timespan(deltaTime)

valueMod = 5.5
ballList = ['Poke Ball', 'Great Ball', 'Ultra Ball', 'Master Ball']
class Spawn:
	name = {}
	pId = {}
	spawned = {}
	fought = {}
	trainer = {}

	@staticmethod
	async def fight(message, capture=0):
		try:
			commandPrefix, spawnChannel = serverMap[message.server.id]
		except KeyError as err:
			return

		if spawnChannel != message.channel.id:
			return

		player = playerMap[message.author.id + message.server.id]

		if message.server.id not in Spawn.spawned:
			msg = '{0.author.mention}, there are no wild pokemon or trainers willing to fight near you at this time.'.format(message)
			em = discord.Embed(title='Ops!', description=msg, colour=0xDEADBF)
			em.set_author(name='Tall Grass', icon_url=grassUrl)
			em.set_footer(text='No wild pokemon? Challenge a friend to a duel by typing {}duel @nickname!'.format(commandPrefix))
			await client.send_message(message.channel, embed=em)
			return
		
		if Spawn.spawned[message.server.id] and not player.pId in Spawn.fought[message.server.id]:
			playerPokemon = player.getSelectedPokemon()

			if not playerPokemon:
				await display_not_started(message, commandPrefix)
				return

			isHealing, deltaTime = playerPokemon.isHealing()
			if isHealing == True:
				msg = '{0.author.mention}, your {1} is currently healing at the pokemon center, and won\'t be able to fight for {2}.'.format(message, playerPokemon.name, convertDeltaToHuman(deltaTime))
				em = discord.Embed(title='There is no way!', description=msg, colour=0xDEADBF)
				em.set_author(name='Nurse Joy', icon_url=joyUrl)
				em.set_thumbnail(url=imageURL.format(playerPokemon.pId))
				em.set_footer(text='Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
				await client.send_message(message.channel, embed=em)
				return
			elif isHealing == False:
				cursor = MySQL.getCursor()
				cursor.execute("""
					UPDATE player_pokemon
					SET healing = NULL
					WHERE id = %s
					""", (playerPokemon.ownId,))
				MySQL.commit()
				playerPokemon.healing = None
				playerPokemon.pokeStats.hp = playerPokemon.pokeStats.current['hp']				

			if playerPokemon.pokeStats.hp > 0:
				level = playerPokemon.pokeStats.level
				levelDeviation = 1/(math.log10(level)+1)
				newLevel =  int(random.uniform(levelDeviation, 1) * level)
				# newLevel = 100 if newLevel > 100 else newLevel
				# newLevel = 1 if newLevel < 1 else newLevel

				isTrainer, gender = Spawn.trainer[message.server.id]
				wildPokemon = Pokemon(name=Spawn.name[message.server.id], pokemonId=Spawn.pId[message.server.id], level=newLevel, wild=1 if not isTrainer else 1.5)
				boost = None
				if player.isBoosted():
					boost = playerPokemon
				battle = Battle(playerPokemon, wildPokemon, True)
				winner, battleLog, levelUpMessage = battle.execute()
				player.commitPokemonToDB()

				captureMessage = ''
				victory = winner == playerPokemon
				if victory:
					Spawn.fought[message.server.id].append(player.pId)

					baseValue = int(3.65*valueMod*(player.level/50)*(wildPokemon.pokeStats.level*255/wildPokemon.captureRate))//3
					player.addExperience(baseValue)
					
					if capture>0:
						player.items[capture-1] -= 1
						captureMessage += '\nYou threw a {} into {} and...\n'.format(ballList[capture-1], wildPokemon.name)
						if True or wildPokemon.attemptCapture(capture-1):
							captureMessage += '```fix\nGotcha! {} was added to your pokemon list!\n```'.format(wildPokemon.name)
							wildPokemon.caughtWith = capture
							player.addExperience(baseValue * math.log10(wildPokemon.pokeStats.level))
							player.addPokemonViaInstace(wildPokemon)
						else:
							captureMessage += '```css\nIt escaped...\n```'

					if levelUpMessage:
						lem = discord.Embed(title='Level up!', description='{0.author.mention}, your '.format(message) + levelUpMessage, colour=0xDEADBF)
						lem.set_author(name='Professor Oak', icon_url=oakUrl)
						lem.set_thumbnail(url=imageURL.format(winner.pId))
						lem.set_footer(text='Two pokemons of the same species and level can have different stats. That happens because pokemon with higher IV are stronger. Check your pokemon\'s IV by typing {}info!'.format(commandPrefix))

				if isTrainer:
					if not player.pId in Spawn.fought[message.server.id]:
						Spawn.fought[message.server.id].append(player.pId)

					if victory:
						money = int(random.uniform(6,7)*baseValue)
						player.addMoney(money)
						trainerMessage = 'Damn, {}! Your *{}* completely destroyed my *{}*! Here\'s **{}₽** for your deserved win!'.format(message.author.mention, playerPokemon.name, wildPokemon.name, money)
					else:
						trainerMessage = 'Wow, {}! My *{}* destroyed your *{}*! Better luck next time!'.format(message.author.mention, wildPokemon.name, playerPokemon.name)

					tem = discord.Embed(title='Well fought!', description=trainerMessage, colour=0xDEADBF)
					tem.set_author(name='Poketrainer', icon_url=pokeballUrl)
					tem.set_thumbnail(url=trainerURL.format(gender))

					player.update()
						
				msg = '{0.author.mention}, your {1} fought a beautiful battle against {2}! Here are the details: \n\n'.format(message, playerPokemon.name, wildPokemon.name)
				em = discord.Embed(title='Battle with {}{} Lv. {}!'.format('Trainer\'s ' if isTrainer else '', wildPokemon.name, newLevel), description=msg+battleLog+captureMessage, colour=0xDEADBF)
				em.set_author(name='Professor Oak', icon_url=oakUrl)
				em.set_thumbnail(url=imageURL.format(Spawn.pId[message.server.id]))
				em.set_footer(text='You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
				await client.send_message(message.channel, embed=em)
				
				if victory and levelUpMessage:
					await client.send_message(message.channel, embed=lem)

				if isTrainer:
					await client.send_message(message.channel, embed=tem)					

			else:
				msg = '{0.author.mention}, your pokemon has 0 HP, it is in no condition to fight! Take it to the pokemon center by typing {1}center.'.format(message, commandPrefix)
				em = discord.Embed(title='Your {} is fainted!'.format(playerPokemon.name), description=msg, colour=0xDEADBF)
				em.set_author(name='Professor Oak', icon_url=oakUrl)
				await client.send_message(message.channel, embed=em)
		else:
			msg = '{0.author.mention}, there are no wild pokemon or trainers willing to fight near you at this time.'.format(message)
			em = discord.Embed(title='Ops!', description=msg, colour=0xDEADBF)
			em.set_author(name='Tall Grass', icon_url=grassUrl)
			em.set_footer(text='No wild pokemon? Challenge a friend to a duel by typing {}duel @nickname!'.format(commandPrefix))
			await client.send_message(message.channel, embed=em)

	@staticmethod	
	async def spawn():
		delay = random.randint(10, 35)
		print('Spawn delay is {}.'.format(delay))
		await asyncio.sleep(delay)

		for server in client.servers:
			try:
				commandPrefix, spawnChannel = serverMap[server.id]
			except KeyError as err:
				return

			if server.id not in Spawn.spawned:
				Spawn.spawned[server.id] = False
				Spawn.name[server.id] = ''
				Spawn.pId[server.id] = 0
				Spawn.fought[server.id] = []
				Spawn.trainer[server.id] = [False, 0]

			for channel in server.channels:
				print(server.id, channel.id, spawnChannel)
				if channel.id == spawnChannel:
					if not Spawn.spawned[server.id]:
						serverSpawnChance = random.randint(0,255)
						print('Spawn chance for server {}/{}.'.format(serverSpawnChance, 50))
						if serverSpawnChance < 50:
							break

						Spawn.spawned[server.id] = True
						Spawn.pId[server.id], Spawn.name[server.id] = get_random_pokemon_spawn()
						Spawn.trainer[server.id][0] = random.randint(0, 255)<=30
						Spawn.trainer[server.id][1] = random.randint(0, 1)
						isTrainer, gender = Spawn.trainer[server.id]
						if isTrainer:
							article = 'him' if gender==0 else 'her'
							msg = 'A poketrainer is looking for a challenger! Type {0}fight to fight {1}!'.format(commandPrefix, article)
							em = discord.Embed(title='Here comes a new challenger!', description=msg, colour=0xDEADBF)
							em.set_author(name='Tall Grass', icon_url=grassUrl)
							em.set_thumbnail(url=trainerURL.format(gender))
							em.set_footer(text='You cannot catch other trainer\'s pokemon, but you will earn money if you win the fight.'.format(commandPrefix))
						else:
							msg = 'A wild {0} wants to fight! Type {1}fight to fight it, or {1}catch to try and catch it as well!'.format(Spawn.name[server.id], commandPrefix)
							em = discord.Embed(title='A wild {} appeared!'.format(Spawn.name[server.id]), description=msg, colour=0xDEADBF)
							em.set_author(name='Tall Grass', icon_url=grassUrl)
							em.set_thumbnail(url=imageURL.format(Spawn.pId[server.id]))
							em.set_footer(text='You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
						await client.send_message(channel, embed=em)
						#await asyncio.sleep(50)
					else:
						isTrainer, gender = Spawn.trainer[server.id]
						if isTrainer:
							msg = 'The poketrainer is gone! Don\'t worry if you didn\'t have a chance to fight {}, though. Pokemon trainers eager to fight always come back.'.format('him' if gender==0 else 'her')
							em = discord.Embed(title='Bye!', description=msg, colour=0xDEADBF)
							em.set_thumbnail(url=trainerURL.format(gender))
							em.set_author(name='Tall Grass', icon_url=grassUrl)
							em.set_footer(text='Your selected pokemon must be in fighting conditions for you to enter a fight! If you need to heal it, type {}center.'.format(commandPrefix))
						else:
							msg = 'Darn it, {} has fled the scene! Don\'t worry if you didn\'t have a chance to fight it, though. Wild pokemon appear a lot around these parts.'.format(Spawn.name[server.id], commandPrefix)
							em = discord.Embed(title='{} fled!'.format(Spawn.name[server.id]), description=msg, colour=0xDEADBF)
							em.set_thumbnail(url=imageURL.format(Spawn.pId[server.id]))
							em.set_author(name='Tall Grass', icon_url=grassUrl)
							em.set_footer(text='Your selected pokemon must be in fighting conditions for you to enter a fight! If you need to heal it, type {}center.'.format(commandPrefix))
						
						Spawn.spawned[server.id] = False
						Spawn.fought[server.id] = []
						await client.send_message(channel, embed=em)
						#await asyncio.sleep(5)
		restSpawn = random.randint(25, 45)
		print('Rest time for spawn is {}.'.format(restSpawn))
		await asyncio.sleep(restSpawn)

@asyncio.coroutine
async def spawn_wild_pokemon():
	await client.wait_until_ready()

	while not client.is_closed:
		#await asyncio.sleep(5)
		await Spawn.spawn()
		
async def add_random_pokemon(message):
	player = playerMap[message.author.id + message.server.id]
	for i in range(1,100):
		player.addPokemon(pokemonId=random.randint(1,500), level=random.randint(1,100))

async def stop_server(message):
	await client.logout()

async def change_prefix(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	temp = message.content.split(' ')
		
	option = None
	if len(temp)<=1:
		msg = 'Invalid prefix. Type {}prefix your_prefix to change the command prefix. In this example, commands would be called as your_prefix!command.'.format(commandPrefix)
	else:
		option = temp[1] + '!'
		if len(option)>10:
			msg = 'Invalid prefix. Prefix is too long. Maximum of 10 characters.'.format(commandPrefix)
		else:
			cursor = MySQL.getCursor()
			cursor.execute("""
				UPDATE server
				SET prefix = %s
				WHERE id = %s
				""", (option, message.server.id))
			msg = 'Prefix set to {0}. Commands now must be called as {0}!command.'.format(option)
			MySQL.commit()

			serverMap[message.server.id][0] = option

	em = discord.Embed(title='Change Prefix', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	await client.send_message(message.channel, embed=em)

async def set_spawn_channel(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	temp = message.content.split(' ')
		
	option = None
	if len(temp)<=1:
		msg = 'Type {}spawn #channel_name to set the channel where wild pokemon will appear.'.format(commandPrefix)
	else:
		option = temp[1].replace('#', '').replace('<', '').replace('>', '')
		selectedChannel = None
		for channel in message.server.channels:
			if int(channel.id) == int(option):
				selectedChannel = channel
				break
		if not selectedChannel:
			msg = 'Invalid channel. Type {}spawn #channel_name to set the channel where wild pokemon will appear.'.format(commandPrefix)
		else:
			cursor = MySQL.getCursor()
			cursor.execute("""
				UPDATE server
				SET spawn_channel = %s
				WHERE id = %s
				""", (selectedChannel.id, message.server.id))
			msg = 'Spawn channel set to #{0}.'.format(selectedChannel)
			MySQL.commit()

			serverMap[message.server.id][1] = selectedChannel.id

	em = discord.Embed(title='Set Spawn Channel', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	await client.send_message(message.channel, embed=em)

async def display_fight(message):
	await Spawn.fight(message)

def getBallsString(player):
	msg = ''
	counter = 1
	for ball in ballList:
		msg += '{}. {} ({} available)\n'.format(counter, ball, player.items[counter-1])
		counter += 1
	return msg

async def display_balls_message(message, player, commandPrefix):
	msg = '{0.author.mention}, type {1}!catch # to try to catch the wild pokemon. These are the possible pokeballs: \n\n'.format(message, commandPrefix)

	msg += getBallsString(player)

	em = discord.Embed(title='Select your pokeball!', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	em.set_footer(text='Low on pokeballs? You can buy more by typing {}shop. Or if you\'re low on cash, you get pokeballs by just staying online!'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_catch(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]

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
					isTrainer, gender = Spawn.trainer[message.server.id]
					if isTrainer:
						msg = '{0.author.mention}, you cannot catch a pokemon that belongs to a trainer!'.format(message, ballList[option-1])
						em = discord.Embed(title='That is not how this works!', description=msg, colour=0xDEADBF)
						em.set_author(name='Professor Oak', icon_url=oakUrl)
						await client.send_message(message.channel, embed=em)
					else:
						await Spawn.fight(message, option)
				else:
					msg = '{0.author.mention}, you don\'t have any {1}s left! Here\'s your list of pokeballs: \n\n'.format(message, ballList[option-1])

					counter = 1
					for ball in ballList:
						msg += '{}. {} ({} available)\n'.format(counter, ball, player.items[counter-1])
						counter += 1

					em = discord.Embed(title='Select your pokeball!', description=msg, colour=0xDEADBF)
					em.set_author(name='Professor Oak', icon_url=oakUrl)
					em.set_footer(text='Low on pokeballs? You can buy more by typing {}shop. Or if you\'re low on cash, you get pokeballs by just staying online!'.format(commandPrefix))
					await client.send_message(message.channel, embed=em)
		except ValueError as err:
			#print(err)
			await display_balls_message(message, player, commandPrefix)

async def display_success_pokecenter(message, commandPrefix):
	msg = '{0.author.mention}, we will take good care of your pokemon!'.format(message)
	em = discord.Embed(title='Thanks for using the pokemon center!', description=msg, colour=0xDEADBF)
	em.set_author(name='Nurse Joy', icon_url=joyUrl)
	em.set_thumbnail(url=imageURL.format(113))
	em.set_footer(text='Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_fail_pokecenter(message, commandPrefix):
	msg = '{0.author.mention}, welcome to the Pokemon Center! You can heal a single pokemon by typing {1}center #, or you can heal all your pokemon by typing {1}center all.'.format(message, commandPrefix)
	em = discord.Embed(title='Hello there!', description=msg, colour=0xDEADBF)
	em.set_author(name='Nurse Joy', icon_url=joyUrl)
	em.set_thumbnail(url=imageURL.format(113))
	em.set_footer(text='Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_healing_pokecenter(message, commandPrefix, pokemon, deltaTime):
	msg = '{0.author.mention}, your {1} is already being healed. It will be ready for battle in {2}.'.format(message, pokemon.name, convertDeltaToHuman(deltaTime))
	em = discord.Embed(title='Already healing!', description=msg, colour=0xDEADBF)
	em.set_author(name='Nurse Joy', icon_url=joyUrl)
	em.set_thumbnail(url=imageURL.format(113))
	em.set_footer(text='Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_healed_pokecenter(message, commandPrefix, pokemon):
	msg = '{0.author.mention}, your {1} is fully healed! It is ready for combat.'.format(message, pokemon.name)
	em = discord.Embed(title='All done!', description=msg, colour=0xDEADBF)
	em.set_author(name='Nurse Joy', icon_url=joyUrl)
	em.set_thumbnail(url=imageURL.format(113))
	em.set_footer(text='Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_center(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]

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
						pokemon = player.getPokemon(option)
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
	msg = '{0.author.mention}, you don\'t have a Pokemon yet! Type {1}start to start your adventure!'.format(message, commandPrefix)
	em = discord.Embed(title='Choose your starter!', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	em.set_footer(text='Use {}start # to select a starter pokemon.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

async def display_success_shop(message, commandPrefix):
	msg = '{0.author.mention}, thank you for your purchase!'.format(message)
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
	msg = ''
	counter = 1
	oldType = -1
	for item in shopItems:
		if oldType < item.itemType:
			msg += '\n' + itemTypes[item.itemType] + '\n\n'
			oldType = item.itemType

		msg += '**{}.** {} ({}₽)\n'.format(counter, item.name, item.price)
		msg += '**Description:** {}\n'.format(item.description)
		counter += 1
	return msg

async def display_info_shop(message, player, commandPrefix):
	msg = '{0.author.mention}, welcome to the Poke Mart! To buy an item type {1}shop *item #*. These are the items we have for sale:\n'.format(message, commandPrefix)
	em = discord.Embed(title='Hello there, {0}. You have {1}₽.'.format(message.author.name, player.money), description=msg+getItemsString(), colour=0xDEADBF)
	em.set_author(name='Poke Mart', icon_url=pokeballUrl)
	em.set_thumbnail(url=pokeMartUrl)
	em.set_footer(text='To use an item, type {0}item #. You can see your items by typing {0}item.'.format(commandPrefix))
	await client.send_message(message.channel, embed=em)

shopItems = []
items = []

async def display_shop(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]

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
					if player.removeMoney(item.price):
						await display_success_shop(message, commandPrefix)
						item = shopItems[option]
						player.addItem(item.id-1)
					else:
						await display_fail_shop(message, commandPrefix)

			except ValueError as err:
				traceback.print_exc()
		else:
			await display_info_shop(message, player, commandPrefix)

async def display_me(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]
	finalStr = str(player) + getBallsString(player)

	em = discord.Embed(title='{}\'s player information!'.format(message.author.name), description=str(finalStr), colour=0xDEADBF)
	em.set_thumbnail(url=message.author.avatar_url)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
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
		msg = '{0.author.mention}, use {1}item # to use an item. Here\'s your usable item list:\n\n'.format(message, commandPrefix)
		em = discord.Embed(title='{}\'s Inventory.'.format(message.author.name), description=msg+itemStr, colour=0xDEADBF)
	else:
		msg = '{0.author.mention}, you don\'t have any items at the moment. You can buy items by typing {1}shop.'.format(message, commandPrefix)
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
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]

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
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	temp = message.content.split(' ')
		
	option = None
	if len(temp)<=1:
		msg = 'Type {}duel @player to challenge a player for a duel.'.format(commandPrefix)
	else:
		player = playerMap[message.author.id + message.server.id]
		
		option = temp[1].replace('@', '').replace('<', '').replace('>', '')
		if str(message.author.id) == option:
			msg = 'You cannot battle yourself.'
		else:
			lastDuel = datetime.datetime.now().timestamp() - player.lastDuel.timestamp()
			if lastDuel < duelCooldown:
				msg = '{0}, you have just battled someone! You will be able to duel again in {1}.'.format(message.author.mention, convertDeltaToHuman(duelCooldown - lastDuel))
			else:
				member = message.server.get_member(option)
				if member:
					msg = '{0}, {1} is challenging you to a duel! Type {2}accept to accept!'.format(temp[1], message.author.mention, commandPrefix)
					duelMap[option + message.server.id] = [message.author.id + message.server.id, message.author.mention]
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
		em.set_thumbnail(url=imageURL.format(pokemon.pId))
		em.set_footer(text='Pokemon healing at pokecenter? You can choose other pokemon to fight by typing {0}select #! Use {0}pokemon to see your full list of pokemon.'.format(commandPrefix))
	
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
		msg = '{0}, your pokemon has 0 HP, it is in no condition to fight! Take it to the pokemon center by typing {1}center.'.format(callout, commandPrefix)
		em = discord.Embed(title='Your {} is fainted!'.format(pokemon.name), description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
	
	return em

def check_not_started(callout, player, commandPrefix):
	em = None
	if not player.hasStarted():
		msg = '{0}, you don\'t have a Pokemon yet! Type {1}start to start your adventure!'.format(callout, commandPrefix)
		em = discord.Embed(title='Choose your starter!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='Use {}start # to select a starter pokemon.'.format(commandPrefix))
	return em

duelCooldown = 300
async def accept_challenge(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	challengedKey = message.author.id + message.server.id
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

		boost = False
		if challenger.isBoosted():
			boost = challengerPokemon
		battle = Battle(challengerPokemon, challengedPokemon, boost)

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

		baseValue = int(3.65*valueMod*(winnerPlayer.level/50)*(loser.pokeStats.level*255/loser.captureRate))//3
		winnerPlayer.addExperience(baseValue)
		money = int(random.uniform(6,7)*baseValue)
		winnerPlayer.addMoney(money)
		winnerPlayer.update()
		
		if levelUpMessage:
			lem = discord.Embed(title='Level up!', description='{0}, your '.format(callout) + levelUpMessage, colour=0xDEADBF)
			lem.set_author(name='Professor Oak', icon_url=oakUrl)
			lem.set_thumbnail(url=imageURL.format(winner.pId))
			lem.set_footer(text='Two pokemons of the same species and level can have different stats. That happens because pokemon with higher IV are stronger. Check your pokemon\'s IV by typing {}info!'.format(commandPrefix))
		
		msg = '{0} and {1}, your {2} and {3} fought a beautiful battle against each other! Here are the details: \n\n'.format(challlengerCallout, message.author.mention, challengerPokemon.name, challengedPokemon.name)
		em = discord.Embed(title='{} Lv. {} vs {} Lv. {}!'.format(challengerPokemon.name, challengerPokemon.pokeStats.level, challengedPokemon.name, challengedPokemon.pokeStats.level), description=msg+battleLog, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_thumbnail(url=imageURL.format(winner.pId))
		await client.send_message(message.channel, embed=em)
		
		if levelUpMessage:
			await client.send_message(message.channel, embed=lem)

duelMap = {}

def check_poketype(callout, pokemon, tId, tAlias, commandPrefix):
	em = None
	if not pokemon.isType(tId):
		msg = '{0}, to claim the {1} gym your pokemon must be primarly {1}. {2}\'s primary type is {3}.'.format(callout, tAlias.upper(), pokemon.name, pokemon.types[0].identifier.upper(), commandPrefix)
		em = discord.Embed(title='Wrong type!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='Use {}start # to select a starter pokemon.'.format(commandPrefix))
	return em

def getGymInfo(serverId, gymId):
	cursor = MySQL.getCursor()
	cursor.execute("""
		SELECT type.id, gym.type_id, gym.pokemon_id as gym_pokemon_id, player_pokemon.id, gym.holder_id, player_pokemon.player_id, player_pokemon.id, pokemon.id as pokemon_p_id, gym.holder_id, player.id, type.identifier as type_identifier, player.name as player_name, pokemon.identifier as pokemon_identifier, player_pokemon.level as pokemon_level, gym.date as gym_date, iv_hp, iv_attack, iv_defense, iv_special_attack, iv_special_defense, iv_speed, gym.server_id as server_id
		FROM gym JOIN type JOIN player_pokemon JOIN pokemon JOIN player
		WHERE type.id = gym.type_id
		AND gym.pokemon_id = player_pokemon.id
		AND gym.holder_id = player_pokemon.player_id
		AND player_pokemon.pokemon_id = pokemon.id
		AND gym.holder_id = player.id
		AND gym.type_id = %s
		AND gym.server_id = %s
		""", (gymId, serverId))
	return cursor.fetchone()

async def display_info_gym(message, gymId, commandPrefix):
	row = getGymInfo(message.server.id, gymId)

	holdTime = convertDeltaToHuman(datetime.datetime.now().timestamp() - row['gym_date'].timestamp())
	msg = 'Here\'s the information about the {} type gym:\n\n'.format(row['type_identifier'].upper())
	msg += '**Pokemon:** {} Lv. {}.\n'.format(row['pokemon_identifier'].upper(), row['pokemon_level'])
	msg += '**Holder:** {}.\n'.format(row['player_name'])
	msg += '**Holding time:** {}.\n'.format(holdTime)

	em = discord.Embed(title='Gyms.', description=msg, colour=0xDEADBF)
	em.set_thumbnail(url=imageURL.format(row['pokemon_p_id']))
	em.set_footer(text='Use {0}gym to get a the full list of gyms'.format(commandPrefix))
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

	msg = 'If you want to become a Pokemon master, you need to beat all the gyms and get all the badges! There are 18 gyms in total, each one with a different pokemon type. Gyms can be held by players if they\'re able to win a fight against the current owner.\n\nFor more information on a gym\'s current owner, type `{0}gym # info`, where *#* is the gym number. To fight a gym and try to earn its badges, type `{0}gym # fight`. To challenge the current holder of a gym, type `{0}gym # claim`. Only pokemon with the correct main type can hold a gym. This means the *FLYING* gym, for instance, can only be held by a primarly *FLYING* pokemon.\n\nThese are the currently available gyms:\n\n'.format(commandPrefix)
	
	counter = 1
	for row in rows:
		msg += '**{}**. {} Gym.\n'.format(counter, row['identifier'].upper())
		counter += 1

	em = discord.Embed(title='Gyms.', description=msg, colour=0xDEADBF)
	em.set_author(name='Professor Oak', icon_url=oakUrl)
	await client.send_message(message.channel, embed=em)

def check_hold_availability(callout, player):
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
		msg = '{0}, your {1} is your only available pokemons. You cannot leave your only pokemon to hold the gym.'.format(callout, player.getSelectedPokemon().name)
		em = discord.Embed(title='No pokemon!', description=msg, colour=0xDEADBF)
		em.set_author(name='Professor Oak', icon_url=oakUrl)
		em.set_footer(text='Once a pokemon becomes the holder of a gym, it stays there until another claims it\'s place. Type {}gym for more information.'.format(commandPrefix))
	return em

gymCooldown = 300	
async def display_gym(message):
	try:
		commandPrefix, spawnChannel = serverMap[message.server.id]
	except KeyError as err:
		return

	player = playerMap[message.author.id + message.server.id]

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
						player.lastGym = datetime.datetime.now()
						row = getGymInfo(message.server.id, gymId)

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

						battle = Battle(challenger1=playerPokemon, challenger2=gymPokemon, gym=True)
						
						winner, battleLog, levelUpMessage = battle.execute()

						msg = '{0.author.mention}, your {1} fought a beautiful battle against gym leader {2}\'s {3}! Here are the details: \n\n'.format(message, playerPokemon.name, row['player_name'], gymPokemon.name)
						em = discord.Embed(title='Gym Battle: {} Lv. {} vs {} Lv. {}!'.format(playerPokemon.name, playerPokemon.pokeStats.level, gymPokemon.name, gymPokemon.pokeStats.level), description=msg+battleLog, colour=0xDEADBF)
						em.set_author(name='Professor Oak', icon_url=oakUrl)
						em.set_thumbnail(url=imageURL.format(gymPokemon.pId))
						em.set_footer(text='You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
						await client.send_message(message.channel, embed=em)

						if winner == playerPokemon:
							if player.addBadge([gymId, row['type_identifier'].upper()]):
								em = discord.Embed(title='You got a new badge!', description='{0.author.mention}, you won against {1}\'s {2} and earned the {3} gym badge!'.format(message, row['player_name'], gymPokemon.name, row['type_identifier'].upper()), colour=0xDEADBF)
								em.set_author(name='Professor Oak', icon_url=oakUrl)
								em.set_thumbnail(url=message.author.avatar_url)
								em.set_footer(text='Think you have what it takes to hold a gym? You can fight for the claim of a gym by typing {}gym # claim.'.format(commandPrefix))
								await client.send_message(message.channel, embed=em)

				elif option == 'claim': 
					lastDuel = datetime.datetime.now().timestamp() - player.lastGym.timestamp()
					if lastDuel < duelCooldown:
						msg = '{0}, you have just battled a gym! You will be able to challenge a gym again in {1}.'.format(message.author.mention, convertDeltaToHuman(gymCooldown - lastDuel))
						em = discord.Embed(title='On cooldwn!', description=msg, colour=0xDEADBF)
						em.set_author(name='Professor Oak', icon_url=oakUrl)
						await client.send_message(message.channel, embed=em)
					else:
						player.lastGym = datetime.datetime.now()
						row = getGymInfo(message.server.id, gymId)

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

						em = check_hold_availability(message.author.mention, player)
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

						battle = Battle(challenger1=playerPokemon, challenger2=gymPokemon, gym=True)
						
						winner, battleLog, levelUpMessage = battle.execute()

						msg = '{0.author.mention}, your {1} fought a beautiful battle against gym leader {2}\'s {3}! Here are the details: \n\n'.format(message, playerPokemon.name, row['player_name'], gymPokemon.name)
						em = discord.Embed(title='Gym Battle: {} Lv. {} vs {} Lv. {}!'.format(playerPokemon.name, playerPokemon.pokeStats.level, gymPokemon.name, gymPokemon.pokeStats.level), description=msg+battleLog, colour=0xDEADBF)
						em.set_author(name='Professor Oak', icon_url=oakUrl)
						em.set_thumbnail(url=imageURL.format(gymPokemon.pId))
						em.set_footer(text='You need pokeballs to catch pokemon! Check your supply by typing {}me.'.format(commandPrefix))
						await client.send_message(message.channel, embed=em)

						if winner == playerPokemon:
							em = discord.Embed(title='{} is now the leader of the {} gym!'.format(message.author.name, row['type_identifier'].upper()), description='{0.author.mention}, you won against {1}\'s {2} and are now the leader of the {3} gym!'.format(message, row['player_name'], gymPokemon.name, row['type_identifier'].upper()), colour=0xDEADBF)
							em.set_author(name='Professor Oak', icon_url=oakUrl)
							em.set_thumbnail(url=imageURL.format(winner.pId))
							em.set_footer(text='Taking too long to level up? Buy an EXP boost at the shop! Type {}shop for more information.'.format(commandPrefix))

							cursor = MySQL.getCursor()
							cursor.execute("""
								UPDATE gym
								SET holder_id = %s,
									pokemon_id = %s
								WHERE server_id = %s
								AND type_id = %s
								""", (player.pId, playerPokemon.ownId, message.server.id, gymId))
							
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

commandList = {
	'welcome' : send_greeting,
	'start' : select_starter,
	'info' : display_pokemon_info,
	'pokemon' : display_pokemons,
	'select' : select_pokemon,
	'help' : display_help,
	'fight' : display_fight,
	'catch' : display_catch,
	'center' : display_center,
	'me' : display_me,
	'shop' : display_shop,
	'item' : display_item,
	'duel' : challenge_player,
	'accept' : accept_challenge,
	'gym' : display_gym
}

admin = 229680411079475201
adminCommandList = {
	#'stop' : stop_server,
	'add' : add_random_pokemon
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
				FROM type JOIN pokemon_type JOIN pokemon
				WHERE pokemon_type.type_id = type.id
				AND pokemon_type.pokemon_id = pokemon.id
				AND type.id = %s
				AND slot = 1
				AND pokemon_type.pokemon_id < 722
				ORDER BY RAND()
				LIMIT 1
				""", (row['id'],))
			rowPokemon = cursor.fetchone()

			pokemon = Pokemon(name='', pokemonId=rowPokemon['pokemon_id'], level=50)
			
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

	client.loop.create_task(spawn_wild_pokemon())
	print('------')
	
	print('Load item list')
	cursor = MySQL.getCursor()
	cursor.execute("""SELECT * FROM item""")

	rows = cursor.fetchall() 
	for row in rows:
		item = PokeItem(id=row['id'], itemType=row['type'], name=row['name'], price=row['price'], description=row['description'], value=row['value'])
		items.append(item)
		if row['price']>0:
			shopItems.append(item)
	print('------')

client.run(TOKEN)