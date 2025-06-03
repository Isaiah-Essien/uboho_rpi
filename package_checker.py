import json
import subprocess
import os
current_dir = os.path.dirname(__file__)


def open_json_file(json_file_path):
    ''' 
    # Opens the json file specified by the file path
    * @params
    - 1.  String json_file_path
    * @return
    - 1. file as a dictionary
        
    '''
    with open(json_file_path,'r') as json_file:
        file = json.load(json_file)
        json_file.close()
    return file

def save_to_json(json_dict, json_file_path):
    ''' 
    # Writes a dictionary as json to a specified file path
    * @params
    - 1.  dictionary json_dict
    - 2.  String json_file_path
    * @return None

    '''
    if type(json_dict) is str:
        with open(json_file_path,'w') as json_file:
            json.dump(json.loads(json_dict),json_file, indent = 4)
            json_file.close()
    else:
        with open(json_file_path,'w') as json_file:
            json.dump(json_dict,json_file, indent = 4)
            json_file.close()

packs = open_json_file(f'{current_dir}/requirements.json')

def install_package(package):
    print(f'Installing package: {package}')
    try:
        output = subprocess.check_output(f'sudo apt-get -y install python3-{package}',shell=True,).decode().strip()
    except Exception:
        print("Package not installed")

def check_packages():
    for pack in packs['packages']:
        # print(pack)
        try:
            output = subprocess.check_output(f'apt-cache policy python3-{pack} | grep \'Installed:\'',shell=True,).decode().strip()
            if output.split()[1] == '(none)':
                install_package(pack)
            else:
                print(f'{pack}: {output}')
        except Exception:
            print("Package not installed")
            install_package(pack)
            continue
        