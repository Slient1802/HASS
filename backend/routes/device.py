# backend/routes/device.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.database import get_db
from backend.models import Device
from backend.security.sanitizer import sanitize_str
from backend.services.device_manager import DeviceManager
from backend.extensions import socketio

device_bp = Blueprint("device", __name__)

# Service manager với socketio
device_manager = DeviceManager(socketio)

@device_bp.route("/test", methods=["GET"])
def test_device():
    socketio.emit("device_test", {"msg": "Hello from device!"})
    return jsonify({"status": "ok"})


@device_bp.route("/register", methods=["POST"])
@jwt_required()
def register_device():
    """
    Sinh viên/giảng viên đăng ký một thiết bị (Arduino / Raspberry Pi).
    """
    try:
        data = request.get_json() or {}
        name = sanitize_str(data.get("name"))
        hw_type = sanitize_str(data.get("type"))  # "arduino" hoặc "raspberry_pi"

        if not name or not hw_type:
            return jsonify({"error": "Missing device name or type"}), 400

        user_id = get_jwt_identity()

        db = next(get_db())
        new_device = Device(name=name, hw_type=hw_type, owner_id=user_id)
        db.add(new_device)
        db.commit()

        return jsonify({"message": "Device registered successfully", "device_id": new_device.id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<int:device_id>/update", methods=["PUT"])
@jwt_required()
def update_device(device_id):
    """
    Cập nhật thông tin thiết bị (tên, loại, trạng thái).
    """
    try:
        user_id = get_jwt_identity()
        db = next(get_db())
        device = db.query(Device).filter_by(id=device_id, owner_id=user_id).first()

        if not device:
            return jsonify({"error": "Device not found"}), 404

        data = request.get_json() or {}
        if "name" in data:
            device.name = sanitize_str(data["name"])
        if "type" in data:
            device.hw_type = sanitize_str(data["type"])
        if "status" in data:
            device.status = sanitize_str(data["status"])

        db.commit()
        return jsonify({"message": "Device updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<int:device_id>/delete", methods=["DELETE"])
@jwt_required()
def delete_device(device_id):
    """
    Xóa thiết bị khỏi tài khoản người dùng.
    """
    try:
        user_id = get_jwt_identity()
        db = next(get_db())
        device = db.query(Device).filter_by(id=device_id, owner_id=user_id).first()

        if not device:
            return jsonify({"error": "Device not found"}), 404

        db.delete(device)
        db.commit()
        return jsonify({"message": "Device deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<int:device_id>/start", methods=["POST"])
@jwt_required()
def start_device(device_id):
    """
    Yêu cầu bật thiết bị.
    """
    try:
        user_id = get_jwt_identity()
        db = next(get_db())
        device = db.query(Device).filter_by(id=device_id, owner_id=user_id).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404

        # Gửi lệnh xuống hardware client
        device_manager.send_command(device.id, {"action": "START"})

        device.status = "running"
        db.commit()
        return jsonify({"message": f"Device {device.name} started"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<int:device_id>/stop", methods=["POST"])
@jwt_required()
def stop_device(device_id):
    """
    Yêu cầu dừng thiết bị.
    """
    try:
        user_id = get_jwt_identity()
        db = next(get_db())
        device = db.query(Device).filter_by(id=device_id, owner_id=user_id).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404

        device_manager.send_command(device.id, {"action": "STOP"})

        device.status = "stopped"
        db.commit()
        return jsonify({"message": f"Device {device.name} stopped"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<int:device_id>/watchdog/reset", methods=["POST"])
@jwt_required()
def reset_watchdog(device_id):
    """
    Reset watchdog timer của thiết bị.
    """
    try:
        user_id = get_jwt_identity()
        db = next(get_db())
        device = db.query(Device).filter_by(id=device_id, owner_id=user_id).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404

        device_manager.send_command(device.id, {"action": "WATCHDOG_RESET"})
        return jsonify({"message": "Watchdog reset signal sent"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_bp.route("/<int:device_id>/command", methods=["POST"])
@jwt_required()
def send_custom_command(device_id):
    """
    Gửi command tùy ý xuống thiết bị (ví dụ 'LED_ON', 'LED_OFF').
    """
    try:
        user_id = get_jwt_identity()
        db = next(get_db())
        device = db.query(Device).filter_by(id=device_id, owner_id=user_id).first()
        if not device:
            return jsonify({"error": "Device not found"}), 404

        data = request.get_json() or {}
        if "command" not in data:
            return jsonify({"error": "Missing command"}), 400

        cmd = sanitize_str(data["command"])
        device_manager.send_command(device.id, {"action": cmd})

        return jsonify({"message": f"Command '{cmd}' sent to {device.name}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
