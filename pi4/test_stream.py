import paho.mqtt.client as mqtt
from picamera2.encoders import H264Encoder
from picamera2 import Picamera2
import time
import os
import paramiko
import threading

username = "USERNAME"
password = "PASSWORD"
root_path = "ROOT_PATH"

# MQTT topics
mqtt_broker_address = "BROKER_IP_ADDRESS"
your_host_pc_address = "HOST_PC_IP_ADDRESS"
mqtt_port = 1883
mqtt_topic_start = "start_video"
mqtt_topic_stop = "stop_video"
mqtt_topic_transfer = "request_video_transfer"
mqtt_topic_stream_start = "start_stream"  # New MQTT topic to start streaming
mqtt_topic_stream_stop = "stop_stream"    # New MQTT topic to stop streaming

# Camera and encoder setup
camera = Picamera2()
preview_config = camera.create_preview_configuration(main={"size": (800, 600)})
camera.configure(preview_config)
encoder = H264Encoder()
camera.start_preview() 


# SSH tunnel setup
ssh_client = paramiko.SSHClient()
ssh_client.load_system_host_keys()
ssh_client.connect(your_host_pc_address, username=username, password=password)

# Track streaming state
is_streaming = False

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with code " + str(rc))
    client.subscribe([(mqtt_topic_start, 0), (mqtt_topic_stop, 0), (mqtt_topic_transfer, 0),
                      (mqtt_topic_stream_start, 0), (mqtt_topic_stream_stop, 0)])

def on_message(client, userdata, msg):
    global is_streaming
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
    elif msg.topic == mqtt_topic_stream_start and message == "start":
        if not is_streaming:
            print("Starting video streaming...")
            start_stream()
    elif msg.topic == mqtt_topic_stream_stop and message == "stop":
        if is_streaming:
            print("Stopping video streaming...")
            stop_stream()

def start_stream():
    global is_streaming
    is_streaming = True

def stop_stream():
    global is_streaming
    is_streaming = False

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

def stream_frame():
    image_path = 'output_image.jpg'
    if os.path.exists(image_path):
        ssh_client = paramiko.SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.connect(your_host_pc_address, username=username, password=password)
        with ssh_client.open_sftp() as sftp:
            destination_path = f'{root_path}videos\frame.jpg'
            sftp.put(image_path, destination_path)
        ssh_client.close()
        print("Frame sent.")
    else:
        print("Image file not found.")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_broker_address, mqtt_port, 60)

def stream():
    print('stream')
    global is_streaming
    global camera
    try:
        while True:
            if is_streaming:
                camera.start_and_capture_file("output_image.jpg")
                stream_frame()
            time.sleep(0.07)
    except Exception as e:
        print(f"Stream thread error: {e}")


stream_thread = threading.Thread(target=stream)
stream_thread.start()

def mqtt_thread_code():
    print('mqtt_thread')
    global client
    try:
        client.loop_forever()
    except Exception as e:
        print(f"MQTT thread error: {e}")

mqtt_thread = threading.Thread(target=mqtt_thread_code)
mqtt_thread.start()

mqtt_thread.join()
stream_thread.join()