import json
import os
import sys
import time
from pathlib import Path
import subprocess
from typing import Optional, Dict, Any, List, Union
from PyQt6.QtWidgets import QDialog, QMessageBox
from keyboard_visualizer.utils.sudo_helper import SudoHelper
from keyboard_visualizer.ui.dialogs.settings_dialog import PasswordDialog


class KeyboardManager:
    """
    Manages keyboard input monitoring with elevated privileges.
    
    This class handles the creation and management of a helper process that runs
    with elevated privileges to monitor keyboard input. It provides methods for
    authenticating with sudo, starting/stopping the helper process, and communicating
    with it to monitor specific keys or wait for key presses.
    
    The manager uses temporary files for inter-process communication with the
    keyboard helper process, allowing for real-time monitoring of keyboard states
    without blocking the main application.
    
    Attributes:
        tmp_dir (Path): Directory for temporary communication files.
        command_file (Path): File used to send commands to the helper process.
        response_file (Path): File used to receive responses from the helper process.
        running_file (Path): File indicating the helper process is running.
        helper_process (Optional[subprocess.Popen]): The running helper process.
        sudo (SudoHelper): Helper for managing sudo authentication and execution.
    """
    
    def __init__(self) -> None:
        """
        Initialize the KeyboardManager.
        
        Sets up the temporary directory structure for inter-process communication
        and initializes the sudo helper. Creates the temporary directory if it
        doesn't already exist.
        """
        self.tmp_dir: Path = Path("/tmp/keyboard_visualizer")
        self.command_file: Path = self.tmp_dir / "command"
        self.response_file: Path = self.tmp_dir / "response"
        self.running_file: Path = self.tmp_dir / "running"
        self.helper_process: Optional[subprocess.Popen] = None
        self.sudo: SudoHelper = SudoHelper()

        # Create tmp directory if it doesn't exist
        self.tmp_dir.mkdir(exist_ok=True)

    def authenticate(self) -> bool:
        """
        Get sudo authentication from user through a password dialog.
        
        Displays a password dialog to the user and attempts to authenticate
        with sudo using the provided password. Will continue prompting until
        the user either provides the correct password or cancels the dialog.
        
        Returns:
            bool: True if authentication was successful, False if user cancelled.
            
        Note:
            This method will show error messages for incorrect passwords and
            allow the user to retry multiple times.
        """
        dialog: PasswordDialog = PasswordDialog()
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False

            password: str = dialog.get_password()
            print(f"Attempting to authenticate with password: {password}")
            if self.sudo.authenticate(password):
                return True

            QMessageBox.critical(
                dialog, "Error", "Incorrect password. Please try again."
            )

    def start(self) -> bool:
        """
        Start the keyboard helper process with elevated privileges.
        
        Launches the keyboard helper script using sudo privileges. The helper
        process runs independently and communicates through temporary files.
        Waits up to 2 seconds for the helper process to indicate it's running.
        
        Returns:
            bool: True if the helper process started successfully, False otherwise.
            
        Note:
            If a helper process is already running, this method returns True
            without starting a new process. If the helper fails to start within
            the timeout period, the process is terminated.
        """
        if self.helper_process is not None:
            return True

        # Create helper script path
        helper_script: Path = Path(__file__).parent.parent / "utils/keyboard_helper.py"
        print(f"Starting keyboard helper from: {helper_script}")

        try:
            # Start the helper process with sudo
            self.helper_process = self.sudo.run_python_script(helper_script)
        except (subprocess.CalledProcessError, RuntimeError):
            return False

        # Wait for the helper to start
        for _ in range(20):  # Wait up to 2 seconds
            if self.running_file.exists():
                return True
            time.sleep(0.1)

        # If we get here, the helper didn't start properly
        if self.helper_process:
            print("Helper process did not start correctly.")
            try:
                self.helper_process.terminate()
            except Exception:
                pass
        return False

    def stop(self) -> None:
        """
        Stop the helper process and clean up resources.
        
        Removes the running indicator file to signal the helper process to stop,
        then terminates the process if it's still running. Also cleans up the
        process reference.
        
        Note:
            This method is safe to call multiple times and will not raise
            exceptions if the process is already stopped or files don't exist.
        """
        if self.running_file.exists():
            self.running_file.unlink()
        if self.helper_process:
            self.helper_process.terminate()
            self.helper_process = None

    def send_command(self, command: Dict[str, Any]) -> bool:
        """
        Send a command to the helper process.
        
        Writes a JSON-encoded command to the command file for the helper process
        to read and execute. Commands are structured as dictionaries with a 'type'
        field indicating the command type and additional parameters as needed.
        
        Args:
            command (Dict[str, Any]): Command dictionary to send to the helper.
                Must include a 'type' field specifying the command type.
                
        Returns:
            bool: True if the command was written successfully, False otherwise.
            
        Example:
            >>> manager.send_command({"type": "wait_key"})
            >>> manager.send_command({"type": "monitor", "scan_codes": [1, 2, 3]})
        """
        try:
            with open(self.command_file, "w") as f:
                json.dump(command, f)
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False

    def wait_for_key(self) -> Optional[Dict[str, Any]]:
        """
        Wait for a single keypress and return its scan code and name.
        
        Sends a 'wait_key' command to the helper process and waits for a response
        containing information about the pressed key. This is typically used for
        key mapping or configuration purposes.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing key information with
                scan code and key name, or None if no key was pressed within
                the timeout period or if an error occurred.
                
        Note:
            This method will wait up to 5 seconds for a key press. The response
            file is automatically cleaned up after reading.
        """
        if not self.send_command({"type": "wait_key"}):
            return None

        # Wait for response
        for _ in range(50):  # Wait up to 5 seconds
            try:
                if self.response_file.exists():
                    with open(self.response_file, "r") as f:
                        response: Dict[str, Any] = json.load(f)
                    try:
                        os.remove(self.response_file)
                    except Exception:
                        pass
                    return response.get("key_info")
            except Exception:
                pass
            time.sleep(0.1)
        return None

    def start_monitoring(self, scan_codes: List[int]) -> bool:
        """
        Start monitoring the specified scan codes.
        
        Instructs the helper process to begin monitoring a specific set of keys
        identified by their scan codes. The helper will continuously track the
        state of these keys and make the information available through the
        response file.
        
        Args:
            scan_codes (List[int]): List of keyboard scan codes to monitor.
                Each scan code should be a valid integer representing a key.
                
        Returns:
            bool: True if the monitoring command was sent successfully,
                False otherwise.
                
        Note:
            This method only sends the command; actual monitoring success
            depends on the helper process. Use get_key_states() to retrieve
            the current state of monitored keys.
        """
        return self.send_command({"type": "monitor", "scan_codes": scan_codes})

    def stop_monitoring(self) -> bool:
        """
        Stop monitoring keys.
        
        Sends a command to the helper process to stop monitoring all keys.
        After this command, get_key_states() will no longer return updated
        key state information.
        
        Returns:
            bool: True if the stop command was sent successfully, False otherwise.
            
        Note:
            This method does not stop the helper process itself, only the
            key monitoring functionality. Use stop() to terminate the helper process.
        """
        return self.send_command({"type": "stop_monitor"})

    def get_key_states(self) -> Dict[Union[str, int], bool]:
        """
        Get the current state of monitored keys.
        
        Reads the response file to get the current pressed/released state of
        all keys that are being monitored. This method is typically called
        repeatedly in a timer loop to get real-time key state updates.
        
        Returns:
            Dict[Union[str, int], bool]: Dictionary mapping scan codes (as strings
                or integers) to their current state (True for pressed, False for
                released). Returns an empty dictionary if the response file doesn't
                exist or contains invalid JSON.
                
        Note:
            The scan codes in the returned dictionary may be strings or integers
            depending on how they were serialized by the helper process. Callers
            should handle both types appropriately.
        """
        try:
            with open(self.response_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
