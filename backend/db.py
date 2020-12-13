import datetime
import hashlib
import os
import bcrypt
from flask_sqlalchemy import SQLAlchemy
import base64
import boto3
import random
import re
import string
from io import BytesIO
from mimetypes import guess_extension, guess_type
from PIL import Image


db = SQLAlchemy()

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET = "hackchallenge-fa20"
S3_BASE_URL = f"https://{S3_BUCKET}.s3-us-east-2.amazonaws.com"

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

class Asset(db.Model):
    __tablename__ = "asset"

    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String, nullable=True)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        self.create(kwargs.get("image_data"))

    def serialize(self):
        return {
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at),
        }

    def create(self, image_data):
        try:
            # base64 string --> .png --> png
            ext = guess_extension(guess_type(image_data)[0])[1:]
            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} not supported!")

            # secure way of generating random string for image name
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )
        
            # remove header of base64 string and open image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{salt}.{ext}"
            self.upload(img, img_filename)
        except Exception as e:
            print(f"Unable to create image due to {e}")

    def upload(self, img, img_filename):
        try:
            # save image temporarily on server
            img_temploc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temploc)

            # upload image to S3
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET, img_filename)

            # make s3 image url public
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET, img_filename)
            object_acl.put(ACL="public-read")

            os.remove(img_temploc)
        except Exception as e:
            print(f"Unable to upload image due to {e}")



