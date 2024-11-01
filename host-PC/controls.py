import time

from picamera2 import Picamera2, Preview

time.sleep(5)

size_img = (1600, 1200)

camera = Picamera2()
preview_config = camera.create_preview_configuration(main={"size": size_img})
camera.configure(preview_config)

camera.start()
time.sleep(5)

metadata = camera.capture_metadata()
controls = {c: metadata[c] for c in ["ExposureTime", "AnalogueGain", "ColourGains"]}
print(controls)

camera.set_controls(controls)
time.sleep(5)