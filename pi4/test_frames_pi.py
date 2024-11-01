from picamera2.outputs import FfmpegOutput
from picamera2.outputs import FileOutput
import paho.mqtt.client as mqtt
from picamera2.encoders import H264Encoder, Quality
from picamera2 import Picamera2
from libcamera import controls, Transform
import time
import os
import paramiko
import threading
import socket
import requests
import io
import json

username = "USERNAME"
password = "PASSWORD"
root_path = "ROOT_PATH"

raspberry_pi_index = "1"

mqtt_broker_address = "BROKER_IP_ADDRESS"
your_host_pc_address = "HOST_PC_IP_ADDRESS"
mqtt_port = 1883
mqtt_topic_record = "record_video"
mqtt_topic_transfer = "request_video_transfer"
mqtt_topic_stream = "stream_frame" 
mqtt_topic_calibration = "calibrate_camera"
mqtt_topic_stream_publish = f"stream/{raspberry_pi_index}"
mqtt_topic_status_publish = f"status/{raspberry_pi_index}"
mqtt_topic_transfered_publish = f"transfered/{raspberry_pi_index}"

camera = Picamera2()
preview_config = camera.create_preview_configuration(main={"size": (800, 600)})
camera.configure(preview_config)
encoder = H264Encoder()

# Track streaming state
is_streaming = False
is_recording = False
filename = ''

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with code " + str(rc))
    client.subscribe([(mqtt_topic_record, 0), (mqtt_topic_transfer, 0),
                      (mqtt_topic_stream, 0)])

def on_message(client, userdata, msg):
    global is_streaming
    global is_recording
    global filename
    print("Message received: " + msg.topic + " " + str(msg.payload.decode()))
    message = msg.payload.decode()
    try:
        message_dict = json.loads(message)
        message = message_dict.get('command')
        filename = message_dict.get('filename')
    except:
        message = message
    if msg.topic == mqtt_topic_record and message == "start":
        print("Starting video recording...")
        camera.video_configuration = camera.create_video_configuration(
            main={"size": (800, 1000)}
        )
        camera.configure("video")
        camera.set_controls({"FrameRate": 60, "AfMode": controls.AfModeEnum.Continuous})
        camera.rotation = 90
        camera.start_recording(encoder, filename, quality=Quality.VERY_HIGH)
        is_recording = True
    elif msg.topic == mqtt_topic_record and message == "stop":
        print("Stopping video recording...")
        camera.stop_recording()
        is_recording = False
        print("Stopped video recording")
    elif msg.topic == mqtt_topic_calibration and message == "calibrate":
        camera_number = message_dict.get('camera_number')
        if camera_number == raspberry_pi_index:
            print("Calibrating camera...")
            camera.set_controls({"FrameRate": 60, "AfMode": controls.AfModeEnum.Continuous})
            camera.rotation = 90
            camera.start_recording(encoder, filename, quality=Quality.VERY_HIGH)
            time.sleep(30)
            camera.stop_recording()
            print("Calibration complete.")
    elif msg.topic == mqtt_topic_transfer and message == "transfer":
        print("Transfer request received. Sending video...")
        send_video()
    elif msg.topic == mqtt_topic_stream and message == "start":
        if is_streaming == False:
            camera.start()
            send_stream_frame()
            is_streaming = True
    elif msg.topic == mqtt_topic_stream and message == "stop":
        if is_streaming == True:
            is_streaming = False
            camera.stop()
    elif msg.topic == mqtt_topic_stream and message == "get_frame":
        if is_streaming == True:
            send_stream_frame()
    elif msg.topic == mqtt_topic_record and message == "get_status":
        if is_recording:
            client.publish(mqtt_topic_status_publish, payload=True)
        else:
            client.publish(mqtt_topic_status_publish, payload=False)

def send_stream_frame():
    global client
    data = io.BytesIO()
    camera.capture_file(data, format='jpeg')
    frame_bytes = data.getvalue()  
    data.close()
    client.publish(mqtt_topic_stream_publish, payload=frame_bytes)

def send_video():
    global filename
    video_path = filename
    subject = (video_path.split("A")[0])[1:]
    if os.path.exists(video_path):
        ssh_client = paramiko.SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.connect(your_host_pc_address, username=username, password=password)
        with ssh_client.open_sftp() as sftp:
            destination_path = f'{root_path}host-PC\\videos\\C{raspberry_pi_index}\\S{subject}\\{video_path}'
            if 'calibration' in video_path:
                destination_path = f'{root_path}host-PC\\videos\\C{raspberry_pi_index}\\S{subject}\\calibration\\{video_path}'
            sftp.put(video_path, destination_path)
        ssh_client.close()
        print("Video sent.")
        client.publish(mqtt_topic_transfered_publish, "transfered successfully: " + video_path)
    else:
        print("Video file not found.")
        client.publish(mqtt_topic_transfered_publish, "transfered failed: " + video_path)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqtt_broker_address, mqtt_port, 60)

client.loop_forever()