"""
Remote CMD - A Python-based SSH remote server management tool.

This package provides functionality for managing remote servers via SSH,
including connection management, command execution, file transfer, and more.

Author: Vae-Scrooge
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Vae-Scrooge"
__license__ = "MIT"

from remote_cmd.core.ssh_client import SSHClient
from remote_cmd.core.host_manager import HostManager

__all__ = ["SSHClient", "HostManager"]
