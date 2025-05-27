"""
Keyboard input management using evdev
"""
import json
import os
import asyncio
import threading
from pathlib import Path
from evdev import InputDevice, categorize, ecodes, list_devices
import re

class KeyboardManager:
    def __init__(self):
        self.tmp_dir = Path('/tmp/keyboard_visualizer')
        self.tmp_dir.mkdir(exist_ok=True)
        
        self.command_file = self.tmp_dir / 'command'
        self.response_file = self.tmp_dir / 'response'
        self.running_file = self.tmp_dir / 'running'
        
        # Clear any existing files
        for file in [self.command_file, self.response_file]:
            if file.exists():
                file.unlink()
                
        # Store current key states and devices
        self.key_states = {}
        self.devices = []
        self.monitored_keys = set()
        self.helper_thread = None
        
        # Find all keyboard devices
        self._find_keyboards()
        
        if not self.devices:
            raise RuntimeError("No keyboard devices found. Make sure you have permission to access input devices.")
            
    def start(self):
        """Start the keyboard helper process."""
        if self.helper_thread is not None:
            return True
            
        # Create running file to indicate the helper is active
        self.running_file.touch()
        
        # Start the helper thread
        self.helper_thread = threading.Thread(target=self.run, daemon=True)
        self.helper_thread.start()
        
        # Wait for the helper to start
        for _ in range(20):  # Wait up to 2 seconds
            if self.running_file.exists():
                return True
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))
            
        # If we get here, the helper didn't start properly
        self.stop()
        return False
        
    def stop(self):
        """Stop the keyboard helper process."""
        if self.running_file.exists():
            try:
                self.running_file.unlink()
            except:
                pass
                
        if self.helper_thread:
            self.helper_thread.join(timeout=2)
            self.helper_thread = None
            
        # Cleanup files
        for file in [self.command_file, self.response_file]:
            if file.exists():
                try:
                    file.unlink()
                except:
                    pass
                    
    def _find_keyboards(self):
        """Find all keyboard devices."""
        self.devices = []
        for path in list_devices():
            try:
                device = InputDevice(path)
                # Check if device has key events
                if ecodes.EV_KEY in device.capabilities():
                    self.devices.append(device)
            except (PermissionError, OSError):
                continue
                
    def _get_key_name(self, keycode):
        """Convert keycode to key name."""
        try:
            # Get the key name from evdev
            key_name = ecodes.KEY[keycode]
            # Remove the KEY_ prefix and convert to lowercase
            key_name = re.sub(r'^KEY_', '', key_name).lower()
            # Special case mappings
            mappings = {
                'leftctrl': 'ctrl',
                'rightctrl': 'ctrl',
                'leftalt': 'alt',
                'rightalt': 'alt',
                'leftshift': 'shift',
                'rightshift': 'shift',
                'leftmeta': 'super',
                'rightmeta': 'super',
                'comma': ',',
                'dot': '.',
                'grave': '`',
                'minus': '-',
                'equal': '=',
                'semicolon': ';',
                'apostrophe': "'",
                'backslash': '\\',
                'slash': '/',
                'space': 'space'
            }
            return mappings.get(key_name, key_name)
        except KeyError:
            return None
            
    async def _monitor_device(self, device):
        """Monitor a single input device for events."""
        async for event in device.async_read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                key_name = self._get_key_name(event.code)
                
                if key_name and key_name in self.monitored_keys:
                    self.key_states[key_name] = key_event.keystate == key_event.key_down
                    try:
                        with open(self.response_file, 'w') as f:
                            json.dump(self.key_states, f)
                    except Exception as err:
                        print(f"Error writing state: {err}")
                        
    def wait_for_key(self):
        """Wait for a single keypress and return its name."""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(self._wait_for_key_async())
        finally:
            loop.close()
            
    async def _wait_for_key_async(self):
        """Async implementation of wait_for_key."""
        tasks = []
        for device in self.devices:
            async def read_device(dev):
                async for event in dev.async_read_loop():
                    if event.type == ecodes.EV_KEY:
                        key_event = categorize(event)
                        if key_event.keystate == key_event.key_down:
                            key_name = self._get_key_name(event.code)
                            if key_name:
                                return key_name
            tasks.append(asyncio.create_task(read_device(device)))
            
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel all other tasks
        for task in pending:
            task.cancel()
            
        # Get the result from the completed task
        key_name = None
        for task in done:
            try:
                key_name = task.result()
                break
            except:
                continue
                
        return key_name
        
    def start_monitoring(self, keys):
        """Start monitoring the specified keys."""
        # Convert keys to lowercase and update monitored keys set
        self.monitored_keys = {key.lower() for key in keys}
        # Initialize all keys as released
        self.key_states = {key: False for key in self.monitored_keys}
        
        # Write initial state
        try:
            with open(self.response_file, 'w') as f:
                json.dump(self.key_states, f)
        except Exception as err:
            print(f"Error writing initial state: {err}")
            
    async def run_async(self):
        """Main async loop to handle commands."""
        print("Keyboard helper running with evdev...")
        
        while self.running_file.exists():
            if self.command_file.exists():
                try:
                    with open(self.command_file, 'r') as f:
                        command = json.load(f)
                        
                    if command['type'] == 'wait_key':
                        key = await self._wait_for_key_async()
                        with open(self.response_file, 'w') as f:
                            json.dump({'key': key}, f)
                            
                    elif command['type'] == 'monitor':
                        print(f"Starting to monitor keys: {command['keys']}")
                        self.start_monitoring(command['keys'])
                        # Start monitoring all devices
                        monitor_tasks = [
                            self._monitor_device(device) 
                            for device in self.devices
                        ]
                        await asyncio.gather(*monitor_tasks)
                        
                    elif command['type'] == 'stop_monitor':
                        self.key_states.clear()
                        self.monitored_keys.clear()
                        if self.response_file.exists():
                            self.response_file.unlink()
                            
                    # Remove the command file after processing
                    self.command_file.unlink()
                    
                except Exception as e:
                    print(f"Error in helper: {e}")
                    
            await asyncio.sleep(0.1)
            
    def run(self):
        """Start the async event loop."""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.run_async())
        finally:
            loop.close()
            
        # Cleanup on exit
        for file in [self.command_file, self.response_file, self.running_file]:
            if file.exists():
                file.unlink()
                
    def get_key_states(self):
        """Get the current state of monitored keys."""
        try:
            with open(self.response_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {} 