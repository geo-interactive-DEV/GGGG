from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_pymongo import PyMongo
from datetime import timedelta
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://hello:yOf5ELAjmDxW78jO@cluster0.quncdr4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
app.config["JWT_SECRET_KEY"] = "super-secret-key"  # Change this for production!
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

mongo = PyMongo(app)
jwt = JWTManager(app)

users = mongo.db.users
games = mongo.db.games

# --- Signup ---
@app.route("/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if users.find_one({"username": data["username"]}):
        return jsonify({"msg": "Username taken"}), 400
    hashed_pw = generate_password_hash(data["password"])
    users.insert_one({
        "username": data["username"],
        "password": hashed_pw,
        "is_admin": False
    })
    return jsonify({"msg": "User created"}), 201

# --- Login ---
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    user = users.find_one({"username": data["username"]})
    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(identity={
        "id": str(user["_id"]),
        "username": user["username"],
        "is_admin": user.get("is_admin", False)
    })
    return jsonify(access_token=access_token)

# --- List approved games ---
@app.route("/games", methods=["GET"])
def list_games():
    approved_games = games.find({"approved": True})
    result = []
    for g in approved_games:
        result.append({
            "id": str(g["_id"]),
            "name": g["name"],
            "description": g.get("description", ""),
            "creator_id": str(g["creator_id"])
        })
    return jsonify(result)

# --- Upload game ---
@app.route("/games/upload", methods=["POST"])
@jwt_required()
def upload_game():
    identity = get_jwt_identity()
    data = request.get_json()
    game_doc = {
        "name": data.get("name"),
        "description": data.get("description", ""),
        "creator_id": ObjectId(identity["id"]),
        "approved": False
    }
    games.insert_one(game_doc)
    return jsonify({"msg": "Game uploaded, pending approval"}), 201

# --- Review game (admin only) ---
@app.route("/games/review", methods=["POST"])
@jwt_required()
def review_game():
    identity = get_jwt_identity()
    if not identity.get("is_admin"):
        return jsonify({"msg": "Admins only"}), 403
    data = request.get_json()
    game_id = data.get("game_id")
    approved = data.get("approved", False)
    if not game_id:
        return jsonify({"msg": "Game ID required"}), 400
    result = games.update_one(
        {"_id": ObjectId(game_id)},
        {"$set": {"approved": approved}}
    )
    if result.matched_count == 0:
        return jsonify({"msg": "Game not found"}), 404
    return jsonify({"msg": f"Game {'approved' if approved else 'rejected'}"}), 200

if __name__ == "__main__":
    app.run(debug=True)
