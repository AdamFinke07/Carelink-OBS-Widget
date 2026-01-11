# Carelink OBS Widget

An **unofficial** integration of the Carelink API for OBS using websocket.

![OBS Widget](img/Preview2.png)
![App Screenshot](img/Preview.png)


## Features:
* **Automated Login**: Handles the login flow for Medtronic Carelink Cloud.
* **Region Support**: Supports both EU (default) and US regions.
* **Supports MMOL/L and MG/DL**: Built in conversion from the API MG/DL to MMOL/L
* **Trend Arrows**: Automatically updates an OBS Image source with the current trend arrow.

## Installation

### Windows
For Windows users, a compiled release is available.

1. Go to the [Releases page](https://github.com/AdamFinke07/Carelink-OBS-Widget/releases/tag/1.0.0).
2. Download the `Carelink-OBS-Widget-Windows.zip` file.
3. Extract the zip file to a location of your choice.
4. **Install Firefox:**
   This tool requires the Firefox browser to be installed on your system to perform the authentication flow.
5. Run the executable inside the folder.

### MacOS / Linux
1. **Clone the repository:**
    ```bash
    git clone https://github.com/AdamFinke07/Carelink-OBS-Widget
    cd Carelink-OBS-Widget
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Install Firefox:**
    This tool requires the Firefox browser to be installed on your system to perform the authentication flow.

4. **Run main.py:**
    ```bash
    python main.py
    ```

## Usage:



1. **Login via the GUI:**
    - Configure your region settings (US/EU).
    - Click the **Login** button. A Firefox window will open.
    - Log in to your Carelink account. Once successful, the window will close automatically.

> **Note:** If the browser does not open or nothing happens, please close any existing Firefox windows and try again.

2. **Configure OBS:**
    - In OBS Studio, go to **Tools** -> **WebSocket Server Settings**. Enable the server and set a password.
    - Create a **Text** source in your OBS scene (e.g., named `Glucose`).
    - Create an **Image** source in your OBS scene (e.g., named `Trend`).
    - In this application, enter your WebSocket IP, Port, Password.
    - Enter the **OBS Text Source Name** (e.g., `Glucose`) and **OBS Image Source Name** (e.g., `Trend`).
    - Click **Save Web Socket Settings**.

3. **Start Sync:**
    - Click **Start Sync** to begin updating the OBS sources with your glucose readings.
    - Use **Force Sync** if you want to trigger an immediate update.


## Special Thanks:
* **@palmarci**: For the original implementation of the Carelink login flow.
* **@ondrej1024**: For creating the original Python library
* **@m0rt4l1n**: For the fix after recent API changes

## Disclaimer:
This project is not affiliated with Medtronic. Use at your own risk.
