"""
SSH Client Module

Provides a high-level interface for SSH connections and operations.
"""

import paramiko
import socket
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from remote_cmd.utils.exceptions import SSHConnectionError, SSHCommandError, SSHFileTransferError

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for SSH connection."""
    
    hostname: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30
    compress: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.password and not self.key_filename:
            raise ValueError("Either password or key_filename must be provided")


class SSHClient:
    """
    A high-level SSH client for remote server management.
    
    This class provides methods for connecting to remote servers, executing commands,
    transferring files, and managing SSH sessions.
    
    Example:
        >>> config = ConnectionConfig(
        ...     hostname="example.com",
        ...     username="admin",
        ...     key_filename="~/.ssh/id_rsa"
        ... )
        >>> with SSHClient(config) as client:
        ...     result = client.execute("ls -la")
        ...     print(result.stdout)
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize SSH client with connection configuration.
        
        Args:
            config: ConnectionConfig object containing connection parameters
        """
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        
    def connect(self) -> "SSHClient":
        """
        Establish SSH connection to the remote server.
        
        Returns:
            self for method chaining
            
        Raises:
            SSHConnectionError: If connection fails
        """
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": self.config.hostname,
                "port": self.config.port,
                "username": self.config.username,
                "timeout": self.config.timeout,
                "compress": self.config.compress,
            }
            
            if self.config.password:
                connect_kwargs["password"] = self.config.password
            elif self.config.key_filename:
                key_path = Path(self.config.key_filename).expanduser()
                if not key_path.exists():
                    raise SSHConnectionError(f"SSH key not found: {key_path}")
                connect_kwargs["key_filename"] = str(key_path)
            
            logger.info(f"Connecting to {self.config.hostname}:{self.config.port}")
            self._client.connect(**connect_kwargs)
            logger.info(f"Successfully connected to {self.config.hostname}")
            
            return self
            
        except paramiko.AuthenticationException as e:
            raise SSHConnectionError(f"Authentication failed: {e}")
        except socket.timeout:
            raise SSHConnectionError(f"Connection timeout to {self.config.hostname}")
        except socket.gaierror as e:
            raise SSHConnectionError(f"Host not found: {self.config.hostname}")
        except Exception as e:
            raise SSHConnectionError(f"Connection error: {e}")
    
    def disconnect(self):
        """Close SSH connection and cleanup resources."""
        if self._sftp:
            try:
                self._sftp.close()
                logger.debug("SFTP connection closed")
            except Exception as e:
                logger.warning(f"Error closing SFTP: {e}")
            self._sftp = None
            
        if self._client:
            try:
                self._client.close()
                logger.debug("SSH connection closed")
            except Exception as e:
                logger.warning(f"Error closing SSH: {e}")
            self._client = None
    
    def __enter__(self) -> "SSHClient":
        """Context manager entry."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def execute(
        self, 
        command: str, 
        timeout: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> "CommandResult":
        """
        Execute a command on the remote server.
        
        Args:
            command: The command to execute
            timeout: Command timeout in seconds
            environment: Environment variables to set
            
        Returns:
            CommandResult object containing stdout, stderr, and return code
            
        Raises:
            SSHCommandError: If command execution fails
            SSHConnectionError: If not connected
        """
        if not self._client:
            raise SSHConnectionError("Not connected. Call connect() first.")
        
        try:
            logger.debug(f"Executing command: {command}")
            
            # Build environment string if provided
            env_str = ""
            if environment:
                env_vars = [f"export {k}={v}" for k, v in environment.items()]
                env_str = "; ".join(env_vars) + "; "
            
            full_command = f"{env_str}cd ~ && {command}"
            
            stdin, stdout, stderr = self._client.exec_command(
                full_command, 
                timeout=timeout
            )
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode("utf-8", errors="replace")
            stderr_data = stderr.read().decode("utf-8", errors="replace")
            
            result = CommandResult(
                command=command,
                stdout=stdout_data,
                stderr=stderr_data,
                exit_code=exit_code
            )
            
            logger.debug(f"Command completed with exit code: {exit_code}")
            return result
            
        except Exception as e:
            raise SSHCommandError(f"Failed to execute command '{command}': {e}")
    
    def execute_sudo(
        self, 
        command: str, 
        password: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> "CommandResult":
        """
        Execute a command with sudo privileges.
        
        Args:
            command: The command to execute
            password: Sudo password (if required)
            timeout: Command timeout
            
        Returns:
            CommandResult object
        """
        if password:
            # Use sudo with password
            full_command = f"echo '{password}' | sudo -S {command}"
        else:
            # Assume passwordless sudo
            full_command = f"sudo {command}"
        
        return self.execute(full_command, timeout)
    
    def upload_file(
        self, 
        local_path: str, 
        remote_path: str
    ) -> None:
        """
        Upload a file to the remote server.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path on remote server
            
        Raises:
            SSHFileTransferError: If transfer fails
        """
        if not self._client:
            raise SSHConnectionError("Not connected. Call connect() first.")
        
        try:
            if not self._sftp:
                self._sftp = self._client.open_sftp()
            
            local_file = Path(local_path)
            if not local_file.exists():
                raise SSHFileTransferError(f"Local file not found: {local_path}")
            
            logger.info(f"Uploading {local_path} -> {remote_path}")
            self._sftp.put(str(local_file), remote_path)
            logger.info("Upload completed")
            
        except Exception as e:
            raise SSHFileTransferError(f"Failed to upload file: {e}")
    
    def download_file(
        self, 
        remote_path: str, 
        local_path: str
    ) -> None:
        """
        Download a file from the remote server.
        
        Args:
            remote_path: Path to remote file
            local_path: Destination path on local machine
            
        Raises:
            SSHFileTransferError: If transfer fails
        """
        if not self._client:
            raise SSHConnectionError("Not connected. Call connect() first.")
        
        try:
            if not self._sftp:
                self._sftp = self._client.open_sftp()
            
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading {remote_path} -> {local_path}")
            self._sftp.get(remote_path, str(local_file))
            logger.info("Download completed")
            
        except Exception as e:
            raise SSHFileTransferError(f"Failed to download file: {e}")
    
    def list_remote_directory(self, remote_path: str = ".") -> List[Dict[str, Any]]:
        """
        List contents of a remote directory.
        
        Args:
            remote_path: Path to remote directory
            
        Returns:
            List of file/directory information dictionaries
        """
        if not self._client:
            raise SSHConnectionError("Not connected. Call connect() first.")
        
        try:
            if not self._sftp:
                self._sftp = self._client.open_sftp()
            
            entries = []
            for entry in self._sftp.listdir_attr(remote_path):
                mode = entry.st_mode if entry.st_mode is not None else 0
                entries.append({
                    "name": entry.filename,
                    "size": entry.st_size,
                    "mode": oct(mode)[-3:] if mode else "000",
                    "mtime": entry.st_mtime,
                    "is_dir": mode & 0o40000 == 0o40000 if mode else False
                })
            
            return entries
            
        except Exception as e:
            raise SSHFileTransferError(f"Failed to list directory: {e}")
    
    def is_connected(self) -> bool:
        """Check if SSH connection is active."""
        if not self._client:
            return False
        try:
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()
        except:
            return False


@dataclass
class CommandResult:
    """Result of a command execution."""
    
    command: str
    stdout: str
    stderr: str
    exit_code: int
    
    @property
    def success(self) -> bool:
        """Check if command executed successfully (exit code 0)."""
        return self.exit_code == 0
    
    def __str__(self) -> str:
        """String representation of command result."""
        status = "✓" if self.success else "✗"
        return f"{status} [{self.exit_code}] {self.command}"
