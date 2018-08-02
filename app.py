from flask import Flask, render_template, url_for, request, redirect, session

import os
import requests
import json
from slackclient import SlackClient
from transferwiseclient.transferwiseclient import getTransferWiseProfiles, createTransferWiseRecipient, createTransferWiseQuote, createPayment, getBorderlessAccountId, getBorderlessAccounts, getTransfers
from model import db, User
import time

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
	slack_id = request.form.get('user_id')

	if token == 'delete':
		print('Deleting user ' + slack_id)
		user = User.query.filter_by(slack_id = slack_id).first()
		if user is None:
			return 'Token deleted'
		else:
			db.session.delete(user)
			db.session.commit()
			return 'Token deleted'

	user = User.query.filter_by(slack_id=slack_id).first()

	# Check that the user has a valid token
	if token is None or len(token)<5:	
		if user is None:
			user = User(slack_id = slack_id)
			db.session.add(user)
			return 'Please provide a TransferWise API key /transferwise api_key'

		if user.transferwise_token is not None:
			token = user.transferwise_token
			profiles = getTransferWiseProfiles(access_token = token)
			print(profiles.status_code)
			print('Profiles: ' + str(json.loads(profiles.text)))

			if profiles.status_code == 401:
				return 'Your token is old, please provide a new one.'

	# Check that the user has connected their Slack account
	if user is None:
		user = User(slack_id = slack_id)
		db.session.add(user)

	print("Token: " + str(token))
	profiles = getTransferWiseProfiles(access_token = token)
	print(profiles.status_code)

	if profiles.status_code == 401:
		return str(json.loads(profiles.text))

	profileId = json.loads(profiles.text)[0]['id']
	print("Profile ID: " + str(json.loads(profiles.text)))

	borderlessId = getBorderlessAccountId(profileId = profileId, access_token = token)

	if borderlessId.status_code == 401:
		return str(borderlessId.error_message)

	borderlessId = json.loads(borderlessId.text)[0]['id']
	print("Borderless ID: " + str(borderlessId))

	accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = token)
	
	if accounts.status_code == 200:
		accounts = json.loads(accounts.text)

		# The first record has the highest balance, so we'll default to that
		sourceCurrency = accounts['balances'][0]['amount']['currency']

	if sourceCurrency not in ['USD','AUD','BGN','BRL','CAD','CHF','CZK','DKK','EUR','GBP','HKD','HRK','HUF','JPY','NOK','NZD','PLN','RON','SEK','SGD','TRY']:
		print("Source currency not valid, assuming GBP")
		sourceCurrency = 'GBP'

	print("Source currency: " + str(sourceCurrency))


	user.transferwise_token = token
	user.transferwise_profile_id = profileId
	user.home_currency = sourceCurrency
	db.session.commit()

	return 'You can now use the TransfeWise bot.'

@app.route('/balances', methods=['POST'])
def borderless():
	slack_id = request.form.get('user_id')
	
	user = User.query.filter_by(slack_id=slack_id).first()

	if user is None:
		user = User(slack_id = slack_id)
		db.session.add(user)

	if user.transferwise_token is None:
		return 'Please add your TransferWise token first using /transferwise token'

	print("TransferWise token: " + str(user.transferwise_token))
	#sc = SlackClient(user.slack_token)

	profiles = getTransferWiseProfiles(access_token = user.transferwise_token)
	print("Profile ID: " + str(json.loads(profiles.text)))

	if profiles.status_code == 401:
		return "Please update your TransferWise token first using /transferwise"

	if profiles.status_code != 200:
		return str(profiles.error_message)
	
	profileId = json.loads(profiles.text)[0]['id']
	borderless = getBorderlessAccountId(profileId = profileId, access_token = user.transferwise_token)
	
	if borderless.status_code != 200:
		return str(profiles.status_code)

	print("Borderless ID: " + str(json.loads(borderless.text)))

	borderlessId = json.loads(borderless.text)[0]['id']
	accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = user.transferwise_token)

	if accounts.status_code != 200:
		return str(profiles.status_code)

	accounts = json.loads(accounts.text)
	text="Your balances are \n"
	for b in accounts['balances']:
		text+=str(b['amount']['value']) + " " + str(b['amount']['currency']) + "\n"

	return text

