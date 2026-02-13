"""
Custom Exceptions

Defines exception hierarchy for the remote_cmd package.
"""


class RemoteCmdError(Exception):
    """Base exception for all remote_cmd errors."""
    pass


class SSHError(RemoteCmdError):
    """Base exception for SSH-related errors."""
    pass


class SSHConnectionError(SSHError):
    """Raised when SSH connection fails."""
    pass


class SSHCommandError(SSHError):
    """Raised when command execution fails."""
    pass


class SSHFileTransferError(SSHError):
    """Raised when file transfer fails."""
    pass


class ConfigError(RemoteCmdError):
    """Raised when configuration is invalid."""
    pass


class ValidationError(RemoteCmdError):
    """Raised when input validation fails."""
    pass
