#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

class SudoHelper:
    def __init__(self):
        self._sudo_password = None
        
    def authenticate(self, password):
        """Test if the password works for sudo."""
        try:
            # Try a simple sudo command to verify the password
            subprocess.run(
                ['sudo', '-S', 'true'],
                input=password.encode(),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                check=True
            )
            self._sudo_password = password
            return True
        except subprocess.CalledProcessError:
            return False
            
    def run_sudo(self, cmd, **kwargs):
        """Run a command with sudo using the stored password."""
        if not self._sudo_password:
            raise RuntimeError("Not authenticated")
            
        full_cmd = ['sudo', '-S'] + cmd
        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('stderr', subprocess.PIPE)
        
        process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            **kwargs
        )
        
        # Send password to stdin
        process.stdin.write(self._sudo_password.encode() + b'\n')
        process.stdin.flush()
        
        return process
        
    def run_python_script(self, script_path, *args):
        """Run a Python script with sudo."""
        cmd = [sys.executable, str(script_path)] + list(args)
        return self.run_sudo(cmd) 