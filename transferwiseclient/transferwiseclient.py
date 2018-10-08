import uuid
import requests
import json


def getTransferWiseProfiles(access_token):
    # To get the personal profile ID, use json.loads(profiles.text)[0]['id']

    profiles = requests.get('https://api.transferwise.com/v1/profiles',
                            headers={
                                'Authorization': 'Bearer ' + access_token,
                                'Content-Type': 'application/json'})

    return profiles


def createTransferWiseRecipient(email,
                                currency,
                                name,
                                legalType,
                                profileId,
                                access_token):
    recipient = requests.post('https://api.transferwise.com/v1/accounts',
                              data=json.dumps(
                                  {
                                      "profile": profileId,
                                      "accountHolderName": name,
                                      "currency": currency,
                                      "type": "email",
                                      "legalType": legalType,
                                      "details":
                                      {
                                          "email": email
                                      }
                                  }
                              ),
                              headers={
                                  'Authorization': 'Bearer ' +
                                  access_token,
                                  'Content-Type': 'application/json'})

# json.loads(recipient.text)['id']
    return recipient


def createTransferWiseQuote(
    profileId,
    sourceCurrency,
    targetCurrency,
    access_token,
    sourceAmount=None,
    targetAmount=None
):
    if sourceAmount is None and targetAmount is None:
        return "Specify sourceAmount or targetAmount"
    elif sourceAmount is not None and targetAmount is not None:
        return "Specify only sourceAmount or targetAmount"
    elif sourceAmount is not None and targetAmount is None:
        quote = requests.post('https://api.transferwise.com/v1/quotes',
                              data=json.dumps(
                                  {
                                      'profile': profileId,
                                      'source': sourceCurrency,
                                      'target': targetCurrency,
                                      'rateType': 'FIXED',
                                      'sourceAmount': sourceAmount,
                                      'type': 'REGULAR'
                                  }
                              ),
                              headers={
                                  'Authorization': 'Bearer ' + access_token,
                                  'Content-Type': 'application/json'}
                              )

    elif sourceAmount is None and targetAmount is not None:
        quote = requests.post('https://api.transferwise.com/v1/quotes',
                              data=json.dumps(
                                  {
                                      'profile': profileId,
                                      'source': sourceCurrency,
                                      'target': targetCurrency,
                                      'rateType': 'FIXED',
                                      'targetAmount': targetAmount,
                                      'type': 'REGULAR'
                                  }
                              ),
                              headers={
                                  'Authorization': 'Bearer ' +
                                  access_token,
                                  'Content-Type': 'application/json'}
                              )
    else:
        return "Something went wrong"

    # json.loads(quote.text)['id']
    return quote


def createPayment(recipientId, quoteId, reference, access_token):
    response = requests.post('https://api.transferwise.com/v1/transfers',
                             data=json.dumps(
                                 {
                                     "targetAccount": recipientId,
                                     "quote": quoteId,
                                     "customerTransactionId":
                                     str(uuid.uuid4()),
                                     "details": {
                                         "reference": reference,
                                     }
                                 }
                             ),
                             headers={
                                 'Authorization': 'Bearer ' +
                                 access_token,
                                 'Content-Type': 'application/json'})
    # json.loads(transfer.text)['id']
    return response


def redirectToPay(transferId):
    return 'https://transferwise.com/transferFlow#/transfer/' +\
        transferId


def getBorderlessAccountId(profileId, access_token):
    url_string = 'https://api.transferwise.com/v1/borderless-accounts?profileId='
    response = requests.get(url_string + str(profileId),
                            headers={
                                'Authorization': 'Bearer ' + str(access_token),
                                'Content-Type': 'application/json'})

    # json.loads(response.text)[0]['id']
    return response


def getBorderlessAccounts(borderlessId, access_token):
    url_string = 'https://api.transferwise.com/v1/borderless-accounts/'
    response = requests.get(url_string + str(borderlessId),
                            headers={
                                'Authorization': 'Bearer ' + str(access_token),
                                'Content-Type': 'application/json'})

    return response


def getBorderlessActivity(borderlessAccountId, access_token):
    url_string = 'https://api.transferwise.com/v1/borderless-accounts/'
    response = requests.get(url_string +
                            str(borderlessAccountId) +
                            '/transactions',
                            headers={
                                'Authorization': 'Bearer ' + str(access_token),
                                'Content-Type': 'application/json'})
    return response


def getTransfers(
        limit,
        offset,
        accessToken,
        createdDateStart=None,
        createdDateEnd=None
):
    url_string = 'https://api.transferwise.com/v1/transfers?limit='
    if createdDateStart is None and createdDateEnd is None:
        response = requests.get(url_string +
                                str(limit) +
                                '&offest=' + str(offset),
                                headers={
                                    'Authorization': 'Bearer ' +
                                    accessToken,
                                    'Content-Type': 'application/json'})

    elif createdDateStart is None and createdDateEnd is not None:
        response = requests.get(url_string +
                                str(limit) +
                                '&offest=' +
                                str(offset) +
                                '&createdDateEnd=' +
                                str(createdDateEnd),
                                headers={
                                    'Authorization': 'Bearer ' + accessToken,
                                    'Content-Type': 'application/json'}
                                )

    elif createdDateStart is not None and createdDateEnd is None:
        response = requests.get(url_string +
                                str(limit) +
                                '&offest=' +
                                str(offset) +
                                '&createdDateStart=' +
                                str(createdDateStart),
                                headers={
                                    'Authorization': 'Bearer ' +
                                    accessToken,
                                    'Content-Type': 'application/json'})

    else:
        response = requests.get(url_string +
                                str(limit) +
                                '&offest=' +
                                str(offset) +
                                '&createdDateStart=' +
                                str(createdDateStart) +
                                '&createdDateEnd=' +
                                str(createdDateEnd),
                                headers={
                                    'Authorization': 'Bearer ' +
                                    accessToken,
                                    'Content-Type': 'application/json'})
        return response


def getExchangeRate(access_token, source_currency, target_currency):
    url_string = "https://api.transferwise.com/v1/rates?source=" +\
        source_currency + "&target=" + target_currency
    response = requests.get(url_string,
                            headers={
                                'Authorization': 'Bearer ' + access_token,
                                'Content-Type': 'application/json'})
    return response
