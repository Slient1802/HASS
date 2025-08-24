from flask import Blueprint, request, jsonify, render_template, request, redirect, url_for, session, flash
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
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # TODO: Replace with real authentication
        if username == "admin" and password == "1234":
            session["user"] = username
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("auth.login"))

    # If GET request → show login form
    return render_template("login.html")


# === LOGOUT ===
@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


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

