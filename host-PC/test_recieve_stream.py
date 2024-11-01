from flask import Flask, render_template, Response, request, jsonify
import requests
import paho.mqtt.client as mqtt
import socket
import cv2
import numpy as np
import threading
import time
from flask import send_file

app = Flask(__name__)

# MQTT Configuration
mqtt_broker_address = "BROKER_IP_ADDRESS"
mqtt_broker_port = 1883

streaming = False
frames = [
    None,
    None,
    None,
    None,
    None,
    None,
]
streaming_status = [
    None,
    None,
    None,
    None,
    None,
    None,
]
recording_list = [
    False,
    False,
    False,
    False,
    False,
    False,
]

mqtt_client = mqtt.Client()
# mqtt_client.connect(mqtt_broker_address, mqtt_broker_port, 60)

def run_mqtt_client():
    global mqtt_client
    def on_connect(client, userdata, flags, rc):
        print(f"Connected with Code: {rc}")
        client.subscribe([("stream/#", 0)])

    def on_message(client, userdata, msg):
        global frame
        topic_parts = msg.topic.split("/")
        if len(topic_parts) >= 2 and topic_parts[0] == "stream":
            raspberry_pi_index = int(topic_parts[1])-1
            nparr = np.frombuffer(msg.payload, np.uint8)
            frames[raspberry_pi_index] = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif len(topic_parts) >= 2 and topic_parts[0] == "status":
            raspberry_pi_index = int(topic_parts[1])-1
            recording_list[raspberry_pi_index] = msg.payload.decode()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.loop_forever()

# mqtt_thread = threading.Thread(target=run_mqtt_client)
# mqtt_thread.daemon = True
# mqtt_thread.start()

def stream_video():
    global streaming
    while True:
        if streaming:
            mqtt_client.publish("stream_send", "send")
            time.sleep(0.1)
        else:
            pass

stream_thread = threading.Thread(target=stream_video)
stream_thread.daemon = True
stream_thread.start()

def gen(index):
    while True:
        if frames[index] is not None:
            _, buffer = cv2.imencode('.jpg', frames[index])
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            yield b''


@app.route('/')
def index():
    global streaming
    return render_template('index.html', streaming=streaming)

@app.route('/video_feed/<int:index>')
def video_feed(index):
    global streaming_status
    if streaming_status[index]:
        return Response(gen(index), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        # Return a placeholder image file when streaming is not active
        return send_file('placeholder.jpg', mimetype='image/jpeg')


@app.route('/start_stream', methods=['POST'])
def start_stream():
    global streaming
    streaming = True
    global streaming_status
    camera_indexes = request.get_json()
    camera_indexes = camera_indexes['cameras']
    print(f'camera_indexes start: {camera_indexes}')
    for index in camera_indexes:
        streaming_status[index] = True
    mqtt_client.publish("start_stream", "start")
    return jsonify(success=True)

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global frames
    global streaming
    streaming = False
    global streaming_status
    camera_indexes = request.get_json()
    camera_indexes = camera_indexes['cameras']
    print(f'camera_indexes stop: {camera_indexes}')
    for index in camera_indexes:
        streaming_status[index] = False
    mqtt_client.publish("stop_stream", "stop")
    frames = [None]*len(frames)
    return jsonify(success=True)

@app.route('/start_recording', methods=['GET'])
def start_recording():
    mqtt_client.publish("start_video", "start")
    return jsonify(success=True)

@app.route('/stop_recording', methods=['GET'])
def stop_recording():
    mqtt_client.publish("stop_video", "stop")
    return jsonify(success=True)

@app.route('/get_recording_status', methods=['GET'])
def get_recording_status():
    global recording_list  
    mqtt_client.publish("get_recording_status", "status")
    return jsonify({'recording': recording_list})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

