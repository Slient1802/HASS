from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from typing import cast

from backend.database import get_db
from backend.models import User
from backend.security.sanitizer import sanitize_str

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

login_manager = LoginManager()


@login_manager.unauthorized_handler
def unauthorized_callback():
    return jsonify({"error": "Unauthorized"}), 401


@login_manager.user_loader
def load_user(user_id):
    db = next(get_db())
    return db.get(User, int(user_id))


# === REGISTER ===
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = sanitize_str(data.get("username"), default="", max_length=64)
    password = data.get("password")
    role = sanitize_str(data.get("role"), default="user", max_length=16)

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    db = next(get_db())
    existing = db.query(User).filter_by(username=username).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)
    user = User(username=username, password_hash=hashed_pw, role=role)
    db.add(user)
    db.commit()

    return jsonify({"message": "User registered successfully"}), 201


# === LOGIN ===
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    username = sanitize_str(data.get("username"), max_length=64)
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    db = next(get_db())
    user = db.query(User).filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user, remember=True)

    return jsonify({
        "message": "Login successful",
        "user": {"id": user.id, "username": user.username, "role": user.role}
    })


# === LOGOUT ===
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})


# === GET CURRENT USER ===
@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    })

