import socketio
import time
import requests

sio = socketio.Client()
DEVICE_UID = "pi-001"   # đổi theo DB

@sio.event
def connect():
    print("Connected to server")
    # gửi heartbeat định kỳ ở thread khác hoặc đơn giản ở đây
    sio.emit("device_heartbeat", {"device_uid": DEVICE_UID})

@sio.on("device_command")
def on_device_command(data):
    print("Received command:", data)
    cmd_id = data.get("id")
    cmd = (data.get("cmd") or data.get("action") or "").lower()

    # TODO: thực thi phần cứng (GPIO/Serial)
    # ví dụ test:
    if cmd in ("start", "stop", "led_on", "led_off", "watchdog_reset"):
        time.sleep(0.5)  # giả lập
        if cmd_id:
            sio.emit("device_command_ack", {"device_uid": DEVICE_UID, "command_id": cmd_id})

def main():
    sio.connect("http://<SERVER-IP>:5000", transports=["websocket"])
    try:
        while True:
            time.sleep(3)
            sio.emit("device_heartbeat", {"device_uid": DEVICE_UID})
    except KeyboardInterrupt:
        pass
    finally:
        sio.disconnect()

if __name__ == "__main__":
    main()
