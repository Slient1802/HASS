# backend/routes/dashboard.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from backend.services.device_manager import DeviceManager
from backend.database import SessionLocal
from backend.models import Device, User
from backend.security.sanitizer import sanitize_str

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")
dm = DeviceManager()

@dashboard_bp.route("/", methods=["GET"])
def dashboard_home():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    snap = dm.get_status_snapshot()
    return render_template("dashboard.html", snapshot=snap)

@dashboard_bp.route("/status", methods=["GET"])
def dashboard_status():
    if "user" not in session:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(dm.get_status_snapshot())

@dashboard_bp.route("/control", methods=["POST"])
def dashboard_control():
    if "user" not in session:
        return jsonify({"error": "unauthorized"}), 401

    # form hoặc json đều được
    data = request.get_json(silent=True) or request.form
    action = sanitize_str(data.get("action"), max_length=32)
    device_id = int(data.get("device_id", 0))

    if not device_id or not action:
        return jsonify({"error": "missing action/device_id"}), 400

    # user id demo (nếu bạn đã có login thật thì lấy từ DB theo session["user"])
    with SessionLocal() as db:
        u = db.query(User).filter(User.username == session["user"]).first()
        user_id = u.id if u else 0

    # Queue + phát lệnh
    if action in ("start", "stop", "watchdog_reset"):
        dm.enqueue_command(device_id, user_id, action)
        dm.dispatch_pending_for_device(device_id)
        return jsonify({"ok": True, "queued": action})
    elif action.startswith("cmd:"):
        # cmd tuỳ ý: "cmd:LED_ON"
        cmd = action.split("cmd:", 1)[1]
        dm.enqueue_command(device_id, user_id, cmd)
        dm.dispatch_pending_for_device(device_id)
        return jsonify({"ok": True, "queued": cmd})
    elif action == "mark_uploaded":
        dm.mark_code_uploaded(device_id, True)
        return jsonify({"ok": True, "uploaded": True})
    elif action == "mark_not_uploaded":
        dm.mark_code_uploaded(device_id, False)
        return jsonify({"ok": True, "uploaded": False})

    return jsonify({"error": "unknown action"}), 400
