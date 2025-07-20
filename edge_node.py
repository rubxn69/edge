import socketio
import psutil
import time
import threading
import socket
import base64
import cv2
import numpy as np
from flask import Flask
import eventlet

sio = socketio.Client()
NODE_ID = "edge2"
SCHEDULER_URL = "http://172.20.10.4:5000"  # <-- Replace with your actual Scheduler IP

# Load Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def register_node():
    while True:
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            ip = get_ip()
            sio.emit("message", {
                "node_id": NODE_ID,
                "cpu_percent": cpu,
                "memory_percent": mem,
                "ip": ip
            })
        except Exception as e:
            print("Error sending status:", e)
        time.sleep(2)

# Flask server on port 5000
app = Flask(__name__)
sio_server = socketio.Server(cors_allowed_origins='*')
app.wsgi_app = socketio.WSGIApp(sio_server, app.wsgi_app)

@sio_server.on("connect")
def connect(sid, environ):
    print("Client connected to edge node")

@sio_server.on("input_frame")
def input_frame(sid, data):
    try:
        b64data = data["frame"].split(",")[1]
        timestamp = data["timestamp"]
        img_bytes = base64.b64decode(b64data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Head (face) detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        _, jpeg = cv2.imencode('.jpg', frame)
        processed_b64 = base64.b64encode(jpeg.tobytes()).decode('utf-8')
        processed_frame = f"data:image/jpeg;base64,{processed_b64}"

        sio_server.emit("output_frame", {
            "frame": processed_frame,
            "timestamp": timestamp
        }, to=sid)
    except Exception as e:
        print("Frame processing error:", e)

if __name__ == "__main__":
    # Start the Flask-SocketIO server in a thread
    threading.Thread(target=lambda: eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)).start()

    @sio.event
    def connect():
        print("Connected to scheduler")
        threading.Thread(target=register_node).start()

    @sio.event
    def disconnect():
        print("Disconnected from scheduler")

    print("Connecting to scheduler...")
    sio.connect(SCHEDULER_URL)
    sio.wait()
