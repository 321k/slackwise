from flask import Flask, render_template, url_for, request, redirect, session

import os
import requests
import json
import base64
from slackclient import SlackClient
from transferwiseclient.transferwiseclient import getTransferWiseProfiles, createTransferWiseRecipient, createTransferWiseQuote, createPayment, getBorderlessAccountId, getBorderlessAccounts, getTransfers, getBorderlessActivity
from model import db, User
import time
from datetime import datetime, timedelta
from slackwise_functions import verify_slack_request, currency_to_flag

#Declare global variables
global slack_token
global transferwise_token
global api_key

#Environment variables
is_prod = os.environ.get('IS_HEROKU', None)
slack_token = os.environ.get('SLACK_TOKEN', None)
port = int(os.environ.get('PORT', 5000))
api_key = os.environ.get('TRANSFERWISE_KEY', None)


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

@app.route('/privacy')
def privacy():
    return render_template('privacy-policy.html')

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

@app.route('/oauth')
def oauth():
    global api_key
    print('Keys: ' + str(session.keys()))
    print('Values: ' + str(session.values()))
    print('Session: ' + str(session))
    print('Request cookie: ' + str(request.cookies['session']))
    print(request.cookies['session'])
    
    print(str(base64.b64decode(request.cookies['session'].split(".")[0])))


    if 'slack_id' in session:
        slack_id = session['slack_id']

    else:
        return 'No valid user. Please use the bot from within Slack.'
    
    code = request.args.get('code')
    token = requests.post('https://api.transferwise.com/oauth/token',
                          data = {'grant_type': 'authorization_code',
                                   'client_id':'erik-edins-slack-bot',
                                   'code': code,
                                   'redirect_uri':'https://slackwise.herokuapp.com/oauth'},
                          headers={'Authorization':'Basic ' + str(api_key)})

    if token.status_code == 401:
        print('Token exchange failed')
        return json.loads(token.text)['error']

    else:
    	token = json.loads(token.text)['access_token']

    if slack_id is None:
        return 'You need to use this bot via Slack for it to work.'

    profiles = getTransferWiseProfiles(access_token = token)

    if profiles.status_code == 401:
        return str(json.loads(profiles.text))

    profileId = json.loads(profiles.text)[0]['id']

    borderlessId = getBorderlessAccountId(profileId = profileId, access_token = token)

    if borderlessId.status_code == 401:
        return str(borderlessId.error_message)

    if len(json.loads(borderlessId.text)) < 1:
        return 'You need to have a borderless account to use the Slack bot'

    borderlessId = json.loads(borderlessId.text)[0]['id']

    accounts = getBorderlessAccounts(borderlessId = borderlessId, access_token = token)
    
    if accounts.status_code == 200:
        accounts = json.loads(accounts.text)

        # The first record has the highest balance, so we'll default to that
        sourceCurrency = accounts['balances'][0]['amount']['currency']

    if sourceCurrency not in ['USD','AUD','BGN','BRL','CAD','CHF','CZK','DKK','EUR','GBP','HKD','HRK','HUF','JPY','NOK','NZD','PLN','RON','SEK','SGD','TRY']:
        print("Source currency not valid, assuming GBP")
        sourceCurrency = 'GBP'

    user = User.query.filter_by(slack_id=slack_id).first()
    user.transferwise_token = token
    user.transferwise_profile_id = profileId
    user.home_currency = sourceCurrency
    db.session.commit()

    return render_template('index.html')

