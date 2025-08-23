# obs-blink1-light
A simple Python script that turns a Blink(1) light into an OBS recording indicator.  Red = recording.

# Installation

Run one of these sets of commands in your terminal.

## Using uv
```bash
> git clone https://github.com/andyacer/obs-blink1-light.git
> cd obs-blink1-light/
> uv sync
Using CPython 3.13.7
Creating virtual environment at: .venv
Resolved 9 packages in 1ms
Installed 8 packages in 66ms
 + blink1==0.4.0
 + click==8.2.1
 + colorama==0.4.6
 + hidapi==0.14.0.post4
 + obs-websocket-py==1.0
 + setuptools==80.9.0
 + webcolors==24.11.1
 + websocket-client==1.8.0
>  .\.venv\Scripts\activate
> python .\obs-blink-controller.py
```

## Using pip
```bash
> git clone https://github.com/andyacer/obs-blink1-light.git
> cd obs-blink1-light/
> pip install -r requirements.txt
> python .\obs-blink-controller.py
```

# Output
```bash
> python .\obs-blink-controller.py
2025-08-23 16:43:49,609 - INFO - Starting OBS Blink(1) Controller...
2025-08-23 16:43:49,824 - INFO - Blink(1) device connected successfully
2025-08-23 16:43:49,824 - INFO - Connecting to ws://localhost:4455...
2025-08-23 16:43:49,830 - INFO - Connected!
2025-08-23 16:43:49,832 - INFO - Connected to OBS at localhost:4455
2025-08-23 16:43:49,834 - INFO - Light color changed to RGB(0, 70, 0)
2025-08-23 16:43:49,835 - INFO - Starting monitoring loop...
2025-08-23 16:45:38,971 - INFO - Recording started - setting light to RED
2025-08-23 16:45:38,973 - INFO - Light color changed to RGB(90, 0, 0)
2025-08-23 16:45:41,975 - INFO - Recording stopped - setting light to GREEN
2025-08-23 16:45:41,978 - INFO - Light color changed to RGB(0, 70, 0)
2025-08-23 16:45:45,144 - WARNING - Connection lost!
2025-08-23 16:45:45,981 - ERROR - Failed to get recording status: socket is already closed.
2025-08-23 16:45:45,981 - WARNING - Lost connection to OBS
2025-08-23 16:45:45,984 - INFO - Light color changed to RGB(70, 70, 0)
2025-08-23 16:45:46,985 - WARNING - OBS connection lost, attempting to reconnect...
2025-08-23 16:45:46,985 - INFO - Connecting to ws://localhost:4455...
2025-08-23 16:45:51,069 - ERROR - Failed to connect to OBS: [WinError 10061] No connection could be made because the target machine actively refused it
2025-08-23 16:45:56,072 - ERROR - Failed to get recording status: socket is already closed.
2025-08-23 16:45:56,072 - WARNING - Lost connection to OBS
2025-08-23 16:45:57,072 - WARNING - OBS connection lost, attempting to reconnect...
2025-08-23 16:45:57,073 - INFO - Connecting to ws://localhost:4455...
2025-08-23 16:45:57,074 - INFO - Connected!
2025-08-23 16:45:57,075 - INFO - Connected to OBS at localhost:4455
2025-08-23 16:45:57,078 - INFO - Light color changed to RGB(0, 70, 0)
```

