#!/usr/bin/env python3
"""
OBS Recording Status Blink(1) Controller with Keyboard Control

This script monitors OBS Studio's recording status and changes a Blink(1) light:
- Red when recording
- Green when not recording
- Also allows toggling recording with a configurable keyboard shortcut
- Flashes the light after a button press until OBS confirms the state change

Requirements:
- pip install obs-websocket-py blink1 pynput
- OBS Studio with WebSocket plugin enabled
- Blink(1) device connected to USB
"""

import time
import queue
import logging
import threading
from obswebsocket import obsws, requests
from blink1.blink1 import Blink1
from pynput import keyboard
from pynput.keyboard import Key

# Configuration
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "OJtycF114KSw0nDs"  # Set your OBS WebSocket password here if you have one

# Keyboard shortcut configuration
# You can change this to any key from pynput.keyboard.Key
# Examples: Key.pause, Key.f1, Key.f2, Key.home, Key.end, Key.insert, etc.
#RECORDING_TOGGLE_KEY = Key.pause
RECORDING_TOGGLE_KEY = Key.f14

# Colors (RGB values 0-255)
COLOR_OFF = (0, 0, 0)             # Light off
COLOR_RECORDING = (90, 0, 0)      # Red
COLOR_NOT_RECORDING = (0, 70, 0)  # Green
COLOR_DISCONNECTED = (70, 70, 0)  # Yellow (when OBS is disconnected)

# Fade delay in milliseconds
FADE_TIME = 10

# --- "State change in progress" flash feedback ---
# After a toggle key press, the light alternates between the color it was
# showing and the flash color below until OBS reports the new state.
# FLASH_COLOR can be any RGB tuple, or COLOR_OFF to blink the light off.
FLASH_COLOR = COLOR_OFF

# Time (seconds) each half of the flash lasts (flash color, then original color).
# Smaller = faster flashing. 0.08 is a rapid flutter, 0.25 is a calm blink.
FLASH_INTERVAL = 0.1

# Which transitions flash
FLASH_ON_STOP = True    # Pressed while recording (saving the file takes time)
FLASH_ON_START = False  # Pressed while not recording

# Safety net: stop flashing after this many seconds even if OBS never confirms.
# Flashing normally lasts until OBS reports the recording has been saved, so
# make this longer than your longest expected save.
FLASH_TIMEOUT = 120

