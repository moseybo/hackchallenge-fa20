from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

association_table_publisher = db.Table(
    'association_publisher',
    db.Model.metadata,
    db.Column('publisher_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'))
)

game_to_player_association_table = db.Table(
    'game_to_player_association_table',
    db.Model.metadata,
    db.Column('game_id', db.Integer, db.ForeignKey('game.id')),
    db.Column('player_id', db.Integer, db.ForeignKey('user.id'))
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    favorites = db.relationship('Game', secondary=game_to_player_association_table, back_populates='players')

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.username = kwargs.get('username')

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
    players = db.relationship("User", secondary=game_to_player_association_table, back_populates="favorites")
    
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
            "players": [u.serialize_without_game for u in self.players],
            "category": {
                "id": self.category_id,
                "title": Category.query.filter_by(id=self.category_id).first().title
            }
        }
    
    def serialize_without_category(self):
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform
        }


