from flask import Flask, render_template, url_for, request, redirect
import os
import requests
import json
from slackclient import SlackClient
from transferwiseclient.transferwiseclient import getTransferWiseProfileId, createTransferWiseRecipient, createTransferWiseQuote, createPayment

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
	sc = SlackClient(slack_token)
	profile_id = getTransferWiseProfileId(isBusiness=False, access_token=transferwise_token)

	x = sc.api_call(
	  "chat.postMessage",
	  channel="general",
	  text="Hello " + str(profile_id)
	)
	print(x)
	return str(profile_id)

# Endpoint for adding verious tokens for local testing
@app.route('/add-token')
def addToken():
	t  = request.args.get('transferwiseToken')
	if t is not None:
		global transferwise_token
		transferwise_token = t

	s  = request.args.get('slackToken')
	if s is not None:
		global slack_token
		slack_token = s

	return redirect(url_for('index'))

@app.route('/transferwise-token', methods=['POST'])
def addToken():
	t  = request.form.get('text')
	if t is not None:
		global transferwise_token
		transferwise_token = t

	return 'asdf '


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)