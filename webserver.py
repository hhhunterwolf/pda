import json
import os
import datetime

from flask import Flask, request
from gevent.pywsgi import WSGIServer
from mysql import MySQL

WEBHOOK_AUTH = os.environ['WEBHOOK_AUTH']
ALLOW_TEST = False

M_TYPE_INFO = 'INFO'
M_TYPE_WARNING = 'WARNING'
M_TYPE_ERROR = 'ERROR'

STREAK_TIME = 24*60*60

app = Flask(__name__)

@app.route('/webhook',methods=['POST'])
def catch_vote_webhook():
	print(datetime.datetime.now(), M_TYPE_INFO, 'Received vote call.')
	print(datetime.datetime.now(), M_TYPE_INFO, '-------------------')
	
	# Authentication
	auth = request.headers.get('Authorization')
	print(datetime.datetime.now(), M_TYPE_INFO, 'Authenticating.', 'Token: ' + auth)
	if auth != WEBHOOK_AUTH:
		print(datetime.datetime.now(), M_TYPE_ERROR, 'Received request with invalid authorization.')
		print(request.headers)
		print(request.data)
		return 'FORBIDDEN'

	# Get user and type
	print(datetime.datetime.now(), M_TYPE_INFO, '-------------------')
	print(datetime.datetime.now(), M_TYPE_INFO, 'Authenticated. Processing request.')
	data = json.loads(request.data)
	user = data['user']
	type = data['type']
	print(datetime.datetime.now(), M_TYPE_INFO, 'User: ' + user, 'Type: ' + type)
	print(datetime.datetime.now(), M_TYPE_INFO, '-------------------')

	# Validate type
	if not ALLOW_TEST and type=='test':
		print(datetime.datetime.now(), M_TYPE_ERROR, 'Received test request. Ignoring.')
		print(request.headers)
		print(request.data)
		return 'FORBIDDEN'

	# Rewarding
	cursor = MySQL.getCursor()
	cursor.execute("""
		SELECT *
		FROM player
		WHERE id = %s
	""", (user,))
	row = cursor.fetchone()

	if not row:
		# User isn't player
		print(datetime.datetime.now(), M_TYPE_ERROR, 'Received vote from non-player. Ignoring.')
		return 'OK'

	cursor.execute("""
		SELECT *
		FROM botlist_upvotes
		WHERE player_id = %s
	""", (user,))
	row = cursor.fetchone()

	streak = 1
	if not row:
		# First time player upvotes
		print(datetime.datetime.now(), M_TYPE_INFO, 'Received first vote from player. Inserting into botlist_upvotes table.')
		cursor.execute("""
			INSERT INTO botlist_upvotes (player_id, last_vote)
			VALUES (%s, CURRENT_TIMESTAMP)
		""", (user,))
	else:
		# Returning voter, updating last vote and checking streak
		print(datetime.datetime.now(), M_TYPE_INFO, 'Returning voter, updating time and streak.')

		cursor.execute("""
			UPDATE botlist_upvotes
			SET last_vote = CURRENT_TIMESTAMP,
				last_reward = 0
			WHERE player_id = %s
		""", (user,))

		deltatime = datetime.datetime.now().timestamp() - row['last_vote'].timestamp()
		print(datetime.datetime.now(), M_TYPE_INFO, 'Deltatime: {}'.format(deltatime))
		if deltatime <= STREAK_TIME:
			streak = row['streak'] + 1

	cursor.execute("""
		UPDATE botlist_upvotes
		SET streak = %s
		WHERE player_id = %s
	""", (streak, user))
	
	MySQL.commit()
	return 'OK'

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
