#!/usr/bin/env python3
import keyboard
import json
import sys
import os
import time
from pathlib import Path

class KeyboardHelper:
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
                
        # Create running file to indicate the helper is active
        self.running_file.touch()
        
        # Store current key states
        self.key_states = {}
        
    def wait_for_key(self):
        """Wait for a single keypress and return its name."""
        key_pressed = None
        
        def on_key(event):
            nonlocal key_pressed
            if event.event_type == keyboard.KEY_DOWN:
                key_pressed = event.name
                keyboard.unhook_all()
                
        keyboard.hook(on_key)
        while not key_pressed:
            time.sleep(0.1)
        return key_pressed
    
    def start_monitoring(self, config):
        """Start monitoring keys based on configuration."""
        keyboard.unhook_all()
        self.key_states = {}  # Reset states
        
        def on_key_event(e):
            print(f"Key {e.name} {e.event_type}")
            if e.name.lower() in config:
                self.key_states[e.name.lower()] = e.event_type == keyboard.KEY_DOWN
                state = "pressed" if e.event_type == keyboard.KEY_DOWN else "released"
                print(f"Key {e.name} {state}")
                try:
                    with open(self.response_file, 'w') as f:
                        json.dump(self.key_states, f)
                except Exception as err:
                    print(f"Error writing state: {err}")
                    
        keyboard.hook(on_key_event)
    
    def run(self):
        """Main loop to handle commands."""
        print("Keyboard helper running with elevated privileges...")
        
        while self.running_file.exists():
            try:
                if self.command_file.exists():
                    with open(self.command_file, 'r') as f:
                        command = json.load(f)
                    
                    # Handle different command types
                    if command['type'] == 'wait_key':
                        key = self.wait_for_key()
                        with open(self.response_file, 'w') as f:
                            json.dump({'key': key}, f)
                            
                    elif command['type'] == 'monitor':
                        self.start_monitoring(command['keys'])
                        
                    elif command['type'] == 'stop_monitor':
                        keyboard.unhook_all()
                        self.key_states.clear()
                        if self.response_file.exists():
                            self.response_file.unlink()
                            
                    # Remove the command file after processing
                    self.command_file.unlink()
                    
            except Exception as e:
                # print(f"Error in helper: {e}")
                ...
                
            time.sleep(0.1)
        
        # Cleanup on exit
        keyboard.unhook_all()
        for file in [self.command_file, self.response_file, self.running_file]:
            if file.exists():
                file.unlink()

if __name__ == '__main__':
    helper = KeyboardHelper()
    helper.run() 