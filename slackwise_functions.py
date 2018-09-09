import os
import time
import urllib
import hmac
import hashlib
import base64
from simplecrypt import encrypt, decrypt

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
    my_signature = 'v0=' + hmac.new(slack_signing_secret, msg=message, digestmod=hashlib.sha256).hexdigest()

    slack_signature = request.headers['X-Slack-Signature']

    if hmac.compare_digest(my_signature, slack_signature):
        print("Verification succeeded.")
        return True
    elif is_prod is None:
        print("Verification failed, but continuing anyway since this is test environment.")
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

def decrypt_transferwise_token(token):
	encryption_key = os.environ.get('ENCRYPTION_KEY', 'dev_key')
	return str(decrypt(encryption_key, base64.b64decode(token)))




