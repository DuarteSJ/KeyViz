#!/usr/bin/env python3
import keyboard
import json
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable


class KeyboardHelper:
    """
    Helper process for monitoring keyboard input with elevated privileges.
    
    This class runs as a separate process with elevated privileges to monitor
    keyboard input events. It communicates with the main application through
    temporary files, processing commands to wait for key presses or monitor
    specific keys continuously.
    
    The helper supports two main operations:
    1. Single key detection: Wait for any key press and return its information
    2. Continuous monitoring: Monitor specific keys and maintain their state
    
    Attributes:
        tmp_dir (Path): Directory for temporary communication files.
        command_file (Path): File for receiving commands from the main application.
        response_file (Path): File for sending responses back to the main application.
        running_file (Path): File indicating the helper process is running.
        key_states (Dict[int, bool]): Current state of monitored keys (scan_code -> pressed).
        last_error_time (float): Timestamp of last error to prevent spam logging.
    """
    
    def __init__(self) -> None:
        """
        Initialize the KeyboardHelper.
        
        Sets up the temporary directory structure for inter-process communication,
        clears any existing communication files, creates the running indicator file,
        and initializes key state tracking.
        """
        self.tmp_dir: Path = Path("/tmp/keyboard_visualizer")
        self.tmp_dir.mkdir(exist_ok=True)

        self.command_file: Path = self.tmp_dir / "command"
        self.response_file: Path = self.tmp_dir / "response"
        self.running_file: Path = self.tmp_dir / "running"

        # Clear any existing files
        for file in [self.command_file, self.response_file]:
            if file.exists():
                file.unlink()

        # Create running file to indicate the helper is active
        self.running_file.touch()

        # Store current key states
        self.key_states: Dict[int, bool] = {}
        self.last_error_time: float = 0  # Track last error time to reduce spam

    def wait_for_key(self) -> Optional[Dict[str, Any]]:
        """
        Wait for a single keypress and return its information.
        
        Sets up a keyboard hook to capture the next key press event and returns
        information about the pressed key including its scan code and name.
        This method blocks until a key is pressed.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing 'scan_code' and 'name'
                of the pressed key, or None if an error occurs.
                
        Note:
            This method unhooks all existing keyboard handlers and sets up a
            temporary hook that removes itself after capturing one key press.
        """
        key_info: Optional[Dict[str, Any]] = None

        def on_key(event: keyboard.KeyboardEvent) -> None:
            """
            Internal callback for handling key press events.
            
            Args:
                event (keyboard.KeyboardEvent): The keyboard event containing key information.
            """
            nonlocal key_info
            if event.event_type == keyboard.KEY_DOWN:
                key_info = {
                    "scan_code": event.scan_code,
                    "name": event.name,
                }
                keyboard.unhook_all()

        keyboard.hook(on_key)
        while not key_info:
            time.sleep(0.1)
        return key_info

    def start_monitoring(self, scan_codes: List[int]) -> None:
        """
        Start monitoring keys based on their scan codes.
        
        Sets up continuous monitoring of the specified keys, tracking their
        press/release states and writing updates to the response file. This
        method replaces any existing keyboard hooks.
        
        Args:
            scan_codes (List[int]): List of scan codes to monitor. Only key events
                for these scan codes will be tracked and reported.
                
        Note:
            The key states are continuously updated in the response file as JSON.
            Each monitored scan code maps to a boolean indicating if it's pressed.
        """
        keyboard.unhook_all()
        self.key_states = {}  # Reset states

        def on_key_event(e: keyboard.KeyboardEvent) -> None:
            """
            Internal callback for handling monitored key events.
            
            Args:
                e (keyboard.KeyboardEvent): The keyboard event to process.
            """
            print(f"Key: {e.name}, Scan code: {e.scan_code}")
            if e.scan_code in scan_codes:
                self.key_states[e.scan_code] = e.event_type == keyboard.KEY_DOWN
                try:
                    with open(self.response_file, "w") as f:
                        json.dump(self.key_states, f)
                except Exception as err:
                    print(f"Error writing state: {err}")

        keyboard.hook(on_key_event)

    def run(self) -> None:
        """
        Main loop to handle commands from the parent process.
        
        Continuously checks for command files and processes them based on their
        command type. Supports 'wait_key', 'monitor', and 'stop_monitor' commands.
        The loop continues until the running file is removed.
        
        Command Types:
        - wait_key: Wait for a single key press and return its information
        - monitor: Start monitoring specified scan codes continuously
        - stop_monitor: Stop all monitoring and clear key states
        
        The method includes error handling and rate limiting for error messages
        to prevent log spam. Cleanup is performed automatically on exit.
        """
        print("Keyboard helper running with elevated privileges...")

        while self.running_file.exists():
            try:
                if self.command_file.exists():
                    with open(self.command_file, "r") as f:
                        command: Dict[str, Any] = json.load(f)

                    # Handle different command types
                    if command["type"] == "wait_key":
                        key_info: Optional[Dict[str, Any]] = self.wait_for_key()
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
                current_time: float = time.time()
                if (
                    current_time - self.last_error_time >= 5
                ):  # Only print every 5 seconds
                    print(f"Error in helper: {e}")
                    self.last_error_time = current_time

            time.sleep(0.1)  # Add a small delay to prevent busy waiting

        # Cleanup on exit
        keyboard.unhook_all()
        for file in [self.command_file, self.response_file, self.running_file]:
            if file.exists():
                file.unlink()


if __name__ == "__main__":
    helper: KeyboardHelper = KeyboardHelper()
    helper.run()