@app.route('/transferwise', methods=['POST'])
def transferwiseToken():
    if not verify_slack_request(request):
        return 'Request verification failed'

    text  = request.form.get('text')
    slack_id = request.form.get('user_id')
    session['slack_id'] = slack_id

    if text == 'delete':
        print('Deleting user ' + str(slack_id))
        user = User.query.filter_by(slack_id = slack_id).first()
        if user is None:
            return 'TransferWise integration removed. Use /transferwise to reconnect.'
        else:
            db.session.delete(user)
            db.session.commit()
            return 'TransferWise integration removed. Use /transferwise to reconnect.'

    user = User.query.filter_by(slack_id=slack_id).first()

    if user is None:
        user = User(slack_id = slack_id)
        db.session.add(user)
        return 'Click here to connect your TransferWise account https://slackwise.herokuapp.com/connect'

    token = user.transferwise_token

    if user.transferwise_token is None:
        return 'Click here to connect your TransferWise account https://slackwise.herokuapp.com/connect'
    else:
        token = user.transferwise_token

    profiles = getTransferWiseProfiles(access_token = token)

    if profiles.status_code == 401:
        return 'Click here to connect your TransferWise account https://slackwise.herokuapp.com/connect'

    profileId = json.loads(profiles.text)[0]['id']

    borderlessId = getBorderlessAccountId(profileId = profileId, access_token = token)

    if borderlessId.status_code == 401:
        return str(borderlessId.error_message)

    if len(json.loads(borderlessId.text)) < 1:
        return 'You need to have a borderless account to use the Slack bot'

    borderlessId = json.loads(borderlessId.text)[0]['id']

    response = getBorderlessAccounts(borderlessId = borderlessId, access_token = token)
    
    if response.status_code == 200:
        accounts = json.loads(response.text)

        # The first record has the highest balance, so we'll default to that
        sourceCurrency = accounts['balances'][0]['amount']['currency']

    if response.status_code == 401:
        return str(response.error_message)

    if sourceCurrency not in ['USD','AUD','BGN','BRL','CAD','CHF','CZK','DKK','EUR','GBP','HKD','HRK','HUF','JPY','NOK','NZD','PLN','RON','SEK','SGD','TRY']:
        print("Source currency not valid, assuming GBP")
        sourceCurrency = 'GBP'

    user.transferwise_token = token
    user.transferwise_profile_id = profileId
    user.home_currency = sourceCurrency
    db.session.commit()

    return 'Your TransferWise account is connected'

@app.route('/connect', methods=['GET'])
def connect():
    return redirect('https://api.transferwise.com/oauth/authorize?response_type=code&client_id=erik-edins-slack-bot&redirect_uri=https://slackwise.herokuapp.com/oauth')

@app.route('/balances', methods=['POST'])
def borderless():
    if not verify_slack_request(request):
        return 'Request verification failed'


    slack_id = request.form.get('user_id')
    
    user = User.query.filter_by(slack_id=slack_id).first()

    if user is None:
        user = User(slack_id = slack_id)
        db.session.add(user)

    if user.transferwise_token is None:
        return 'Please add your TransferWise token first using /transferwise token'

    borderless = getBorderlessAccountId(profileId = user.transferwise_profile_id, access_token = user.transferwise_token)
    
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

        currency = str(b['amount']['currency'])
        currency = currency_to_flag(currency)

        text+=currency + " " + str(b['amount']['value']) + " " + str(b['amount']['currency']) + "\n"

    return text

@app.route('/pay', methods=['POST'])
def pay():
    start_time = time.time()
    if not verify_slack_request(request):
        return 'Request verification failed'


    text  = request.form.get('text')
    print(text)
    text = text.split(' ')

    slack_id = request.form.get('user_id')

    user = User.query.filter_by(slack_id=slack_id).first()

    if user is None or user.transferwise_token is None:
        return 'Please connect your TransferWise account using /transerwise token'

    profileId = user.transferwise_profile_id

    if profileId is None:
        return 'Please connect your TransferWise account using /transerwise token'
    
    if len(text) < 3:
        return 'Please use the format /pay email amount currency'

    if len(text[0].split('@')) < 2:
        return 'Please include a valid email'
    
    
    recipient_email = text[0]
    recipient_email = recipient_email.split('|')[1].replace(">", "")
    
    print('Recipient email: ' + str(recipient_email))

    amount = text[1]
    print('Amount: ' + str(amount))

    currency = text[2].upper()
    print('Currency: ' + str(currency))

    name = recipient_email.split('@')[0].split('.')

    first_name = name[0]
    first_name = ''.join([i for i in first_name if not i.isdigit()])
    
    if len(name) < 2:
        last_name = 'Unknown'

    else:
        last_name = name[len(name)-1]
        last_name = ''.join([i for i in last_name if not i.isdigit()])


    if len(last_name)<3:
        last_name = 'Unknown'

    name = first_name + ' ' + last_name
    print('Name: ' + name)

    recipient = createTransferWiseRecipient(email = recipient_email, currency = currency, name = name, legalType='PRIVATE', profileId = profileId, access_token = user.transferwise_token)
    print(recipient)

    if recipient.status_code == 401:
        return 'Connect your TransferWise account using /transferwise token'

    if recipient.status_code != 200:
        return str(recipient.text)

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
        return str(json.loads(transfer.text))

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

