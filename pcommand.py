class Command:
	def __init__(self, message, client):
		self.message = message
		self.client = client
		self.handleMessage()
	
	def handleMessage(self):
		pass

	def displaySuccess(self):
		pass

	def displayFail(self):
		pass