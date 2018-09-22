import os
import time
import urllib
import hmac
import hashlib
import base64
from simplecrypt import encrypt, decrypt
from transferwiseclient.transferwiseclient import getTransferWiseProfiles, \
    createTransferWiseRecipient, createTransferWiseQuote, createPayment, \
    getBorderlessAccountId, getBorderlessAccounts, getBorderlessActivity
import json
from Crypto.Cipher import Salsa20

def verify_slack_request(request):
    slack_signing_secret = os.environ.get('SLACK_SIGNING_SECRET', None)
    is_prod = os.environ.get('IS_HEROKU', None)

    if 'X-Slack-Request-Timestamp' not in request.headers:
        return 'Error'

    timestamp = request.headers['X-Slack-Request-Timestamp']

    if is_prod == 'True' and (time.time() - int(timestamp) > 60 * 5):
        return 'Error'

    form_data = request.form.to_dict()
    form_string = urllib.parse.urlencode(form_data)

    message = 'v0:' + str(timestamp) + ":" + str(form_string)
    message = message.encode('utf-8')

    slack_signing_secret = bytes(slack_signing_secret, 'utf-8')
    my_signature = 'v0=' + \
        hmac.new(
            slack_signing_secret,
            msg=message,
            digestmod=hashlib.sha256
        ).hexdigest()

    slack_signature = request.headers['X-Slack-Signature']

    if hmac.compare_digest(my_signature, slack_signature):
        print("Verification succeeded.")
        return True
    elif is_prod is None:
        print("Verification failed, \
            but continuing anyway since this is test environment.")
        return True
    else:
        print("Verification failed")
        return False


def currency_to_flag(currency):
    if currency == 'USD':
        currency = ':flag-us: '
    elif currency == 'AUD':
        currency = ':flag-au:'
    elif currency == 'BGN':
        currency = ':flag-bg:'
    elif currency == 'BRL':
        currency = ':flag-br:'
    elif currency == 'CAD':
        currency = ':flag-ca:'
    elif currency == 'CHF':
        currency = ':flag-ch:'
    elif currency == 'CZK':
        currency = ':flag-cz:'
    elif currency == 'DKK':
        currency = ':flag-dk:'
    elif currency == 'EUR':
        currency = ':flag-eu:'
    elif currency == 'GBP':
        currency = ':flag-uk:'
    elif currency == 'HKD':
        currency = ':flag-hk:'
    elif currency == 'HRK':
        currency = ':flag-ia:'
    elif currency == 'HUF':
        currency = ':flag-hu:'
    elif currency == 'ILS':
        currency = ':flag-il:'
    elif currency == 'JPY':
        currency = ':flag-jp:'
    elif currency == 'NOK':
        currency = ':flag-no:'
    elif currency == 'NZD':
        currency = ':flag-nz:'
    elif currency == 'PLN':
        currency = ':flag-pl:'
    elif currency == 'RON':
        currency = ':flag-ro:'
    elif currency == 'SEK':
        currency = ':flag-se:'
    elif currency == 'SGD':
        currency = ':flag-sg:'
    elif currency == 'TRY':
        currency = ':flag-tr:'
    elif currency == 'UAH':
        currency = ':flag-ua:'
    elif currency == 'ZAR':
        currency = ':flag-za:'
    else:
        currency = ''
    return currency


def encrypt_transferwise_token(plaintext):
    if (isinstance(plaintext, str)):
        plaintext = plaintext.encode('utf-8')

    if not (isinstance(plaintext, bytes)):
        return 'Incorrect input'

    secret = os.environ.get('ENCRYPTION_KEY',
                            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    secret = secret.encode('utf-8')

    cipher = Salsa20.new(key=secret)
    msg = cipher.nonce + cipher.encrypt(plaintext)
    return msg


def decrypt_transferwise_token(msg):
    if not (isinstance(msg, bytes)):
        return 'Incorrect input'

    secret = os.environ.get('ENCRYPTION_KEY',
                            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    secret = secret.encode('utf-8')

    msg_nonce=msg[:8]
    ciphertext=msg[8:]
    cipher = Salsa20.new(key=secret, nonce=msg_nonce)
    plaintext = cipher.decrypt(ciphertext)
    return plaintext.decode('utf-8')


def print_balance_activity(activity):
    # Uses the response from getBorderlessActivity()
    # to generate a print version suitable for slack

    text = "Your latest borderless activity: \n"
    for b in activity:
        activityType = str(b['type'])
        if b['type'] in ['WITHDRAWAL', 'DEPOSIT']:
            currency = str(b['amount']['currency'])

            currency = currency_to_flag(currency)

            activityType = str(b['type'])

            if activityType == 'DEPOSIT':
                activityType = ':moneybag:'
            elif activityType == 'WITHDRAWAL':
                activityType = ':wave:'

            text += str(currency) + \
                str(b['amount']['value']) + " " + \
                str(b['amount']['currency']) + " " + \
                activityType + " " + str(b['type']) + " " + \
                str(b['creationTime'])[0:10] + " " + \
                str(b['creationTime'])[11:16] + "\n"

        elif b['type'] == 'CONVERSION':
            activityType = ':currency_exchange:'
            text += activityType + str(b['sourceAmount']['value']) + " " \
                + str(b['sourceAmount']['currency']) + " to " \
                + str(b['targetAmount']['value']) + " " \
                + str(b['targetAmount']['currency']) + '\n'

        else:
            text += b['type'] + '\n'

    return text


def get_latest_borderless_activity(user):
    borderlessId = getBorderlessAccountId(
        user.transferwise_profile_id,
        user.getToken()
    )

    if len(json.loads(borderlessId.text)) < 1:
        return 'You need to have a borderless account to use the Slack bot'

    if borderlessId.status_code != 200:
        return str(borderlessId.status_code)

    borderlessAccountId = json.loads(borderlessId.text)[0]['id']

    activity = getBorderlessActivity(
        borderlessAccountId,
        user.getToken()
    )
    activity = json.loads(activity.text)
    text = print_balance_activity(activity)

    return str(text)


def decide_user_home_currency(token, profileId):
    borderlessId = getBorderlessAccountId(
        profileId=profileId,
        access_token=token)

    if borderlessId.status_code == 401:
        return str(borderlessId.error_message)

    if len(json.loads(borderlessId.text)) < 1:
        return 'You need to have a borderless account to use the Slack bot'

    borderlessId = json.loads(borderlessId.text)[0]['id']

    accounts = getBorderlessAccounts(
        borderlessId=borderlessId,
        access_token=token)

    if accounts.status_code == 200:
        accounts = json.loads(accounts.text)

        # The first record has the highest balance, so we'll default to that
        homeCurrency = accounts['balances'][0]['amount']['currency']

    currencies = [
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

    if homeCurrency not in currencies:
        print("Source currency not valid, assuming GBP")
        homeCurrency = 'GBP'

    return homeCurrency
