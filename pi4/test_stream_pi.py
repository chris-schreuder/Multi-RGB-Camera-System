from picamera2.outputs import FfmpegOutput
from picamera2.outputs import FileOutput
import paho.mqtt.client as mqtt
from picamera2.encoders import H264Encoder, Quality
from picamera2 import Picamera2, MappedArray, Preview
from libcamera import controls, Transform
import time
import os
import paramiko
import threading
import socket
import requests
import io
import json
import ntplib
from time import ctime
from glob import glob
from fastprogress import progress_bar
import shutil
import subprocess
from datetime import datetime
import ntplib
from time import ctime

username = "USERNAME"
password = "PASSWORD"
root_path = "ROOT_PATH"

def get_router_time(router_ip):
    client = ntplib.NTPClient()
    try:
        response = client.request(router_ip, version=3)
        return ctime(response.tx_time)
    except Exception as e:
        print(f"Could not get time from router: {e}")
        return None
    
file = glob('/home/p*/*.py')
print(file)
raspberry_pi_index = file[0].split('/')[2][-1]
print(f'Running pi {raspberry_pi_index}')

# raspberry_pi_index = "1"

mqtt_broker_address = "BRIDGE_IP_ADDRESS"
your_host_pc_address = "HOST_PC_IP_ADDRESS"
mqtt_port = 1883
mqtt_topic_record = "record_video"
mqtt_topic_transfer = "request_video_transfer"
mqtt_topic_stream = "stream_frame" 
mqtt_topic_calibration = "calibrate_camera"
mqtt_topic_group_calibration = "calibrate_group_camera"
mqtt_topic_calibration_single = "calibrate_camera_single"
mqtt_topic_group_calibration_single = "calibrate_group_camera_single"
mqtt_topic_sync_time = "sync_time"
mqtt_topic_set_controls = "set_controls"
mqtt_topic_stream_publish = f"stream/{raspberry_pi_index}"
mqtt_topic_status_publish = f"status/{raspberry_pi_index}"
mqtt_topic_transfered_publish = f"transfered/{raspberry_pi_index}"
mqtt_topic_time_start_publish = f"time_start/{raspberry_pi_index}"

# size_img = (1800, 1200)
# size_img = (2304, 1296)
size_img = (1800,1150)
set_controls = None

camera = Picamera2()
preview_config = camera.create_preview_configuration(main={"size": size_img})
camera.configure(preview_config)
encoder = H264Encoder()

# Track streaming state
is_streaming = False
is_recording = False
filename = ''
filename_save = ''

def get_online_time():
    try:
        response = requests.get('http://worldtimeapi.org/api/ip')
        response.raise_for_status()  

        data = response.json()
        utc_time = data['utc_datetime']
        print(f"Universal Time (UTC): {utc_time}")
        return utc_time

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return 'TimeSyncFailed'

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with code " + str(rc))
    client.subscribe([(mqtt_topic_record, 0), (mqtt_topic_transfer, 0),
                      (mqtt_topic_stream, 0), (mqtt_topic_calibration, 0), 
                      (mqtt_topic_sync_time, 0), (mqtt_topic_group_calibration, 0),
                      (mqtt_topic_calibration_single, 0), (mqtt_topic_group_calibration_single, 0),
                      (mqtt_topic_set_controls, 0)])

