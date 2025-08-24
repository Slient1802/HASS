# backend/app.py
import os
from flask import Flask
from flask_socketio import SocketIO
from flask import render_template
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal
from .services.device_manager import DeviceManager
from .routes.auth import auth_bp, login_manager
from .config import Config

from backend.extensions import socketio   # <-- important
from backend.routes.auth import auth_bp
# from backend.routes.user import user_bp
from backend.routes.device import device_bp

# --- Khởi tạo Flask + Socket.IO ---
def create_app():
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    # app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(device_bp, url_prefix="/device")

    socketio.init_app(app)

    # ✅ root route
    @app.route("/")
    def home():
        return render_template("index.html")

    return app


# --- Main ---
app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Khởi tạo DB ---
Base.metadata.create_all(bind=engine)

# Service manager với socketio
device_manager = DeviceManager(socketio)

# Middleware DB session (cho API routes nếu cần)
@app.before_request
def create_session():
    setattr(app, "db", SessionLocal())

@app.teardown_request
def remove_session(exception=None):
    db = getattr(app, "db", None)
    if isinstance(db, Session):
        db.close()


# --- Socket.IO Events ---
@socketio.on("connect")
def handle_connect():
    print("⚡ Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    print("⚡ Client disconnected")


@socketio.on("device_heartbeat")
def handle_heartbeat(data):
    """
    Thiết bị gửi heartbeat định kỳ
    data = {"device_uid": "pi-001"}
    """
    uid = data.get("device_uid")
    if uid:
        device_manager.handle_heartbeat(uid)
        socketio.emit("heartbeat_ack", {"uid": uid})


@socketio.on("device_command_ack")
def handle_command_ack(data):
    """
    Thiết bị báo đã nhận command
    data = {"device_uid": "pi-001", "command_id": 123}
    """
    uid = data.get("device_uid")
    cmd_id = data.get("command_id")
    if uid and cmd_id:
        device_manager.mark_command_ack(cmd_id)
        print(f"✅ ACK từ {uid} cho command {cmd_id}")



# --- Run app ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 Starting IoT Lab Live System on http://127.0.0.1:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
