import json
import os

from db import db
from db import User, Category, Game, Asset
from flask import Flask
from flask import request
import users_dao

db_filename = "auth.db"
app = Flask(__name__)

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

@app.route("/api/games/")
def get_games():
    return success_response([g.serialize_without_category() for g in Game.query.all()])

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



# -- AUTHORIZATION ROUTES --------------------------------------------------

def extract_token(request):
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, json.dumps({"error": "Missing authorization header."})
    
    bearer_token = auth_header.replace("Bearer", "").strip()
    if bearer_token is None or not bearer_token:
        return False, json.dumps({"error": "Invalid authorization header."})

    return True, bearer_token


@app.route("/api/register/", methods=["POST"])
def register_account():
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")

    if email is None or password is None:
        return json.dumps({"error": "Invalid email or password"})
    
    was_created, user = users_dao.create_user(email, password)

    if not was_created:
        return json.dumps({"error": "User already exists."})

    return json.dumps(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token,
        }
    )


@app.route("/api/login/", methods=["POST"])
def login():
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")

    if email is None or password is None:
        return json.dumps({"error": "Invalid email or password"})
    
    was_successful, user = users_dao.verify_credentials(email, password)

    if not was_successful:
        return json.dumps({"error": "Incorrect email or password"})

    return json.dumps(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token,
        }
    )


@app.route("/api/session/", methods=["POST"])
def update_session():
    was_successful, update_token = extract_token(request)

    if not was_successful:
        return update_token

    try:
        user= users_dao.renew_session(update_token)
    except Exception as e:
        return json.dumps({"error": f"Invalid update token: {str(e)}"})
    
    return json.dumps(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token,
        }
    )


@app.route("/api/secret/", methods=["GET"])
def secret_message():
    was_successful, session_token = extract_token(request)

    if not was_successful:
        return session_token

    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error": "Invalid session token."})

    return json.dumps(
        {"message": "You have successfully implemented sessions."}
    )

# -- ASSET ROUTES --------------------------------------------------

@app.route("/api/upload/", methods=["POST"])
def upload():
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No base64 URL to be found!")

    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
