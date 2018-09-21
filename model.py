from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from simplecrypt import decrypt
import os
import base64
from slackwise_functions import encrypt_transferwise_token, \
decrypt_transferwise_token

db = SQLAlchemy()


class BaseModel(db.Model):
    """Base data model for all objects"""
    __abstract__ = True

    def __init__(self, *args):
        super().__init__(*args)


class User(BaseModel):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    slack_id = db.Column(db.String(120))
    slack_token = db.Column(db.String(120))
    transferwise_token = db.Column(db.String(120))
    encrypted_tw_token = db.Column(db.String(240))
    transferwise_profile_id = db.Column(db.Integer)
    home_currency = db.Column(db.String(120))
    email = db.Column(db.String(120))
    date_created = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow)

    def __init__(self,
                 slack_token=None,
                 transferwise_token=None,
                 slack_id=None, email=None,
                 transferwise_profile_id=None,
                 home_currency=None):

        if transferwise_token is None:
            encrypted_tw_token = None
        else:
            encrypted_tw_token = encrypt_transferwise_token(
                transferwise_token
            ),
        self.slack_id = slack_id
        self.slack_token = slack_token
        self.transferwise_token = transferwise_token
        self.email = email
        self.transferwise_profile_id = transferwise_profile_id
        self.home_currency = home_currency
        self.encrypted_tw_token = encrypted_tw_token

    def __repr__(self):
        if self.transferwise_token is None:
            token = None
        else:
            token = self.transferwise_token
            #token = decrypt_transferwise_token(
            #    self.encrypted_tw_token
            #),
        return json.dumps({
            'slack_id': self.slack_id,
            'slack_token': self.slack_token,
            'transferwise_token': token,
            'email': self.email,
            'transferwise_profile_id': self.transferwise_profile_id,
            'home_currency': self.home_currency})

    def addEncryptedToken(self, token):
        self.encrypted_tw_token = encrypt_transferwise_token(token)

    def getToken(self):
        return decrypt_transferwise_token(self.encrypted_tw_token)


x = User(transferwise_token='asdf')
print(str(x))
x.encrypted_tw_token = 'asdf'
print(x)