@app.route('/pay', methods=['POST'])
def pay():
	start_time = time.time()

	text  = request.form.get('text')
	slack_id = request.form.get('user_id')

	user = User.query.filter_by(slack_id=slack_id).first()

	if user is None or user.transferwise_token is None:
		return 'Please connect your TransferWise account using /transerwise token'

	profileId = user.transferwise_profile_id

	if profileId is None:
		return "Please update your TransferWise token first using /transferwise token"

	text = text.split(' ')

	if len(text) < 3:
		return 'Please use the format /pay email amount currency'

	if len(text[0].split('@')) < 2:
		return 'Please include a valid email'
	
	recipient_email = text[0]

	amount = text[1]
	print('Amount: ' + str(amount))

	currency = text[2].upper()
	print('Currency: ' + str(currency))

	name = recipient_email.split('@')[0].split('.')

	if len(name) < 2:
		first_name = name[0]
		last_name = 'Unknown'

	else:
		first_name = name[0]
		last_name = name[len(name)-1]

	if len(last_name)<3:
		last_name = 'Unknown'

	name = first_name + ' ' + last_name
	print('Name: ' + name)

	recipient = createTransferWiseRecipient(email = recipient_email, currency = currency, name = name, legalType='PRIVATE', profileId = profileId, access_token = user.transferwise_token)
	print(recipient)

	if recipient.status_code == 401:
		return 'Your token is old, get a new one at http://moneytoemail.herokuapp.com/code and use "/transferwise token" to update'

	end_time = time.time()
	print("Recipient Time: " + str(end_time - start_time))

	if user.home_currency is None:
		sourceCurrency = 'GBP'
	else:
		sourceCurrency = user.home_currency

	quote = createTransferWiseQuote(profileId = profileId, sourceCurrency = sourceCurrency, targetCurrency = currency, access_token = user.transferwise_token, targetAmount = amount)
	print(quote.status_code)

	if quote.status_code == 422:
		print("Unsupported currency, defaulting to GBP")
		sourceCurrency = 'GBP'
		quote = createTransferWiseQuote(profileId = profileId, sourceCurrency = sourceCurrency, targetCurrency = currency, access_token = user.transferwise_token, targetAmount = amount)

	if quote.status_code == 401:
		return str(quote.error_message)

	quoteId = json.loads(quote.text)['id']
	print("Quote ID: " + str(quoteId))
	end_time = time.time()
	print("Quote Time: " + str(end_time - start_time))


	recipientId = json.loads(recipient.text)['id']
	transfer = createPayment(recipientId = recipientId, quoteId = quoteId, reference = 'Slackwise', access_token = user.transferwise_token)
	if transfer.status_code == 401:
		return str(transfer.error_message)

	end_time = time.time()
	print("Transfer Time: " + str(end_time - start_time))

	transferId = json.loads(transfer.text)['id']
	print("Transfer ID: " + str(transferId))

	end_time = time.time()
	print("Total Time: " + str(end_time - start_time))

	if transferId == 'Failed to create transfer':
		return "Failed to pay"

	else:
		return 'Click here to pay: https://transferwise.com/transferFlow#/transfer/' + str(transferId)
	

@app.route('/homecurrency', methods=['POST'])
def home_currency():
	home_currency  = request.form.get('text')
	print(home_currency)

	home_currency = home_currency.upper()

	if home_currency not in ['USD','AUD','BGN','BRL','CAD','CHF','CZK','DKK','EUR','GBP','HKD','HRK','HUF','JPY','NOK','NZD','PLN','RON','SEK','SGD','TRY']:
		return "Currency not supported"

	if is_prod == 'True':	
		slack_id = request.form.get('user_id')
	else:
		slack_id = 'UBH7TETRB'

	user = User.query.filter_by(slack_id=slack_id).first()

	if user is None:
		return 'Please connect your Slack account first at slackwise.herokuapp.com'

	user.home_currency = home_currency
	db.session.commit()

	return "Home currency updated"
	

@app.route('/latest', methods=['POST'])
def lastest():
	text = request.form.get('text')
	if text is None:
		limit = 5
	elif text.isdigit():
		limit = min(int(text), 10)
	else:
		limit = 5

	slack_id = request.form.get('user_id')
	user = User.query.filter_by(slack_id=slack_id).first()
	#endDate = time.gmtime()
	#startDate = time.gmtime()
	transfers = getTransfers(limit = limit, offset = 0, accessToken = user.transferwise_token)
	transfers = json.loads(transfers.text)
	text="Your latest transfers: \n"
	for b in transfers:
		if b['reference'] == "":
			reference = '(No reference)'
		else:
			reference = b['reference']
		text+=str(reference) + " " + str(b['targetValue']) + " " + str(b['targetCurrency']) + ", " + str(b['status']) + "\n"


	return str(text)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)