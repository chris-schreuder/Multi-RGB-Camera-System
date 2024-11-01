from flask import Flask, render_template, Response, request, jsonify
import requests
import paho.mqtt.client as mqtt
import socket
import cv2
import numpy as np
import threading
import time
from flask import send_file
import base64
import os
from datetime import datetime
import json

app = Flask(__name__)

# MQTT Configuration
mqtt_broker_address = "BROKER_IP_ADDRESS"
mqtt_broker_port = 1883
mqtt_topic_record_publish = "record_video"
mqtt_topic_transfer_publish = "request_video_transfer"
mqtt_topic_stream_publish = "stream_frame"
mqtt_topic_calibration_publish = "calibrate_camera"
mqtt_topic_group_calibration_publish = "calibrate_group_camera"
mqtt_topic_calibration_single_publish = "calibrate_camera_single"
mqtt_topic_group_calibration_single_publish = "calibrate_group_camera_single"
mqtt_topic_sync_time_publish = "sync_time"
mqtt_topic_set_controls_publish = "set_controls"
mqtt_topic_stream = f"stream/#"
mqtt_topic_status = f"status/#"
mqtt_topic_transfered = f"transfered/#"
mqtt_topic_time_start = f'time_start/#'

streaming = False
frames = [None]*6
streaming_status = [None]*6
recording_list = [None]*6
filename = ''

mqtt_client = mqtt.Client()
mqtt_client.connect(mqtt_broker_address, mqtt_broker_port, 60)

def run_mqtt_client():
    global mqtt_client
    def on_connect(client, userdata, flags, rc):
        print(f"Connected with Code: {rc}")
        client.subscribe([(mqtt_topic_stream, 0), (mqtt_topic_status, 0), (mqtt_topic_transfered, 0), (mqtt_topic_time_start, 0)])

    def on_message(client, userdata, msg):
        global frame
        topic_parts = msg.topic.split("/")
        if len(topic_parts) >= 2 and topic_parts[0] == mqtt_topic_stream.split("/")[0]:
            raspberry_pi_index = int(topic_parts[1])-1
            nparr = np.frombuffer(msg.payload, np.uint8)
            frames[raspberry_pi_index] = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif len(topic_parts) >= 2 and topic_parts[0] == mqtt_topic_status.split("/")[0]:
            raspberry_pi_index = int(topic_parts[1])-1
            recording_list[raspberry_pi_index] = msg.payload.decode()
        elif len(topic_parts) >= 2 and topic_parts[0] == mqtt_topic_transfered.split("/")[0]:
            raspberry_pi_index = int(topic_parts[1])-1
            transfered_message = msg.payload.decode()
            print(f'Pi{raspberry_pi_index+1} -> {transfered_message}')
        elif len(topic_parts) >= 2 and topic_parts[0] == mqtt_topic_time_start.split("/")[0]:
            raspberry_pi_index = int(topic_parts[1])
            transfered_message = msg.payload.decode()
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            with open('rec_times_host.txt', 'a') as txt_file:
                txt_file.write(f'C{raspberry_pi_index}_{transfered_message}\t{current_datetime}\n')
                print(f'{transfered_message}\t{current_datetime}\n')

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.loop_forever()

mqtt_thread = threading.Thread(target=run_mqtt_client)
mqtt_thread.daemon = True
mqtt_thread.start()

def get_frame_data(index):
    if 0 <= index < len(frames) and frames[index] is not None:
        success, frame_data = cv2.imencode('.jpg', frames[index])
        if success:
            return frame_data.tobytes()

@app.route('/')
def index():
    global streaming
    return render_template('index.html', streaming=streaming)

@app.route('/sync_time', methods=['POST'])
def sync_time():
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    current_datetime = current_datetime.split('.')[0]
    message = {
        "command": "sync_time",
        "time_date": current_datetime
    }   
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_sync_time_publish, message_json)
    print(f'Sent cameras time sync {current_datetime}')
    time.sleep(1)
    return jsonify(success=True)

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global filename
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    current_datetime = current_datetime.split('.')[0]
    data = request.get_json()
    subject_number = data.get('subjectNumber')
    action_number = data.get('actionNumber')
    duration_number = data.get('durationNumber')
    filename = f'S{subject_number}A{action_number}D{duration_number}.h264'
    print(filename)
    for i in range(6):
        os.makedirs(f'videos/C{i+1}/S{subject_number}', exist_ok=True)
    message = {
        "command": "start",
        "filename": filename,
        "subject_num": subject_number,
        "current_datetime": current_datetime
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_record_publish, message_json)
    return jsonify(success=True)

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global filename
    message = {
        "command": "stop",
        "filename": filename
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_record_publish, message_json)
    return jsonify(success=True)


@app.route('/get_recording_status', methods=['GET'])
def get_recording_status():
    global recording_list  
    mqtt_client.publish(mqtt_topic_record_publish, "get_status")
    return jsonify({'recording': recording_list})

