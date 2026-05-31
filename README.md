# Remote CMD — SSH Server Management Without the Overhead

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/remote_cmd_manager)](https://pypi.org/project/remote_cmd_manager/)
[![PyPI downloads](https://img.shields.io/pypi/dm/remote_cmd_manager)](https://pypi.org/project/remote_cmd_manager/)
[![CI](https://github.com/Vae-Scrooge/remote-cmd/workflows/CI/badge.svg)](https://github.com/Vae-Scrooge/remote-cmd/actions)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

```bash
pip install remote_cmd_manager
```

[Quick Start](#quick-start) · [Use Cases](#use-cases) · [Python API](#python-api) · [Docs](./docs) · [Contributing](./CONTRIBUTING.md)

</div>

Ascii-cast demo:
```
$ remote-cmd host add web-01 192.168.1.10 ubuntu --key ~/.ssh/id_rsa
$ remote-cmd host add db-01 192.168.1.11 ubuntu --key ~/.ssh/id_rsa
$ remote-cmd batch-run -t production "df -h /"
  ✓ web-01  → Disk: 32G/100G (32%)
  ✓ db-01   → Disk: 45G/100G (45%)
```

Remote CMD is a lightweight Python CLI + API for managing servers over SSH. Add hosts, run commands, transfer files, and target groups by tags — no Ansible DSL or shell loops required.

---

## Why Remote CMD?

| Feature | `remote-cmd` | `ssh` + shell | Ansible | Fabric |
|---|---|---|---|---|
| Host CRUD + tag groups | ✅ Built-in | ❌ Manual | ✅ Inventory | ❌ |
| Batch commands across hosts | ✅ `batch-run` | ❌ Write a loop | ✅ Playbook | ✅ |
| File transfer (upload/download) | ✅ Built-in | ✅ scp | ✅ copy module | ✅ |
| Python API | ✅ `from remote_cmd import ...` | ❌ | ❌ YAML-only | ✅ |
| Zero setup | ✅ pip install → go | ❌ Config SSH | ❌ ansible.cfg | ❌ |
| Learning curve | **Low** | Low | **High** | Medium |

**Use `remote-cmd` when** you need a CLI that works immediately for ad-hoc SSH tasks. **Use Ansible when** you need full configuration management and idempotent playbooks.

---

## Quick Start

```bash
# 1. Install
pip install remote_cmd_manager

# 2. Add a server
remote-cmd host add web-01 192.168.1.10 ubuntu --key ~/.ssh/id_rsa

# 3. Run a command
remote-cmd run web-01 "uptime"

# 4. Run across all production servers
remote-cmd batch-run -t production "df -h /"
```

---

## Use Cases

### System Admin — Check disk across 20 servers in one command
```bash
remote-cmd batch-run -t production "df -h / | tail -1"
# Output:
#   ✓ web-01  → /dev/sda1  32G  12G  19G  40% /
#   ✓ web-02  → /dev/sda1  32G  28G   3G  90% /   ⚠️
#   ✗ db-01   → Connection refused
```

### Deploy — Pull code and restart service
```python
from remote_cmd.core.host_manager import HostManager

manager = HostManager("hosts.json")
for host in manager.list_hosts(tag="staging"):
    with manager.connect_to_host(host.name) as client:
        client.execute("cd /app && git pull")
        client.execute("pip install -r requirements.txt")
        client.execute_sudo("systemctl restart app", password="sudopass")
```

### Incident Response — Check logs across all servers
```bash
remote-cmd batch-run -t web "journalctl -xe -n 50 | grep -i error"
```

### Config Update — Upload and reload nginx across tagged hosts
```bash
# Upload new config
scp nginx.conf user@server:/tmp/nginx.conf  # or use the upload command
remote-cmd run web-01 "sudo cp /tmp/nginx.conf /etc/nginx/nginx.conf && sudo nginx -t && sudo systemctl reload nginx"
```

---

## Python API

Use Remote CMD inside your own scripts and automation:

```python
from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig

config = ConnectionConfig(
    hostname="192.168.1.100",
    username="ubuntu",
    key_filename="~/.ssh/id_rsa",
)

with SSHClient(config) as client:
    # Execute commands
    result = client.execute("uptime")
    print(result.stdout)

    # Transfer files
    client.upload_file("./local.txt", "/remote/path/file.txt")
    client.download_file("/remote/path/file.txt", "./local.txt")

    # List remote directory
    for entry in client.list_remote_directory("/var/log"):
        print(f"{entry['name']}: {entry['size']} bytes")
```

---

## Features

| Category | Details |
|---|---|
| **SSH Auth** | Password + key file + ssh-agent |
| **Commands** | Single, multi-line, sudo with password |
| **File Transfer** | Upload/download via SFTP |
| **Host Management** | CRUD with JSON/YAML persistence |
| **Tag System** | Filter hosts by tag (e.g., `production`, `web`, `db`) |
| **Batch Ops** | Run commands across any host group |
| **Connection Test** | Ping all hosts and report status |
| **Type Safety** | Full type annotations + mypy strict |

---

## Installation

```bash
# From PyPI (recommended)
pip install remote_cmd_manager

# From source
git clone git@github.com:Vae-Scrooge/remote-cmd.git
cd remote-cmd
pip install -e ".[dev]"
```

---

## Documentation

| Document | Contents |
|---|---|
| [API Reference](./docs/API.md) | Full API docs for SSHClient, HostManager, and more |
| [Quickstart Tutorial](./docs/tutorial-quickstart.md) | Step-by-step walkthrough |
| [Advanced Tutorial](./docs/tutorial-advanced.md) | Batch ops, error handling, production patterns |
| [Development Guide](./docs/DEVELOPMENT.md) | Setup dev environment, contributing |
| [Troubleshooting](./docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Changelog](./CHANGELOG.md) | Release history |

---

## Project Status

Beta. The core API is stable. Breaking changes will be communicated via semantic versioning.

**Roadmap:**
- [ ] Async SSH operations (parallel execution)
- [ ] Configuration profiles (AWS, GCP, custom)
- [ ] Output formatting (JSON, table)

---

## License

MIT © Vae-Scrooge

---

<div align="center">

**Star on [GitHub](https://github.com/Vae-Scrooge/remote-cmd) · Report bugs [here](https://github.com/Vae-Scrooge/remote-cmd/issues)**

</div>