@app.route('/home-currency', methods=['POST'])
def home_currency():
    if not verify_slack_request(request):
        return 'Request verification failed'

    home_currency  = request.form.get('text')
    print(home_currency)

    if home_currency == "":
        user = User.query.filter_by(slack_id=slack_id).first()
        return user.home_currency

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
    if not verify_slack_request(request):
        return 'Request verification failed'

    text = request.form.get('text')
    if text is None:
        limit = 5
    elif text.isdigit():
        limit = min(int(text), 10)
    else:
        limit = 5

    slack_id = request.form.get('user_id')
    user = User.query.filter_by(slack_id=slack_id).first()

    startDate = datetime.today() - timedelta(days=1)
    endDate = datetime.today()

    borderlessId = getBorderlessAccountId(user.transferwise_profile_id, user.transferwise_token)

    if len(json.loads(borderlessId.text)) < 1:
        return 'You need to have a borderless account to use the Slack bot'

    if accounts.status_code != 200:
        return str(profiles.status_code)

    borderlessAccountId = json.loads(borderlessId.text)[0]['id']

    activity = getBorderlessActivity(borderlessAccountId, user.transferwise_token)
    activity = json.loads(activity.text)

    text="Your latest borderless activity: \n"
    for b in activity:

        activityType = str(b['type'])
        print(activityType)
        
        if b['type'] in ['WITHDRAWAL', 'DEPOSIT']:
            currency = str(b['amount']['currency'])

            currency = currency_to_flag(currency)

            activityType = str(b['type'])

            if activityType == 'DEPOSIT':
                activityType = ':moneybag:'
            elif activityType == 'WITHDRAWAL':
                activityType = ':wave:'

            text+= str(currency) + str(b['amount']['value']) + " " + str(b['amount']['currency']) +  " " + activityType + " " + str(b['type']) + " " + str(b['creationTime'])[0:10] + " " + str(b['creationTime'])[11:16] + "\n"

        elif  b['type'] == 'CONVERSION':
            activityType = ':currency_exchange:'
            text += activityType + str(b['sourceAmount']['value']) + " "  + str(b['sourceAmount']['currency']) + " to "  + str(b['targetAmount']['value']) + " "  + str(b['targetAmount']['currency']) + '\n'

        else:
            text+= b['type'] + '\n'
            
    return str(text)

@app.route('/switch-profile', methods=['POST'])
def profile():
    if not verify_slack_request(request):
        return 'Request verification failed'

    slack_id = request.form.get('user_id')
    user = User.query.filter_by(slack_id = slack_id).first()
    print('Previous TransferWise profile: ' + str(user.transferwise_profile_id))
    profiles = getTransferWiseProfiles(access_token = user.transferwise_token)

    if profiles.status_code != 200:
        print(str(profiles.status_code))
        return 'Error.'

    if(len(json.loads(profiles.text))==1):
        return 'You only have one profile.'

    personalProfileId = json.loads(profiles.text)[0]['id']

    if user.transferwise_profile_id == personalProfileId:
        user.transferwise_profile_id = json.loads(profiles.text)[1]['id']
        db.session.commit()
        return 'Active TransferWise profile: ' + json.loads(profiles.text)[1]['details']['name']

    else:
        user.transferwise_profile_id = json.loads(profiles.text)[0]['id']
        db.session.commit()
        return 'Active TransferWise profile: ' + json.loads(profiles.text)[0]['details']['firstName'] + ' ' + json.loads(profiles.text)[0]['details']['lastName']

@app.route('/transferwise-bot-feedback', methods=['POST'])
def feedback():
    if not verify_slack_request(request):
        return 'Request verification failed'

    text = request.form.get('text')
    print('Feedback: ' + str(text))
    return 'Thank you for your feedback'

@app.route('/addkey', methods=['GET'])
def addkey():
    if is_prod == 'True':
        return 'This endpoint is not available in production'

    global api_key
    api_key = request.args.get('key')
    return 'Key added'



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)

