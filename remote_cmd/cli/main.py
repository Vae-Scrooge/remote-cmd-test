import click
import sys
from typing import Optional

from remote_cmd.core.host_manager import HostManager
from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig
from remote_cmd.utils.config import load_config, get_default_config_path


@click.group()
@click.version_option(version="1.0.0")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    help="Path to configuration file"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Remote CMD - SSH Remote Server Management Tool"""
    ctx.ensure_object(dict)
    
    # Initialize configuration
    config_path = config or get_default_config_path()
    ctx.obj["config"] = load_config(config_path)
    ctx.obj["verbose"] = verbose
    
    if verbose:
        click.echo(f"Using config: {config_path}")


@cli.group()
def host():
    """Manage remote hosts"""
    pass


@host.command("add")
@click.argument("name")
@click.argument("hostname")
@click.argument("username")
@click.option("--port", "-p", default=22, help="SSH port")
@click.option("--password", "-P", help="Password authentication")
@click.option("--key", "-k", help="SSH private key file")
@click.option("--tag", "-t", multiple=True, help="Host tags")
@click.option("--description", "-d", help="Host description")
@click.pass_context
def host_add(ctx, name, hostname, username, port, password, key, tag, description):
    """Add a new host"""
    manager = HostManager()
    
    from remote_cmd.core.host_manager import Host
    
    host = Host(
        name=name,
        hostname=hostname,
        username=username,
        port=port,
        password=password,
        key_filename=key,
        tags=list(tag),
        description=description or ""
    )
    
    try:
        manager.add_host(host)
        manager.save_to_file(ctx.obj["config"].get("hosts_file", "hosts.json"))
        click.echo(f"✓ Host '{name}' added successfully")
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@host.command("list")
@click.option("--tag", "-t", help="Filter by tag")
@click.pass_context
def host_list(ctx, tag):
    """List all hosts"""
    manager = HostManager(ctx.obj["config"].get("hosts_file", "hosts.json"))
    
    hosts = manager.list_hosts(tag=tag)
    
    if not hosts:
        click.echo("No hosts found")
        return
    
    click.echo(f"\n{'Name':<20} {'Hostname':<25} {'Username':<15} {'Tags':<20}")
    click.echo("-" * 80)
    
    for host in hosts:
        tags = ", ".join(host.tags) if host.tags else "-"
        click.echo(f"{host.name:<20} {host.hostname:<25} {host.username:<15} {tags:<20}")
    
    click.echo()


@host.command("remove")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to remove this host?")
@click.pass_context
def host_remove(ctx, name):
    """Remove a host"""
    manager = HostManager(ctx.obj["config"].get("hosts_file", "hosts.json"))
    
    try:
        manager.remove_host(name)
        manager.save_to_file(ctx.obj["config"].get("hosts_file", "hosts.json"))
        click.echo(f"✓ Host '{name}' removed successfully")
    except KeyError as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@host.command("test")
@click.argument("name")
@click.pass_context
def host_test(ctx, name):
    """Test connection to a host"""
    manager = HostManager(ctx.obj["config"].get("hosts_file", "hosts.json"))
    
    click.echo(f"Testing connection to '{name}'...")
    
    if manager.test_connection(name):
        click.echo(f"✓ Connection to '{name}' successful")
    else:
        click.echo(f"✗ Connection to '{name}' failed", err=True)
        sys.exit(1)


@cli.command()
@click.argument("host_name")
@click.argument("command")
@click.pass_context
def run(ctx, host_name, command):
    """Execute a command on remote host"""
    manager = HostManager(ctx.obj["config"].get("hosts_file", "hosts.json"))
    
    try:
        with manager.connect_to_host(host_name) as client:
            result = client.execute(command)
            
            if result.stdout:
                click.echo(result.stdout)
            
            if result.stderr:
                click.echo(result.stderr, err=True)
            
            sys.exit(result.exit_code)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("host_name")
@click.argument("local_path")
@click.argument("remote_path")
@click.pass_context
def upload(ctx, host_name, local_path, remote_path):
    """Upload file to remote host"""
    manager = HostManager(ctx.obj["config"].get("hosts_file", "hosts.json"))
    
    try:
        with manager.connect_to_host(host_name) as client:
            client.upload_file(local_path, remote_path)
            click.echo(f"✓ Uploaded {local_path} -> {host_name}:{remote_path}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("host_name")
@click.argument("remote_path")
@click.argument("local_path")
@click.pass_context
def download(ctx, host_name, remote_path, local_path):
    """Download file from remote host"""
    manager = HostManager(ctx.obj["config"].get("hosts_file", "hosts.json"))
    
    try:
        with manager.connect_to_host(host_name) as client:
            client.download_file(remote_path, local_path)
            click.echo(f"✓ Downloaded {host_name}:{remote_path} -> {local_path}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()
