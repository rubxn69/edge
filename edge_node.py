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
SCHEDULER_URL = "http://172.20.10.4:5000"

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def get_usage():
    return {
        "node_id": NODE_ID,
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "ip": get_ip()
    }

def send_usage():
    while True:
        sio.emit("message", get_usage())
        time.sleep(3)

@sio.event
def connect():
    print("Connected to scheduler")
    threading.Thread(target=send_usage, daemon=True).start()

@sio.event
def disconnect():
    print("Disconnected from scheduler")

sio.connect(SCHEDULER_URL)

# Edge Node Frame Processor
flask_app = Flask(__name__)
edge_sio = socketio.Server(cors_allowed_origins='*')
flask_app.wsgi_app = socketio.WSGIApp(edge_sio, flask_app.wsgi_app)

@edge_sio.event
def connect(sid, environ):
    print(f"Web client connected: {sid}")

@edge_sio.event
def disconnect(sid):
    print(f"Web client disconnected: {sid}")

@edge_sio.event
def input_frame(sid, data_url):
    header, encoded = data_url.split(",", 1)
    frame = base64.b64decode(encoded)
    np_arr = np.frombuffer(frame, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Process image here (example: draw text)
    cv2.putText(img, "Edge Processed", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    _, buffer = cv2.imencode('.jpg', img)
    b64_output = base64.b64encode(buffer).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{b64_output}"
    edge_sio.emit("output_frame", data_url, to=sid)

if __name__ == '__main__':
    print("Edge node ready at port 6000")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 6000)), flask_app)
