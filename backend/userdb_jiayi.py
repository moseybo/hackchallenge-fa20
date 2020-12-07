from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

association_table_pulisher = db.Table(
    'association_pulisher',
    db.Model.metadata,
    db.Column('pulisher_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'))
)

association_table_player = db.Table(
    'association_player',
    db.Model.metadata,
    db.Column('player_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'))
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    games_publisher = db.relationship('Game', secondary=association_table_publisher, back_populates='publishers')
    games_player = db.relationship('Game', secondary=association_table_player, back_populates='players')
    user_type = ""

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.username = kwargs.get('username')

    def serialize(self):
        if self.user_type == "player":
            if self.games_player is None:
                games = []
            else:
                games = [game.serialize() for game in self.games_player]
            return {
                'id': self.id,
                'name': self.name,
                'username': self.username,
                'games': self.games_player
            }
        else:
            if self.games_publisher is None:
                games = []
            else:
                games = [game.serialize() for game in self.games_publisher]
            return {
                'id': self.id,
                'name': self.name,
                'username': self.username,
                'games': self.games_publisher
            }

    def serialize_without_game(self):
        if self.user_type == "player":
            return {
                'id': self.id,
                'name': self.name,
                'username': self.username
            }
        else:
            return {
                'id': self.id,
                'name': self.name,
                'username': self.username
            }

# class Category(db.Model):

# class Game(db.Model):
