"""
Host Manager Module

Manages a collection of remote hosts and their configurations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig

logger = logging.getLogger(__name__)


@dataclass
class Host:
    """Represents a remote host configuration."""
    
    name: str
    hostname: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    tags: Optional[List[str]] = None
    description: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_connection_config(self) -> ConnectionConfig:
        """Convert Host to ConnectionConfig."""
        return ConnectionConfig(
            hostname=self.hostname,
            username=self.username,
            port=self.port,
            password=self.password,
            key_filename=self.key_filename
        )
    
    def to_dict(self) -> Dict:
        """Convert Host to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Host":
        """Create Host from dictionary."""
        return cls(**data)


class HostManager:
    """
    Manages a collection of remote hosts.
    
    Provides functionality to add, remove, and manage host configurations
    with persistence to JSON files.
    
    Example:
        >>> manager = HostManager()
        >>> manager.add_host(Host(
        ...     name="web-server",
        ...     hostname="192.168.1.100",
        ...     username="admin",
        ...     key_filename="~/.ssh/id_rsa"
        ... ))
        >>> manager.save_to_file("hosts.json")
    """
    
    def __init__(self, hosts_file: Optional[str] = None):
        """
        Initialize HostManager.
        
        Args:
            hosts_file: Path to JSON file for persistent storage
        """
        self.hosts: Dict[str, Host] = {}
        self.hosts_file = hosts_file
        
        if hosts_file and Path(hosts_file).exists():
            self.load_from_file(hosts_file)
    
    def add_host(self, host: Host) -> None:
        """
        Add a host to the manager.
        
        Args:
            host: Host object to add
            
        Raises:
            ValueError: If host with same name already exists
        """
        if host.name in self.hosts:
            raise ValueError(f"Host '{host.name}' already exists")
        
        self.hosts[host.name] = host
        logger.info(f"Added host: {host.name}")
    
    def remove_host(self, name: str) -> None:
        """
        Remove a host from the manager.
        
        Args:
            name: Name of the host to remove
            
        Raises:
            KeyError: If host not found
        """
        if name not in self.hosts:
            raise KeyError(f"Host '{name}' not found")
        
        del self.hosts[name]
        logger.info(f"Removed host: {name}")
    
    def get_host(self, name: str) -> Host:
        """
        Get a host by name.
        
        Args:
            name: Name of the host
            
        Returns:
            Host object
            
        Raises:
            KeyError: If host not found
        """
        if name not in self.hosts:
            raise KeyError(f"Host '{name}' not found")
        return self.hosts[name]
    
    def list_hosts(self, tag: Optional[str] = None) -> List[Host]:
        """
        List all hosts, optionally filtered by tag.
        
        Args:
            tag: Optional tag to filter by
            
        Returns:
            List of Host objects
        """
        hosts = list(self.hosts.values())
        if tag:
            hosts = [h for h in hosts if h.tags and tag in h.tags]
        return hosts
    
    def list_tags(self) -> List[str]:
        """Get a list of all unique tags."""
        tags = set()
        for host in self.hosts.values():
            if host.tags:
                tags.update(host.tags)
        return sorted(list(tags))
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save hosts to JSON file.
        
        Args:
            filepath: Path to output file
        """
        data = {name: host.to_dict() for name, host in self.hosts.items()}
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.hosts)} hosts to {filepath}")
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load hosts from JSON file.
        
        Args:
            filepath: Path to input file
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Hosts file not found: {filepath}")
            return
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.hosts = {
            name: Host.from_dict(host_data) 
            for name, host_data in data.items()
        }
        
        logger.info(f"Loaded {len(self.hosts)} hosts from {filepath}")
    
    def connect_to_host(self, name: str) -> SSHClient:
        """
        Create an SSH connection to a host.
        
        Args:
            name: Name of the host to connect to
            
        Returns:
            Connected SSHClient instance
        """
        host = self.get_host(name)
        config = host.to_connection_config()
        client = SSHClient(config)
        return client.connect()
    
    def test_connection(self, name: str) -> bool:
        """
        Test connection to a host.
        
        Args:
            name: Name of the host to test
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.connect_to_host(name) as client:
                return client.is_connected()
        except Exception as e:
            logger.error(f"Connection test failed for {name}: {e}")
            return False
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test connections to all hosts.
        
        Returns:
            Dictionary mapping host names to connection status
        """
        results = {}
        for name in self.hosts:
            results[name] = self.test_connection(name)
        return results
    
    def __len__(self) -> int:
        """Return number of hosts."""
        return len(self.hosts)
    
    def __contains__(self, name: str) -> bool:
        """Check if host exists."""
        return name in self.hosts