# How often (seconds) to poll OBS: normally, and while waiting for confirmation
POLL_INTERVAL = 1.0
POLL_INTERVAL_FAST = 0.2

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OBSBlink1Controller:
    def __init__(self):
        self.ws = None
        self.blink1 = None
        self.current_color = None
        self.is_recording = False
        self.keyboard_listener = None
        self.running = True

        # Flash state
        self.flashing = False
        self.pending_target = None   # True = waiting for recording to start, False = to stop
        self.flash_stop = None       # threading.Event for the active flash thread
        self.flash_thread = None
        self.state_lock = threading.Lock()

        # Key presses are queued and handled one at a time by a worker thread.
        # The worker waits for any flash (i.e. a save in progress) to finish
        # before acting on the next press.
        self.key_queue = queue.Queue()
        self.idle = threading.Event()   # set when no flash/state change is in progress
        self.idle.set()
        self.key_worker = None
        
    def setup_blink1(self):
        """Initialize Blink(1) device"""
        try:
            self.blink1 = Blink1()
            logger.info("Blink(1) device connected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blink(1) device: {e}")
            return False
    
    def setup_obs_connection(self):
        """Initialize OBS WebSocket connection"""
        try:
            self.ws = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
            self.ws.connect()
            logger.info(f"Connected to OBS at {OBS_HOST}:{OBS_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")
            return False
    
    def setup_keyboard_listener(self):
        """Setup global keyboard listener for recording toggle"""
        try:
            self.key_worker = threading.Thread(target=self._key_worker_loop, daemon=True)
            self.key_worker.start()
            self.keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press
            )
            self.keyboard_listener.start()
            logger.info(f"Keyboard listener started. Press {RECORDING_TOGGLE_KEY} to toggle recording.")
            return True
        except Exception as e:
            logger.error(f"Failed to setup keyboard listener: {e}")
            return False
    
    def on_key_press(self, key):
        """Handle key press events (just queues the press; never blocks)"""
        try:
            if key == RECORDING_TOGGLE_KEY:
                logger.info(f"Recording toggle key ({RECORDING_TOGGLE_KEY}) pressed")
                self.key_queue.put(time.time())
        except Exception as e:
            logger.error(f"Error handling key press: {e}")

    def _key_worker_loop(self):
        """Process queued key presses in order, one at a time"""
        while self.running:
            try:
                pressed_at = self.key_queue.get()
                if pressed_at is None:  # shutdown sentinel
                    break
                if not self.idle.is_set():
                    logger.info("Save in progress - key press queued until it finishes")
                # Wait for any in-progress flash (save) to finish before acting
                while self.running and not self.idle.wait(timeout=0.5):
                    pass
                if not self.running:
                    break
                self.toggle_recording()
            except Exception as e:
                logger.error(f"Error processing key press: {e}")
    
    def start_recording(self):
        """Start recording in OBS"""
        try:
            if not self.ws:
                logger.error("Cannot start recording - not connected to OBS")
                return False
            
            response = self.ws.call(requests.StartRecord())
            logger.info("Recording started via keyboard shortcut")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self):
        """Stop recording in OBS"""
        try:
            if not self.ws:
                logger.error("Cannot stop recording - not connected to OBS")
                return False
            
            response = self.ws.call(requests.StopRecord())
            logger.info("Recording stopped via keyboard shortcut")
            return True
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False
    
    def toggle_recording(self):
        """Toggle recording state in OBS"""
        if not self.ws:
            logger.error("Cannot toggle recording - not connected to OBS")
            return

        # Get current recording status to ensure we're in sync
        current_status = self.get_recording_status()
        if current_status is None:
            logger.error("Cannot determine current recording status")
            return
        
        if current_status:
            logger.info("Currently recording - stopping recording")
            if FLASH_ON_STOP:
                self.start_flash(target_recording=False)
            if not self.stop_recording():
                self.end_flash()
        else:
            logger.info("Currently not recording - starting recording")
            if FLASH_ON_START:
                self.start_flash(target_recording=True)
            if not self.start_recording():
                self.end_flash()

    # ------------------------------------------------------------------
    # Light control
    # ------------------------------------------------------------------
    def _write_light(self, color):
        """Write a color to the device unconditionally"""
        if not self.blink1:
            return
        try:
            r, g, b = color
            self.blink1.fade_to_rgb(FADE_TIME, r, g, b)  # First argument is fade time
            self.current_color = color
        except Exception as e:
            logger.error(f"Failed to set light color: {e}")

    def set_light_color(self, color):
        """Set Blink(1) light color (suppressed while the flash thread owns the light)"""
        if self.flashing:
            return
        if self.blink1 and color != self.current_color:
            self._write_light(color)
            logger.info(f"Light color changed to RGB{color}")

    # ------------------------------------------------------------------
    # Flash feedback
    # ------------------------------------------------------------------
    def start_flash(self, target_recording):
        """Begin flashing to show a state change is in progress"""
        with self.state_lock:
            if self.flashing:
                return
            base_color = self.current_color if self.current_color is not None else (
                COLOR_RECORDING if self.is_recording else COLOR_NOT_RECORDING
            )
            self.pending_target = target_recording
            self.flash_stop = threading.Event()
            self.flashing = True
            self.idle.clear()
            self.flash_thread = threading.Thread(
                target=self._flash_worker,
                args=(base_color, self.flash_stop),
                daemon=True,
            )
            self.flash_thread.start()
        logger.info("State change in progress - flashing light")

    def end_flash(self):
        """Stop flashing (state change confirmed, failed, or timed out)"""
        self.pending_target = None
        if self.flash_stop:
            self.flash_stop.set()

    def _flash_worker(self, base_color, stop_event):
        """Alternate between FLASH_COLOR and the original color until stopped"""
        deadline = time.time() + FLASH_TIMEOUT
        show_flash = True
        while not stop_event.is_set() and time.time() < deadline:
            self._write_light(FLASH_COLOR if show_flash else base_color)
            show_flash = not show_flash
            stop_event.wait(FLASH_INTERVAL)

        if not stop_event.is_set():
            logger.warning(f"No state change confirmed after {FLASH_TIMEOUT}s - giving up on flashing")
            self.pending_target = None

        # Hand the light back and show the color for the current state
        self.flashing = False
        if self.ws:
            final = COLOR_RECORDING if self.is_recording else COLOR_NOT_RECORDING
        else:
            final = COLOR_DISCONNECTED
        self._write_light(final)
        logger.info(f"Flashing finished - light set to RGB{final}")
        self.idle.set()  # queued key presses may now be processed
    
    def get_recording_status(self):
        """Get current recording status from OBS"""
        try:
            response = self.ws.call(requests.GetRecordStatus())
            return response.datain.get('outputActive', False)
        except Exception as e:
            logger.error(f"Failed to get recording status: {e}")
            return None
    
    def handle_recording_status(self, is_recording):
        """Handle recording status change"""
        if is_recording != self.is_recording:
            self.is_recording = is_recording
            if is_recording:
                logger.info("Recording started - setting light to RED")
                self.set_light_color(COLOR_RECORDING)
            else:
                logger.info("Recording stopped - setting light to GREEN")
                self.set_light_color(COLOR_NOT_RECORDING)

        # OBS confirmed the state we were waiting for - stop flashing
        if self.pending_target is not None and is_recording == self.pending_target:
            logger.info("OBS confirmed state change")
            self.end_flash()
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop...")
        
        while self.running:
            try:
                # Check if OBS connection is still alive
                if not self.ws:
                    logger.warning("OBS connection lost, attempting to reconnect...")
                    if self.setup_obs_connection():
                        self.set_light_color(COLOR_NOT_RECORDING)
                    else:
                        self.set_light_color(COLOR_DISCONNECTED)
                        time.sleep(5)
                        continue
                
                # Get recording status
                recording_status = self.get_recording_status()
                
                if recording_status is None:
                    # Connection issue
                    logger.warning("Lost connection to OBS")
                    self.ws = None
                    self.end_flash()
                    self.set_light_color(COLOR_DISCONNECTED)
                else:
                    # Update light based on status
                    self.handle_recording_status(recording_status)
                
                # Poll faster while waiting for a state change to be confirmed
                time.sleep(POLL_INTERVAL_FAST if self.pending_target is not None else POLL_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}")
                time.sleep(5)
    
    def cleanup(self):
        """Clean up connections"""
        try:
            self.running = False
            self.key_queue.put(None)  # wake the key worker so it can exit
            self.end_flash()
            if self.flash_thread:
                self.flash_thread.join(timeout=1)
            
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                logger.info("Keyboard listener stopped")
            
            if self.blink1:
                # Turn off the light
                self.blink1.fade_to_rgb(FADE_TIME, 0, 0, 0)
                logger.info("Blink(1) light turned off")
            
            if self.ws:
                self.ws.disconnect()
                logger.info("Disconnected from OBS")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def run(self):
        """Main run method"""
        logger.info("Starting OBS Blink(1) Controller with Keyboard Control...")
        
        # Setup Blink(1)
        if not self.setup_blink1():
            logger.error("Cannot continue without Blink(1) device")
            return
        
        # Setup keyboard listener
        if not self.setup_keyboard_listener():
            logger.warning("Failed to setup keyboard listener - continuing without keyboard control")
        
        # Setup OBS connection
        if not self.setup_obs_connection():
            logger.warning("Starting without OBS connection - will attempt to connect periodically")
            self.set_light_color(COLOR_DISCONNECTED)
        else:
            # Set initial state
            initial_status = self.get_recording_status()
            if initial_status:
                self.set_light_color(COLOR_RECORDING)
                self.is_recording = True
            else:
                self.set_light_color(COLOR_NOT_RECORDING)
                self.is_recording = False
        
        try:
            self.monitor_loop()
        finally:
            self.cleanup()

def main():
    """Entry point"""
    controller = OBSBlink1Controller()
    controller.run()

if __name__ == "__main__":
    main()