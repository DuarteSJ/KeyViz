#!/usr/bin/env python3
import keyboard
import json
import sys
import os
import time
from pathlib import Path


class KeyboardHelper:
    def __init__(self):
        self.tmp_dir = Path("/tmp/keyboard_visualizer")
        self.tmp_dir.mkdir(exist_ok=True)

        self.command_file = self.tmp_dir / "command"
        self.response_file = self.tmp_dir / "response"
        self.running_file = self.tmp_dir / "running"

        # Clear any existing files
        for file in [self.command_file, self.response_file]:
            if file.exists():
                file.unlink()

        # Create running file to indicate the helper is active
        self.running_file.touch()

        # Store current key states
        self.key_states = {}
        self.last_error_time = 0  # Track last error time to reduce spam

    def wait_for_key(self):
        """Wait for a single keypress and return its scan code and name."""
        key_info = None

        def on_key(event):
            nonlocal key_info
            if event.event_type == keyboard.KEY_DOWN:
                key_info = {
                    'scan_code': event.scan_code,
                    'name': event.name,
                }
                keyboard.unhook_all()

        keyboard.hook(on_key)
        while not key_info:
            time.sleep(0.1)
        return key_info

    def start_monitoring(self, scan_codes):
        """Start monitoring keys based on scan codes."""
        keyboard.unhook_all()
        self.key_states = {}  # Reset states

        def on_key_event(e):
            print(f"Key: {e.name}, Scan code: {e.scan_code}")
            if e.scan_code in scan_codes:
                self.key_states[e.scan_code] = e.event_type == keyboard.KEY_DOWN
                try:
                    with open(self.response_file, "w") as f:
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
                    with open(self.command_file, "r") as f:
                        command = json.load(f)

                    # Handle different command types
                    if command["type"] == "wait_key":
                        key_info = self.wait_for_key()
                        with open(self.response_file, "w") as f:
                            json.dump({"key_info": key_info}, f)

                    elif command["type"] == "monitor":
                        self.start_monitoring(command["scan_codes"])

                    elif command["type"] == "stop_monitor":
                        keyboard.unhook_all()
                        self.key_states.clear()
                        if self.response_file.exists():
                            self.response_file.unlink()

                    # Remove the command file after processing
                    self.command_file.unlink()

            except FileNotFoundError:
                # Command file doesn't exist yet, just wait
                time.sleep(0.1)
            except json.JSONDecodeError:
                # File might be partially written, wait and retry
                time.sleep(0.1)
            except Exception as e:
                # Only print error if enough time has passed since last error
                current_time = time.time()
                if current_time - self.last_error_time >= 5:  # Only print every 5 seconds
                    print(f"Error in helper: {e}")
                    self.last_error_time = current_time

            time.sleep(0.1)  # Add a small delay to prevent busy waiting

        # Cleanup on exit
        keyboard.unhook_all()
        for file in [self.command_file, self.response_file, self.running_file]:
            if file.exists():
                file.unlink()


if __name__ == "__main__":
    helper = KeyboardHelper()
    helper.run()
 