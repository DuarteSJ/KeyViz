import subprocess
import sys
import os
from typing import Optional, List, Union
from pathlib import Path


class SudoHelper:
    """
    A helper class for executing commands with sudo privileges.

    This class provides methods to authenticate with sudo and execute
    commands or Python scripts with elevated privileges.

    Attributes:
        password (Optional[str]): The stored sudo password after successful authentication.
    """

    def __init__(self) -> None:
        """
        Initialize the SudoHelper instance.

        Sets the password attribute to None, requiring authentication
        before running privileged commands.
        """
        self.password: Optional[str] = None

    def authenticate(self, password: str) -> bool:
        """
        Test if the provided sudo password is valid.

        Args:
            password (str): The sudo password to test.

        Returns:
            bool: True if the password is valid and authentication succeeds,
                  False otherwise.

        Example:
            >>> helper = SudoHelper()
            >>> if helper.authenticate("my_password"):
            ...     print("Authentication successful")
            ... else:
            ...     print("Authentication failed")
        """
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

    def run_sudo(self, command: List[str]) -> subprocess.CompletedProcess:
        """
        Run a command with sudo using the stored password.

        Args:
            command (List[str]): The command to run as a list of strings,
                               where the first element is the command name
                               and subsequent elements are arguments.

        Returns:
            subprocess.CompletedProcess: The completed process object
                                       containing return code and output.

        Raises:
            RuntimeError: If no sudo password is available (authentication required).
            subprocess.CalledProcessError: If the command execution fails.

        Example:
            >>> helper = SudoHelper()
            >>> helper.authenticate("my_password")
            >>> result = helper.run_sudo(["ls", "/root"])
        """
        if not self.password:
            raise RuntimeError("No sudo password available")

        proc = subprocess.run(
            ["sudo", "-S"] + command,
            input=self.password.encode(),
            stderr=subprocess.PIPE,
            check=True,
        )
        return proc

    def run_python_script(self, script_path: Union[str, Path]) -> subprocess.Popen:
        """
        Run a Python script with sudo using the stored password.

        Args:
            script_path (Union[str, Path]): Path to the Python script to execute.
                                          Can be a string or Path object.

        Returns:
            subprocess.Popen: The Popen process object for the running script.
                            Use .wait() to wait for completion or .communicate()
                            to get output.

        Raises:
            RuntimeError: If no sudo password is available (authentication required).

        Example:
            >>> helper = SudoHelper()
            >>> helper.authenticate("my_password")
            >>> proc = helper.run_python_script("/path/to/script.py")
            >>> stdout, stderr = proc.communicate()
        """
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