def on_message(client, userdata, msg):
    global is_streaming
    global is_recording
    global filename
    global filename_save
    global set_controls
    global subject_num
    print("Message received: " + msg.topic + " " + str(msg.payload.decode()))
    message = msg.payload.decode()
    try:
        message_dict = json.loads(message)
        message = message_dict.get('command')
        filename = message_dict.get('filename')
        subject_num = 'None'
        if 'subject_num' in message_dict:
            subject_num = message_dict['subject_num']
    except:
        message = message
    if msg.topic == mqtt_topic_set_controls:
        camera.stop()
        preview_config = camera.create_preview_configuration(main={"size": size_img})
        camera.configure(preview_config)
        camera.start()
        time.sleep(5)
        metadata = camera.capture_metadata()
        controls = {c: metadata[c] for c in ["ExposureTime", "AnalogueGain", "ColourGains", "LensPosition"]}
        set_controls = controls
        print(f'Controls: {controls}')
        camera.set_controls(controls)
        camera.set_controls({"LensPosition": 0.5})
        time.sleep(5)
        camera.stop()
    elif msg.topic == mqtt_topic_record and message == "start":
        print("Starting video recording...")
        camera.video_configuration = camera.create_video_configuration(
            main={"size": size_img}
        )
        camera.configure("video")
        camera.set_controls({"FrameRate": 60})
        camera.set_controls(set_controls)
        camera.set_controls({"LensPosition": 0.5})
        camera.options["quality"] = 95
        os.makedirs(f'data/C{raspberry_pi_index}S{subject_num}/', exist_ok=True)
        filename_save = f'data/C{raspberry_pi_index}S{subject_num}/C{raspberry_pi_index}{filename}'
        date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        date_time = message_dict.get('current_datetime')
        with open(f'data/C{raspberry_pi_index}S{subject_num}/rec_times.txt', 'a') as txt_file:
            txt_file.write(f'{filename_save}\t{date_time}\n')
        camera.start_recording(encoder, filename_save, pts=f'{filename_save.replace(".h264", "")}.txt')
        client.publish(mqtt_topic_time_start_publish, f"{filename_save}")
        print(f'{filename_save}\t{date_time}\n')
        is_recording = True
    elif msg.topic == mqtt_topic_record and message == "stop":
        print("Stopping video recording...")
        camera.stop_recording()
        is_recording = False
        print("Stopped video recording")
    elif msg.topic == mqtt_topic_calibration and message == "calibrate":
        camera_number = message_dict.get('camera_index')
        if str(camera_number) == str(raspberry_pi_index):
            print("Calibrating camera...")
            camera.video_configuration = camera.create_video_configuration(
                main={"size": size_img}
            )
            camera.configure("video")
            camera.set_controls({"FrameRate": 60})
            camera.rotation = 90
            camera.set_controls(set_controls)
            camera.set_controls({"LensPosition": 0.5})
            os.makedirs(f'data/C{raspberry_pi_index}S{subject_num}/', exist_ok=True)
            filename_save = filename.replace('CX', f'C{raspberry_pi_index}')
            filename_save = f'data/C{raspberry_pi_index}S{subject_num}/{filename_save}'
            camera.start_recording(encoder, filename_save, quality=Quality.VERY_HIGH)
            time.sleep(35)
            camera.stop_recording()
            print("Calibration complete.")
    elif msg.topic == mqtt_topic_calibration_single and message == "calibrate":
        camera_number = message_dict.get('camera_index')
        if str(camera_number) == str(raspberry_pi_index):
            print("Calibrating camera...")
            camera.still_configuration = camera.create_still_configuration(
                main={"size": size_img}
            )
            camera.set_controls(set_controls)
            camera.set_controls({"LensPosition": 0.5})
            camera.start()
            camera.options["quality"] = 95
            filename_save = filename.replace('CX', f'C{raspberry_pi_index}')
            os.makedirs(f'data/C{raspberry_pi_index}S{subject_num}/', exist_ok=True)
            # os.makedirs(filename_save, exist_ok=True)
            files = glob(f'data/C{raspberry_pi_index}S{subject_num}/C{raspberry_pi_index}{filename_save}/*.jpg')
            # If there are files in the directory, get the last file and increment the number
            if len(files) > 0:
                filename_save = f'{filename_save}/{filename}_{"{0:0=4d}".format(len(files)+1)}.jpg'
            else:
                filename_save = f'{filename_save}/{filename}_0001.jpg'
            filename_save = f'data/C{raspberry_pi_index}S{subject_num}/{filename_save}'
            camera.start_and_capture_file(filename_save)
            print(f"Image {filename_save} captured.")
            camera.stop()
    elif msg.topic == mqtt_topic_group_calibration and message == "calibrate":
        camera_number = message_dict.get('camera_index')
        camera_number2 = message_dict.get('camera_index2')
        if ((str(camera_number) in ['1', '6']) and (str(raspberry_pi_index) == str(camera_number2))) or ((str(raspberry_pi_index) in ['1']) and (str(camera_number2) in ['2', '3'])) or ((str(raspberry_pi_index) in ['6']) and (str(camera_number2) in ['4', '5'])):

            print(f"Group {camera_number} calibration...")
            camera.video_configuration = camera.create_video_configuration(
                main={"size": size_img}
            )
            camera.configure("video")
            camera.set_controls({"FrameRate": 60})
            camera.set_controls(set_controls)
            camera.options["quality"] = 95
            camera.set_controls({"LensPosition": 0.5})
            os.makedirs(f'data/C{raspberry_pi_index}S{subject_num}/', exist_ok=True)
            filename_save = filename.replace('CX', f'C{raspberry_pi_index}')
            filename_save = f'data/C{raspberry_pi_index}S{subject_num}/{filename_save}'
            camera.start_recording(encoder, filename_save, quality=Quality.VERY_HIGH)
            time.sleep(35)
            camera.stop_recording()
            print("Calibration complete.")
    elif msg.topic == mqtt_topic_group_calibration_single and message == "calibrate":
        camera_number = message_dict.get('camera_index')
        camera_number2 = message_dict.get('camera_index2')
        if ((str(camera_number) in ['1', '6']) and (str(raspberry_pi_index) == str(camera_number2))) or ((str(raspberry_pi_index) in ['1']) and (str(camera_number2) in ['2', '3'])) or ((str(raspberry_pi_index) in ['6']) and (str(camera_number2) in ['4', '5'])):
            print(f"Group {camera_number} calibration...")
            camera.still_configuration = camera.create_still_configuration(
                main={"size": size_img}
            )
            camera.set_controls(set_controls)
            camera.set_controls({"LensPosition": 0.5})
            camera.start()
            camera.options["quality"] = 95
            filename_save = filename.replace('CX', f'C{raspberry_pi_index}')
            os.makedirs(f'data/C{raspberry_pi_index}S{subject_num}/{filename_save}/', exist_ok=True)
            # os.makedirs(filename_save, exist_ok=True)
            files = glob(f'data/C{raspberry_pi_index}S{subject_num}/{filename_save}/*.jpg')
            # If there are files in the directory, get the last file and increment the number
            if len(files) > 0:
                filename_save = f'{filename_save}/{filename_save}_{"{0:0=4d}".format(len(files)+1)}.jpg'
            else:
                filename_save = f'{filename_save}/{filename_save}_0001.jpg'
            filename_save = f'data/C{raspberry_pi_index}S{subject_num}/{filename_save}'
            camera.start_and_capture_file(filename_save)
            print(f"Image {filename_save} captured.")
            time.sleep(0.5)
            camera.stop()
    elif msg.topic == mqtt_topic_transfer and message == "transfer":
        print("Transfer request received. Sending video...")
        # send_video()
    elif msg.topic == mqtt_topic_transfer and message == "transfer_all":
        camera_number = message_dict.get('camera_index')
        if str(camera_number) == str(raspberry_pi_index):
            print("Transfer request received. Sending data...")
            # send_all()
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
    global preview_config 
    data = io.BytesIO()
    camera.capture_file(data, format='jpeg')
    frame_bytes = data.getvalue()  
    data.close()
    client.publish(mqtt_topic_stream_publish, payload=frame_bytes)

