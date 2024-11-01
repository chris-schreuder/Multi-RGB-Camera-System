import os
import time
from picamera2.encoders import H264Encoder
import picamera2
import paramiko

root_path = "ROOT_PATH"

# Function to record a short video
def record_video(video_path, duration_seconds):
    with picamera2.Picamera2() as camera:
        encoder = H264Encoder()
        camera.start_recording(encoder, video_path)
        time.sleep(duration_seconds)
        camera.stop_recording()

# Function to send the video to the host PC
def send_video(video_path, host_pc_address, username, password):
    if os.path.exists(video_path):
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.connect(host_pc_address, username=username, password=password)
            
            with ssh_client.open_sftp() as sftp:
                destination_path = f'{root_path}videos\video.h264'
                sftp.put(video_path, destination_path)
            
            ssh_client.close()
            print("Video sent.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Video file not found.")

# Set the video file path and duration (in seconds)
video_path = 'output_video.h264'
duration_seconds = 10  # Change this to the desired duration

# Replace with your host PC information
host_pc_address = 'HOST_PC_IP_ADDRESS'
username = 'USERNAME'
password = 'PASSWORD'

# Record the video
record_video(video_path, duration_seconds)

# Send the recorded video to the host PC
send_video(video_path, host_pc_address, username, password)
