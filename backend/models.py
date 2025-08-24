# backend/models.py
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime

from flask_login import UserMixin
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
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

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    logs: Mapped[list["Log"]] = relationship("Log", back_populates="user", cascade="all, delete-orphan")
    commands: Mapped[list["CommandQueue"]] = relationship("CommandQueue", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} role={self.role}>"


# === DEVICE MODEL ===
class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # hardware UID
    slot: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # e.g., physical slot/port
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hw_type: Mapped[str] = mapped_column(String(64), nullable=False)   # ✅ renamed from type → hw_type
    status: Mapped[str] = mapped_column(String(32), default="offline")
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped["User"] = relationship("User", back_populates="devices")

    logs: Mapped[list["Log"]] = relationship("Log", back_populates="device", cascade="all, delete-orphan")
    commands: Mapped[list["CommandQueue"]] = relationship("CommandQueue", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Device id={self.id} uid={self.device_uid} name={self.name} hw_type={self.hw_type} status={self.status}>"




# === COMMAND QUEUE MODEL ===
class CommandQueue(Base):
    __tablename__ = "command_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ack_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # ✅ add this

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    device: Mapped["Device"] = relationship("Device", back_populates="commands")
    user: Mapped["User"] = relationship("User", back_populates="commands")

    def __repr__(self) -> str:
        return f"<CommandQueue id={self.id} device_id={self.device_id} status={self.status}>"


# === LOG MODEL ===
class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="logs")

    def __repr__(self) -> str:
        return f"<Log id={self.id} action={self.action}>"
