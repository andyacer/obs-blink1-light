#!/usr/bin/env python3
"""
OBS Recording Status Blink(1) Controller with Keyboard Control

This script monitors OBS Studio's recording status and changes a Blink(1) light:
- Red when recording
- Green when not recording
- Also allows toggling recording with a configurable keyboard shortcut

Requirements:
- pip install obs-websocket-py blink1 pynput
- OBS Studio with WebSocket plugin enabled
- Blink(1) device connected to USB
"""

import time
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
COLOR_RECORDING = (90, 0, 0)    # Red
COLOR_NOT_RECORDING = (0, 70, 0)  # Green
COLOR_DISCONNECTED = (70, 70, 0)  # Yellow (when OBS is disconnected)

# Fade delay in milliseconds
FADE_TIME = 10

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
        """Handle key press events"""
        try:
            if key == RECORDING_TOGGLE_KEY:
                logger.info(f"Recording toggle key ({RECORDING_TOGGLE_KEY}) pressed")
                self.toggle_recording()
        except Exception as e:
            logger.error(f"Error handling key press: {e}")
    
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
            self.stop_recording()
        else:
            logger.info("Currently not recording - starting recording")
            self.start_recording()
    
    def set_light_color(self, color):
        """Set Blink(1) light color"""
        if self.blink1 and color != self.current_color:
            try:
                r, g, b = color
                self.blink1.fade_to_rgb(FADE_TIME, r, g, b)  # First argument is fade time
                self.current_color = color
                logger.info(f"Light color changed to RGB{color}")
            except Exception as e:
                logger.error(f"Failed to set light color: {e}")
    
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
                    self.set_light_color(COLOR_DISCONNECTED)
                else:
                    # Update light based on status
                    self.handle_recording_status(recording_status)
                
                time.sleep(1)  # Check every second
                
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