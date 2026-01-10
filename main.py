import obsws_python as obs
import json
import Carelink
from datetime import datetime
import FreeSimpleGUI as sg
import CarelinkLogin
import os
import threading
import pathlib


def load_settings():
    with open('settings.json', 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

def create_settings():
    settings = {"obs_credentials": {"ip": "localhost", "port": "4455", "password": ""}, "use_mmol": True, "use_US_region": False, "obs_source_name": "Glucose"}
    with open('settings.json', 'w+') as f:
        json.dump(settings, f, indent=4)


def connect_obs(): # connects to obs websocket and returns the obsClient object and available requests
    settings = load_settings()
    try:
        obsClient = obs.ReqClient(
            host=settings["obs_credentials"]["ip"],
            port=int(settings["obs_credentials"]["port"]),
            password=settings["obs_credentials"]["password"]
        )
    except Exception as e:
        sg.popup(f'Cannot Connect To OBS Check Your Web Socket Settings. {e}')
        return None, []

    response = obsClient.get_version()
    print(f'Connected to OBS Version: {response.obs_version}')
    print(f'Web Socket Version: {response.obs_web_socket_version}')
    print(f'Platform: {response.platform_description}')
    return obsClient, response.available_requests

def login_carelink():
    settings = load_settings()
    CarelinkLogin.main(is_us_region=settings['use_US_region'])

def connect_carelink(): # connects to carelink api and returns the carelinkClient object
    carelinkClient = Carelink.CareLinkClient(tokenFile="logindata.json")
    return carelinkClient
    
def request_carelink_data(carelinkClient): # sends a request for recent data and returns the entire request and lastSG
    settings = load_settings()
    carelinkData = None
    if carelinkClient.init():
        carelinkData = carelinkClient.getRecentData()
    
    if carelinkData is None:
        return None, None, None

    try:
        lastSG = carelinkData['patientData']['lastSG']['sg']
        if settings["use_mmol"] == 1:
            lastSG = round(lastSG / 18, 1)

        sgs = [(item['sg'], datetime.fromisoformat(item['timestamp'])) for item in carelinkData['patientData']['sgs']]
        return carelinkData, lastSG, sgs
    except Exception as e:
        print(f"Error processing data: {e}")
        return None, None, None

def update_obs(carelinkClient, obsClient, stop_event):
    while not stop_event.is_set():
        carelinkData, lastSG, sgs = request_carelink_data(carelinkClient)
        if lastSG is not None:
            print(f"New SG: {lastSG}")
            if obsClient:
                try:
                    settings = load_settings()
                    source_name = settings["obs_source_name"]
                    obsClient.set_input_settings(name=source_name, settings={"text": str(lastSG)}, overlay=True)
                except Exception as e:
                    print(f"Error updating OBS: {e}")
        
        if stop_event.wait(300):
            break

def main():
    from pathlib import Path

    f = Path("settings.json")
    if not(f.is_file()):
        create_settings()
    carelinkClient = connect_carelink()        
    
    loggedin = False
    loginButtonText = 'Login'
    loggedInText = 'Not Logged In'
    
    if carelinkClient.init():
        carelinkData, lastSG, sgs = request_carelink_data(carelinkClient)
        if carelinkData:
            loginButtonText = 'Logged In'
            loggedInText = f'Logged In As : {carelinkData["patientData"]["firstName"]}'
            loggedin = True
            
    settings = load_settings()
    
    stop_event = threading.Event()
    update_thread = None
    
    windowLayout = [
        [sg.Text('General Settings:')],
        [sg.Text('Use US Region:'), sg.Checkbox('', default=settings['use_US_region'], key='is_us_region', enable_events=True)],
        [sg.Text('Use MMOL/L:'), sg.Checkbox('', default=settings['use_mmol'], key='is_mmol', enable_events=True)],
        [sg.Text('Web Socket Settings:')],
        [sg.Text('Web Socket IP: '), sg.Input(default_text=settings['obs_credentials']['ip'], key='obs_ip')],
        [sg.Text('Web Socket Port: '), sg.Input(default_text=settings['obs_credentials']['port'], key='obs_port')],
        [sg.Text('Web Socket Password: '), sg.Input(default_text=settings['obs_credentials']['password'], key='obs_password', password_char='*')],
        [sg.Text('OBS Source Name: '), sg.Input(default_text=settings['obs_source_name'], key='obs_source_name')],
        [sg.Button('Save Web Socket Settings', key='saveSettings')],
        [sg.Text(loggedInText, key='loginStatus'), sg.Button(button_text=loginButtonText, key='loginButton', disabled=loggedin), sg.Button(button_text='Sign Out', key='signOutButton', disabled=not(loggedin))],
        [sg.Button('Start Sync', key='startSync'), sg.Button('Stop Sync', key='stopSync', disabled=True)]
    ]
    sg.theme('Python')
    window = sg.Window('Carelink OBS Widget', windowLayout)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            stop_event.set()
            if update_thread and update_thread.is_alive():
                update_thread.join()
            break
        if event == 'loginButton':
            login_carelink()
            carelinkClient = connect_carelink()
            if carelinkClient.init():
                carelinkData, lastSG, sgs = request_carelink_data(carelinkClient)
                loggedin = True
                window['loginButton'].update(text='Logged In', disabled=True)
                window['signOutButton'].update(disabled=False)
                window['loginStatus'].update(f'Logged In As : {carelinkData["patientData"]["firstName"]}')
        if event == 'is_us_region':
            settings['use_US_region'] = values['is_us_region']
            save_settings(settings)
        if event == 'is_mmol':
            settings['use_mmol'] = values['is_mmol']
            save_settings(settings)
        if event == 'saveSettings':
            settings['obs_credentials']['ip'] = values['obs_ip']
            settings['obs_credentials']['port'] = values['obs_port']
            settings['obs_credentials']['password'] = values['obs_password']
            settings['obs_source_name'] = values['obs_source_name']
            save_settings(settings)
            sg.popup('Settings Saved!')
        if event == 'signOutButton':
            if os.path.exists('logindata.json'):
                os.remove('logindata.json')
            window['loginButton'].update(text='Login', disabled=False)
            window['signOutButton'].update(disabled=True)
            window['loginStatus'].update('Not Logged In')
            loggedin = False
            sg.popup('You Have Now Logged Out. You Must Log In Again To Continue.')
        
        if event == 'startSync':
            obsClient, available_requests = connect_obs()
            if loggedin and obsClient != None:
                stop_event.clear()
                update_thread = threading.Thread(target=update_obs, args=(carelinkClient, obsClient, stop_event), daemon=True)
                update_thread.start()
                window['startSync'].update(disabled=True)
                window['stopSync'].update(disabled=False)
            
        if event == 'stopSync':
            stop_event.set()
            window['startSync'].update(disabled=False)
            window['stopSync'].update(disabled=True)

    window.close()

main()