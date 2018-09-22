from simplecrypt import encrypt, decrypt
from model import db, User
import time
import os
import requests
import json
import base64
from flask import Flask, \
    render_template, url_for, request, redirect, session, flash, make_response
from slackwise_functions import verify_slack_request, \
    currency_to_flag, print_balance_activity, get_latest_borderless_activity, \
    decide_user_home_currency
from transferwiseclient.transferwiseclient import getTransferWiseProfiles, \
    createTransferWiseRecipient, createTransferWiseQuote, createPayment, \
    getBorderlessAccountId, getBorderlessAccounts, getBorderlessActivity
from tasks import make_celery

# Declare global variables
global slack_token
global encryption_key
global is_prod

# Environment variables
is_prod = os.environ.get('IS_HEROKU', None)
slack_token = os.environ.get('SLACK_TOKEN', None)
port = int(os.environ.get('PORT', 5000))

encryption_key = os.environ.get('ENCRYPTION_KEY', 'dev_key')

if is_prod == 'True':
    static_url = 'http://slackwise.herokuapp.com'
else:
    static_url = 'localhost:5000'


def create_app():
    app = Flask(__name__)
    app.secret_key = encryption_key
    app.config['DEBUG'] = True
    app.config['CELERY_BROKER_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    app.config['CELERY_BACKEND'] = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    app.static_folder = 'static'
    return app


app = create_app()
celery = make_celery(app)


# Congiguring database
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


@celery.task()
def add_together(a, b):
    return a + b


@app.route('/process/<name>')
def process(name):
    reverse.delay(name)
    return reverse(name)


@celery.task(name='celery_for_slack.celery_latest')
def celery_latest(user):
    return get_latest_borderless_activity(user)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy-policy.html')


@app.route('/oauth', methods=['GET'])
def oauth():
    referrer_url = 'https://transferwise.com/' + \
        'oauth/authorize?response_type=code' + \
        '&client_id=erik-edins-slack-bot&' + \
        'redirect_uri=https://slackwise.herokuapp.com/oauth'

    if request.referrer != referrer_url:
        message = 'Authentication failed. \
        Make sure you use connect the bot from Slack.'
        flash(message, 'alert-warning')
        return render_template('index.html')

    api_key = os.environ.get('TRANSFERWISE_KEY', None)

    if 'slack_id' in session:
        slack_id = session['slack_id']

    elif 'session' in request.cookies:
        request_session = json.loads(
            base64.b64decode(request.cookies['session'].split(".")[0])
        )
        print(request_session)

        if 'slack_id' in request_session:
            slack_id = request_session['slack_id']

    else:
        message = 'Couldn\'t find a Slack user. \
        Make sure you connect via Slack using /transferwise.'
        flash(message, 'alert-warning')
        return redirect(url_for('index'))

    code = request.args.get('code')
    response = requests.post('https://api.transferwise.com/oauth/token',
                             data={'grant_type': 'authorization_code',
                                   'client_id': 'erik-edins-slack-bot',
                                   'code': code,
                                   'redirect_uri':
                                   'https://slackwise.herokuapp.com/oauth'},
                             headers={'Authorization': 'Basic ' +
                                      str(api_key)})

    if response.status_code == 401:
        print('Token exchange failed')
        return json.loads(response.text)['error']

    else:
        token = json.loads(response.text)['access_token']

    if slack_id is None:
        return 'You need to use this bot via Slack for it to work.'

    profiles = getTransferWiseProfiles(access_token=token)
    if profiles.status_code == 401:
        return str(json.loads(profiles.text))

    profileId = json.loads(profiles.text)[0]['id']
    homeCurrency = decide_user_home_currency(token, profileId)
    user = User.query.filter_by(slack_id=slack_id).first()
    user.addEncryptedToken(token)
    user.transferwise_profile_id = profileId
    user.home_currency = homeCurrency
    db.session.commit()

    flash(
        'Your TransferWise account is set up. \
        Go back to Slack to continue using the TransferWise Slack bot.',
        'alert-success'
    )

    return render_template('index.html')


@app.route('/addcookie')
def addcookie():
    slack_id = request.args.get('slack_id')
    session['slack_id'] = slack_id
    return 'Added cookie'


@app.route('/transferwise', methods=['POST'])
def transferwise():
    if not verify_slack_request(request):
        return 'Request verification failed'

    text = request.form.get('text')
    slack_id = request.form.get('user_id')
    user = User.query.filter_by(slack_id=slack_id).first()

    if user is not None:
        token = user.getToken()

    print(app.secret_key)

    session['slack_id'] = slack_id

    print('Slack ID ' + str(session['slack_id']) + ' added to session.')

    if text == 'delete':
        print('Deleting user ' + str(slack_id))
        if user is None:
            return 'TransferWise integration removed.\
 Use /transferwise to reconnect.'
        else:
            db.session.delete(user)
            db.session.commit()
            return 'TransferWise integration removed.\
 Use /transferwise to reconnect.'

    if user is None:
        user = User(slack_id=slack_id)
        db.session.add(user)
        db.session.commit()

    if user.encrypted_tw_token is not None:
        profiles = getTransferWiseProfiles(
            access_token=token
        )
        if profiles.status_code == 200:
            return 'TransferWise account connected'

    return 'Click here to connect your TransferWise account\
 https://slackwise.herokuapp.com/connect?slack_id=' + slack_id


@app.route('/connect', methods=['GET'])
def connect():
    slack_id = request.args.get('slack_id')
    session['slack_id'] = slack_id
    redirect_url = 'https://api.transferwise.com/' + \
        'oauth/authorize?response_type=code' + \
        '&client_id=erik-edins-slack-bot&' + \
        'redirect_uri=https://slackwise.herokuapp.com/oauth'
    return redirect(redirect_url)


@app.route('/balances', methods=['POST'])
def borderless():
    start_time = time.time()

    if not verify_slack_request(request):
        return 'Request verification failed'

    global encryption_key

    slack_id = request.form.get('user_id')
    user = User.query.filter_by(slack_id=slack_id).first()

    print("Start fetching token " + str(time.time() - start_time))
    token = user.getToken()
    print(str(token))
    print("Token available after " + str(time.time() - start_time))

    if user is None:
        user = User(slack_id=slack_id)
        db.session.add(user)

    if user.encrypted_tw_token is None:
        return 'Please connect your TransferWise account using /transferwise'

    end_time = time.time()
    print("User fetched: " + str(end_time - start_time))
    borderless = getBorderlessAccountId(
        profileId=user.transferwise_profile_id,
        access_token=token
    )

    if borderless.status_code != 200:
        return str(borderless.status_code)

    print("Borderless ID fetched in " + str(time.time() - start_time))

    if len(json.loads(borderless.text)) < 1:
        return 'You need to have a borderless account to use the Slack bot'

    borderlessId = json.loads(borderless.text)[0]['id']
    accounts = getBorderlessAccounts(
        borderlessId=borderlessId,
        access_token=token
    )

    print("Borderless accounts fetched in " + str(time.time() - start_time))

    if accounts.status_code != 200:
        return str(accounts.status_code)

    accounts = json.loads(accounts.text)
    text = "Your balances are \n"
    for b in accounts['balances']:
        currency = str(b['amount']['currency'])
        currency = currency_to_flag(currency)
        text += currency + " " + str(b['amount']['value']) + \
            " " + str(b['amount']['currency']) + "\n"

    print("Completed in " + str(time.time() - start_time))
    return text


@app.route('/pay', methods=['POST'])
def pay():
    start_time = time.time()
    if not verify_slack_request(request):
        return 'Request verification failed'

    text = request.form.get('text')
    print(text)
    text = text.split(' ')

    slack_id = request.form.get('user_id')
    token = user.getToken()

    user = User.query.filter_by(slack_id=slack_id).first()

    if user is None or user.encrypted_tw_token is None:
        return 'Please connect your TransferWise \
        account using /transerwise token'

    profileId = user.transferwise_profile_id

    if profileId is None:
        return 'Please connect your TransferWise \
        account using /transerwise token'

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
        last_name = name[len(name) - 1]
        last_name = ''.join([i for i in last_name if not i.isdigit()])

    if len(last_name) < 3:
        last_name = 'Unknown'

    name = first_name + ' ' + last_name
    print('Name: ' + name)

    recipient = createTransferWiseRecipient(
        email=recipient_email,
        currency=currency,
        name=name,
        legalType='PRIVATE',
        profileId=profileId,
        access_token=token
    )
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

    quote = createTransferWiseQuote(
        profileId=profileId,
        sourceCurrency=sourceCurrency,
        targetCurrency=currency,
        access_token=token,
        targetAmount=amount
    )
    print(quote.status_code)

    if quote.status_code == 422:
        print("Unsupported currency, defaulting to GBP")
        sourceCurrency = 'GBP'
        quote = createTransferWiseQuote(
            profileId=profileId,
            sourceCurrency=sourceCurrency,
            targetCurrency=currency,
            access_token=token,
            targetAmount=amount
        )

    if quote.status_code == 401:
        return str(quote.error_message)

    quoteId = json.loads(quote.text)['id']
    print("Quote ID: " + str(quoteId))
    end_time = time.time()
    print("Quote Time: " + str(end_time - start_time))

    recipientId = json.loads(recipient.text)['id']
    transfer = createPayment(
        recipientId=recipientId,
        quoteId=quoteId,
        reference='Slackwise',
        access_token=token
    )

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
        return 'Click here to pay: \
        https://transferwise.com/transferFlow#/transfer/' + str(transferId)


@app.route('/home-currency', methods=['POST'])
def home_currency():
    if not verify_slack_request(request):
        return 'Request verification failed'

    home_currency = request.form.get('text')
    print('Home currency switched to ' + home_currency)

    if home_currency == "":
        slack_id = request.form.get('user_id')
        user = User.query.filter_by(slack_id=slack_id).first()
        return user.home_currency

    home_currency = home_currency.upper()

    supported_currencies = [
        'USD',
        'AUD',
        'BGN',
        'BRL',
        'CAD',
        'CHF',
        'CZK',
        'DKK',
        'EUR',
        'GBP',
        'HKD',
        'HRK',
        'HUF',
        'JPY',
        'NOK',
        'NZD',
        'PLN',
        'RON',
        'SEK',
        'SGD',
        'TRY'
    ]
    if home_currency not in supported_currencies:
        return "Currency not supported"

    if is_prod == 'True':
        slack_id = request.form.get('user_id')
    else:
        slack_id = 'UBH7TETRB'

    user = User.query.filter_by(slack_id=slack_id).first()

    if user is None:
        return 'Please connect your Slack account first at \
        slackwise.herokuapp.com'

    user.home_currency = home_currency
    db.session.commit()

    return "Home currency updated"


@app.route('/latest', methods=['POST'])
def lastest():
    if not verify_slack_request(request):
        return 'Request verification failed'

    slack_id = request.form.get('user_id')
    user = User.query.filter_by(slack_id=slack_id).first()
    celery_latest.delay(str(user))

    return 'Thank you'


@app.route('/switch-profile', methods=['POST'])
def profile():
    if not verify_slack_request(request):
        return 'Request verification failed'

    slack_id = request.form.get('user_id')
    user = User.query.filter_by(slack_id=slack_id).first()
    token = user.getToken()
    print(
        'Previous TransferWise profile: ' + str(
            user.transferwise_profile_id
        )
    )
    profiles = getTransferWiseProfiles(
        access_token=token
    )

    if profiles.status_code != 200:
        print(str(profiles.status_code))
        return 'Error.'

    if(len(json.loads(profiles.text)) == 1):
        return 'You only have one profile.'

    personalProfileId = json.loads(profiles.text)[0]['id']

    if user.transferwise_profile_id == personalProfileId:
        user.transferwise_profile_id = json.loads(profiles.text)[1]['id']
        db.session.commit()
        return 'Active TransferWise profile: ' \
            + json.loads(profiles.text)[1]['details']['name']

    else:
        user.transferwise_profile_id = json.loads(profiles.text)[0]['id']
        db.session.commit()
        return 'Active TransferWise profile: ' \
            + json.loads(profiles.text)[0]['details']['firstName'] + ' ' \
            + json.loads(profiles.text)[0]['details']['lastName']


@app.route('/transferwise-bot-feedback', methods=['POST'])
def feedback():
    if not verify_slack_request(request):
        return 'Request verification failed'

    text = request.form.get('text')
    print('Feedback: ' + str(text))
    return 'Thank you for your feedback'


@app.route('/add-token', methods=['POST'])
def attToken():
    global is_prod
    if is_prod is 'True':
        return 'Not available in production'

    token = request.form.get('token')
    slack_id = request.form.get('user_id')

    if slack_id is None:
        return 'You have to post a User ID (slack ID)'

    if token is None:
        return 'You have to include a TransferWise token'

    profiles = getTransferWiseProfiles(access_token=token)
    if profiles.status_code == 401:
        return str(json.loads(profiles.text))

    profileId = json.loads(profiles.text)[0]['id']
    homeCurrency = decide_user_home_currency(token, profileId)

    user = User.query.filter_by(slack_id=slack_id).first()
    if user is None:
        user = User(slack_id=slack_id,
                    transferwise_profile_id=profileId,
                    home_currency=homeCurrency)
        user.addEncryptedToken(token)
        db.session.add(user)
        db.session.commit()

        return 'New user created with token'

    else:
        user.addEncryptedToken(token)
        user.transferwise_profile_id = profileId
        user.home_currency = homeCurrency
        db.session.commit()
        return 'Token added or updated to existing user'


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=port)


