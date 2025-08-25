# backend/app.py
import os
from flask import Flask, redirect, url_for, session, render_template
from backend.config import Config
from backend.database import engine, Base
from backend.extensions import socketio
from backend.routes.auth import auth_bp
from backend.routes.user import user_bp
from backend.routes.device import device_bp
from backend.routes.dashboard import dashboard_bp
from backend.services.device_manager import DeviceManager

dm = DeviceManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(dashboard_bp)

    # Root → redirect dashboard
    @app.route("/")
    def home():
        if "user" not in session:
            return render_template("index.html")
        return redirect(url_for("dashboard.dashboard_home"))

    # SocketIO init
    socketio.init_app(app, cors_allowed_origins="*")

    # DB create tables if not exist
    Base.metadata.create_all(bind=engine)

    return app


app = create_app()

# ---- Socket.IO Events ----
@socketio.on("connect")
def on_connect():
    print("⚡ client connected")

@socketio.on("disconnect")
def on_disconnect():
    print("⚡ client disconnected")

@socketio.on("device_heartbeat")
def on_device_heartbeat(data):
    uid = (data or {}).get("device_uid")
    if uid:
        dm.handle_heartbeat(uid)

@socketio.on("device_command_ack")
def on_device_command_ack(data):
    cid = (data or {}).get("command_id")
    if cid:
        dm.mark_command_ack(int(cid))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 IoT Lab running: http://0.0.0.0:{port}")
    print("http://192.168.2.11:5000/auth/login")
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
    