# def send_video():
#     global filename_save
#     global subject_num
#     video_path = filename_save
#     subject = (video_path.split("A")[0])[1:]
#     if os.path.exists(video_path):
#         ssh_client = paramiko.SSHClient()
#         ssh_client.load_system_host_keys()
#         ssh_client.connect(your_host_pc_address, username=username, password=password, look_for_keys=False)
#         with ssh_client.open_sftp() as sftp:
#             destination_path = f'{root_path}host-PC\\videos\\C{raspberry_pi_index}\\S{subject}\\{video_path}'
#             if 'calibration' in video_path:
#                 destination_path = f'{root_path}host-PC\\videos\\C{raspberry_pi_index}\\S{subject}\\calibration\\{video_path}'
#             sftp.put(video_path, destination_path)
#             os.remove(video_path)
#             if 'calibration' not in video_path:
#                 destination_path = f'{root_path}host-PC\\videos\\C{raspberry_pi_index}\\S{subject}\\{filename_save.replace(".h264", "")}.txt'
#                 sftp.put(f'{filename_save.replace(".h264", "")}.txt', destination_path)
#                 os.remove(f'{filename_save.replace(".h264", "")}.txt')
#         ssh_client.close()
#         print("Video sent.")
#         client.publish(mqtt_topic_transfered_publish, "transfered successfully: " + video_path)
#     else:
#         print("Video file not found.")
#         client.publish(mqtt_topic_transfered_publish, "transfered failed: " + video_path)

# # def send_all():
# #     mount_path = glob(f'/media/pi{raspberry_pi_index}/*/')[0]
# #     if raspberry_pi_index in ['1']:
# #         mount_path = glob(f'/media/pi{raspberry_pi_index}/*/')[1]
# #     all_files = glob(f'*.h264')
# #     for video_path in progress_bar(all_files):
# #         print(video_path)
# #         subject = (video_path.split("A")[0])[1:]
# #         if os.path.exists(video_path):
# #             destination_path = f'{mount_path}/videos/C{raspberry_pi_index}/S{subject}/{video_path}'
# #             if 'calibration' in video_path:
# #                 destination_path = f'{mount_path}/videos/C{raspberry_pi_index}/S{subject}/calibration/{video_path}'
# #             destination_dir = os.path.dirname(destination_path)
# #             if not os.path.exists(destination_dir):
# #                 os.makedirs(destination_dir)
# #             shutil.copy(video_path, destination_path)
# #             os.remove(video_path)
# #             if 'calibration' not in video_path:
# #                 # destination_path = f'videos/C{raspberry_pi_index}/S{subject}/{video_path.replace(".h264", "")}.txt'
# #                 destination_path = destination_path.replace(".h264", ".txt")
# #                 destination_dir = os.path.dirname(destination_path)
# #                 if not os.path.exists(destination_dir):
# #                     os.makedirs(destination_dir)
# #                 shutil.copy(f'{video_path.replace(".h264", "")}.txt', destination_path)
# #                 os.remove(f'{video_path.replace(".h264", "")}.txt')
# #             client.publish(mqtt_topic_transfered_publish, "transfered successfully: " + video_path)
# #         else:
# #             print("Video file not found.")
# #             client.publish(mqtt_topic_transfered_publish, "transfered failed: " + video_path)
# #     # Unmount the drive at the end
# #     try:
# #         subprocess.run(['sudo', 'umount', mount_path])
# #     except subprocess.CalledProcessError as e:
# #         print(f"Error unmounting the drive: {e}")



client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqtt_broker_address, mqtt_port, 60)

client.loop_forever()