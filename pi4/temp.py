from picamera2.outputs import FfmpegOutput
from picamera2.outputs import FileOutput
import paho.mqtt.client as mqtt
from picamera2.encoders import H264Encoder, Quality
from picamera2 import Picamera2, MappedArray
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

size_img = (1800, 1000)

camera = Picamera2()
preview_config = camera.create_preview_configuration(main={"size": size_img})
camera.configure(preview_config)
encoder = H264Encoder()

camera.video_configuration = camera.create_video_configuration(
    main={"size": size_img}
)
camera.configure("video")
camera.set_controls({"FrameRate": 60})
camera.rotation = 90
filename_save = f'test.h264'
camera.start_recording(encoder, filename_save, quality=Quality.VERY_HIGH, pts=f'{filename_save.replace(".h264", "")}.txt')
time.sleep(15)
camera.stop_recording()