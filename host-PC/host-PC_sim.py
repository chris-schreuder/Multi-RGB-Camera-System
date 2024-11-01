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

def start_recording(s, a, d):
    global filename
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    current_datetime = current_datetime.split('.')[0]
    subject_number = s
    action_number = a
    duration_number = d
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

def stop_recording():
    global filename
    message = {
        "command": "stop",
        "filename": filename
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_record_publish, message_json)

def set_controls():
    message = {
        "command": "set_controls"
    }
    message_json = json.dumps(message)
    mqtt_client.publish(mqtt_topic_set_controls_publish, message_json)


if __name__ == '__main__':
    # set_controls()
    for s in range(2,6):
        for a in range(1,10):
            for d in range(1,4):
                print(f'Recording: S{s}A{a}D{d}')
                time.sleep(30)
                start_recording(s, a, d)
                time.sleep(45)
                stop_recording()
    time.sleep(900)