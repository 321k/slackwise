from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from datetime import datetime
import json

db = SQLAlchemy()


class BaseModel(db.Model):
    """Base data model for all objects"""
    __abstract__ = True

    def __init__(self, *args):
        super().__init__(*args)

    def __repr__(self):
        return json.dumps(self, self.__class__)

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
        self.transferwise_token = transferwise_token
        self.email = email
        self.transferwise_profile_id = transferwise_profile_id
        self.home_currency = home_currency

