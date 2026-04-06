from flask import Flask, jsonify, render_template
import threading

app = Flask(__name__, static_folder='static', template_folder='static')

_controller = None

def set_controller(ctrl):
    global _controller
    _controller = ctrl

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/events')
def get_events():
    if _controller is None:
        return jsonify([])
    return jsonify(_controller.get_events())

@app.route('/api/topology')
def get_topology():
    if _controller is None:
        return jsonify({"nodes": [], "edges": []})
    return jsonify(_controller.get_topology_data())

def launch_dashboard(ctrl):
    set_controller(ctrl)
    t = threading.Thread(target=lambda: app.run(
        host='0.0.0.0', port=5000, debug=False, use_reloader=False
    ), daemon=True)
    t.start()