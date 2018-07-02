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
		'scope':'users.profile:read+identity.basic',
		'code': code}
		response = requests.get('https://slack.com/api/oauth.access',
			params = payload,
			headers={
	                 'Content-Type': 'application/x-www-form-urlencoded'})
		oauth = json.loads(response.text)
		print(str(oauth['ok']))

	else:
		oauth = {'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX','scope': 'users.profile:read', 'team_name': 'TransferWise', 'team_id': 'TXXXXXXXXX' }

	if 'error' in oauth:
		print('Failed to authenticate to Slack')
		return 'Failed to authenticate to Slack'

	token = oauth['access_token']
	print("Slack token: " + token)

	payload = {'token': token}
	response = requests.get('https://slack.com/api/users.identity',
		params = payload,
		headers={
                 'Content-Type': 'application/x-www-form-urlencoded'})
	userIdentity = json.loads(response.text)
	print('Success: ' + str(userIdentity['ok']))
	
	if userIdentity['ok'] == True:
		user = User.query.filter_by(slack_token=token).first()
		if user is None:
			user = User(slack_token = token, slack_id = userIdentity['user']['id'])
			db.session.add(user)
			db.session.commit()

		elif user.slack_id is None:
			user.slack_id = userIdentity['user']['id']
			db.session.commit()

		if user.email is None:
			payload = {'token': token, 'user': user.slack_id}
			response = requests.get('https://slack.com/api/users.profile.get',
				params = payload,
				headers={
				'Content-Type': 'application/x-www-form-urlencoded'})
			userProfile = json.loads(response.text)
			if userProfile['ok']==True:
				user.email = userProfile['profile']['email']
				db.session.commit()

	return redirect(url_for('index'))

@app.route('/transferwise', methods=['POST'])
def transferwiseToken():
	token  = request.form.get('text')

	if is_prod == 'True':	
		slack_id = request.form.get('user_id')
	else:
		slack_id = 'UBCUSHSNP'
	
	user = User.query.filter_by(slack_id=slack_id).first()
	
	if token is None or len(token)<5:	
		if user is None:
			return 'Connect your account here: http://slackwise.herokuapp.com'

		elif user.transferwise_token is not None:
			profileId = getTransferWiseProfileId(isBusiness = False, access_token = user.transferwise_token)
			print('Profile ID: ' + profileId)
			if profileId == 'Failed to get profile':
				return 'Your token is old, get a new one at http://moneytoemail.herokuapp.com/code and use "/transferwise token" to update'
		
		else:
			return 'Get a token here: http://moneytoemail.herokuapp.com/code'

	if user is None:
		return "Please connect your account first"
	else:	
		user.transferwise_token = token
		db.session.commit()

	return 'Thank you, you can now interact with the slackwise bot'

@app.route('/balances', methods=['POST'])
def borderless():

	if is_prod == 'True':
		slack_id = request.form.get('user_id')
		print("Live slack ID: " + str (slack_id))
	else:
		slack_id = 'UBCUSHSNP'
		print("Test slack ID: " + str(slack_id))

	user = User.query.filter_by(slack_id=slack_id).first()

	if user is None:
		return 'Please connect your Slack account first from slackwise.herokuapp.com'
	elif user.slack_token is None:
		return 'Please connect your Slack account first from slackwise.herokuapp.com'
	elif user.transferwise_token is None:
		return 'Please connect your TransferWise account first using /transferwise'

	print("Slack token: " + str(user.slack_token))
	print("TransferWise token: " + str(user.transferwise_token))
	#sc = SlackClient(user.slack_token)

	profileId = getTransferWiseProfileId(isBusiness=False, access_token = user.transferwise_token)
	print("Profile ID: " + str(profileId))

	if profileId == 'invalid_token':
		return "Please update your TransferWise token first using /transferwise"
	
	borderlessId = getBorderlessAccountId(profileId = profileId, access_token = user.transferwise_token)
	print("Borderless ID: " + str(borderlessId))

	accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = user.transferwise_token)

	text="Your balances are \n"
	for b in accounts['balances']:
		text+=str(b['amount']['value']) + " " + str(b['amount']['currency']) + "\n"

	return text

@app.route('/pay', methods=['POST'])
def pay():
	payment  = request.form.get('text')
	print(str(payment))

	if is_prod == 'True':
		slack_id = request.form.get('user_id')
		print("Live slack ID: " + str(slack_id))
	else:
		slack_id = 'UBCUSHSNP'
		print("Test slack ID: " + str(slack_id))

	user = User.query.filter_by(slack_id=slack_id).first()

	if user is None:
		return 'Please connect your Slack account first from slackwise.herokuapp.com'
	elif user.slack_token is None:
		return 'Please connect your Slack account first from slackwise.herokuapp.com'
	elif user.transferwise_token is None:
		return 'Please connect your TransferWise account first using /transferwise'

	print("Slack token: " + str(user.slack_token))
	print("TransferWise token: " + str(user.transferwise_token))
	
	profileId = getTransferWiseProfileId(isBusiness=False, access_token = user.transferwise_token)
	print("Profile ID: " + str(profileId))

	if profileId == 'invalid_token':
		return "Please update your TransferWise token first using /transferwise"

	payment = payment.split(' ')

	if len(payment) < 3:
		return 'Please use the format /pay @user amount currency'

	if len(payment[0].split('@')) < 2:
		return 'Please specify a Slack user'
	else:
		recipient_slack_id = payment[0].split('@')[1].split("|")[0]
		print('Recipient slack ID: ' + str(recipient_slack_id))

	amount = payment[1]
	print('Amount: ' + str(amount))

	currency = payment[2].upper()
	print('Currency: ' + str(currency))

	recipient = User.query.filter_by(slack_id=recipient_slack_id).first()

	first_name = recipient.email.split('@')[0].split('.')[0]
	last_name = recipient.email.split('@')[0].split('.')[1]
	if len(last_name)<3:
		last_name = first_name

	name = first_name + ' ' + last_name
	print('Name: ' + name)

	recipientId = createTransferWiseRecipient(email = recipient.email, currency = currency, name = name, legalType='PRIVATE', profileId = profileId, access_token = user.transferwise_token)

	if recipientId == 'Failed to create recipient':
		return 'Your token is old, get a new one at http://moneytoemail.herokuapp.com/code and use "/transferwise token" to update'

	print("Recipient ID: " + str(recipientId))

	borderlessId = getBorderlessAccountId(profileId = profileId, access_token = user.transferwise_token)
	print("Borderless ID: " + str(borderlessId))

	accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = user.transferwise_token)
	sourceCurrency = accounts['balances'][0]['amount']['currency']
	print("Source currency: " + str(sourceCurrency))

	quoteId = createTransferWiseQuote(profileId = profileId, sourceCurrency = sourceCurrency, targetCurrency = currency, access_token = user.transferwise_token, targetAmount = amount)
	print("Quote ID: " + str(quoteId))

	transferId = createPayment(recipientId = recipientId, quoteId = quoteId, reference = 'Slackwise', access_token = user.transferwise_token)
	print("Transfer ID: " + str(transferId))

	if transferId == 'Failed to create transfer':
		return "Failed to pay"

	else:
		return 'Click here to pay: https://transferwise.com/transferFlow#/transfer/' + str(transferId)

	return 'Successful'
	

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)