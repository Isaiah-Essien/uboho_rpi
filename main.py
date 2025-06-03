


'''Your code starts here:'''

from package_checker import check_packages, current_dir,open_json_file, save_to_json
check_packages()
import signal
import sys
from cv2 import VideoCapture,imwrite
import subprocess
import time
import pandas as pd
import os

if not os.path.exists(f'{current_dir}/images'):
    os.mkdir(f'{current_dir}/images')

def handler(signum, frame):
    """Handles ctrl+C interrupt and stops all afm"""
    print("\nStopping all processes!")
    print("All Processes stopped; exiting now!")
    sys.exit(0)


def get_camera_IP(mac_address):
    '''
    ## Gets the IP address of the camera using the MAC address
    * @params 
    - 1. string mac_address (MAC address of the intended camera) 
    * @return 
    - 1. string IP_address (IP address of the camera) 
    - @comment returns "not found" if the IP address of the camera is not on the ARP table
    
    '''
    if mac_address is None:
        return 'not_found'
    mac_address = mac_address.lower().replace("-",":")
    print('MAC: ',mac_address)
    retries = 2
    for attempt in range(retries):        
        print("Attempt: ",attempt+1)
        df = pd.read_csv('/proc/net/arp' )
        column = df.columns.values[0]
        arp = df[column].str.split(expand=True)
        cols_to_use = ['IP_address','HW_type','Flags','MAC_address','Mask','Device']
        arp.columns=cols_to_use
        arp.reset_index(drop=True,inplace=True)
        # print(arp[arp['MAC_address'].str.contains(f'{mac_address}')])
        ip_address = arp[arp['MAC_address'].str.contains(f'{mac_address}')]['IP_address'].values
        print('IP Address: ', ip_address)
        if ip_address.size > 0:
            ip = ip_address[0]
            return ip
        else:
            if attempt == 1: return ip
            ip = 'not_found'
            try:
                print("Trying to get IP addresses")
                subnet =  subprocess.check_output('ip route | tail -1 | cut -d " " -f 1',shell=True,).decode().strip()
                subprocess.check_output(f'sudo nmap -sn --unique --send-ip {subnet}',shell=True,)
            except Exception as e:
                ip = 'not_found'
    return ip


def capture_images():
    '''
    ## Captures images from the configured cameras
    * @params 
    - None
    * @return 
    - None
    
    '''
    db = open_json_file(f'{current_dir}/resources/setup.json')
    cameras = dict(db["cameras"].items())
    for camera in cameras:
        camera = dict(cameras[f"{camera}"].items())
        if camera['name'] is not None:
            camera_name = camera['name']
            camera_manufacturer = camera['manufacturer'].lower()
            camera_ip = camera['network_settings']['ip_address']
            cam_mac_address = camera['network_settings']['mac_address']
            camera_username = camera['username']
            camera_password = camera['password']
            print("Getting image from camera", camera_name, " IP: ", camera_ip)
            if camera_manufacturer == 'hikvision':
                camera_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}:554/ch1/main/av_stream"
            elif camera_manufacturer == 'tiandy':
                camera_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}:554"
            else:
                camera_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}"
            stream = VideoCapture(camera_url)
            current_time = time.strftime("%Y%m%dT%H%M%S", time.localtime())
            try:
                cam_available, frame = stream.read()
                if cam_available:
                    images = sorted(os.listdir(f"{current_dir}/images"))
                    if len(images) >= 6:
                        image_to_delete = os.path.join("./images", images[0])
                        print(f"Image to delete is {image_to_delete}")
                        os.remove(image_to_delete)
                    picture_name = f"{current_dir}/images/{current_time}_{camera_name.replace(' ','_')}.jpg"
                    print(f"Image captured from camera {camera_name}")
                    # print("Image frame: ",frame)
                    imwrite(picture_name, frame)
            except Exception as e:
                print(f"An error occurred while capturing image from camera {camera_name}: {e}")

def configure_cameras():
    '''
    ## Sets the time and name of the cameras
    * @params 
    - None
    * @return 
    - 1. list cameras_configured
    - 2. list cameras_not_configured
    - @comment returns the list of cameras configured and the ones not configured
    
    '''
    # set time, change name
    cameras_configured = []
    cameras_not_configured = []
    if os.path.isfile(f'{current_dir}/resources/setup.json'):
        try:
            db = open_json_file(f'{current_dir}/resources/setup.json')
        except Exception as e:
            return cameras_configured,cameras_not_configured
        cameras = dict(db["cameras"].items())
        i = 0
        for camera in cameras:
            i+=1
            camera = dict(cameras[f"{camera}"].items())
            if camera['name'] is not None:
                camera_name = camera['name']
                camera_manufacturer = camera['manufacturer'].lower()
                camera_ip = camera['network_settings']['ip_address']
                cam_mac_address = (camera['network_settings']['mac_address']).lower()
                camera_username = camera['username']
                camera_password = camera['password']
                print("MAC ADDRESS: ",cam_mac_address)
                camera_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}"
                if camera_manufacturer == 'hikvision':
                    camera_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}:554/ch1/main/av_stream"
                elif camera_manufacturer == 'tiandy':
                    camera_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}:554"
                # Try capturing an image
                stream = VideoCapture(camera_url)
                cam_available, frame = stream.read()
                if cam_available:
                    cameras_configured.append(i)
                    continue
                else:
                    # It means that the camera IP address has changed; get the correct IP and save it
                    correct_IP = get_camera_IP(cam_mac_address)
                    if correct_IP != "not_found":
                        camera_ip = correct_IP
                        gateway = subprocess.check_output('ip route | head -1 | cut -d " " -f 3',shell=True,).decode().strip()
                        db['cameras'][f'camera{i}']['network_settings']['ip_address'] = correct_IP
                        db['cameras'][f'camera{i}']['network_settings']['gateway'] = gateway
                        save_to_json(db,f'{current_dir}/resources/setup.json')
                        cameras_configured.append(i)
                        continue
                    else:
                        print(f"Check Camera {i+1} network details")
                        cameras_not_configured.append(i)
                        continue
            else:
                cameras_not_configured.append(i)
    return cameras_configured,cameras_not_configured

cameras_configured,cameras_not_configured = configure_cameras()
print(f'Camera config done : {cameras_configured,cameras_not_configured}')

print("Main program started")
start = time.time()
i = 0
while True:
    signal.signal(signal.SIGINT, handler)
    if time.time() - start > 10:
        if cameras_configured:
            capture_images()
        start = time.time()
        
    break