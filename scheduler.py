import socketio
from flask import Flask, send_from_directory
import eventlet
import threading

sio = socketio.Server(cors_allowed_origins='*')
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

edge_nodes = {}

@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
def disconnect(sid):
    for node_id, info in list(edge_nodes.items()):
        if info["sid"] == sid:
            del edge_nodes[node_id]
            print(f"{node_id} disconnected")

@sio.event
def message(sid, data):
    if isinstance(data, dict):
        edge_nodes[data["node_id"]] = {
            "sid": sid,
            "cpu": data["cpu_percent"],
            "memory": data["memory_percent"],
            "ip": data["ip"]
        }

@sio.event
def start(sid):
    best = select_best_node()
    if best:
        node_id, info = best
        sio.emit("best_node", {
            "node_id": node_id,
            "cpu": info["cpu"],
            "memory": info["memory"],
            "ip": info["ip"]
        }, to=sid)

def select_best_node():
    best = None
    best_score = float('inf')
    for node_id, info in edge_nodes.items():
        score = 0.6 * info["cpu"] + 0.4 * info["memory"]
        if score < best_score:
            best_score = score
            best = (node_id, info)
    return best

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    print("Server running at http://0.0.0.0:5000")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)
