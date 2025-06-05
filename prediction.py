'''This prediction script takes a video stream from an RTSP camera, processes the frames to extract pose landmarks using MediaPipe, and predicts seizure events using a TensorFlow Lite model.

It also triggers a buzzer alert when a seizure is detected.

Alarms are managed using the GPIO library for Raspberry Pi.

The script handles the video stream using FFmpeg and processes the frames in a sliding window fashion to make predictions.

The script is designed to run indefinitely, restarting the FFmpeg stream if it fails.

The script includes error handling for stream interruptions and manages the buzzer state to ensure it only buzzes when a seizure is detected.

The script is designed to run on a Raspberry Pi with GPIO support and requires the installation of several Python packages, including OpenCV, TensorFlow, and MediaPipe.

The script is structured to be modular, with functions for starting the FFmpeg stream, processing frames, making predictions, and handling buzzer alerts.

The script is designed to be run as a standalone program, and it includes signal handling to allow for graceful shutdowns.

This script is intended for use in a medical or research context, where real-time seizure detection is required.
'''

import os
import time
import signal
import sys
import cv2
import numpy as np
import tensorflow as tf
import subprocess
from collections import deque
from package_checker import check_packages, current_dir
from gpiozero import Buzzer
import mediapipe as mp

check_packages()

RTSP_URL = "rtsp://admin:Isaiah123@192.168.1.98:554" # I am using this until I am able to dynamically get  the IP address of the camera from HC's script
WIDTH, HEIGHT = 2880, 1620
FRAME_SIZE = WIDTH * HEIGHT * 3

buzzer = Buzzer(17)
buzzer_available = True

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, model_complexity=1)

mean = np.load("./model/scaler_mean.npy")
scale = np.load("./model/scaler_scale.npy")

interpreter = tf.lite.Interpreter(model_path="./model/multihead_attention_model_raw_pose.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

fps = 30
frames_per_window = int(5 * fps)
sliding_window = deque(maxlen=frames_per_window)

def trigger_buzzer_alert():
    if buzzer_available:
        for i in range(5):
            buzzer.on()
            print(f"[BUZZ] Alert {i+1}/5")
            time.sleep(1)
            buzzer.off()
            time.sleep(1)

def predict_pose_features():
    avg_features = np.mean(sliding_window, axis=0)
    scaled = (avg_features - mean) / scale
    model_input = scaled.reshape(1, 132, 1).astype(np.float32)

    interpreter.set_tensor(input_details[0]['index'], model_input)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])
    prediction_prob = output[0][0]
    label = "SEIZURE" if prediction_prob > 0.55 else "NO SEIZURE"
    print(f"[PREDICTION] {label} ({prediction_prob:.2f})")

    if label == "SEIZURE":
        trigger_buzzer_alert()

    sliding_window.clear()

def handler(signum, frame):
    print("\n[INFO] Exiting gracefully.")
    buzzer.off()
    sys.exit(0)

signal.signal(signal.SIGINT, handler)

def start_ffmpeg_stream():
    cmd = [
        "ffmpeg", "-rtsp_transport", "tcp",
        "-i", RTSP_URL,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-"
    ]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

def run_inference_from_stream():
    print("[INFO] Running inference with auto-restarting FFmpeg...")
    retries = 0
    max_retries = 5

    while True:
        process = start_ffmpeg_stream()
        print("[INFO] FFmpeg started.")
        try:
            while True:
                raw_frame = process.stdout.read(FRAME_SIZE)
                if len(raw_frame) != FRAME_SIZE:
                    raise RuntimeError("Incomplete frame received.")

                frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(image_rgb)

                if results.pose_landmarks:
                    features = [f for lm in results.pose_landmarks.landmark for f in [lm.x, lm.y, lm.z, lm.visibility]]
                    if len(features) == 132:
                        sliding_window.append(features)

                if len(sliding_window) == frames_per_window:
                    predict_pose_features()
                    time.sleep(1)

        except Exception as e:
            retries += 1
            print(f"[ERROR] {e}")
            print(f"[INFO] Restarting FFmpeg... ({retries}/{max_retries})")
            process.kill()
            time.sleep(2)
            if retries >= max_retries:
                print("[FATAL] Too many stream failures. Exiting.") #Just incase the  stream fails, shaa
                break
            continue

if __name__ == "__main__":
    run_inference_from_stream()
