import subprocess
import sys
import os


class SudoHelper:
    def __init__(self):
        self.password = None

    def authenticate(self, password):
        """Test if the provided sudo password is valid."""
        try:
            # Try a simple sudo command to test the password
            proc = subprocess.run(
                ["sudo", "-S", "true"],
                input=password.encode(),
                stderr=subprocess.PIPE,
                check=True,
            )
            self.password = password
            return True
        except subprocess.CalledProcessError:
            return False

    def run_sudo(self, command):
        """Run a command with sudo using the stored password."""
        if not self.password:
            raise RuntimeError("No sudo password available")

        proc = subprocess.run(
            ["sudo", "-S"] + command,
            input=self.password.encode(),
            stderr=subprocess.PIPE,
            check=True,
        )
        return proc

    def run_python_script(self, script_path):
        """Run a Python script with sudo using the stored password."""
        if not self.password:
            raise RuntimeError("No sudo password available")

        # Get the path to the current Python interpreter
        python_path = sys.executable

        # Run the script with the current Python interpreter
        proc = subprocess.Popen(
            ["sudo", "-S", python_path, str(script_path)],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Send the password
        proc.stdin.write(self.password.encode() + b"\n")
        proc.stdin.flush()

        return proc
