#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, List, Any, Dict


class SudoHelper:
    """
    Helper class for managing sudo authentication and executing commands with elevated privileges.

    This class provides a secure way to authenticate with sudo once and then execute
    multiple commands with elevated privileges without repeatedly prompting for passwords.
    It's specifically designed for running Python scripts that require root access.

    The helper stores the authenticated password securely in memory and uses it to
    execute subsequent commands. It provides methods for testing authentication,
    running arbitrary sudo commands, and specifically running Python scripts.

    Attributes:
        _sudo_password (Optional[str]): The authenticated sudo password stored in memory.
    """

    def __init__(self) -> None:
        """
        Initialize the SudoHelper.

        Creates a new instance with no stored password. Authentication must be
        performed using the authenticate() method before running sudo commands.
        """
        self._sudo_password: Optional[str] = None

    def authenticate(self, password: str) -> bool:
        """
        Test if the provided password works for sudo authentication.

        Attempts to run a simple sudo command ('sudo true') with the provided
        password to verify that it's correct. If successful, stores the password
        for use in subsequent operations.

        Args:
            password (str): The sudo password to test and store.

        Returns:
            bool: True if the password is valid and authentication succeeded,
                False if the password is incorrect or authentication failed.

        Note:
            This method uses 'sudo true' as a test command because it's harmless
            and quick to execute while still requiring valid sudo authentication.
        """
        try:
            # Try a simple sudo command to verify the password
            subprocess.run(
                ["sudo", "-kS", "true"],
                input=password.encode(),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                check=True,
            )
            self._sudo_password = password
            return True
        except subprocess.CalledProcessError:
            return False

    def run_sudo(self, cmd: List[str], **kwargs: Any) -> subprocess.Popen:
        """
        Run a command with sudo using the stored password.

        Executes the specified command with sudo privileges, automatically
        providing the stored password through stdin. The command is run
        asynchronously and returns a Popen object for further interaction.

        Args:
            cmd (List[str]): Command and arguments to execute with sudo.
            **kwargs (Any): Additional keyword arguments passed to subprocess.Popen.
                Common arguments include stdout, stderr, cwd, etc.

        Returns:
            subprocess.Popen: Process object for the running command.

        Raises:
            RuntimeError: If no sudo password is available (authentication required).
        """
        if not self._sudo_password:
            raise RuntimeError("Not authenticated")

        full_cmd = ["sudo", "-S"] + cmd
        kwargs.setdefault("stdout", subprocess.PIPE)
        kwargs.setdefault("stderr", subprocess.PIPE)

        process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, **kwargs)

        # Send password to stdin
        process.stdin.write(self._sudo_password.encode() + b"\n")
        process.stdin.flush()

        return process

    def run_python_script(self, script_path, *args):
        """
        Run a Python script with sudo using the stored password.
        Executes the specified Python script with sudo privileges, automatically
        providing the stored password through stdin. The script is run_sudo
        asynchronously and returns a Popen object for further interaction.
        Args:
            script_path (str or Path): Path to the Python script to execute.
            *args: Additional arguments to pass to the script.
        Returns:
            subprocess.Popen: Process object for the running script.
        Raises:
            RuntimeError: If no sudo password is available (authentication required).
        """
        cmd = [sys.executable, str(script_path)] + list(args)
        return self.run_sudo(cmd)