@app.route('/set_controls', methods=['POST'])
def set_controls():
    message = {
        "command": "set_controls"
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_set_controls_publish, message_json)
    return jsonify(success=True)

@app.route('/record_calibration', methods=['POST'])
def record_calibration():
    global filename
    data = request.get_json()
    subject_number = data.get('subjectNumber')
    action_number = data.get('actionNumber')
    duration_number = data.get('durationNumber')
    camera_number = data.get('cameraNumber')
    filename = f'CXS{subject_number}A{action_number}D{duration_number}_calibration.h264'
    print(f'Calibration camera {camera_number} -> {filename}')
    os.makedirs(f'videos/C{camera_number}/S{subject_number}/calibration', exist_ok=True)
    message = {
        "command": "calibrate",
        "filename": filename,
        "camera_index": camera_number,
        "subject_num": subject_number
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_calibration_publish, message_json)
    return jsonify(success=True)

@app.route('/record_group_calibration', methods=['POST'])
def record_group_calibration():
    global filename
    data = request.get_json()
    subject_number = data.get('subjectNumber')
    action_number = data.get('actionNumber')
    duration_number = data.get('durationNumber')
    camera_number = data.get('cameraNumber')
    camera_number2 = data.get('cameraNumber2')
    filename = f'CXS{subject_number}A{action_number}D{duration_number}_grouped_G{camera_number}{camera_number2}_calibration.h264'
    print(f'Calibration camera {camera_number} and {camera_number2} -> {filename}')
    os.makedirs(f'videos/C{camera_number}/S{subject_number}/calibration', exist_ok=True)
    os.makedirs(f'videos/C{camera_number2}/S{subject_number}/calibration', exist_ok=True)
    message = {
        "command": "calibrate",
        "filename": filename,
        "camera_index": camera_number,
        "camera_index2": camera_number2,
        "subject_num": subject_number
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_group_calibration_publish, message_json)
    return jsonify(success=True)

@app.route('/record_calibration_single', methods=['POST'])
def record_calibration_single():
    global filename
    data = request.get_json()
    subject_number = data.get('subjectNumber')
    action_number = data.get('actionNumber')
    duration_number = data.get('durationNumber')
    camera_number = data.get('cameraNumber')
    filename = f'CXS{subject_number}A{action_number}D{duration_number}_calibration'
    print(f'Calibration camera {camera_number} -> {filename}')
    os.makedirs(f'videos/C{camera_number}/S{subject_number}/calibration', exist_ok=True)
    message = {
        "command": "calibrate",
        "filename": filename,
        "camera_index": camera_number,
        "subject_num": subject_number
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_calibration_single_publish, message_json)
    return jsonify(success=True)

@app.route('/record_group_calibration_single', methods=['POST'])
def record_group_calibration_single():
    global filename
    data = request.get_json()
    subject_number = data.get('subjectNumber')
    action_number = data.get('actionNumber')
    duration_number = data.get('durationNumber')
    camera_number = data.get('cameraNumber')
    camera_number2 = data.get('cameraNumber2')
    filename = f'CXS{subject_number}A{action_number}D{duration_number}_grouped_G{camera_number}{camera_number2}_calibration'
    print(f'Calibration camera {camera_number} and {camera_number2} -> {filename}')
    os.makedirs(f'videos/C{camera_number}/S{subject_number}/calibration', exist_ok=True)
    os.makedirs(f'videos/C{camera_number2}/S{subject_number}/calibration', exist_ok=True)
    message = {
        "command": "calibrate",
        "filename": filename,
        "camera_index": camera_number,
        "camera_index2": camera_number2,
        "subject_num": subject_number
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_group_calibration_single_publish, message_json)
    return jsonify(success=True)

@app.route('/transfer_all', methods=['POST'])
def transfer_all():
    global filename
    data = request.get_json()
    camera_number = data.get('cameraNumber')
    print(f'Transferring all data from {camera_number}')
    message = {
        "command": "transfer_all",
        "camera_index": camera_number
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_transfer_publish, message_json)
    return jsonify(success=True)

@app.route('/transfer_video', methods=['POST'])
def transfer_video():
    global filename
    message = {
        "command": "transfer",
        "filename": filename
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_transfer_publish, message_json)
    return jsonify(success=True)

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
    mqtt_client.publish(mqtt_topic_stream_publish, "start")
    time.sleep(1)
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
    frames = [None]*len(frames)
    mqtt_client.publish(mqtt_topic_stream_publish, "stop")
    return jsonify(success=True)

@app.route('/get_frame_data/<int:index>')
def get_frame_data(index):
    global streaming
    if streaming:
        print(index)
        if index == 0:
            mqtt_client.publish(mqtt_topic_stream_publish, "get_frame")
        if 0 <= index < len(frames) and frames[index] is not None:
            image = frames[index]
            rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            success, frame_data = cv2.imencode('.jpg', rotated_image)
            if success:
                frame_data_base64 = base64.b64encode(frame_data).decode('utf-8')
                return jsonify({'frameData': frame_data_base64})
    
    return jsonify({'frameData': ''})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)