import datetime
import hashlib
import os

import bcrypt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

game_to_user_association_table = db.Table(
    'game_to_user_association_table',
    db.Model.metadata,
    db.Column('game_id', db.Integer, db.ForeignKey('game.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    favorites = db.relationship('Game', secondary=game_to_user_association_table, back_populates='players')

    # User information
    email = db.Column(db.String, nullable=False, unique=True)
    password_digest = db.Column(db.String, nullable=False)

    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.username = kwargs.get('username')
        self.email = kwargs.get("email")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.renew_session()

     # Used to randomly generate session/update tokens
    def _urlsafe_base_64(self):
        return hashlib.sha1(os.urandom(64)).hexdigest()

    # Generates new tokens, and resets expiration time
    def renew_session(self):
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    # Checks if session token is valid and hasn't expired
    def verify_session_token(self, session_token):
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        return update_token == self.update_token
   

    def serialize(self):
        publishers_out = []
        [publishers_out.append(game.publisher) for game in self.favorites if game.publisher not in publishers_out]
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'favorites': [game.serialize() for game in self.favorites],
            'publishers': publishers_out
        }

    def serialize_without_game(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username
        }

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    games = db.relationship("Game", cascade="delete")

    def __init__(self, **kwargs):
        self.title = kwargs.get("title")

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "games": [g.serialize_without_category() for g in self.games]
        }
    
    def serialize_without_game(self):
        return {
            "id": self.id,
            "title": self.title
        }

class Game(db.Model):
    __tablename__ = 'game'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    platform = db.Column(db.String, nullable=False)
    publisher = db.Column(db.String, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    release_date = db.Column(db.String, nullable=False)
    players = db.relationship("User", secondary=game_to_user_association_table, back_populates="favorites")
    
    def __init__(self, **kwargs):
        self.title = kwargs.get("title")
        self.platform = kwargs.get("platform")
        self.publisher = kwargs.get("publisher")
        self.release_date = kwargs.get("release_date")
        self.category_id = kwargs.get("category_id")

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform,
            "publisher": self.publisher,
            "release_date": self.release_date,
            "players": [u.serialize_without_game() for u in self.players],
            "category": Category.query.filter_by(id=self.category_id).first().serialize_without_game()
        }
    
    def serialize_without_category(self):
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform
        }


