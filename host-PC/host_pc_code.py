import paho.mqtt.client as mqtt
import time

mqtt_broker_address = "BROKER_IP_ADDRESS"  
mqtt_port = 1883  
mqtt_topic_start = "start_video"
mqtt_topic_stop = "stop_video"
mqtt_topic_transfer = "request_video_transfer"

client = mqtt.Client()
client.connect(mqtt_broker_address, mqtt_port, 60)

def start_video_recording():
    client.publish(mqtt_topic_start, "start")

def stop_video_recording():
    client.publish(mqtt_topic_stop, "stop")

def request_video_transfer():
    client.publish(mqtt_topic_transfer, "transfer")

while True:
    print("Choose an action:")
    print("1. Start video recording")
    print("2. Stop video recording")
    print("3. Request video transfer")
    print("4. Quit")
    
    choice = input("Enter your choice (1/2/3/4): ")
    
    if choice == "1":
        start_video_recording()
    elif choice == "2":
        stop_video_recording()
    elif choice == "3":
        request_video_transfer()
    elif choice == "4":
        break
    else:
        print("Invalid choice. Please choose a valid option.")

# Disconnect from MQTT broker and exit
client.disconnect()
