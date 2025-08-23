#!/usr/bin/env python3
"""
Simple Blink(1) Test Script
Tests if your Blink(1) device is working properly
"""

import time
import sys

def test_blink1():
    """Test Blink(1) device connection and basic functionality"""
    print("Testing Blink(1) device...")
    
    try:
        from blink1.blink1 import Blink1
        print("✓ blink1 library imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import blink1 library: {e}")
        print("Try: pip install blink1")
        return False
    
    try:
        # Try to connect to device
        device = Blink1()
        print("✓ Blink(1) device connected successfully")
        
        # Test colors
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green  
            (0, 0, 255),    # Blue
            (0, 0, 0)       # Off
        ]
        
        for i, (r, g, b) in enumerate(colors):
            print(f"Setting color to RGB({r}, {g}, {b})")
            device.fade_to_rgb(500, r, g, b)  # 500ms fade
            time.sleep(1)
        
        print("✓ Blink(1) test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Blink(1) device test failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure your Blink(1) device is plugged in")
        print("2. Try: pip uninstall hid hidapi hidapi-cffi")
        print("3. Then: pip install hidapi blink1")
        print("4. On Windows, you might need to install the Blink(1) driver")
        return False

def test_hidapi():
    """Test hidapi library"""
    print("\nTesting hidapi library...")
    
    try:
        import hid
        print("✓ hid library imported successfully")
        
        # List HID devices
        devices = hid.enumerate()
        print(f"Found {len(devices)} HID devices")
        
        # Look for Blink(1) devices
        blink1_devices = [d for d in devices if d.get('vendor_id') == 0x27b8]
        print(f"Found {len(blink1_devices)} Blink(1) devices")
        
        if blink1_devices:
            for device in blink1_devices:
                print(f"  - {device.get('product_string', 'Unknown')} (Path: {device.get('path', 'Unknown')})")
        
        return len(blink1_devices) > 0
        
    except ImportError as e:
        print(f"✗ hidapi library not available: {e}")
        return False
    except Exception as e:
        print(f"✗ hidapi test failed: {e}")
        return False

if __name__ == "__main__":
    print("Blink(1) Device Test")
    print("=" * 30)
    
    hidapi_ok = test_hidapi()
    blink1_ok = test_blink1()
    
    print("\n" + "=" * 30)
    if hidapi_ok and blink1_ok:
        print("✓ All tests passed! Your Blink(1) device should work with the main script.")
    else:
        print("✗ Some tests failed. Please follow the troubleshooting steps above.")
        sys.exit(1)