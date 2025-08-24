from flask import Blueprint, render_template, session, redirect, url_for, request, flash

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

# Fake queue list
student_queue = [
    {"id": 1, "name": "Alice", "status": "Waiting"},
    {"id": 2, "name": "Bob", "status": "Waiting"},
    {"id": 3, "name": "Charlie", "status": "Done"},
]

@dashboard_bp.route("/", methods=["GET"])
def dashboard_home():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", queue=student_queue)


@dashboard_bp.route("/control", methods=["POST"])
def control():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    action = request.form.get("action")

    if action == "on":
        flash("✅ Hardware turned ON", "success")
        # TODO: call actual hardware control function here
    elif action == "off":
        flash("⛔ Hardware turned OFF", "danger")
        # TODO: call actual hardware control function here
    elif action == "test":
        flash("🔄 Testing queue hardware control...", "info")
        # TODO: simulate student queue controlling hardware
    else:
        flash("Unknown action", "warning")

    return redirect(url_for("dashboard.dashboard_home"))
