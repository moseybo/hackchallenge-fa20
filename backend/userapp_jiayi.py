import json

from userdb_jiayi import db
from userdb_jiayi import User, Category, Game
from flask import Flask
from flask import request

db_filename = "gameapp.db"
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()

def success_response(data, code=200):
    return json.dumps({"success": True, "data": data}), code

def failure_response(message, code=404):
    return json.dumps({"success": False, "error": message}), code


# -- USER ROUTES --------------------------------------------------

@app.route("/")
@app.route("/api/users/")
def get_users():
    return success_response([u.serialize() for u in User.query.all()])


@app.route("/api/users/", methods=["POST"])
def create_user():
    body = json.loads(request.data)
    name = body.get('name')
    if name is None:
        return failure_response("Name cannot be empty")
    username = body.get('username')
    if username is None:
        return failure_response("Username cannot be empty")
    new_user = User(name=name, username=username)
    db.session.add(new_user)
    db.session.commit()
    return success_response(new_user.serialize(), 201)


@app.route("/api/users/<int:user_id>/")
def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found")
    return success_response(user.serialize())


@app.route("/api/users/<int:user_id>/", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found")
    db.session.delete(user)
    db.session.commit()
    return success_response(user.serialize())

# -- CATEGORY ROUTES --------------------------------------------------

@app.route("/api/categories/")
def get_categories():
    return success_response([c.serialize_without_game() for c in Category.query.all()])

@app.route("/api/categories/", methods=["POST"])
def create_category():
    body = json.loads(request.data)
    title = body.get('title')
    if title is None:
        return failure_response("Title cannot be empty")
    new_category = Category(title=title)
    db.session.add(new_category)
    db.session.commit()
    return success_response(new_category.serialize(), 201)

@app.route("/api/categories/<int:category_id>/")
def get_category(category_id):
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        return failure_response("Category not found!")
    return success_response(category.serialize())

# -- GAME ROUTES --------------------------------------------------

@app.route("/api/games/", methods=["POST"])
def create_game():
    body = json.loads(request.data)
    title = body.get('title')
    if title is None:
        return failure_response("Title cannot be empty")
    platform = body.get('platform')
    if platform is None:
        return failure_response("Platform cannot be empty")
    publisher = body.get('publisher')
    if publisher is None:
        return failure_response("Publisher cannot be empty")
    release_date = body.get('release_date')
    if release_date is None:
        return failure_response("Release_date cannot be empty")
    category_id = body.get('category_id')
    if category_id is None:
        return failure_response("Category_id cannot be empty")
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        return failure_response("Category not found!")
    new_game = Game(title=title, platform=platform, publisher=publisher, release_date=release_date, category_id=category_id)
    db.session.add(new_game)
    db.session.commit()
    return success_response(new_game.serialize(), 201)
    
    

@app.route("/api/games/<int:game_id>/", methods=["GET"])
def get_game(game_id):
    game = Game.query.filter_by(id=game_id).first()
    if game is None:
        return failure_response("Game not found!")
    return success_response(game.serialize())


@app.route("/api/games/<int:game_id>/add/", methods=["POST"])
def add_user(game_id):
    game = Game.query.filter_by(id=game_id).first()
    if game is None:
        return failure_response("Game not found!")
    body = json.loads(request.data)
    user_id = body.get('user_id')
    if user_id is None:
        return failure_response("User ID cannot be empty")
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")

    user.favorites.append(game)
    game.players.append(user)
        
    db.session.commit()
    return success_response(user.serialize(), 201)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
