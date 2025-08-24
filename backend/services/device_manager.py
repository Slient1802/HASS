import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask_socketio import emit, join_room
from ..config import Config
from ..database import SessionLocal
from ..models import Device
from backend.models import Device, CommandQueue


class DeviceManager:
    """
    Device Manager: quản lý vòng đời thiết bị
    - CRUD thiết bị
    - Điều khiển thiết bị (start, stop, reset watchdog, command)
    - TDMA (slot-based scheduling)
    - FDMA (namespace channel assignment)
    - Watchdog (giám sát timeout)
    """

    def __init__(self, socketio):
        self.socketio = socketio
        self.slot_seconds = Config.TDMA_SLOT_SECONDS
        self.num_slots = Config.TDMA_NUM_SLOTS
        self.watchdog_timeout = getattr(Config, "WATCHDOG_TIMEOUT", 60)  # giây

    # ============================================================
    # CRUD: List, Get, Update, Delete
    # ============================================================

    def list_devices(self) -> List[Dict[str, Any]]:
        """Trả về danh sách tất cả thiết bị."""
        with SessionLocal() as db:
            devices = db.query(Device).all()
            return [
                {
                    "id": d.id,
                    "name": d.name,
                    "type": d.hw_type,
                    "status": d.status,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                }
                for d in devices
            ]

    def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin chi tiết của một thiết bị theo ID."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if not d:
                return None
            return {
                "id": d.id,
                "name": d.name,
                "type": d.hw_type,
                "status": d.status,
                "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            }

    def update_device(self, device_id: int, updates: Dict[str, Any]) -> bool:
        """Cập nhật thông tin thiết bị (name, type, status)."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if not d:
                return False
            if "name" in updates:
                d.name = updates["name"]
            if "type" in updates:
                d.hw_type = updates["type"]
            if "status" in updates:
                d.status = updates["status"]
            db.commit()
            return True

    def delete_device(self, device_id: int) -> bool:
        """Xóa thiết bị theo ID."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if not d:
                return False
            db.delete(d)
            db.commit()
            return True

    # ============================================================
    # Device Control
    # ============================================================

    def start_device(self, device_id: int) -> bool:
        """Gửi lệnh start xuống thiết bị."""
        ns = self._get_namespace(device_id)
        if not ns:
            return False
        self.socketio.emit("device_command", {"action": "start"}, room=ns)
        return True

    def stop_device(self, device_id: int) -> bool:
        """Gửi lệnh stop xuống thiết bị."""
        ns = self._get_namespace(device_id)
        if not ns:
            return False
        self.socketio.emit("device_command", {"action": "stop"}, room=ns)
        return True

    def reset_watchdog(self, device_id: int) -> bool:
        """Reset watchdog thủ công (cập nhật last_seen)."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if not d:
                return False
            d.last_seen = datetime.utcnow()
            db.commit()
        return True

    def send_command(self, device_id: int, command: Dict[str, Any]) -> bool:
        """Gửi command tùy ý xuống thiết bị."""
        ns = self._get_namespace(device_id)
        if not ns:
            return False
        self.socketio.emit("device_command", command, room=ns)
        return True

    # ============================================================
    # TDMA / FDMA
    # ============================================================

    def current_slot(self) -> int:
        """Trả về slot hiện tại dựa theo thời gian thực."""
        return int(time.time() // self.slot_seconds) % self.num_slots

    def slot_ok(self, device_id: int) -> bool:
        """Kiểm tra xem thiết bị có được phép truyền trong slot hiện tại không."""
        return self.current_slot() == (device_id % self.num_slots)

    def assign_namespace(self, device: Device) -> str:
        """Gán thiết bị vào một namespace (FDMA channel)."""
        channels = Config.SOCKETIO_CHANNELS
        return channels[device.id % len(channels)]

    def join_fdma_room(self, device_id: int) -> str:
        """Cho phép thiết bị tham gia đúng room tương ứng với namespace."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if not d:
                return "/ch0"
            ns = self.assign_namespace(d)
            join_room(ns)
            return ns

    def _get_namespace(self, device_id: int) -> Optional[str]:
        """Helper: lấy namespace theo device_id."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if not d:
                return None
            return self.assign_namespace(d)

    # ============================================================
    # Monitoring & Watchdog
    # ============================================================

    def touch_last_seen(self, device_id: int):
        """Cập nhật last_seen khi thiết bị gửi dữ liệu."""
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.id == device_id).first()
            if d:
                d.last_seen = datetime.utcnow()
                db.commit()

    def broadcast_schedule(self):
        """Phát tín hiệu lịch TDMA hiện tại xuống tất cả client."""
        now_slot = self.current_slot()
        self.socketio.emit(
            "schedule",
            {
                "slot_seconds": self.slot_seconds,
                "current_slot": now_slot,
                "num_slots": self.num_slots,
            },
            namespace="/",
        )

    def check_watchdog(self):
        """
        Kiểm tra thiết bị có bị timeout không.
        Nếu quá WATCHDOG_TIMEOUT giây không gửi tín hiệu → báo offline.
        """
        now = datetime.utcnow()
        timeout_delta = timedelta(seconds=self.watchdog_timeout)

        with SessionLocal() as db:
            devices = db.query(Device).all()
            for d in devices:
                if not d.last_seen:
                    continue
                if now - d.last_seen > timeout_delta:
                    self.socketio.emit(
                        "device_timeout",
                        {
                            "device_id": d.id,
                            "last_seen": d.last_seen.isoformat(),
                            "status": "offline",
                        },
                        namespace="/",
                    )


    # ============================================================
    # Heartbeat & Command ACK
    # ============================================================

    def handle_heartbeat(self, device_uid: str) -> bool:
        """
        Xử lý heartbeat từ thiết bị → cập nhật last_seen + báo online.
        """
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.device_uid == device_uid).first()
            if not d:
                return False

            d.last_seen = datetime.utcnow()
            d.status = "online"
            db.commit()

            self.socketio.emit(
                "device_status",
                {
                    "device_id": d.id,
                    "uid": d.device_uid,
                    "status": "online",
                    "last_seen": d.last_seen,
                },
                namespace="/",
            )
            return True

    def mark_command_ack(self, command_id: int) -> bool:
        """
        Đánh dấu một command trong CommandQueue đã được ACK.
        """
        from ..models import CommandQueue  # tránh circular import

        with SessionLocal() as db:
            cmd = db.query(CommandQueue).filter(CommandQueue.id == command_id).first()
            if not cmd:
                return False

            cmd.status = "ack"
            cmd.ack_time = datetime.utcnow()
            db.commit()

            self.socketio.emit(
                "command_ack",
                {
                    "command_id": cmd.id,
                    "device_id": cmd.device_id,
                    "status": "ack",
                    "ack_time": cmd.ack_time,
                },
                namespace="/",
            )
            return True

