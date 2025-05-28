import json
import subprocess
import time
import os
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QMessageBox
from ..utils.sudo_helper import SudoHelper
from ..ui.dialogs import PasswordDialog

class KeyboardManager:
    def __init__(self):
        self.helper_process = None
        self.tmp_dir = Path('/tmp/keyboard_visualizer')
        self.command_file = self.tmp_dir / 'command'
        self.response_file = self.tmp_dir / 'response'
        self.running_file = self.tmp_dir / 'running'
        self.sudo = SudoHelper()
        
        # Create tmp directory if it doesn't exist
        self.tmp_dir.mkdir(exist_ok=True)
        
    def authenticate(self):
        """Get sudo authentication from user."""
        dialog = PasswordDialog()
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False
                
            password = dialog.get_password()
            if self.sudo.authenticate(password):
                return True
                
            QMessageBox.critical(dialog, "Error", "Incorrect password. Please try again.")
        
    def start(self):
        """Start the keyboard helper process with elevated privileges."""
        if self.helper_process is not None:
            return True
            
        # Create helper script path - now using absolute path from workspace root
        helper_script = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / 'keyboard_helper.py'
        print(f"Starting keyboard helper at: {helper_script}", flush=True)
        
        try:
            # Start the helper process with sudo
            self.helper_process = self.sudo.run_python_script(helper_script)
        except (subprocess.CalledProcessError, RuntimeError) as e:
            print(f"Error starting helper: {e}", flush=True)
            return False
                
        # Wait for the helper to start
        for _ in range(20):  # Wait up to 2 seconds
            if self.running_file.exists():
                print("Helper started successfully", flush=True)
                return True
            time.sleep(0.1)
            
        # If we get here, the helper didn't start properly
        print("Helper failed to start (timeout)", flush=True)
        if self.helper_process:
            try:
                self.helper_process.terminate()
            except:
                pass
        return False
        
    def stop(self):
        """Stop the keyboard helper process."""
        if self.running_file.exists():
            try:
                self.sudo.run_sudo(['rm', str(self.running_file)])
            except:
                pass
                
        if self.helper_process:
            try:
                self.helper_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    self.helper_process.terminate()
                except:
                    pass
            self.helper_process = None
            
    def send_command(self, command):
        """Send a command to the helper process."""
        try:
            with open(self.command_file, 'w') as f:
                json.dump(command, f)
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
            
    def wait_for_key(self):
        """Wait for a single keypress and return its name."""
        if not self.send_command({'type': 'wait_key'}):
            return None
            
        # Wait for response
        for _ in range(50):  # Wait up to 5 seconds
            try:
                if self.response_file.exists():
                    with open(self.response_file, 'r') as f:
                        response = json.load(f)
                    try:
                        os.remove(self.response_file)
                    except:
                        pass
                    return response.get('key')
            except:
                pass
            time.sleep(0.1)
        return None
        
    def start_monitoring(self, keys):
        """Start monitoring the specified keys."""
        print(f"Attempting to monitor keys: {keys}", flush=True)
        return self.send_command({'type': 'monitor', 'keys': keys})
            
    def stop_monitoring(self):
        """Stop monitoring keys."""
        return self.send_command({'type': 'stop_monitor'})
            
    def get_key_states(self):
        """Get the current state of monitored keys."""
        try:
            with open(self.response_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {} 