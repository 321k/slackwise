from flask import Flask, render_template, url_for, request, redirect, session

import os
import requests
import json
from slackclient import SlackClient
from transferwiseclient.transferwiseclient import getTransferWiseProfileId, createTransferWiseRecipient, createTransferWiseQuote, createPayment, getBorderlessAccountId, getBorderlessAccounts
from model import db, User

#Declare global variables
global slack_token
global transferwise_token

#Environment variables
is_prod = os.environ.get('IS_HEROKU', None)
slack_token = os.environ.get('SLACK_TOKEN', None)
port = int(os.environ.get('PORT', 5000))

if is_prod == 'True':
  static_url = 'http://slackwise.herokuapp.com'
else:
  static_url = 'localhost:5000'

def create_app():  
  app = Flask(__name__)
  app.secret_key = os.urandom(24)
  app.config['DEBUG'] = True
  app.static_folder = 'static'
  return app

app = create_app()

#Congiguring database
if is_prod == 'True':
  POSTGRES = {
      'user': 'pkarwhotjkxyjt',
      'pw': os.environ.get('PG_PASSWORD', None),
      'db': 'd2ta6fjdj5k607',
      'host': 'ec2-54-235-196-250.compute-1.amazonaws.com',
      'port': '5432',
  }
  static_url = 'http://slackwise.herokuapp.com'
else:
  POSTGRES = {
      'user': 'erik.johansson',
      'pw': '',
      'db': 'slackwise',
      'host': 'localhost',
      'port': '5433',
  }
  static_url = 'localhost:5000'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
db.init_app(app)

port = int(os.environ.get('PORT', 5000))

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/slack')
def slack():
	if is_prod == 'True':
		code = request.args.get('code')
		payload = {'client_id': '387079239778.387986429910', 
		'client_secret': '12df7e70460efc4c8c6e8a1cea961612',
		'code': code}
		response = requests.get('https://slack.com/api/oauth.access',
			params = payload,
			headers={
	                 'Content-Type': 'application/x-www-form-urlencoded'})
		oauth = json.loads(response.text)

	else:
		oauth = {'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX','scope': 'groups:write', 'team_name': 'TransferWise', 'team_id': 'TXXXXXXXXX' }

	if 'error' in oauth:
		return 'Failed to authenticate'

	else:
		token = oauth['access_token']
		print(token)
		session['slack_token'] = token
		user = User.query.filter_by(slack_token=token).first()

		if user is None:
			user = User(slack_token = token)
			db.session.add(user)
			db.session.commit()
			user = User.query.filter_by(slack_token=token).first()

		return redirect(url_for('index'))

@app.route('/send-message')
def sendMessage():
	sc = SlackClient(slack_token)
	profile_id = getTransferWiseProfileId(isBusiness=False, access_token=session['transferwise_token'])

	x = sc.api_call(
	  "chat.postMessage",
	  channel="general",
	  text="Hello " + str(profile_id)
	)
	return str(profile_id)

# Endpoint for adding verious tokens for local testing
@app.route('/add-token')
def addToken():
	global transferwise_token
	t  = request.args.get('transferwiseToken')
	if t is not None:
		transferwise_token = t

	s  = request.args.get('slackToken')
	if s is not None:
		global slack_token
		slack_token = s

	return t + s

@app.route('/transferwise-token', methods=['POST'])
def transferwiseToken():

	token  = request.form.get('text')

	user = User.query.filter_by(slack_token=token).first()

	if user is None:
		user = User(transferwise_token = token)
		db.session.add(user)
		db.session.commit()
	else:	
		user.transferwise_token = token
		db.session.commit()

	if token is None or len(token)<5:
		return 'Get a token  here: http://moneytoemail.herokuapp.com/code'
	else:
		transferwise_token = token

	session['transferwise_token'] = token
	return 'Thank you, you can now interact with the slackwise bot'

@app.route('/borderless', methods=['POST'])
def borderless():

	user_id = request.form.get('user_id')
	print(user_id)
	user = User.query.first()

	sc = SlackClient(user.slack_token)

	profileId = getTransferWiseProfileId(isBusiness=False, access_token = session['transferwise_token'])
	borderlessId = getBorderlessAccountId(profileId = profileId, access_token = session['transferwise_token'])
	accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = session['transferwise_token'])

	text="Your balances are \n"
	for b in accounts['balances']:
		text+=str(b['amount']['value']) + " " + str(b['amount']['currency']) + "\n"

	return text


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)