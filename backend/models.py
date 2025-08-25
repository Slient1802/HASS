# backend/models.py
from datetime import datetime
from typing import Optional, List

from flask_login import UserMixin
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base for all models."""


# === USER MODEL ===
class User(UserMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Trạng thái online
    online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    devices: Mapped[List["Device"]] = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    logs: Mapped[List["Log"]] = relationship("Log", back_populates="user", cascade="all, delete-orphan")
    commands: Mapped[List["CommandQueue"]] = relationship("CommandQueue", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} role={self.role} online={self.online}>"


# === DEVICE MODEL ===
class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # hardware UID
    # slot vật lý/ logic (string cho linh hoạt), có index để TDMA/FDMA
    slot: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # "arduino_uno" | "raspberry_pi"
    status: Mapped[str] = mapped_column(String(32), default="offline")  # offline|online|running|stopped
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    # Đã có code upload/flash chưa (để dashboard hiển thị)
    code_uploaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    code_uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped["User"] = relationship("User", back_populates="devices")

    logs: Mapped[List["Log"]] = relationship("Log", back_populates="device", cascade="all, delete-orphan")
    commands: Mapped[List["CommandQueue"]] = relationship("CommandQueue", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Device id={self.id} uid={self.device_uid} name={self.name} type={self.type} status={self.status} uploaded={self.code_uploaded}>"


# === COMMAND QUEUE MODEL ===
class CommandQueue(Base):
    __tablename__ = "command_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|sent|ack|failed|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    ack_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    device: Mapped["Device"] = relationship("Device", back_populates="commands")
    user: Mapped["User"] = relationship("User", back_populates="commands")

    def __repr__(self) -> str:
        return f"<CommandQueue id={self.id} device_id={self.device_id} status={self.status}>"

Index("ix_command_status", CommandQueue.status)

# === LOG MODEL ===
class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="logs")

    def __repr__(self) -> str:
        return f"<Log id={self.id} action={self.action}>"
