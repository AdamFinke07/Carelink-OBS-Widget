import obsws_python as obs
import json
import Carelink
from datetime import datetime, timedelta
import FreeSimpleGUI as sg
import CarelinkLogin
import os
import threading
from pathlib import Path


def load_settings():
    f = Path("settings.json")
    if f.is_file():
        with open('settings.json', 'r') as f:
            return json.load(f)
    else:
        create_settings()
        with open('settings.json', 'r') as f:
            return json.load(f)

def save_settings(settings):
    with open('settings.json', 'w+') as f:
        json.dump(settings, f, indent=4)

def create_settings():
    settings = {"obs_credentials": {"ip": "localhost", "port": 4455, "password": ""}, "use_mmol": True, "use_US_region": False, "obs_text_source_name": "Glucose", "obs_image_source_name": "Trend", "wait_time": 300}
    with open('settings.json', 'w+') as f:
        json.dump(settings, f, indent=4)


def connect_obs(): # connects to obs websocket and returns the obsClient object and available requests
    settings = load_settings()
    try:
        obsClient = obs.ReqClient(
            host=settings["obs_credentials"]["ip"],
            port=settings["obs_credentials"]["port"],
            password=settings["obs_credentials"]["password"]
        )
    except Exception as e:
        sg.popup(f'Cannot Connect To OBS Check Your Web Socket Settings. {e}')
        return None, []

    response = obsClient.get_version()
    print(f'Connected to OBS Version: {response.obs_version}')
    print(f'Web Socket Version: {response.obs_web_socket_version}')
    print(f'Platform: {response.platform_description}')
    return obsClient

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
            return None, None, None, None
        lastSG = carelinkData['patientData']['lastSG']['sg']
        lastTrend = carelinkData['patientData']['lastSGTrend']
        if settings["use_mmol"] == 1:
            lastSG = round(lastSG / 18, 1)
        sgs = [(item['sg'], datetime.fromisoformat(item['timestamp'])) for item in carelinkData['patientData']['sgs']]
        return carelinkData, lastSG, sgs, lastTrend
    else:
        return None, None, None, None

def update_obs(carelinkClient, obsClient, stop_event, force_sync_event, window):
    settings = load_settings()
    text_source = settings['obs_text_source_name']
    image_source = settings['obs_image_source_name']
    while not stop_event.is_set():
        try:
            carelinkData, lastSG, sgs, lastTrend = request_carelink_data(carelinkClient)
            if lastSG is not None and obsClient:
                obsClient.set_input_settings(name=text_source, settings={"text": str(lastSG)}, overlay=True)
                image_path = os.path.abspath(f'assets/{lastTrend.lower()}.png')
                obsClient.set_input_settings(name=image_source, settings={"file": image_path}, overlay=True)
                wait_time = settings['wait_time']
            else:
                wait_time = 20
        except Exception as e:
            print(f"Error in update loop: {e}")
            wait_time = 20
        
        for i in range(wait_time, 0, -1):
            window['nextSync'].update(f"Next Sync: {i}s")
            if force_sync_event.wait(1):
                force_sync_event.clear()
                break
            if stop_event.is_set():
                break




