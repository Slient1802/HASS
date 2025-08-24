# backend/sanitizer.py
import re
import html
from typing import Optional


def sanitize_str(value, default: str = "", max_length: int | None = None) -> str:
    """
    Clean a string input:
    - fallback to default if value is None or not str
    - trim whitespace
    - cut off if longer than max_length
    """
    if not isinstance(value, str):
        return default
    value = value.strip()
    if max_length is not None:
        value = value[:max_length]
    return value or default



def sanitize_uid(uid: Optional[str]) -> str:
    """
    Làm sạch UID thiết bị:
    - Chỉ cho phép chữ cái, số, dấu gạch ngang/underscore
    """
    if not uid:
        return ""
    uid = str(uid).strip()
    uid = re.sub(r"[^a-zA-Z0-9_\-]", "", uid)
    return uid


def sanitize_username(username: Optional[str]) -> str:
    """
    Làm sạch username (chỉ cho phép chữ cái, số, underscore)
    """
    if not username:
        return ""
    username = str(username).strip()
    username = re.sub(r"[^a-zA-Z0-9_]", "", username)
    return username


def sanitize_command(command: Optional[str], max_length: int = 512) -> str:
    """
    Làm sạch lệnh gửi xuống thiết bị:
    - Escape HTML
    - Loại bỏ ký tự nguy hiểm (;, |, &&, ..)
    """
    if not command:
        return ""
    command = str(command).strip()
    command = html.escape(command)
    command = re.sub(r"[;&|`$><]", "", command)
    if len(command) > max_length:
        command = command[:max_length]
    return command


def sanitize_int(value, default: int = 0,
                 min_value: Optional[int] = None,
                 max_value: Optional[int] = None) -> int:
    try:
        ivalue = int(value)
    except (ValueError, TypeError):
        return default

    if min_value is not None and ivalue < min_value:
        return min_value
    if max_value is not None and ivalue > max_value:
        return max_value
    return ivalue


def sanitize_float(value,
                   default: float = 0.0,
                   min_value: Optional[float] = None,
                   max_value: Optional[float] = None) -> float:
    try:
        fvalue = float(value)
    except (ValueError, TypeError):
        return default

    if min_value is not None and fvalue < min_value:
        return min_value
    if max_value is not None and fvalue > max_value:
        return max_value
    return fvalue