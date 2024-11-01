import paho.mqtt.client as mqtt
from picamera2.encoders import H264Encoder
from picamera2 import Picamera2
import time
import os
import paramiko

username = "USERNAME"
password = "PASSWORD"
root_path = "ROOT_PATH"

mqtt_broker_address = "BROKER_IP_ADDRESS" 
your_host_pc_address = "HOST_PC_IP_ADDRESS"
mqtt_port = 1883  
mqtt_topic_start = "start_video"
mqtt_topic_stop = "stop_video"
mqtt_topic_transfer = "request_video_transfer"

camera = Picamera2()
encoder = H264Encoder()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with code " + str(rc))
    client.subscribe([(mqtt_topic_start, 0), (mqtt_topic_stop, 0), (mqtt_topic_transfer, 0)])

def on_message(client, userdata, msg):
    print("Message received: " + msg.topic + " " + str(msg.payload.decode()))
    message = msg.payload.decode()
    if msg.topic == mqtt_topic_start and message == "start":
        print("Starting video recording...")
        camera.start_recording(encoder, 'output_video.h264')
    elif msg.topic == mqtt_topic_stop and message == "stop":
        print("Stopping video recording...")
        camera.stop_recording()
        print("Stopped video recording")
    elif msg.topic == mqtt_topic_transfer and message == "transfer":
        print("Transfer request received. Sending video...")
        send_video()

def send_video():
    video_path = 'output_video.h264'
    if os.path.exists(video_path):
        ssh_client = paramiko.SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.connect(your_host_pc_address, username=username, password=password)
        with ssh_client.open_sftp() as sftp:
            destination_path = f'{root_path}videos\video.h264'
            sftp.put(video_path, destination_path)
        ssh_client.close()
        print("Video sent.")
    else:
        print("Video file not found.")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqtt_broker_address, mqtt_port, 60)

client.loop_forever()