def main():
    carelinkClient = connect_carelink()        
    loggedin = False
    loginButtonText = 'Login'
    loggedInText = 'Not Logged In'
    stop_event = threading.Event()
    force_sync_event = threading.Event()
    update_thread = None
    settings = load_settings()
    
    
    if carelinkClient.init():
        carelinkData, lastSG, sgs, lastTrend = request_carelink_data(carelinkClient)
        if carelinkData:
            loginButtonText = 'Logged In'
            loggedInText = f'Logged In As: {carelinkData["patientData"]["firstName"]}'
            loggedin = True
            
    windowLayout = [
        [sg.Text('Settings:')],
        [sg.Text('Use US Region:'), sg.Checkbox('', default=settings['use_US_region'], key='is_us_region')],
        [sg.Text('Use MMOL/L:'), sg.Checkbox('', default=settings['use_mmol'], key='is_mmol')],
        [sg.Text('Web Socket IP: '), sg.Input(default_text=settings['obs_credentials']['ip'], key='obs_ip')],
        [sg.Text('Web Socket Port: '), sg.Input(default_text=settings['obs_credentials']['port'], key='obs_port')],
        [sg.Text('Web Socket Password: '), sg.Input(default_text=settings['obs_credentials']['password'], key='obs_password', password_char='*')],
        [sg.Text('OBS Text Source Name: '), sg.Input(default_text=settings['obs_text_source_name'], key='obs_text_source_name')],
        [sg.Text('OBS Image Source Name: '), sg.Input(default_text=settings['obs_image_source_name'], key='obs_image_source_name')],
        [sg.Text('Wait Time Between Syncs: '), sg.Input(default_text=settings['wait_time'], key='wait_time')],
        [sg.Button('Save Web Socket Settings', key='saveSettings')],
        [sg.Text(loggedInText, key='loginStatus'), sg.Button(button_text=loginButtonText, key='loginButton', disabled=loggedin), sg.Button(button_text='Sign Out', key='signOutButton', disabled=not(loggedin))],
        [sg.Button('Start Sync', key='startSync'), sg.Button('Stop Sync', key='stopSync', disabled=True), sg.Button('Force Sync', key='forceSync', disabled=True), sg.Text('Next Sync: N/A', key='nextSync')]
    ]
    
    window = sg.Window('Carelink OBS Widget', windowLayout, icon=os.path.abspath('assets/icon.ico'))
    sg.theme('Python')
    while True:
        event, values = window.read()
        
        if event in (sg.WIN_CLOSED, 'Cancel'):
            stop_event.set()
            force_sync_event.set()
            if update_thread and update_thread.is_alive():
                update_thread.join()
            break
        
        if event == 'loginButton':
            login_carelink()
            carelinkClient = connect_carelink()
            if carelinkClient.init():
                carelinkData, lastSG, sgs, lastTrend = request_carelink_data(carelinkClient)
                loggedin = True
                window['loginButton'].update(text='Logged In', disabled=True)
                window['signOutButton'].update(disabled=False)
                window['loginStatus'].update(f'Logged In As : {carelinkData["patientData"]["firstName"]}')
        
        if event == 'saveSettings':
            settings['use_US_region'] = values['is_us_region']
            settings['use_mmol'] = values['is_mmol']
            settings['obs_credentials']['ip'] = values['obs_ip']
            settings['obs_credentials']['password'] = values['obs_password']
            settings['obs_text_source_name'] = values['obs_text_source_name']
            settings['obs_image_source_name'] = values['obs_image_source_name']

            try:
                settings['obs_credentials']['port'] = int(values['obs_port'])
            except Exception:
                sg.popup('Web socket port must be an integer, value not saved')

            try:
                settings['wait_time'] = int(values['wait_time'])
            except Exception:
                sg.popup('Wait time must be an integer, value not saved')
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
            obsClient = connect_obs()
            if loggedin and obsClient != None:
                stop_event.clear()
                force_sync_event.clear()
                update_thread = threading.Thread(target=update_obs, args=(carelinkClient, obsClient, stop_event, force_sync_event, window), daemon=True)
                update_thread.start()
                window['startSync'].update(disabled=True)
                window['stopSync'].update(disabled=False)
                window['forceSync'].update(disabled=False)
                window['saveSettings'].update(disabled=True)
            
        if event == 'stopSync':
            stop_event.set()
            force_sync_event.set()
            window['startSync'].update(disabled=False)
            window['stopSync'].update(disabled=True)
            window['forceSync'].update(disabled=True)
            window['saveSettings'].update(disabled=False)
            window['nextSync'].update('Next Sync: N/A')

        if event == 'forceSync':
            force_sync_event.set()

    window.close()

main()