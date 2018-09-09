from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from datetime import datetime
import json
from simplecrypt import encrypt, decrypt
import os
import base64

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
    transferwise_profile_id = db.Column(db.Integer)
    home_currency = db.Column(db.String(120))
    email = db.Column(db.String(120))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, slack_token = None, transferwise_token = None, slack_id = None, email = None, transferwise_profile_id = None, home_currency = None):
        self.slack_id = slack_id
        self.slack_token = slack_token
        self.transferwise_token = base64.b64encode(encrypt(encryption_key, transferwise_token))
        self.email = email
        self.transferwise_profile_id = transferwise_profile_id
        self.home_currency = home_currency

    def __repr__(self):
        return json.dumps({'slack_id' : self.slack_id,
        'slack_token' : self.slack_token,
        'transferwise_token' : str(decrypt(encryption_key, base64.b64decode(self.transferwise_token))),
        'email' : self.email,
        'transferwise_profile_id' : self.transferwise_profile_id,
        'home_currency' : self.home_currency})

