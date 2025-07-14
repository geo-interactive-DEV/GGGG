from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from datetime import timedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///geo_launcher.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-key"  # Change this for production
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ---- Models ----

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Store hashed in prod
    is_admin = db.Column(db.Boolean, default=False)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    description = db.Column(db.String(500))
    approved = db.Column(db.Boolean, default=False)

# ---- Routes ----

@app.route("/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"msg": "Username taken"}), 400
    user = User(username=data["username"], password=data["password"])  # Store hashed in prod
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "User created"}), 201

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data["username"], password=data["password"]).first()
    if not user:
        return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(identity={"id": user.id, "username": user.username, "is_admin": user.is_admin})
    return jsonify(access_token=access_token)

@app.route("/games", methods=["GET"])
def list_games():
    games = Game.query.filter_by(approved=True).all()
    result = []
    for g in games:
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "creator_id": g.creator_id
        })
    return jsonify(result)

@app.route("/games/upload", methods=["POST"])
@jwt_required()
def upload_game():
    identity = get_jwt_identity()
    data = request.get_json()
    game = Game(
        name=data.get("name"),
        description=data.get("description", ""),
        creator_id=identity["id"],
        approved=False
    )
    db.session.add(game)
    db.session.commit()
    return jsonify({"msg": "Game uploaded, pending approval", "game_id": game.id}), 201

@app.route("/games/review", methods=["POST"])
@jwt_required()
def review_game():
    identity = get_jwt_identity()
    if not identity.get("is_admin"):
        return jsonify({"msg": "Admins only"}), 403
    data = request.get_json()
    game = Game.query.get(data.get("game_id"))
    if not game:
        return jsonify({"msg": "Game not found"}), 404
    game.approved = data.get("approved", False)
    db.session.commit()
    return jsonify({"msg": f"Game {'approved' if game.approved else 'rejected'}"}), 200

# ---- Initialize DB ----

@app.before_first_request
def create_tables():
    db.create_all()

# ---- Run server ----

if __name__ == "__main__":
    app.run(debug=True)
