from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality

import os
from glob import glob

size_img = (1000, 1800)
raspberry_pi_index = 1
filename = 'C1S1A1D1_calibration'

camera = Picamera2()
print("Calibrating camera...")
camera.still_configuration = camera.create_still_configuration(
    main={"size": size_img}
)
camera.start()
# camera.options["quality"] = Quality.VERY_HIGH
camera.options["quality"] = 95
# camera.rotation = 90
filename_save = filename.replace('CX', f'C{raspberry_pi_index}')
os.makedirs(filename_save, exist_ok=True)
files = glob(f'{filename_save}/*.jpg')
# If there are files in the directory, get the last file and increment the number
if len(files) > 0:
    filename_save = f'{filename_save}/{filename}_{"{0:0=4d}".format(len(files)+1)}.jpg'
else:
    filename_save = f'{filename_save}/{filename}_0001.jpg'
camera.start_and_capture_file(filename_save)
print(f"Image {filename_save} captured.")
camera.stop()
