import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from flask_socketio import join_room
from backend.config import Config
from backend.database import SessionLocal
from backend.models import Device, User, CommandQueue
from backend.extensions import socketio


class DeviceManager:
    """Quản lý thiết bị + TDMA/FDMA + Watchdog + Queue."""

    def __init__(self) -> None:
        self.slot_seconds = Config.TDMA_SLOT_SECONDS
        self.num_slots = Config.TDMA_NUM_SLOTS
        self.watchdog_timeout = getattr(Config, "WATCHDOG_TIMEOUT", 60)

    # ========= USER PRESENCE =========
    def set_user_online(self, user_id: int) -> None:
        with SessionLocal() as db:
            u = db.get(User, user_id)
            if not u:
                return
            u.online = True
            u.last_seen = datetime.utcnow()
            db.commit()

    def set_user_offline(self, user_id: int) -> None:
        with SessionLocal() as db:
            u = db.get(User, user_id)
            if not u:
                return
            u.online = False
            u.last_seen = datetime.utcnow()
            db.commit()

    # ========= DEVICE CRUD HELPERS =========
    def touch_last_seen(self, device_uid: str) -> None:
        with SessionLocal() as db:
            d = db.query(Device).filter_by(device_uid=device_uid).first()
            if d:
                d.last_seen = datetime.utcnow()
                db.commit()

    def mark_code_uploaded(self, device_id: int, uploaded: bool) -> None:
        with SessionLocal() as db:
            d = db.get(Device, device_id)
            if d:
                d.code_uploaded = uploaded
                d.code_uploaded_at = datetime.utcnow() if uploaded else None
                db.commit()

    # ========= SNAPSHOT for dashboard =========
    def get_status_snapshot(self) -> Dict[str, Any]:
        with SessionLocal() as db:
            users = db.query(User).all()
            devices = db.query(Device).all()
            q = (
                db.query(CommandQueue)
                .order_by(CommandQueue.created_at.desc())
                .limit(50)
                .all()
            )
            return {
                "users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "online": u.online,
                        "last_seen": u.last_seen.isoformat() if u.last_seen else None,
                    }
                    for u in users
                ],
                "devices": [
                    {
                        "id": d.id,
                        "device_uid": d.device_uid,
                        "name": d.name,
                        "type": d.type,  # ✅ FIX: use .type not .hw_type
                        "status": d.status,
                        "code_uploaded": d.code_uploaded,
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    }
                    for d in devices
                ],
                "queue": [
                    {
                        "id": c.id,
                        "device_id": c.device_id,
                        "user_id": c.user_id,
                        "command": c.command,
                        "status": c.status,
                        "created_at": c.created_at.isoformat(),
                        "sent_at": c.sent_at.isoformat() if c.sent_at else None,
                        "ack_time": c.ack_time.isoformat() if c.ack_time else None,
                    }
                    for c in q
                ],
            }

    # ========= TDMA / FDMA =========
    def current_slot(self) -> int:
        """Trả về slot hiện tại dựa theo thời gian thực."""
        return int(time.time() // self.slot_seconds) % self.num_slots

    def slot_ok(self, device: Device) -> bool:
        """Kiểm tra xem thiết bị có được phép truyền trong slot hiện tại không."""
        if not device.slot:
            return True
        try:
            return self.current_slot() == (int(device.slot) % self.num_slots)
        except ValueError:
            return True

    def assign_namespace(self, device: Device) -> str:
        channels = Config.SOCKETIO_CHANNELS
        idx = device.id % len(channels)
        return channels[idx]

    def join_fdma_room(self, device_id: int) -> str:
        with SessionLocal() as db:
            d = db.get(Device, device_id)
            if not d:
                return "/ch0"
            ns = self.assign_namespace(d)
            join_room(ns)
            return ns

    def _get_namespace(self, device_id: int) -> Optional[str]:
        with SessionLocal() as db:
            d = db.get(Device, device_id)
            if not d:
                return None
            return self.assign_namespace(d)

    # ========= CONTROL / QUEUE =========
    def enqueue_command(self, device_id: int, user_id: int, command: str) -> int:
        with SessionLocal() as db:
            cmd = CommandQueue(
                device_id=device_id,
                user_id=user_id,
                command=command,
                status="pending",
            )
            db.add(cmd)
            db.commit()
            return cmd.id

    def send_command(self, device_id: int, user_id: int, command: str) -> bool:
        """Gửi command ngay lập tức xuống thiết bị + lưu queue."""
        ns = self._get_namespace(device_id)
        if not ns:
            return False

        with SessionLocal() as db:
            cmd = CommandQueue(
                device_id=device_id,
                user_id=user_id,
                command=command,
                status="sent",
                sent_at=datetime.utcnow(),
            )
            db.add(cmd)
            db.commit()

            socketio.emit(
                "device_command",
                {"id": cmd.id, "cmd": cmd.command, "user_id": user_id},
                to=ns,
            )
        return True

    def dispatch_pending_for_device(self, device_id: int) -> int:
        """Gửi lệnh pending → socket, đổi trạng thái sent + sent_at."""
        with SessionLocal() as db:
            pending = (
                db.query(CommandQueue)
                .filter_by(device_id=device_id, status="pending")
                .order_by(CommandQueue.created_at.asc())
                .all()
            )
            count = 0
            ns = self._get_namespace(device_id)
            if not ns:
                return 0
            for c in pending:
                socketio.emit("device_command", {"id": c.id, "cmd": c.command}, to=ns)
                c.status = "sent"
                c.sent_at = datetime.utcnow()
                db.commit()
                count += 1
            return count

    def mark_command_ack(self, command_id: int) -> bool:
        with SessionLocal() as db:
            c = db.get(CommandQueue, command_id)
            if not c:
                return False
            c.status = "ack"
            c.ack_time = datetime.utcnow()
            db.commit()

            socketio.emit(
                "command_ack",
                {
                    "command_id": c.id,
                    "device_id": c.device_id,
                    "status": c.status,
                    "ack_time": c.ack_time if c.ack_time else None,
                },
                namespace="/",
            )
            return True

    def start_device(self, device_id: int) -> bool:
        return self.send_command(device_id, 0, "start")

    def stop_device(self, device_id: int) -> bool:
        return self.send_command(device_id, 0, "stop")

    def reset_watchdog(self, device_id: int) -> bool:
        with SessionLocal() as db:
            d = db.get(Device, device_id)
            if not d:
                return False
            d.last_seen = datetime.utcnow()
            db.commit()
        return True

    # ========= HEARTBEAT & WATCHDOG =========
    def handle_heartbeat(self, device_uid: str) -> bool:
        with SessionLocal() as db:
            d = db.query(Device).filter(Device.device_uid == device_uid).first()
            if not d:
                return False
            d.last_seen = datetime.utcnow()
            d.status = "online"
            db.commit()

            socketio.emit(
                "device_status",
                {
                    "device_id": d.id,
                    "uid": d.device_uid,
                    "type": d.type,  # ✅ FIX here too
                    "status": "online",
                    "last_seen": d.last_seen if d.last_seen else None,
                },
                namespace="/",
            )
            return True

    def check_watchdog(self) -> None:
        now = datetime.utcnow()
        timeout_delta = timedelta(seconds=self.watchdog_timeout)

        with SessionLocal() as db:
            devices = db.query(Device).all()
            for d in devices:
                if not d.last_seen:
                    continue
                if now - d.last_seen > timeout_delta and d.status != "offline":
                    d.status = "offline"
                    db.commit()
                    socketio.emit(
                        "device_timeout",
                        {
                            "device_id": d.id,
                            "uid": d.device_uid,
                            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                            "status": "offline",
                        },
                        namespace="/",
                    )
