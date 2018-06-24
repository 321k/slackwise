from flask import Flask, render_template, url_for, request, redirect, session

import os
import requests
import json
from slackclient import SlackClient
from transferwiseclient.transferwiseclient import getTransferWiseProfileId, createTransferWiseRecipient, createTransferWiseQuote, createPayment, getBorderlessAccountId, getBorderlessAccounts

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


@app.route('/')
def index():
	return render_template('index.html')

@app.route('/slack')
def slack():
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
	global transferwise_token
	t  = request.form.get('text')
	if t is None or len(t)<5:
		return 'Get a token  here: http://moneytoemail.herokuapp.com/code'
	else:
		transferwise_token = t
	return 'Thank you, you can now interact with the slackwise bot'

@app.route('/borderless', methods=['POST'])
def borderless():
	global slack_token
	global transferwise_token
	session['transferwise_token'] = transferwise_token
	sc = SlackClient(slack_token)

	profileId = getTransferWiseProfileId(isBusiness=False, access_token = session['transferwise_token'])
	borderlessId = getBorderlessAccountId(profileId = profileId, access_token = session['transferwise_token'])
	accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = session['transferwise_token'])

	text="Your balances are \n"
	for b in accounts['balances']:
		text+=str(b['amount']['value']) + " " + str(b['amount']['currency']) + "\n"

	return text


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)