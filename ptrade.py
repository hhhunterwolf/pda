from player import Player
from pokemon import Pokemon

# TODO
#	Finish trades, fix trading confirmation	

class TradeManager:
	tradeMap = {}

	@staticmethod
	def getKey(player1, player2):
		key = ''
		return player1.pId + player2.pId if player1.pId > player2.pId else player2.pId + player1.pId

	@staticmethod
	def getTrade(offeror, receiver=None, createTrade=False):
		trade = None

		if receiver:
			key = TradeManager.getKey(offeror, receiver)
			if key not in TradeManager.tradeMap and createTrade:
				TradeManager.tradeMap[key] = Trade(offeror, receiver)
				trade = TradeManager.tradeMap[key]
		else:
			for key, value in TradeManager.tradeMap.items():
				if offeror.pId in key:
					trade = value
					break
			
		return trade

	@staticmethod
	def isTrading(player):
		return TradeManager.getTrade(player) is not None

	@staticmethod
	def endTrade(player):
		for key, value in TradeManager.tradeMap.items():
			if player.pId in key:
				del TradeManager.tradeMap[key]
				return

class Trade:
	def __init__(self, offeror, receiver):
		self.offerMap = {}
		self.confirmationMap = {}
		self.offeror = offeror
		self.receiver = receiver

	def makeOffer(self, player, pokemonId):
		self.offerMap[player.pId] = pokemonId
		for key, value in self.confirmationMap.items():
			self.confirmationMap[key] = False

	def confirmOffer(self, player):
		self.confirmationMap[player.pId] = True

	def isTradeConfirmed(self):
		return self.hasPlayerConfirmed(self.offeror) and self.hasPlayerConfirmed(self.receiver)

	def isReceiver(self, player):
		return player==self.receiver

	def makeTrade(self):
		if self.isTradeConfirmed():
			offerorPokemon = self.getOffer(self.offeror)
			receiverPokemon = self.getOffer(self.receiver)

			# Problems with cursor last row
			if offerorPokemon:
				self.offeror.releasePokemon(offerorPokemon.ownId)
				
			if receiverPokemon:
				self.receiver.releasePokemon(receiverPokemon.ownId)

			if offerorPokemon:
				self.receiver.addPokemonViaInstance(offerorPokemon)
				
			if receiverPokemon:
				self.offeror.addPokemonViaInstance(receiverPokemon)
				
	def hasPlayerConfirmed(self, player):
		return player.pId in self.confirmationMap and self.confirmationMap[player.pId]

	def getOffer(self, player):
		pokemon = None
		if player.pId in self.offerMap:
			pId = self.offerMap[player.pId]
			pokemon, inGym = player.getPokemon(pId)
		
		return pokemon

	def getOfferString(self, player):
		if player.pId in self.offerMap:
			pId = self.offerMap[player.pId]
			pokemon, inGym = player.getPokemon(pId)
			return '**{}**: is offering a *Lv. {} {} (IV {}/31)*.'.format(player.name, pokemon.pokeStats.level, pokemon.name, pokemon.getAverageIV())
		else:
			return '**{}**: *No offer.*'.format(player.name)

	def getStatusString(self, status):
		return '*Ready.*' if status else '*Not ready.*'

	def getTradeInfo(self):
		return """Here's the information about the ongoing trade:

		{}
		**Trade Status:** {}

		{}
		**Trade Status:** {}		
		
		The trade will be completed once both players are ready.
		""".format(self.getOfferString(self.offeror), self.getStatusString(self.hasPlayerConfirmed(self.offeror)), self.getOfferString(self.receiver), self.getStatusString(self.hasPlayerConfirmed(self.receiver)))